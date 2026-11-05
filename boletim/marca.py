"""Identidade visual do "Brasil e Mundo Hoje": paleta, tipografia e símbolo (SVG gerado em código).

Conceito do símbolo: um globo dentro de uma órbita âmbar que funciona como mostrador de relógio e termina num
"sol" na posição das 6 horas, o horário do boletim. Guia completo em marca/GUIA.md."""
from __future__ import annotations

from pathlib import Path

AZUL_NOITE = "#0B1F3A"   # base: fundos, cabeçalhos
AZUL = "#1F4E8C"         # apoio
AMBAR = "#F5A623"        # destaque: o amanhecer das 6h (órbita, barras, links em fundo escuro)
VERDE = "#00A86B"        # Brasil: detalhes pontuais
PAPEL = "#F7F4EE"        # fundo claro do site
TINTA = "#14213D"        # texto sobre fundo claro
CINZA = "#5B6675"        # texto secundário

FONTE_SITE = "'Inter', system-ui, -apple-system, 'Segoe UI', Roboto, sans-serif"
_INTER = Path("/usr/share/fonts/opentype/inter")
_DEJAVU = Path("/usr/share/fonts/truetype/dejavu")


def fonte(peso: str = "Regular") -> str:
    """Arquivo da fonte Inter (pacote fonts-inter) para o ffmpeg; DejaVu se a Inter não estiver instalada."""
    p = _INTER / f"Inter-{peso}.otf"
    if p.exists():
        return str(p)
    return str(_DEJAVU / ("DejaVuSans-Bold.ttf" if peso in ("Bold", "ExtraBold", "SemiBold", "Black")
                          else "DejaVuSans.ttf"))


def fonte_manim() -> str:
    return "Inter" if _INTER.exists() else "DejaVu Sans"


def simbolo_svg(tamanho: int = 512, fundo: bool = True) -> str:
    """Símbolo quadrado (512×512 em viewBox)."""
    bg = f'<rect width="512" height="512" rx="112" fill="{AZUL_NOITE}"/>' if fundo else ""
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512" width="{tamanho}" height="{tamanho}" '
        f'role="img" aria-label="Brasil e Mundo Hoje">{bg}'
        # órbita/relógio: das 9h, passando por 12h e 3h, até perto das 6h
        f'<path d="M78 256 A178 178 0 1 1 293 430" fill="none" stroke="{AMBAR}" stroke-width="22" '
        'stroke-linecap="round"/>'
        f'<circle cx="256" cy="434" r="30" fill="{AMBAR}"/>'
        # globo
        '<g fill="none" stroke="#FFFFFF" stroke-linecap="round">'
        '<circle cx="256" cy="256" r="118" stroke-width="18"/>'
        '<ellipse cx="256" cy="256" rx="52" ry="118" stroke-width="12"/>'
        '<line x1="138" y1="256" x2="374" y2="256" stroke-width="12"/>'
        '<path d="M160 190 Q256 214 352 190 M160 322 Q256 298 352 322" stroke-width="10" stroke-opacity=".8"/>'
        '</g>'
        f'<circle cx="218" cy="292" r="14" fill="{VERDE}"/>'
        '</svg>')


def logo_svg(claro: bool = False) -> str:
    """Logotipo horizontal: símbolo + nome. claro=True para fundo claro."""
    cor = TINTA if claro else "#FFFFFF"
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1240 300" role="img" aria-label="Brasil e Mundo Hoje">'
        f'<g transform="translate(10 10) scale(.5469)">{simbolo_svg(512)[simbolo_svg(512).index(">") + 1:-6]}</g>'
        f'<text x="330" y="140" font-family="Inter, sans-serif" font-weight="800" font-size="92" '
        f'letter-spacing="-1" fill="{cor}">BRASIL E MUNDO</text>'
        f'<text x="330" y="245" font-family="Inter, sans-serif" font-weight="800" font-size="92" '
        f'letter-spacing="-1" fill="{AMBAR}">HOJE</text>'
        f'<text x="610" y="238" font-family="Inter, sans-serif" font-weight="600" font-size="46" '
        f'fill="{cor}" fill-opacity=".75">todo dia às 6h</text>'
        '</svg>')
