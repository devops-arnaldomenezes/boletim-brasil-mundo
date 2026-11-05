"""Gera as imagens da marca (PNG) a partir dos SVGs de boletim/marca.py. Rodar localmente quando a marca mudar:
    python marca/gerar_imagens.py
Requer Chrome/Chromium (variável CHROME ou "chromium" no PATH) e a fonte Inter instalada (pacote fonts-inter)."""
import os
import subprocess
import sys
import tempfile
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
from boletim import marca  # noqa: E402

CAPA = f"""<html><body style="margin:0;width:3000px;height:3000px;background:{marca.AZUL_NOITE};
display:flex;flex-direction:column;align-items:center;justify-content:center;font-family:Inter,sans-serif">
<div style="width:1500px;height:1500px">{marca.simbolo_svg(1500, fundo=False)}</div>
<div style="color:#fff;font-weight:800;font-size:250px;letter-spacing:-4px;line-height:1;margin-top:40px">BRASIL E MUNDO</div>
<div style="color:{marca.AMBAR};font-weight:800;font-size:250px;letter-spacing:-4px;line-height:1.05">HOJE</div>
<div style="color:#fff;opacity:.8;font-weight:500;font-size:110px;margin-top:70px">Notícias do dia · todo dia às 6h</div>
</body></html>"""


def _png(html: str, destino: Path, w: int, h: int) -> None:
    chrome = os.environ.get("CHROME", "chromium")
    with tempfile.NamedTemporaryFile("w", suffix=".html", delete=False, encoding="utf-8") as f:
        f.write(html)
    subprocess.run([chrome, "--headless", "--no-sandbox", "--hide-scrollbars", "--default-background-color=00000000",
                    f"--window-size={w},{h}", f"--screenshot={destino}", f"file://{f.name}"],
                   check=True, capture_output=True)
    os.unlink(f.name)


def main() -> None:
    for nome, svg, w in (("simbolo-512.png", marca.simbolo_svg(512), 512), ("simbolo-96.png", marca.simbolo_svg(96), 96)):
        _png(f'<html><body style="margin:0;background:transparent">{svg}</body></html>', RAIZ / "marca" / nome, w, w)
    _png(CAPA, RAIZ / "marca" / "capa-podcast.png", 3000, 3000)


if __name__ == "__main__":
    main()
