"""Bloco "Números e agenda do dia": indicadores e agenda vindos direto de APIs oficiais e gratuitas.

Nada aqui passa pela IA, então não há risco de número inventado:
- Banco Central, SGS (api.bcb.gov.br): dólar e euro (venda), meta da Selic, IPCA em 12 meses (dado do IBGE).
- Câmara dos Deputados (dadosabertos.camara.leg.br) e Senado (legis.senado.leg.br): sessões do plenário no dia.
Qualquer falha de rede apenas omite o indicador; o boletim segue sem ele."""
from __future__ import annotations

import json
import urllib.request
from datetime import date, datetime, timedelta
from pathlib import Path

from .util import log

UA = {"User-Agent": "BoletimBrasilMundo/1.0", "Accept": "application/json"}
SGS = "https://api.bcb.gov.br/dados/serie/bcdata.sgs.{codigo}/dados/ultimos/{n}?formato=json"
PAGINA_SGS = "https://www3.bcb.gov.br/sgspub/localizarseries/localizarSeries.do?method=prepararTelaLocalizarSeries"
# codigo SGS, nome lido, unidade, fonte citada
SERIES = {
    "dolar": (1, "Dólar comercial", "R$", "Banco Central"),
    "euro": (21619, "Euro", "R$", "Banco Central"),
    "selic": (432, "Meta da Selic", "%", "Banco Central"),
    "ipca12": (13522, "Inflação (IPCA) em 12 meses", "%", "IBGE, via Banco Central"),
}


def _get(url: str, timeout: int = 20):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))


def serie(codigo: int, n: int = 30) -> list[tuple[date, float]]:
    pontos = []
    for p in _get(SGS.format(codigo=codigo, n=n)):
        try:
            pontos.append((datetime.strptime(p["data"], "%d/%m/%Y").date(), float(str(p["valor"]).replace(",", "."))))
        except (KeyError, ValueError):
            continue
    return pontos


def _num(v: float, casas: int = 2) -> str:
    return f"{v:,.{casas}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _data_curta(d: date) -> str:
    return d.strftime("%d/%m")


def indicadores() -> dict[str, list[tuple[date, float]]]:
    saida = {}
    for chave, (codigo, nome, _, _) in SERIES.items():
        try:
            # séries diárias aceitam no máximo 20 "últimos" valores (mais que isso dá HTTP 400);
            # a meta da Selic é publicada até a próxima reunião do Copom, então descartamos datas futuras
            pontos = [p for p in serie(codigo, 20 if chave in ("dolar", "euro") else 5) if p[0] <= date.today()]
            if pontos:
                saida[chave] = pontos
        except Exception as e:  # noqa: BLE001
            log.warning("Indicador %s indisponível: %s", nome, e)
    return saida


def _camara(dia: date) -> list[str]:
    url = (f"https://dadosabertos.camara.leg.br/api/v2/eventos?dataInicio={dia:%Y-%m-%d}&dataFim={dia:%Y-%m-%d}"
           "&ordem=ASC&ordenarPor=dataHoraInicio&itens=100")
    linhas = []
    for ev in _get(url).get("dados", []):
        siglas = {o.get("sigla", "") for o in ev.get("orgaos", [])}
        tipo = ev.get("descricaoTipo", "")
        if "PLEN" not in siglas or "Sessão" not in tipo or ev.get("situacao", "") == "Cancelada":
            continue
        hora = (ev.get("dataHoraInicio") or "")[11:16]
        linhas.append(f"Câmara dos Deputados: {tipo.lower()}" + (f" às {hora.replace(':', 'h')}" if hora else ""))
    return linhas[:3]


