"""Classifica notícias por tema (palavras-chave PT/EN + dica da fonte) e pontua relevância."""
from __future__ import annotations

from .coletor import Noticia
from .util import normalizar

PALAVRAS = {
    # mercado de seguros e corretoras (Brasil e exterior). Evita "seguro" isolado, que também é adjetivo ("ambiente seguro").
    "seguros": ["seguros", "seguradora", "segurador", "corretor de seguro", "corretora de seguro", "corretores de seguro",
                "corretoras de seguro", "seguro de", "seguro auto", "seguro rural", "seguro garantia", "segurado",
                "susep", "cnseg", "fenacor", "fenseg", "fenaprevi", "fenacap", "fenasaude", "ibracor", "sincor",
                "resseguro", "ressegurador", " irb ", "previdencia privada", "previdencia complementar",
                "capitalizacao", "sinistro", "apolice", "open insurance", "insurtech", "saude suplementar",
                "insurance", "insurer", "reinsurance", "reinsurer", "underwriting", "insurance broker",
                "catastrophe bond", "cat bond", "lloyd s", "munich re", "swiss re", "eiopa", " naic "],
    "ia": ["inteligencia artificial", " ia ", "artificial intelligence", " ai ", "openai", "anthropic", "claude",
           "chatgpt", "gemini", "llm", "machine learning", "aprendizado de maquina", "deepmind", "nvidia",
           "generative", "generativa", "chatbot", "deepseek", "modelo de linguagem"],
    "tecnologia": ["tecnologia", "technology", "tech", "software", "apple", "google", "microsoft", "meta ",
                   "chip", "semicondutor", "semiconductor", "ciberseguranca", "cyber", "hacker", "5g", "satelite",
                   "satellite", "startup", "smartphone", "internet", "spacex", "nasa", "quantum", "quantica",
                   "robo", "robot", "dados", "data center", "big tech"],
    "politica": ["governo", "government", "presidente", "president", "congresso", "congress", "senado", "senate",
                 "camara", "eleicao", "election", "ministro", "minister", "parlamento", "parliament", "stf",
                 "supremo", "lula", "trump", "partido", "party", "lei ", "projeto de lei", "bill", "diplomacia",
                 "guerra", "war", "otan", "nato", "sancoes", "sanctions", "cupula", "summit", "onu", "united nations",
                 "conselho de seguranca", "ucrania", "ukraine", "gaza", "israel", "china", "russia"],
    "economia": ["economia", "economy", "inflacao", "inflation", "juros", "interest rate", "pib", "gdp", "mercado",
                 "market", "bolsa", "stocks", "ibovespa", "dolar", "dollar", "fed ", "federal reserve",
                 "banco central", "central bank", "selic", "tarifa", "tariff", "comercio", "trade", "emprego",
                 "jobs", "desemprego", "unemployment", "fiscal", "imposto", "tax", "petroleo", "oil", "fmi", "imf",
                 "ibge", "investimento", "investment", "bce", "ecb", "recessao", "recession"],
    "saude": ["saude", "health", "hospital", "vacina", "vaccine", "doenca", "disease", "virus", "oms", "who ",
              "sus ", "medico", "doctor", "cancer", "dengue", "covid", "epidemia", "epidemic", "pandemia",
              "pandemic", "anvisa", "fda", "medicamento", "drug", "tratamento", "treatment", "fiocruz", "nih",
              "saude mental", "mental health", "surto", "outbreak"],
    "cultura": ["cultura", "culture", "cinema", "film", "filme", "musica", "music", "festival", "livro", "book",
                "arte", "art ", "museu", "museum", "teatro", "theatre", "theater", "oscar", "premio", "award",
                "patrimonio", "heritage", "unesco", "literatura", "literature", "exposicao", "exhibition",
                "show", "serie", "series", "netflix", "carnaval", "futebol", "football", "olimpiada", "esporte"],
}

PESO_TIPO = {"oficial": 1.5, "multilateral": 1.5, "ciencia": 1.2, "imprensa": 1.0}
PESO_REGIAO = {"brasil": 1.4, "europa": 1.1, "eua": 1.1, "asia": 1.1, "global": 1.2}


def classificar(n: Noticia) -> Noticia:
    texto = f" {normalizar(n.titulo)} {normalizar(n.resumo)} "
    pontos = {}
    for cat, termos in PALAVRAS.items():
        p = sum(texto.count(t) for t in termos)
        if cat in n.dicas:
            p += 2
        if p:
            pontos[cat] = p
    cats = sorted(pontos, key=pontos.get, reverse=True)[:2]
    if "ia" in cats and "tecnologia" not in cats:
        cats.append("tecnologia")
    n.categorias = cats or (n.dicas[:1] if n.dicas else ["politica"])
    n.relevancia = (1 + n.relevancia) * PESO_TIPO.get(n.tipo, 1) * PESO_REGIAO.get(n.regiao, 1) \
        * (1 + 0.15 * sum(pontos.values()) ** 0.5)
    return n


def agrupar(noticias: list[Noticia], secoes: list[str], max_por_secao: int) -> dict[str, list[Noticia]]:
    for n in noticias:
        classificar(n)
    grupos: dict[str, list[Noticia]] = {s: [] for s in secoes}
    usados = set()
    # seções mais específicas escolhem primeiro, para não serem "engolidas" pelas genéricas
    especificidade = ["seguros", "ia", "saude", "cultura", "economia", "tecnologia", "politica"]
    for s in sorted(secoes, key=lambda x: especificidade.index(x) if x in especificidade else 99):
        if s in ("destaques", "encerramento"):
            continue
        candidatos = sorted((n for n in noticias if s in n.categorias and n.id not in usados),
                            key=lambda n: n.relevancia, reverse=True)
        # garante diversidade regional: intercala regiões
        por_regiao: dict[str, list[Noticia]] = {}
        for n in candidatos:
            por_regiao.setdefault(n.regiao, []).append(n)
        escolhidos = []
        while len(escolhidos) < max_por_secao and any(por_regiao.values()):
            for r in ["brasil", "global", "europa", "eua", "asia"]:
                if por_regiao.get(r) and len(escolhidos) < max_por_secao:
                    escolhidos.append(por_regiao[r].pop(0))
        grupos[s] = escolhidos
        usados.update(n.id for n in escolhidos[: max_por_secao // 2])
    if "destaques" in grupos:
        grupos["destaques"] = sorted(noticias, key=lambda n: n.relevancia, reverse=True)[:max_por_secao]
    return grupos
