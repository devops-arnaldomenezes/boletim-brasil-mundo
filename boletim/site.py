"""Monta o site estático (GitHub Pages) em _site/: índice, feed do podcast e páginas das edições."""
import shutil
import sys
from pathlib import Path

from .publicador import atualizar_indice
from .util import RAIZ, carregar_yaml


def main(destino: str = "_site") -> None:
    cfg = carregar_yaml("config.yaml")
    site = RAIZ / destino
    if site.exists():
        shutil.rmtree(site)
    for pagina in (RAIZ / "edicoes").glob("*/*/*/index.html"):
        alvo = site / pagina.relative_to(RAIZ)
        alvo.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(pagina, alvo)
        for extra in ("boletim.md", "legendas.srt", "noticias.json"):
            if (pagina.parent / extra).exists():
                shutil.copy2(pagina.parent / extra, alvo.parent / extra)
    atualizar_indice(cfg, RAIZ / "edicoes", site)
    (site / ".nojekyll").touch()


if __name__ == "__main__":
    main(*sys.argv[1:])
