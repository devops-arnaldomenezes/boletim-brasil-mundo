"""Publicação: gera Markdown/HTML/JSON da edição, índice do site e feed RSS de podcast."""
from __future__ import annotations

import html
import json
import os
from datetime import datetime
from email.utils import format_datetime
from pathlib import Path

from .util import RAIZ

REGIAO = {"brasil": "🇧🇷 Brasil", "europa": "🇪🇺 Europa", "eua": "🇺🇸 EUA", "asia": "🌏 Ásia", "global": "🌐 Mundo"}


def url_midia(data_iso: str, arquivo: str) -> str:
    repo = os.environ.get("GITHUB_REPOSITORY", "OWNER/boletim-brasil-mundo")
    return f"https://github.com/{repo}/releases/download/edicao-{data_iso}/{arquivo}"


def url_site() -> str:
    repo = os.environ.get("GITHUB_REPOSITORY", "OWNER/boletim-brasil-mundo")
    dono, nome = repo.split("/")
    return f"https://{dono.lower()}.github.io/{nome}"


def markdown(cfg: dict, data_ext: str, data_iso: str, segmentos: list[dict], dur_min: float | None) -> str:
    linhas = [f"# {cfg['titulo']} — {data_ext}", ""]
    midia = []
    if cfg.get("gerar_audio"):
        midia.append(f"🎧 [Podcast (MP3)]({url_midia(data_iso, f'boletim-{data_iso}.mp3')})")
    if cfg.get("gerar_video"):
        midia.append(f"🎬 [Vídeo (MP4)]({url_midia(data_iso, f'boletim-{data_iso}.mp4')})")
    if midia:
        linhas += [" · ".join(midia) + (f" · ⏱️ {dur_min:.0f} min" if dur_min else ""), ""]
    linhas += ["> Resumo gerado automaticamente a partir de fontes oficiais, organismos internacionais e imprensa "
               "reconhecida. Confira sempre a fonte original nos links.", ""]
    for s in segmentos:
        if not s.get("itens"):
            continue
        linhas += [f"## {s['titulo']}", ""]
        for it in s["itens"]:
            fontes = ", ".join(f"[{f}]({l})" if l else f for f, l in
                               zip(it.get("fontes", []), (it.get("links", []) + [""] * 9)))
            reg = REGIAO.get(it.get("regiao", ""), "")
            linhas += [f"**{it['titulo']}** {('· ' + reg) if reg else ''}  ", f"{it['texto']}  ",
                       f"<sub>Fonte: {fontes}</sub>" if fontes else "", ""]
    linhas += ["---", "", "<details><summary>Roteiro completo da locução</summary>", ""]
    for s in segmentos:
        linhas += [f"### {s['titulo']}", "", s["roteiro"], ""]
    linhas += ["</details>", ""]
    return "\n".join(linhas)


CSS = """:root{--bg:#f6f7f9;--fg:#15171a;--card:#fff;--mute:#5b6470;--acc:#0B3D91}
@media (prefers-color-scheme:dark){:root{--bg:#0f1115;--fg:#e8eaed;--card:#181b21;--mute:#9aa3ad;--acc:#7fb0ff}}
body{margin:0;font:16px/1.6 system-ui,-apple-system,Segoe UI,Roboto,sans-serif;background:var(--bg);color:var(--fg)}
main{max-width:860px;margin:0 auto;padding:24px 16px}a{color:var(--acc)}h1{font-size:1.7rem;line-height:1.25}
h2{margin-top:2rem;padding-left:10px;border-left:6px solid var(--c,var(--acc))}
.item{background:var(--card);border-radius:10px;padding:12px 16px;margin:10px 0}.meta{color:var(--mute);font-size:.85rem}
audio,video{width:100%;margin:8px 0;border-radius:8px}ul.ed{list-style:none;padding:0}ul.ed li{padding:8px 0;border-bottom:1px solid #8883}"""


def html_edicao(cfg: dict, data_ext: str, data_iso: str, segmentos: list[dict]) -> str:
    e = html.escape
    corpo = [f"<h1>{e(cfg['titulo'])}<br><small>{e(data_ext)}</small></h1>"]
    if cfg.get("gerar_video"):
        corpo.append(f'<video controls preload="none" src="{url_midia(data_iso, f"boletim-{data_iso}.mp4")}"></video>')
    if cfg.get("gerar_audio"):
        corpo.append(f'<audio controls preload="none" src="{url_midia(data_iso, f"boletim-{data_iso}.mp3")}"></audio>')
    for s in segmentos:
        if not s.get("itens"):
            continue
        corpo.append(f'<h2 style="--c:{s["cor2"]}">{e(s["titulo"])}</h2>')
        for it in s["itens"]:
            links = " · ".join(f'<a href="{e(l)}">{e(f)}</a>' for f, l in zip(it.get("fontes", []), it.get("links", [])) if l)
            corpo.append(f'<div class="item"><div class="meta">{e(REGIAO.get(it.get("regiao",""),""))}</div>'
                         f'<strong>{e(it["titulo"])}</strong><p>{e(it["texto"])}</p><div class="meta">{links}</div></div>')
    corpo.append('<p class="meta"><a href="../../../../index.html">← todas as edições</a></p>')
    return (f'<!doctype html><html lang="pt-BR"><head><meta charset="utf-8"><meta name="viewport" '
            f'content="width=device-width,initial-scale=1"><title>{e(cfg["titulo"])} — {data_iso}</title>'
            f'<style>{CSS}</style></head><body><main>{"".join(corpo)}</main></body></html>')


