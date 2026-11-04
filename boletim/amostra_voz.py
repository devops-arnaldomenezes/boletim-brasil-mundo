"""Gera uma amostra curta da locução (vinheta + 2 trechos reais da última edição) com as configurações atuais
de voz, para avaliar mudanças de áudio sem refazer a edição. Uso: python -m boletim.amostra_voz saida.mp3"""
import json
import sys
from pathlib import Path

from . import audio
from .util import RAIZ, carregar_yaml


def main(destino: str = "amostra-voz.mp3", palavras: int = 160) -> None:
    cfg = carregar_yaml("config.yaml")
    roteiro = sorted(RAIZ.glob("edicoes/*/*/*/roteiro.json"))[-1]
    segmentos = json.loads(roteiro.read_text(encoding="utf-8"))[:2]
    trab = Path(destino).resolve().parent / "_amostra"
    trab.mkdir(exist_ok=True)
    vin = trab / "vinheta.mp3"
    audio.vinheta(vin)
    partes = []
    for i, s in enumerate(segmentos):
        texto = " ".join(s["roteiro"].split()[:palavras])
        texto = texto[: texto.rfind(".") + 1] or texto  # termina numa frase completa
        fala = trab / f"{i}.mp3"
        voz = cfg["voz_tts"] if i % 2 == 0 else cfg.get("voz_tts_secundaria", cfg["voz_tts"])
        audio.sintetizar(texto, voz, fala, rate=cfg.get("velocidade_voz", "+0%"),
                         pausa=float(cfg.get("pausa_entre_blocos_s", 0.5)), voz_reserva=cfg.get("voz_tts_reserva"))
        partes += [vin, fala]
    audio.montar_podcast(partes, Path(destino), cfg["titulo"], f"amostra de voz ({roteiro.parent.name})")
    print(f"Amostra gerada a partir de {roteiro}: {destino} ({audio.duracao(Path(destino)):.0f}s)")


if __name__ == "__main__":
    main(*sys.argv[1:])
