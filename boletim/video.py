"""Versão em vídeo: cada seção ganha identidade visual própria (paleta, fundo animado, vinheta),
com manchetes em destaque, forma de onda animada da voz, barra de progresso e, opcionalmente, legendas.
Tudo renderizado com ffmpeg, sem dependências pagas."""
from __future__ import annotations

import subprocess
import textwrap
from pathlib import Path

from . import marca
from .util import RAIZ, log

FONTE = marca.fonte("Regular")
FONTE_M = marca.fonte("Medium")
FONTE_B = marca.fonte("ExtraBold")
SIMBOLO = RAIZ / "marca" / "simbolo-96.png"
AMBAR = marca.AMBAR.lstrip("#")
REGIAO = {"brasil": "BRASIL", "europa": "EUROPA", "eua": "ESTADOS UNIDOS", "asia": "ÁSIA", "global": "MUNDO"}


def _esc(caminho: Path) -> str:
    return str(caminho).replace("\\", "/").replace(":", r"\:").replace("'", r"\'")


def _cor(hexa: str) -> str:
    return "0x" + hexa.lstrip("#")


def _largura(texto: str, tamanho: int) -> int:
    """Largura aproximada do texto em Inter ExtraBold (para posicionar a palavra em âmbar ao lado do nome)."""
    if not texto:
        return 0
    try:
        from PIL import ImageFont
        return int(ImageFont.truetype(FONTE_B, tamanho).getlength(texto + " "))
    except Exception:  # noqa: BLE001
        return int(len(texto + " ") * tamanho * 0.66)