def _senado(dia: date) -> list[str]:
    dados = _get(f"https://legis.senado.leg.br/dadosabertos/plenario/agenda/dia/{dia:%Y%m%d}")
    sessoes = []

    def busca(no):  # o formato do Senado varia; procura qualquer objeto com tipo de sessão e hora
        if isinstance(no, dict):
            tipo = no.get("TipoSessao") or no.get("DescricaoTipoSessao") or no.get("tipoSessao")
            hora = no.get("Hora") or no.get("HoraInicio") or no.get("hora")
            if tipo and hora:
                sessoes.append((str(hora)[:5], str(tipo)))
            for v in no.values():
                busca(v)
        elif isinstance(no, list):
            for v in no:
                busca(v)

    busca(dados)
    def tipo(t: str) -> str:  # "Sessão Não Deliberativa " → "sessão não deliberativa"
        t = " ".join(t.split()).lower()
        return t if t.startswith("sessão") else f"sessão {t}"

    return [f"Senado: {tipo(t)} às {h.replace(':', 'h')}" for h, t in sessoes[:3]]


def agenda(dia: date) -> list[str]:
    linhas = []
    for nome, f in (("Câmara", _camara), ("Senado", _senado)):
        try:
            linhas += f(dia)
        except Exception as e:  # noqa: BLE001
            log.warning("Agenda da %s indisponível: %s", nome, e)
    return linhas


