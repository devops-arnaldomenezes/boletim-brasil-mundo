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
    for k in ("ANTHROPIC_API_KEY", "GITHUB_TOKEN", "GEMINI_API_KEY"):
        monkeypatch.delenv(k, raising=False)
    cfg = carregar_yaml("config.yaml")
    grupos = classificador.agrupar(coletor.carregar(FIX), [s["id"] for s in cfg["secoes"]], 18)
    segs = Redator(cfg).escrever("terça-feira, 3 de novembro de 2026", grupos)
    assert segs[0]["id"] == "destaques" and segs[-1]["id"] == "encerramento"
    md = publicador.markdown(cfg, "terça-feira", "2026-11-03", segs, 38)
    assert "## Política" in md and "releases/download/edicao-2026-11-03" in md


def test_estado_pausa_e_calibra():
    from datetime import date

    from boletim import estado as m
    est = {"fontes": {}, "ppm_medido": None}
    for _ in range(7):
        m.registrar_fonte(est, "X", False, 0, date(2026, 11, 3))
    assert m.pausadas(est) == ["X"]
    m.registrar_fonte(est, "X", True, 5, date(2026, 11, 4))
    assert not m.pausadas(est)
    assert m.registrar_ritmo(est, 1500, 600) == 150


def test_vinheta_manim_renderiza(tmp_path):
    import pytest

    from boletim import vinhetas
    if not vinhetas.disponivel():
        pytest.skip("manim não instalado")
    p = vinhetas.render("Transicao", {"duracao": 1, "cor": "#0B3D91", "cor2": "#1E88E5", "titulo": "Saúde"},
                        tmp_path / "v.mp4", "640x360")
    assert p and p.stat().st_size > 1000


def test_extrativo_usa_orcamento_de_palavras():
    cfg = carregar_yaml("config.yaml")
    itens = [n for n in coletor.carregar(FIX)] * 5  # repete a fixture para simular uma seção cheia
    r = Redator.__new__(Redator)
    r.cfg = cfg
    secao = {"id": "politica", "titulo": "Política"}
    curto = r._extrativo(secao, itens, "hoje", 0)
    longo = r._extrativo(secao, itens, "hoje", 700)
    assert len(curto["itens"]) == min(8, len(itens))
    assert len(longo["itens"]) > len(curto["itens"]) and len(longo["roteiro"].split()) >= 700


def test_fator_extensao_aprende():
    from boletim import estado as m
    est = {"fontes": {}}
    f = m.registrar_extensao(est, 2500, 5000)  # IA escreveu metade do pedido
    assert 1.3 < f <= 2.5


def test_completa_secao_curta(monkeypatch):
    for k in ("ANTHROPIC_API_KEY", "GITHUB_TOKEN", "GEMINI_API_KEY"):
        monkeypatch.delenv(k, raising=False)
    cfg = carregar_yaml("config.yaml")
    itens = coletor.carregar(FIX)
    r = Redator(cfg)
    curto = {"itens": [{"titulo": itens[0].titulo, "texto": "x", "links": [itens[0].link]}], "roteiro": "Curto."}
    out = r._completar({"id": "politica", "titulo": "Política"}, curto, itens, 400)
    assert len(out["roteiro"].split()) > 100 and len(out["itens"]) > 1
