"""Monta o site estático (GitHub Pages) em _site/: índice, feed do podcast e páginas das edições."""
import shutil
import sys
from pathlib import Path

import json

from .publicador import atualizar_indice, html_edicao
from .util import RAIZ, carregar_yaml


def main(destino: str = "_site") -> None:
    cfg = carregar_yaml("config.yaml")
    site = RAIZ / destino
    if site.exists():
        shutil.rmtree(site)
    for pagina in (RAIZ / "edicoes").glob("*/*/*/index.html"):
        alvo = site / pagina.relative_to(RAIZ)
        alvo.parent.mkdir(parents=True, exist_ok=True)
        roteiro, meta = pagina.parent / "roteiro.json", pagina.parent / "meta.json"
        if roteiro.exists() and meta.exists():  # refaz a página com o visual atual da marca
            m = json.loads(meta.read_text(encoding="utf-8"))
            segs = json.loads(roteiro.read_text(encoding="utf-8"))
            alvo.write_text(html_edicao({**cfg, "gerar_audio": True, "gerar_video": True}, m["data_extenso"],
                                        m["data"], segs), encoding="utf-8")
        else:
            shutil.copy2(pagina, alvo)
        for extra in ("boletim.md", "legendas.srt", "noticias.json"):
            if (pagina.parent / extra).exists():
                shutil.copy2(pagina.parent / extra, alvo.parent / extra)
    atualizar_indice(cfg, RAIZ / "edicoes", site)
    (site / "marca").mkdir(exist_ok=True)
    for arq in (RAIZ / "marca").glob("*.*"):
        if arq.suffix in (".png", ".svg"):
            shutil.copy2(arq, site / "marca" / arq.name)
    (site / ".nojekyll").touch()


if __name__ == "__main__":
    main(*sys.argv[1:])
