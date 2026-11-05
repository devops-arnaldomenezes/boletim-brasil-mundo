"""Diagnóstico de feeds: testa URLs (das fontes ou candidatas) com o agente do boletim e com agente de navegador.

Uso: python scripts/validar_fontes.py [URL ...]   (sem argumentos: testa todas as fontes de config/fontes.yaml)
"""
import sys
from datetime import datetime, timezone

import feedparser
import yaml

AGENTES = {
    "boletim": "BoletimBrasilMundo/1.0 (+https://github.com) feedparser",
    "navegador": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36",
}


def testar(url: str) -> str:
    partes = []
    for nome, ua in AGENTES.items():
        try:
            f = feedparser.parse(url, agent=ua, request_headers={"Accept": "application/rss+xml, application/xml, */*"})
            st = getattr(f, "status", "-")
            if f.entries:
                t = f.entries[0].get("published_parsed") or f.entries[0].get("updated_parsed")
                data = datetime(*t[:6], tzinfo=timezone.utc).date().isoformat() if t else "sem-data"
                partes.append(f"{nome}: {st} {len(f.entries)} itens, último {data} | {f.entries[0].get('title', '')[:70]}")
            else:
                partes.append(f"{nome}: {st} 0 itens ({str(getattr(f, 'bozo_exception', ''))[:80]})")
        except Exception as e:  # noqa: BLE001
            partes.append(f"{nome}: erro {e}")
    return "\n    ".join(partes)


if __name__ == "__main__":
    urls = sys.argv[1:]
    if not urls:
        fontes = yaml.safe_load(open("config/fontes.yaml", encoding="utf-8"))["fontes"]
        urls = [f["url"] for f in fontes]
    for u in urls:
        print(f"{u}\n    {testar(u)}", flush=True)