def grafico(pontos: list[tuple[date, float]], titulo: str, destino: Path, unidade: str = "R$") -> Path | None:
    """Gráfico de linha na identidade da marca (PNG transparente, 340x300) para o painel do vídeo."""
    try:
        from PIL import Image, ImageDraw, ImageFont

        from . import marca
    except ImportError:
        return None
    if len(pontos) < 3:
        return None
    w, h, m = 340, 300, 26
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([0, 0, w - 1, h - 1], radius=18, fill=(11, 31, 58, 215))
    try:
        f_t, f_v, f_p = (ImageFont.truetype(marca.fonte(p), s) for p, s in (("Medium", 18), ("ExtraBold", 30),
                                                                             ("Regular", 14)))
    except OSError:
        f_t = f_v = f_p = ImageFont.load_default()
    d.text((m, 16), titulo, font=f_t, fill="white")
    d.text((m, 40), f"{unidade} {_num(pontos[-1][1], 4 if unidade == 'R$' else 2)}", font=f_v, fill=marca.AMBAR)
    vs = [v for _, v in pontos]
    lo, hi = min(vs), max(vs)
    hi = hi if hi > lo else lo + 1
    x0, x1, y0, y1 = m, w - m, 96, h - 40
    xy = [(x0 + (x1 - x0) * i / (len(vs) - 1), y1 - (y1 - y0) * (v - lo) / (hi - lo)) for i, v in enumerate(vs)]
    d.polygon(xy + [(x1, y1), (x0, y1)], fill=(245, 166, 35, 45))
    d.line(xy, fill=marca.AMBAR, width=4, joint="curve")
    d.ellipse([xy[-1][0] - 6, xy[-1][1] - 6, xy[-1][0] + 6, xy[-1][1] + 6], fill=marca.AMBAR)
    d.text((x0, y1 + 10), _data_curta(pontos[0][0]), font=f_p, fill=(255, 255, 255, 170))
    d.text((x1, y1 + 10), _data_curta(pontos[-1][0]), font=f_p, fill=(255, 255, 255, 170), anchor="ra")
    d.text((w // 2, y1 + 10), "Fonte: Banco Central", font=f_p, fill=(255, 255, 255, 150), anchor="ma")
    img.save(destino)
    return destino


def _variacao(pontos: list[tuple[date, float]]) -> float | None:
    if len(pontos) < 2 or not pontos[-2][1]:
        return None
    return (pontos[-1][1] / pontos[-2][1] - 1) * 100


def segmento(cfg: dict, hoje: date, pasta: Path, ind: dict | None = None, ag: list[str] | None = None) -> dict | None:
    """Monta o segmento do boletim (mesmo formato dos demais: itens + roteiro). None se não houver nenhum dado."""
    opc = cfg.get("numeros_do_dia") or {}
    if not opc.get("ativo", True):
        return None
    ind = indicadores() if ind is None else ind
    ag = agenda(hoje) if ag is None else ag
    itens, falas = [], []
    for chave in ("dolar", "euro"):
        if chave not in ind:
            continue
        _, nome, un, fonte = SERIES[chave]
        pts = ind[chave]
        (dia, v), var = pts[-1], _variacao(pts)
        sentido = "" if var is None else (f", {'alta' if var > 0 else 'queda'} de {_num(abs(var))}% sobre o dia anterior"
                                          if abs(var) >= 0.005 else ", estável em relação ao dia anterior")
        texto = f"{nome} a {un} {_num(v, 4)} na cotação de venda de {_data_curta(dia)}{sentido}."
        item = {"titulo": f"{nome}: {un} {_num(v, 4)}", "texto": texto, "regiao": "brasil", "fontes": [fonte],
                "links": [PAGINA_SGS]}
        png = grafico(pts, f"{nome}, últimos pregões", pasta / f"grafico_{chave}.png", un)
        if png:
            item["imagem"] = str(png)
        itens.append(item)
        falas.append(f"O {nome.lower()} fechou a {_num(v, 2)} reais{sentido}, segundo o {fonte}.")
    for chave in ("selic", "ipca12"):
        if chave not in ind:
            continue
        _, nome, un, fonte = SERIES[chave]
        dia, v = ind[chave][-1]
        quando = f"referente a {dia:%m/%Y}" if chave == "ipca12" else f"dado de {_data_curta(dia)}"
        itens.append({"titulo": f"{nome}: {_num(v)}%", "texto": f"{nome} em {_num(v)}% ({quando}).",
                      "regiao": "brasil", "fontes": [fonte], "links": [PAGINA_SGS]})
        falas.append(f"A meta da taxa Selic está em {_num(v)} por cento ao ano, segundo o Banco Central."
                     if chave == "selic" else
                     f"A inflação oficial, medida pelo IPCA, acumula {_num(v)} por cento em doze meses, segundo o IBGE.")
    for linha in ag:
        itens.append({"titulo": linha, "texto": linha + ".", "regiao": "brasil",
                      "fontes": ["Câmara dos Deputados" if linha.startswith("Câmara") else "Senado Federal"],
                      "links": ["https://www.camara.leg.br/agenda" if linha.startswith("Câmara")
                                else "https://www25.senado.leg.br/web/atividade/agenda"]})
    if not itens:
        log.warning("Números e agenda do dia: nenhum dado disponível; bloco omitido.")
        return None
    roteiro = "Agora, os números do dia. " + " ".join(falas)
    if ag:
        casas = {"Câmara dos Deputados": "na Câmara dos Deputados", "Senado": "no Senado"}
        roteiro += " Na agenda de hoje em Brasília: " + "; ".join(
            f"{l.split(': ', 1)[1]} {casas.get(l.split(': ', 1)[0], '')}".strip() for l in ag) + "."
    return {"id": "numeros", "titulo": opc.get("titulo", "Números e agenda do dia"),
            "cor": opc.get("cor", "#0B1F3A"), "cor2": opc.get("cor2", "#7A5A12"), "itens": itens,
            "roteiro": roteiro}


def inserir(segmentos: list[dict], seg: dict | None) -> list[dict]:
    """Coloca o bloco logo depois das manchetes."""
    if seg:
        pos = 1 if segmentos and segmentos[0].get("id") == "destaques" else 0
        segmentos.insert(pos, seg)
    return segmentos


if __name__ == "__main__":  # diagnóstico: python -m boletim.dados
    import logging
    logging.basicConfig(level=logging.INFO)
    ind = indicadores()
    for k, v in ind.items():
        print(k, v[-3:])
    amanha = date.today() + timedelta(days=1)
    for dia in (date.today(), amanha):
        print(dia, agenda(dia))
    s = segmento({"numeros_do_dia": {"ativo": True}}, date.today(), Path("."), ind)
    print(json.dumps(s, ensure_ascii=False, indent=1)[:3000] if s else s)