def atualizar_indice(cfg: dict, raiz_edicoes: Path, destino_site: Path) -> None:
    """Gera index.html e feed.xml (podcast) a partir de edicoes/*/*/*/meta.json."""
    metas = sorted((json.loads(p.read_text(encoding="utf-8")) for p in raiz_edicoes.glob("*/*/*/meta.json")),
                   key=lambda m: m["data"], reverse=True)
    e = html.escape
    lis = "".join(f'<li><a href="edicoes/{m["data"].replace("-", "/")}/index.html">{e(m["data_extenso"])}</a>'
                  f' <span class="meta">· {m.get("duracao_min") or "?"} min · '
                  f'<a href="{url_midia(m["data"], f"boletim-{m["data"]}.mp3")}">MP3</a> · '
                  f'<a href="{url_midia(m["data"], f"boletim-{m["data"]}.mp4")}">MP4</a></span></li>' for m in metas)
    # player da edição mais recente direto na página inicial: ouvir e assistir sem baixar
    player = ""
    if metas:
        u = metas[0]["data"]
        player = (f'<h2>Última edição: {e(metas[0]["data_extenso"])}</h2>'
                  f'<video controls preload="metadata" src="{url_midia(u, f"boletim-{u}.mp4")}"></video>'
                  f'<audio controls preload="metadata" src="{url_midia(u, f"boletim-{u}.mp3")}"></audio>'
                  '<h2>Todas as edições</h2>')
    destino_site.mkdir(parents=True, exist_ok=True)
    (destino_site / "index.html").write_text(
        f'<!doctype html><html lang="pt-BR"><head><meta charset="utf-8"><meta name="viewport" '
        f'content="width=device-width,initial-scale=1"><title>{e(cfg["titulo"])}</title>'
        f'<link rel="alternate" type="application/rss+xml" href="feed.xml"><style>{CSS}</style></head><body><main>'
        f'<h1>{e(cfg["titulo"])}</h1><p>Boletim diário de notícias do Brasil e do mundo, publicado todos os dias às 6h '
        f'(Brasília). Assine o <a href="feed.xml">feed do podcast</a>.</p>{player}<ul class="ed">{lis}</ul></main></body></html>',
        encoding="utf-8")

    itens = []
    for m in metas[:60]:
        dt = datetime.fromisoformat(m["publicado"])
        mp3 = url_midia(m["data"], f"boletim-{m['data']}.mp3")
        itens.append(f"<item><title>{e(cfg['titulo'])} — {e(m['data_extenso'])}</title>"
                     f"<link>{url_site()}/edicoes/{m['data'].replace('-', '/')}/index.html</link>"
                     f"<guid isPermaLink=\"false\">boletim-{m['data']}</guid><pubDate>{format_datetime(dt)}</pubDate>"
                     f"<description>{e(m.get('manchetes', ''))}</description>"
                     f"<enclosure url=\"{mp3}\" length=\"{m.get('bytes_mp3', 0)}\" type=\"audio/mpeg\"/>"
                     f"<itunes:duration>{int((m.get('duracao_min') or 0) * 60)}</itunes:duration></item>")
    (destino_site / "feed.xml").write_text(
        '<?xml version="1.0" encoding="UTF-8"?><rss version="2.0" '
        'xmlns:itunes="http://www.itunes.com/dtds/podcast-1.0.dtd"><channel>'
        f"<title>{e(cfg['titulo'])}</title><link>{url_site()}</link><language>pt-br</language>"
        "<description>Resumo diário de notícias do Brasil e do mundo: política, economia, tecnologia, IA, saúde e "
        "cultura.</description><itunes:category text=\"News\"/>" + "".join(itens) + "</channel></rss>",
        encoding="utf-8")


def escrever_readme_ultima(cfg: dict, data_ext: str, data_iso: str) -> None:
    caminho = RAIZ / "edicoes" / "ULTIMA.md"
    caminho.write_text(f"# Última edição: {data_ext}\n\n"
                       f"- [Ler o boletim]({data_iso.replace('-', '/')}/boletim.md)\n"
                       f"- [Podcast MP3]({url_midia(data_iso, f'boletim-{data_iso}.mp3')})\n"
                       f"- [Vídeo MP4]({url_midia(data_iso, f'boletim-{data_iso}.mp4')})\n", encoding="utf-8")
