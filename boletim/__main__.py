"""Executa o pipeline completo: coleta → classificação → redação → áudio → vídeo → publicação.

Uso:
  python -m boletim                      # edição de hoje
  python -m boletim --fixture tests/fixtures/noticias.json --sem-video
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
from datetime import datetime
from pathlib import Path

from . import audio, classificador, coletor, estado as memoria, publicador, video
from .redator import Redator
from .util import RAIZ, agora, carregar_yaml, data_extenso, log


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Boletim Brasil e Mundo Hoje")
    ap.add_argument("--fixture", help="JSON de notícias já coletadas (pula a coleta)")
    ap.add_argument("--data", help="Data da edição AAAA-MM-DD (padrão: hoje em Brasília)")
    ap.add_argument("--sem-audio", action="store_true")
    ap.add_argument("--sem-video", action="store_true")
    ap.add_argument("--midia", default=str(RAIZ / "_midia"), help="Pasta para MP3/MP4 (fora do git)")
    a = ap.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    cfg = carregar_yaml("config.yaml")
    fontes = carregar_yaml("fontes.yaml")["fontes"]
    hoje = datetime.fromisoformat(a.data).replace(tzinfo=agora(cfg["fuso_horario"]).tzinfo) if a.data \
        else agora(cfg["fuso_horario"])
    data_iso, data_ext = hoje.strftime("%Y-%m-%d"), data_extenso(hoje)
    pasta = RAIZ / "edicoes" / hoje.strftime("%Y/%m/%d")
    pasta.mkdir(parents=True, exist_ok=True)
    midia = Path(a.midia)
    midia.mkdir(parents=True, exist_ok=True)
    trab = midia / "_trabalho"
    trab.mkdir(exist_ok=True)

    est = memoria.carregar()
    if est.get("ppm_medido"):
        cfg["palavras_por_minuto"] = est["ppm_medido"]
        log.info("Ritmo de locução calibrado: %.0f palavras/min", est["ppm_medido"])

    # 1. Coleta (fontes pausadas por falhas repetidas são re-testadas semanalmente)
    saude: dict = {}
    if a.fixture:
        noticias = coletor.carregar(Path(a.fixture))
    else:
        ativas = [f for f in fontes if memoria.fonte_ativa(est, f["nome"], hoje.date())]
        noticias = coletor.coletar(ativas, cfg["janela_horas"], cfg["max_itens_por_fonte"], saude)
        for nome, (ok, qtd) in saude.items():
            memoria.registrar_fonte(est, nome, ok, qtd, hoje.date())
    if len(noticias) < 10:
        log.error("Poucas notícias coletadas (%d). Abortando para não publicar edição vazia.", len(noticias))
        return 2
    coletor.salvar(noticias, pasta / "noticias.json")

    # 2. Classificação e 3. Redação
    grupos = classificador.agrupar(noticias, [s["id"] for s in cfg["secoes"]], cfg["max_itens_por_secao"])
    segmentos = Redator(cfg).escrever(data_ext, grupos)
    (pasta / "roteiro.json").write_text(json.dumps(segmentos, ensure_ascii=False, indent=1), encoding="utf-8")
    palavras = sum(len(s["roteiro"].split()) for s in segmentos)
    log.info("Roteiro com %d palavras (~%.0f min)", palavras, palavras / cfg["palavras_por_minuto"])

    # 4. Áudio por seção (vinheta + locução) e legendas
    dur_total, partes_audio, srt_total, t0, dur_fala = 0.0, [], [], 0.0, 0.0
    gerar_audio = cfg.get("gerar_audio") and not a.sem_audio
    gerar_video = gerar_audio and cfg.get("gerar_video") and not a.sem_video
    cfg["gerar_audio"], cfg["gerar_video"] = gerar_audio, gerar_video
    partes_video = []
    if gerar_audio:
        vin = trab / "vinheta.mp3"
        audio.vinheta(vin)
        dvin = audio.duracao(vin)
        for i, s in enumerate(segmentos):
            voz = cfg["voz_tts"] if i % 2 == 0 else cfg.get("voz_tts_secundaria", cfg["voz_tts"])
            fala = trab / f"{i:02d}_{s['id']}_fala.mp3"
            cues = audio.sintetizar(s["roteiro"], voz, fala, cfg["palavras_por_minuto"])
            dur_fala += audio.duracao(fala)
            seg_mp3 = trab / f"{i:02d}_{s['id']}.mp3"
            lista = trab / "_l.txt"
            lista.write_text(f"file '{vin.resolve()}'\nfile '{fala.resolve()}'\n")
            audio._ff("-f", "concat", "-safe", "0", "-i", str(lista), "-ar", "44100", "-ac", "1", "-b:a", "96k",
                      str(seg_mp3))
            d = audio.duracao(seg_mp3)
            cues_seg = [(a_ + dvin, b_ + dvin, t) for a_, b_, t in cues]
            srt = trab / f"{i:02d}_{s['id']}.srt"
            audio.escrever_srt(cues_seg, srt)
            srt_total += [(a_ + t0, b_ + t0, t) for a_, b_, t in cues_seg]
            partes_audio.append(seg_mp3)
            if gerar_video:
                mp4 = trab / f"{i:02d}_{s['id']}.mp4"
                video.render_segmento(s, seg_mp3, srt, d, mp4, cfg["titulo"], data_ext, cfg["resolucao_video"])
                partes_video.append(mp4)
            t0 += d
        dur_total = t0
        mp3_final = midia / f"boletim-{data_iso}.mp3"
        audio.montar_podcast(partes_audio, mp3_final, cfg["titulo"], data_ext)
        audio.escrever_srt(srt_total, pasta / "legendas.srt")
        if gerar_video:
            video.concatenar(partes_video, midia / f"boletim-{data_iso}.mp4")
        log.info("Duração total: %.1f min", dur_total / 60)
        if not a.fixture and dur_fala > 60:
            log.info("Ritmo medido da voz: %.0f palavras/min", memoria.registrar_ritmo(est, palavras, dur_fala))
        if not 30 <= dur_total / 60 <= 45:
            log.warning("Duração fora da meta de 30–45 min. Ajuste duracao_alvo_min ou o número de fontes.")

    # 5. Publicação
    dur_min = round(dur_total / 60, 1) if dur_total else None
    (pasta / "boletim.md").write_text(publicador.markdown(cfg, data_ext, data_iso, segmentos, dur_min), encoding="utf-8")
    (pasta / "index.html").write_text(publicador.html_edicao(cfg, data_ext, data_iso, segmentos), encoding="utf-8")
    manchetes = " | ".join(i["titulo"] for i in (segmentos[0].get("itens") or [])[:5]) if segmentos else ""
    mp3 = midia / f"boletim-{data_iso}.mp3"
    (pasta / "meta.json").write_text(json.dumps({
        "data": data_iso, "data_extenso": data_ext, "publicado": hoje.replace(hour=6, minute=0, second=0).isoformat(),
        "duracao_min": dur_min, "palavras": palavras, "noticias_coletadas": len(noticias),
        "manchetes": manchetes, "bytes_mp3": mp3.stat().st_size if mp3.exists() else 0,
    }, ensure_ascii=False, indent=1), encoding="utf-8")
    publicador.escrever_readme_ultima(cfg, data_ext, data_iso)
    (pasta / "relatorio.json").write_text(json.dumps({
        "fontes_ok": sorted(n for n, (ok, _) in saude.items() if ok),
        "fontes_com_falha": sorted(n for n, (ok, _) in saude.items() if not ok),
        "fontes_pausadas": memoria.pausadas(est), "duracao_min": dur_min,
        "meta_duracao_ok": bool(dur_min and 30 <= dur_min <= 45), "palavras": palavras,
        "ppm_usado": cfg["palavras_por_minuto"], "provedor_ia": cfg.get("provedor_ia"),
        "secoes": {s["id"]: len(s.get("itens") or []) for s in segmentos},
    }, ensure_ascii=False, indent=1), encoding="utf-8")
    if not a.fixture:
        memoria.salvar(est)
    log.info("Edição gerada em %s", pasta)
    return 0


if __name__ == "__main__":
    sys.exit(main())
