from pathlib import Path

from boletim import classificador, coletor, publicador
from boletim.redator import Redator, _extrair_json
from boletim.util import carregar_yaml

FIX = Path(__file__).parent / "fixtures" / "noticias.json"


def test_classificacao_cobre_todas_as_secoes():
    cfg = carregar_yaml("config.yaml")
    grupos = classificador.agrupar(coletor.carregar(FIX), [s["id"] for s in cfg["secoes"]], 18)
    for s in ("destaques", "politica", "economia", "tecnologia", "ia", "saude", "cultura"):
        assert grupos[s], f"seção {s} vazia"


def test_deduplicacao():
    ns = coletor.carregar(FIX)
    copia = coletor.Noticia(**{**ns[0].__dict__, "fonte": "Outra", "id": "x"})
    assert len(coletor.deduplicar(ns + [copia])) == len(ns)


def test_extrair_json_tolera_texto_extra():
    assert _extrair_json('Aqui está:\n{"itens": [], "roteiro": "ok"}\nFim')["roteiro"] == "ok"


def test_modo_extrativo_e_markdown(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    cfg = carregar_yaml("config.yaml")
    grupos = classificador.agrupar(coletor.carregar(FIX), [s["id"] for s in cfg["secoes"]], 18)
    segs = Redator(cfg).escrever("terça-feira, 3 de novembro de 2026", grupos)
    assert segs[0]["id"] == "destaques" and segs[-1]["id"] == "encerramento"
    md = publicador.markdown(cfg, "terça-feira", "2026-11-03", segs, 38)
    assert "## Política" in md and "releases/download/edicao-2026-11-03" in md
