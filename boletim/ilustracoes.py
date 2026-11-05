"""Ilustrações do vídeo: globo com a região da notícia (ou gráfico do indicador), ícone da seção e cartão de
citação da reportagem original.

Direitos autorais (Lei 9.610/1998, art. 46): o cartão mostra só o nome do veículo em texto (sem logotipo), a data,
um trecho curto do resumo que o próprio veículo distribui no RSS e um QR code para a matéria original. Nada de
captura de tela nem foto de veículo de imprensa. Fontes em outro idioma mostram só veículo, data e QR code, para o
vídeo não exibir texto estrangeiro.

Tudo é desenhado com Pillow em uma camada transparente por notícia; o vídeo recebe essa camada como uma única
entrada (lista do concat demuxer do ffmpeg), o que mantém a renderização leve."""
from __future__ import annotations

import re
import textwrap
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from . import marca
from .util import RAIZ, log

ICONES = RAIZ / "marca" / "icones"
MAPAS = RAIZ / "marca" / "mapas"
FUSO = ZoneInfo("America/Sao_Paulo")

# geometria (1280x720; outras resoluções são escaladas)
CARTAO_X1 = 880          # o cartão da manchete vai até aqui; à direita fica o globo/gráfico
PAINEL = (900, 150, 340)  # x, y, lado do globo/gráfico
CITACAO_Y = 384
ICONE = (58, 106, 36)     # x, y, lado do ícone da seção (ao lado do rótulo)


def _fonte(peso: str, tamanho: int):
    from PIL import ImageFont
    try:
        return ImageFont.truetype(marca.fonte(peso), tamanho)
    except OSError:
        return ImageFont.load_default()


def _trecho(resumo: str, limite: int = 170) -> str:
    """Uma ou duas frases do resumo, até ~170 caracteres, cortando em palavra."""
    texto = re.sub(r"\s+", " ", resumo or "").strip()
    frases = re.split(r"(?<=[.!?])\s+", texto)
    saida = ""
    for f in frases:
        if len(saida) + len(f) + 1 > limite:
            break
        saida = f"{saida} {f}".strip()
    if not saida:
        saida = texto[:limite].rsplit(" ", 1)[0].rstrip(",;:") + "…" if len(texto) > limite else texto
    return saida


def citacoes(segmentos: list[dict], noticias: list) -> None:
    """Anexa a cada item a reportagem original (casada pelo link) para o cartão de citação."""
    por_link = {n.link: n for n in noticias if getattr(n, "link", "")}
    for seg in segmentos:
        for it in seg.get("itens") or []:
            n = next((por_link[l] for l in it.get("links", []) if l in por_link), None)
            if not n:
                continue
            try:
                quando = datetime.fromisoformat(n.publicado).astimezone(FUSO).strftime("%d/%m %Hh%M")
            except ValueError:
                quando = ""
            it["citacao"] = {"veiculo": n.fonte, "quando": quando, "link": n.link, "idioma": n.idioma,
                             "trecho": _trecho(n.resumo) if n.idioma == "pt" else ""}


def _qr(link: str, lado: int):
    try:
        import qrcode
    except ImportError:
        return None
    q = qrcode.QRCode(border=2, box_size=4, error_correction=qrcode.constants.ERROR_CORRECT_L)
    q.add_data(link)
    q.make(fit=True)
    return q.make_image(fill_color=marca.AZUL_NOITE, back_color="white").convert("RGBA").resize((lado, lado))


def _base(w: int, h: int, secao: str):
    from PIL import Image
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    ic = ICONES / f"{secao}.png"
    if ic.exists():
        x, y, lado = ICONE
        img.alpha_composite(Image.open(ic).convert("RGBA").resize((lado, lado)), (x, y))
    return img