def render_segmento(seg: dict, audio: Path, srt: Path | None, dur: float, destino: Path, titulo: str,
                    data: str, resolucao: str = "1280x720", vinheta: Path | None = None,
                    dur_vinheta: float = 3.0) -> None:
    w, h = map(int, resolucao.split("x"))
    tmp = destino.parent / f"_txt_{seg['id']}"
    tmp.mkdir(exist_ok=True)

    def arq(nome: str, texto: str) -> str:
        p = tmp / nome
        p.write_text(texto, encoding="utf-8")
        return _esc(p)

    c1, c2 = _cor(seg["cor"]), _cor(seg["cor2"])
    filtros = [
        f"gradients=s={w}x{h}:c0={c1}:c1={c2}:c2={c1}:x0=0:y0=0:x1={w}:y1={h}:speed=0.008:r=24:d={dur:.2f}[bg]",
        f"[0:a]asplit[a1][a2]",
        f"[a1]showwaves=s={w - 160}x110:mode=cline:rate=24:colors=white@0.85,format=rgba[wav]",
        f"[bg][wav]overlay=80:{h - 250}:shortest=1[v0]",
    ]
    v = "[v0]"
    nome, _, ultima = titulo.upper().rpartition(" ")  # "BRASIL E MUNDO" em branco, "HOJE" em âmbar
    passos = [
        # cabeçalho da marca: faixa azul-noite, símbolo, nome e fio âmbar
        f"drawbox=x=0:y=0:w=iw:h=78:color={_cor(marca.AZUL_NOITE)}@0.82:t=fill",
        f"drawbox=x=0:y=78:w=iw:h=3:color=0x{AMBAR}:t=fill",
        f"drawtext=fontfile={FONTE_B}:textfile='{arq('marca.txt', nome or titulo.upper())}':x=92:y=25:fontsize=28:"
        "fontcolor=white",
        f"drawtext=fontfile={FONTE_B}:textfile='{arq('marca2.txt', ultima if nome else '')}':x=92+{_largura(nome, 28)}:"
        f"y=25:fontsize=28:fontcolor=0x{AMBAR}",
        f"drawtext=fontfile={FONTE_M}:textfile='{arq('data.txt', data)}':x=w-tw-40:y=30:fontsize=20:fontcolor=white@0.85",
        # cartão de abertura da seção (primeiros 3 s) — substituído pela vinheta Manim quando houver
        "null" if vinheta else f"drawtext=fontfile={FONTE_B}:textfile='{arq('secao.txt', seg['titulo'].upper())}':x=(w-tw)/2:y=(h-th)/2-30:"
        f"fontsize=64:fontcolor=white:alpha='if(lt(t,2.4),1,max(0,1-(t-2.4)/0.6))':enable='lt(t,3)'",
        # rótulo da seção no topo após o cartão
        f"drawbox=x=40:y=104:w=8:h=40:color=0x{AMBAR}:t=fill:enable='gte(t,3)'",
        f"drawtext=fontfile={FONTE_B}:textfile='{arq('secao2.txt', seg['titulo'].upper())}':x=60:y=106:fontsize=30:"
        f"fontcolor=white:enable='gte(t,3)'",
        # barra de progresso
        f"drawbox=x=0:y=ih-6:w='iw*t/{dur:.2f}':h=6:color=0x{AMBAR}:t=fill",
    ]
    itens = seg.get("itens") or []
    if itens:
        janela = max(dur - 3, 1) / len(itens)
        for i, it in enumerate(itens):
            a, b = 3 + i * janela, 3 + (i + 1) * janela
            manchete = textwrap.fill(it.get("titulo", ""), 44)
            meta = f"{REGIAO.get(it.get('regiao', ''), 'MUNDO')}  ·  {', '.join(it.get('fontes', [])[:2])}"
            en = f"enable='between(t,{a:.2f},{b:.2f})'"
            fade = f"alpha='min(1,(t-{a:.2f})/0.5)'"
            passos += [
                f"drawbox=x=40:y=170:w={w - 80}:h=200:color={_cor(marca.AZUL_NOITE)}@0.55:t=fill:{en}",
                f"drawbox=x=40:y=170:w=6:h=200:color=0x{AMBAR}:t=fill:{en}",
                f"drawtext=fontfile={FONTE}:textfile='{arq(f'm{i}.txt', meta)}':x=64:y=188:fontsize=20:"
                f"fontcolor=white@0.8:{fade}:{en}",
                f"drawtext=fontfile={FONTE_B}:textfile='{arq(f't{i}.txt', manchete)}':x=64:y=226:fontsize=38:"
                f"line_spacing=8:fontcolor=white:{fade}:{en}",
            ]
    estilo = ("FontName=Inter,FontSize=15,PrimaryColour=&H00FFFFFF,OutlineColour=&H80000000,"
              "BorderStyle=3,Outline=1,Shadow=0,MarginV=24")
    if srt:  # legendas queimadas no vídeo só se config.yaml → legendas: true
        passos.append(f"subtitles='{_esc(srt)}':force_style='{estilo}'")
    if SIMBOLO.exists():  # símbolo da marca no canto do cabeçalho
        filtros.append(f"movie='{_esc(SIMBOLO)}',scale=54:54,format=rgba[lg]")
        passos.append("null[vlg];[vlg][lg]overlay=24:12")
    if vinheta:
        filtros.append(f"{v}{','.join(passos)}[vtx]")
        filtros.append(f"[1:v]scale={w}:{h},setpts=PTS-STARTPTS,trim=0:{dur_vinheta:.2f}[vin]")
        filtros.append("[vtx][vin]overlay=eof_action=pass[vout]")
    else:
        filtros.append(f"{v}{','.join(passos)}[vout]")

    entradas = ["-i", str(audio)] + (["-i", str(vinheta)] if vinheta else [])
    cmd = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", *entradas,
           "-filter_complex", ";".join(filtros), "-map", "[vout]", "-map", "[a2]",
           "-c:v", "libx264", "-preset", "veryfast", "-crf", "27", "-pix_fmt", "yuv420p", "-r", "24",
           "-c:a", "aac", "-b:a", "96k", "-ar", "44100", "-ac", "1", "-t", f"{dur:.2f}", str(destino)]
    log.info("Renderizando vídeo da seção %s (%.0fs)", seg["id"], dur)
    subprocess.run(cmd, check=True)
    for p in tmp.iterdir():
        p.unlink()
    tmp.rmdir()


def concatenar(partes: list[Path], destino: Path) -> None:
    lista = destino.parent / "_concat_v.txt"
    lista.write_text("".join(f"file '{p.resolve()}'\n" for p in partes), encoding="utf-8")
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-f", "concat", "-safe", "0",
                    "-i", str(lista), "-c", "copy", "-movflags", "+faststart", str(destino)], check=True)
    lista.unlink()
