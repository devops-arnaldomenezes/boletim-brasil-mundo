"""Coleta de notícias via RSS/Atom de fontes oficiais, multilaterais e da imprensa confiável."""
from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass, field
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import feedparser

from .util import chave, limpar_html, log, normalizar

USER_AGENT = "BoletimBrasilMundo/1.0 (+https://github.com) feedparser"


@dataclass
class Noticia:
    titulo: str
    resumo: str
    link: str
    fonte: str
    regiao: str
    idioma: str
    tipo: str
    publicado: str  # ISO 8601 UTC
    dicas: list = field(default_factory=list)
    categorias: list = field(default_factory=list)
    relevancia: float = 0.0
    id: str = ""


def _data(entry) -> datetime | None:
    for k in ("published_parsed", "updated_parsed", "created_parsed"):
        t = entry.get(k)
        if t:
            return datetime(*t[:6], tzinfo=timezone.utc)
    return None


def coletar_fonte(fonte: dict, desde: datetime, limite: int) -> tuple[list[Noticia], bool]:
    """Retorna (notícias recentes, feed respondeu corretamente)."""
    try:
        feed = feedparser.parse(fonte["url"], agent=USER_AGENT)
    except Exception as e:  # noqa: BLE001
        log.warning("Falha em %s: %s", fonte["nome"], e)
        return [], False
    if not feed.entries:
        log.warning("Feed sem itens: %s (%s)", fonte["nome"], getattr(feed, "bozo_exception", ""))
        return [], False
    itens = []
    for e in feed.entries[:limite]:
        dt = _data(e)
        if dt is None or dt < desde:
            continue
        titulo = limpar_html(e.get("title", ""))
        if not titulo:
            continue
        itens.append(Noticia(
            titulo=titulo,
            resumo=limpar_html(e.get("summary", ""))[:700],
            link=e.get("link", ""),
            fonte=fonte["nome"], regiao=fonte["regiao"], idioma=fonte.get("idioma", "pt"),
            tipo=fonte.get("tipo", "imprensa"), publicado=dt.isoformat(),
            dicas=list(fonte.get("categorias", [])), id=chave(titulo),
        ))
    log.info("%-28s %3d itens", fonte["nome"], len(itens))
    return itens, True


def deduplicar(noticias: list[Noticia]) -> list[Noticia]:
    """Remove duplicatas por título quase idêntico (Jaccard de palavras)."""
    vistos: list[tuple[set, Noticia]] = []
    for n in sorted(noticias, key=lambda x: x.tipo != "oficial"):
        palavras = {p for p in normalizar(n.titulo).split() if len(p) > 3}
        dup = False
        for pal, outro in vistos:
            if palavras and pal and len(palavras & pal) / len(palavras | pal) > 0.6:
                dup = True
                outro.relevancia += 1  # citada por mais de uma fonte = mais relevante
                break
        if not dup:
            vistos.append((palavras, n))
    return [n for _, n in vistos]


def coletar(fontes: list[dict], janela_horas: int, limite: int, saude: dict | None = None) -> list[Noticia]:
    """saude (opcional) recebe {nome_da_fonte: (ok, qtd_itens)} para o estado do agente."""
    # uma fonte pode ter janela própria (ex.: checagem, que não publica nos fins de semana)
    agora_utc = datetime.now(timezone.utc)
    desde = lambda f: agora_utc - timedelta(hours=f.get("janela_horas", janela_horas))  # noqa: E731
    with ThreadPoolExecutor(max_workers=12) as ex:
        lotes = list(ex.map(lambda f: coletar_fonte(f, desde(f), limite), fontes))
    if saude is not None:
        for f, (itens, ok) in zip(fontes, lotes):
            saude[f["nome"]] = (ok, len(itens))
    todas = [n for lote, _ in lotes for n in lote]
    unicas = deduplicar(todas)
    log.info("Coletadas %d notícias (%d após deduplicação)", len(todas), len(unicas))
    return unicas


def links_publicados(pasta_edicoes: Path, hoje: date, dias: int = 3) -> set[str]:
    """Links já lidos nas últimas edições (roteiro.json), para fontes de janela longa não repetirem notícia."""
    links: set[str] = set()
    for d in range(1, dias + 1):
        roteiro = pasta_edicoes / (hoje - timedelta(days=d)).strftime("%Y/%m/%d") / "roteiro.json"
        try:
            for seg in json.loads(roteiro.read_text(encoding="utf-8")):
                for item in seg.get("itens", []):
                    links.update(item.get("links", []))
        except (OSError, ValueError):
            continue
    return links


def salvar(noticias: list[Noticia], caminho: Path) -> None:
    caminho.write_text(json.dumps([asdict(n) for n in noticias], ensure_ascii=False, indent=1), encoding="utf-8")


def carregar(caminho: Path) -> list[Noticia]:
    return [Noticia(**d) for d in json.loads(caminho.read_text(encoding="utf-8"))]
