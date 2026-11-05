"""Renderiza as vinhetas animadas com Manim (gratuito). Se o Manim não estiver disponível,
o vídeo usa o cartão de título simples do ffmpeg."""
from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

from . import marca
from .util import RAIZ, log

CENAS = Path(__file__).with_name("cenas_manim.py")


def disponivel() -> bool:
    return shutil.which("manim") is not None


def render(cena: str, params: dict, destino: Path, resolucao: str = "1280x720") -> Path | None:
    if not disponivel():
        return None
    w, h = resolucao.split("x")
    midia = destino.parent / "_manim"
    env = {**os.environ, "BOLETIM_VINHETA": json.dumps(params, ensure_ascii=False)}
    cmd = ["manim", "render", "-q", "m", "-r", f"{w},{h}", "--fps", "24", "--media_dir", str(midia),
           "--disable_caching", "-o", destino.stem, str(CENAS), cena]
    try:
        subprocess.run(cmd, check=True, env=env, capture_output=True, text=True, timeout=300)
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as e:
        log.warning("Manim falhou na cena %s: %s", cena, getattr(e, "stderr", "")[-500:])
        return None
    gerado = next(midia.rglob(f"{destino.stem}.mp4"), None)
    if gerado:
        shutil.move(str(gerado), destino)
        return destino
    return None


def gerar_todas(segmentos: list[dict], titulo: str, data: str, duracao: float, pasta: Path,
                resolucao: str = "1280x720") -> dict[str, Path]:
    """Gera uma vinheta por segmento: 'Abertura' para o primeiro, 'Transicao' para os demais."""
    saida: dict[str, Path] = {}
    if not disponivel():
        log.info("Manim não instalado: usando cartões de título simples.")
        return saida
    for i, s in enumerate(segmentos):
        cena = "Abertura" if i == 0 else "Transicao"
        params = {"duracao": duracao, "cor": s["cor"], "cor2": s["cor2"], "titulo": titulo if i == 0 else s["titulo"],
                  "data": data, "marca": titulo.upper(), "fonte": marca.fonte_manim(), "ambar": marca.AMBAR,
                  "noite": marca.AZUL_NOITE, "verde": marca.VERDE,
                  "simbolo_png": str(RAIZ / "marca" / "simbolo-512.png")}
        p = render(cena, params, pasta / f"vinheta_{i:02d}_{s['id']}.mp4", resolucao)
        if p:
            saida[s["id"]] = p
    log.info("Vinhetas animadas geradas: %d/%d", len(saida), len(segmentos))
    return saida