def quadro_item(it: dict, secao: str, w: int = 1280, h: int = 720):
    """Camada transparente de uma notícia: ícone, globo ou gráfico e cartão de citação."""
    from PIL import Image, ImageDraw
    img = _base(w, h, secao)
    px, py, lado = PAINEL
    figura = Path(it["imagem"]) if it.get("imagem") else MAPAS / f"{it.get('regiao') or 'global'}.png"
    if not figura.exists():
        figura = MAPAS / "global.png"
    if figura.exists():
        fig = Image.open(figura).convert("RGBA")
        fig.thumbnail((lado, lado), Image.LANCZOS)
        img.alpha_composite(fig, (px + (lado - fig.width) // 2, py))
    cit = it.get("citacao")
    if not cit:
        return img
    d = ImageDraw.Draw(img)
    x0, y0, x1, y1 = 40, CITACAO_Y, CARTAO_X1, CITACAO_Y + 80
    d.rectangle([x0, y0, x1, y1], fill=(11, 31, 58, 200))
    qr = _qr(cit["link"], 68)
    texto_x1 = x1 - (84 if qr else 16)
    if qr:
        img.alpha_composite(qr, (x1 - 76, y0 + 6))
    assinatura = f"— {cit['veiculo']}" + (f" · {cit['quando']}" if cit.get("quando") else "")
    if cit.get("trecho"):
        f = _fonte("Regular", 17)
        linhas = textwrap.wrap(f"“{cit['trecho']}”", 78)[:2]
        if len(textwrap.wrap(f"“{cit['trecho']}”", 78)) > 2:
            linhas[-1] = linhas[-1].rstrip("”").rstrip(" .,;") + "…”"
        for i, l in enumerate(linhas):
            d.text((x0 + 18, y0 + 8 + i * 22), l, font=f, fill=(255, 255, 255, 235))
        d.text((x0 + 18, y0 + 54), assinatura, font=_fonte("Medium", 15), fill=marca.AMBAR)
    else:
        d.text((x0 + 18, y0 + 14), "Reportagem original", font=_fonte("Medium", 15), fill=(255, 255, 255, 200))
        d.text((x0 + 18, y0 + 38), assinatura.lstrip("— "), font=_fonte("ExtraBold", 20), fill=marca.AMBAR)
    if qr:
        d.text((texto_x1, y1 - 18), "leia na fonte", font=_fonte("Regular", 12), fill=(255, 255, 255, 170),
               anchor="ra")
    return img


def camada(seg: dict, janelas: list[tuple[float, float] | None], dur: float, pasta: Path,
           resolucao: str = "1280x720", inicio: float = 3.0) -> Path | None:
    """Gera os quadros e a lista do concat demuxer (uma imagem por janela de notícia). None se faltar Pillow."""
    try:
        from PIL import Image
    except ImportError:
        return None
    w, h = map(int, resolucao.split("x"))
    pasta.mkdir(parents=True, exist_ok=True)
    escala = (w, h) != (1280, 720)

    def salvar(img, nome: str) -> Path:
        if escala:
            img = img.resize((w, h), Image.LANCZOS)
        p = pasta / nome
        img.save(p)
        return p

    vazio = salvar(Image.new("RGBA", (1280, 720), (0, 0, 0, 0)), "vazio.png")
    base = salvar(_base(1280, 720, seg["id"]), "base.png")
    trechos: list[tuple[Path, float]] = []
    t = 0.0

    def ate(fim: float, arq: Path) -> None:
        nonlocal t
        if fim - t > 0.04:
            trechos.append((arq, fim - t))
            t = fim

    ate(min(inicio, dur), vazio)
    itens = seg.get("itens") or []
    ordem = sorted((j for j in zip(janelas, itens) if j[0]), key=lambda j: j[0][0])
    for k, ((a, b), it) in enumerate(ordem):
        ate(max(a, t), base)
        try:
            quadro = salvar(quadro_item(it, seg["id"]), f"item{k:02d}.png")
        except Exception as e:  # noqa: BLE001
            log.warning("Ilustração do item %d falhou: %s", k, e)
            quadro = base
        ate(min(b, dur), quadro)
    ate(dur, base)
    if not trechos:
        return None
    lista = pasta / "camada.txt"
    corpo = "".join(f"file '{p.resolve()}'\nduration {d:.3f}\n" for p, d in trechos)
    lista.write_text(corpo + f"file '{trechos[-1][0].resolve()}'\n", encoding="utf-8")
    return lista
