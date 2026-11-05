"""Gera as ilustrações fixas do vídeo a partir de fontes livres guardadas em marca/fontes-ilustracao/:
- ícones por seção (Lucide, licença ISC) em branco, 96 px → marca/icones/<secao>.png
- globo da marca centrado em cada região, com pino âmbar (Natural Earth 1:110m, domínio público) → marca/mapas/<regiao>.png

Rode uma vez quando mudar seções ou regiões:  pip install cairosvg numpy pillow && python marca/gerar_ilustracoes.py
Os PNGs ficam no repositório; o pipeline diário não depende de cairosvg."""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
from boletim import marca  # noqa: E402

FONTES = RAIZ / "marca" / "fontes-ilustracao"
ICONE_DA_SECAO = {
    "destaques": "newspaper", "numeros": "chart-line", "politica": "landmark", "economia": "trending-up",
    "seguros": "umbrella", "clima": "leaf", "tecnologia": "cpu", "ia": "brain-circuit", "saude": "heart-pulse",
    "cultura": "palette", "checagem": "search-check", "encerramento": "calendar-days",
}
# centro de cada globo (longitude, latitude) e se leva pino
REGIOES = {
    "brasil": (-52, -12, True), "latam": (-66, -18, True), "eua": (-98, 39, True), "europa": (12, 49, True),
    "asia": (104, 30, True), "global": (-20, 18, False),
}


def _rgb(hexa: str) -> tuple[int, int, int]:
    h = hexa.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def icones(destino: Path, tamanho: int = 96) -> None:
    import cairosvg
    destino.mkdir(parents=True, exist_ok=True)
    for secao, nome in ICONE_DA_SECAO.items():
        svg = (FONTES / "icones" / f"{nome}.svg").read_text().replace("currentColor", "#FFFFFF")
        cairosvg.svg2png(bytestring=svg.encode(), write_to=str(destino / f"{secao}.png"),
                         output_width=tamanho, output_height=tamanho)


def _mascara_terra(largura: int = 2048) -> np.ndarray:
    """Terra rasterizada em projeção equirretangular (True = terra)."""
    alt = largura // 2
    img = Image.new("L", (largura, alt), 0)
    d = ImageDraw.Draw(img)
    geo = json.loads((FONTES / "ne_110m_land.geojson").read_text())
    for f in geo["features"]:
        g = f["geometry"]
        polis = [g["coordinates"]] if g["type"] == "Polygon" else g["coordinates"]
        for p in polis:
            anel = [((lon + 180) / 360 * largura, (90 - lat) / 180 * alt) for lon, lat in p[0]]
            d.polygon(anel, fill=255)
    return np.array(img) > 0


def globo(lon0: float, lat0: float, pino: bool, terra: np.ndarray, lado: int = 360) -> Image.Image:
    esc = 3  # supersampling
    n = lado * esc
    r = n * 0.37
    cx = cy = n / 2
    y, x = np.mgrid[0:n, 0:n]
    xs, ys = (x - cx) / r, -(y - cy) / r
    rho = np.sqrt(xs ** 2 + ys ** 2)
    dentro = rho <= 1
    c = np.arcsin(np.clip(rho, 0, 1))
    phi0, lam0 = math.radians(lat0), math.radians(lon0)
    with np.errstate(invalid="ignore", divide="ignore"):
        lat = np.arcsin(np.cos(c) * math.sin(phi0) + np.where(rho > 0, ys * np.sin(c) * math.cos(phi0) / rho, 0))
        lon = lam0 + np.arctan2(xs * np.sin(c), rho * np.cos(c) * math.cos(phi0) - ys * np.sin(c) * math.sin(phi0))
    lon = (np.degrees(lon) + 180) % 360
    lat = np.degrees(lat)
    h, w = terra.shape
    iy = np.clip(((90 - lat) / 180 * h).astype(int), 0, h - 1)
    ix = np.clip((lon / 360 * w).astype(int), 0, w - 1)
    eh_terra = dentro & terra[iy, ix]
    # luz suave vinda do alto à esquerda, para dar volume
    luz = np.clip(0.75 + 0.25 * (-xs * 0.5 + ys * 0.6) * np.sqrt(np.clip(1 - rho ** 2, 0, 1)), 0.55, 1.0)
    oceano, solo = np.array(_rgb("#15335C")), np.array(_rgb("#3F6FA8"))
    rgb = np.where(eh_terra[..., None], solo, oceano) * luz[..., None]
    alfa = np.where(dentro, 255, 0)
    img = Image.fromarray(np.dstack([rgb, alfa]).astype(np.uint8), "RGBA")
    d = ImageDraw.Draw(img)
    # órbita âmbar da marca, aberta em cima como no símbolo, terminando num "sol" às 6 horas
    ro = r * 1.16
    caixa = [cx - ro, cy - ro, cx + ro, cy + ro]
    d.arc(caixa, start=180 + 12, end=360 + 90 - 8, fill=marca.AMBAR, width=int(7 * esc))
    d.ellipse([cx - 13 * esc, cy + ro - 13 * esc, cx + 13 * esc, cy + ro + 13 * esc], fill=marca.AMBAR)
    if pino:  # o centro da projeção é a região: pino âmbar com halo
        halo = Image.new("RGBA", img.size, (0, 0, 0, 0))
        ImageDraw.Draw(halo).ellipse([cx - 34 * esc, cy - 34 * esc, cx + 34 * esc, cy + 34 * esc],
                                     fill=(*_rgb(marca.AMBAR), 110))
        img = Image.alpha_composite(img, halo.filter(ImageFilter.GaussianBlur(10 * esc)))
        d = ImageDraw.Draw(img)
        d.ellipse([cx - 11 * esc, cy - 11 * esc, cx + 11 * esc, cy + 11 * esc], fill=marca.AMBAR,
                  outline=marca.AZUL_NOITE, width=3 * esc)
    return img.resize((lado, lado), Image.LANCZOS)


def mapas(destino: Path) -> None:
    destino.mkdir(parents=True, exist_ok=True)
    terra = _mascara_terra()
    for reg, (lon, lat, pino) in REGIOES.items():
        globo(lon, lat, pino, terra).save(destino / f"{reg}.png")


if __name__ == "__main__":
    icones(RAIZ / "marca" / "icones")
    mapas(RAIZ / "marca" / "mapas")
    print("ok")
