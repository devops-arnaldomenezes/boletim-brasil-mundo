"""Publicação: gera Markdown/HTML/JSON da edição, índice do site e feed RSS de podcast."""
from __future__ import annotations

import html
import json
import os
from datetime import datetime
from email.utils import format_datetime
from pathlib import Path

from . import marca
from .util import RAIZ

REGIAO = {"brasil": "🇧🇷 Brasil", "latam": "🌎 América Latina", "europa": "🇪🇺 Europa", "eua": "🇺🇸 EUA", "asia": "🌏 Ásia", "global": "🌐 Mundo"}


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


CSS = f""":root{{--bg:{marca.PAPEL};--fg:{marca.TINTA};--card:#fff;--mute:{marca.CINZA};--acc:#1F4E8C;
--noite:{marca.AZUL_NOITE};--ambar:{marca.AMBAR};--borda:#14213D1A}}
@media (prefers-color-scheme:dark){{:root{{--bg:#08162A;--fg:#E8ECF2;--card:#0F2340;--mute:#9AA8BC;--acc:#8DB8FF;
--borda:#FFFFFF1A}}}}
*{{box-sizing:border-box}}body{{margin:0;font:16px/1.65 {marca.FONTE_SITE};background:var(--bg);color:var(--fg)}}
header.marca{{background:var(--noite);border-bottom:3px solid var(--ambar)}}
header.marca a{{display:block;max-width:880px;margin:0 auto;padding:14px 16px}}header.marca svg{{height:clamp(56px,14vw,80px);width:auto;display:block}}
main{{max-width:880px;margin:0 auto;padding:24px 16px 48px}}a{{color:var(--acc)}}
h1{{font-size:1.8rem;line-height:1.2;letter-spacing:-.02em;margin:.4em 0}}h1 small{{font-weight:500;color:var(--mute);font-size:1rem}}
h2{{margin-top:2.2rem;padding-left:12px;border-left:6px solid var(--c,var(--ambar));letter-spacing:-.01em}}
.item{{background:var(--card);border:1px solid var(--borda);border-radius:12px;padding:14px 18px;margin:12px 0}}
.meta{{color:var(--mute);font-size:.85rem}}.selo{{display:inline-block;background:var(--ambar);color:var(--noite);
font-weight:700;font-size:.75rem;letter-spacing:.06em;border-radius:99px;padding:2px 10px;text-transform:uppercase}}
audio,video{{width:100%;margin:8px 0;border-radius:12px;background:#000}}
ul.ed{{list-style:none;padding:0}}ul.ed li{{padding:10px 0;border-bottom:1px solid var(--borda)}}
footer{{color:var(--mute);font-size:.85rem;text-align:center;padding:24px 16px}}"""


def _pagina(titulo: str, corpo: str, raiz: str = "", extra_head: str = "") -> str:
    """Moldura comum das páginas: fonte Inter, favicon e cabeçalho com o logotipo."""
    e = html.escape
    return ('<!doctype html><html lang="pt-BR"><head><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width,initial-scale=1">'
            f'<title>{e(titulo)}</title><meta name="theme-color" content="{marca.AZUL_NOITE}">'
            f'<link rel="icon" type="image/png" href="{raiz}marca/simbolo-96.png">'
            '<link rel="preconnect" href="https://fonts.googleapis.com">'
            '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;700;800&display=swap">'
            f'{extra_head}<style>{CSS}</style></head><body>'
            f'<header class="marca"><a href="{raiz}index.html" aria-label="Início">{marca.logo_svg()}</a></header>'
            f'<main>{corpo}</main><footer>Brasil e Mundo Hoje · resumo diário automático com links para as fontes '
            'originais · publicado todos os dias às 6h (Brasília)</footer></body></html>')


def html_edicao(cfg: dict, data_ext: str, data_iso: str, segmentos: list[dict]) -> str:
    e = html.escape
    corpo = [f'<p><span class="selo">Edição do dia</span></p><h1>{e(data_ext)}</h1>']
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
    return _pagina(f'{cfg["titulo"]} — {data_iso}', "".join(corpo), "../../../../")


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
        player = (f'<p><span class="selo">Última edição</span></p><h1>{e(metas[0]["data_extenso"])}</h1>'
                  f'<video controls preload="metadata" src="{url_midia(u, f"boletim-{u}.mp4")}"></video>'
                  f'<audio controls preload="metadata" src="{url_midia(u, f"boletim-{u}.mp3")}"></audio>'
                  '<h2>Todas as edições</h2>')
    destino_site.mkdir(parents=True, exist_ok=True)
    (destino_site / "index.html").write_text(_pagina(
        cfg["titulo"],
        '<p>Boletim diário de notícias do Brasil e do mundo, publicado todos os dias às 6h (Brasília). '
        f'Assine o <a href="feed.xml">feed do podcast</a>.</p>{player}<ul class="ed">{lis}</ul>',
        extra_head='<link rel="alternate" type="application/rss+xml" href="feed.xml">'),
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
        "cultura.</description><itunes:category text=\"News\"/>"
        f"<itunes:image href=\"{url_site()}/marca/capa-podcast.png\"/>"
        f"<image><url>{url_site()}/marca/capa-podcast.png</url><title>{e(cfg['titulo'])}</title>"
        f"<link>{url_site()}</link></image>" + "".join(itens) + "</channel></rss>",
        encoding="utf-8")


def escrever_readme_ultima(cfg: dict, data_ext: str, data_iso: str) -> None:
    caminho = RAIZ / "edicoes" / "ULTIMA.md"
    caminho.write_text(f"# Última edição: {data_ext}\n\n"
                       f"- [Ler o boletim]({data_iso.replace('-', '/')}/boletim.md)\n"
                       f"- [Podcast MP3]({url_midia(data_iso, f'boletim-{data_iso}.mp3')})\n"
                       f"- [Vídeo MP4]({url_midia(data_iso, f'boletim-{data_iso}.mp4')})\n", encoding="utf-8")
