from pathlib import Path

from boletim import classificador, coletor, publicador
from boletim.redator import Redator, _extrair_json, _normalizar
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


def test_normalizar_tolera_campos_ausentes_da_ia():
    c = _normalizar({"itens": [{"titulo": "Só título"}, {"texto": "Só texto"}, {}, "lixo"], "roteiro": " ok "})
    assert [i["titulo"] for i in c["itens"]] == ["Só título", "Só texto"]
    assert all(set(i) >= {"titulo", "texto", "regiao", "fontes", "links"} for i in c["itens"])
    assert c["roteiro"] == "ok"
    assert _normalizar({"itens": None})["roteiro"] == ""


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


def test_blocos_respeitam_paragrafos_e_limite():
    from boletim.audio import blocos
    assert blocos("Primeira notícia. Detalhe.\n\nSegunda notícia.") == ["Primeira notícia. Detalhe.", "Segunda notícia."]
    longo = " ".join(f"Frase número {i} com algumas palavras a mais." for i in range(40))
    partes = blocos(longo, max_palavras=90)
    assert len(partes) > 1 and all(len(p.split()) <= 100 for p in partes)
    assert " ".join(partes) == longo


def test_sintetizar_com_pausas_e_tratamento(tmp_path, monkeypatch):
    import shutil

    import pytest

    from boletim import audio
    if not shutil.which("ffmpeg"):
        pytest.skip("ffmpeg ausente")
    usadas = []

    async def falso_edge(texto, voz, mp3, rate):
        usadas.append(voz)
        if voz == "voz-quebrada":
            raise RuntimeError("voz inexistente")
        audio._ff("-f", "lavfi", "-i", "sine=f=440:d=1", "-ar", "24000", "-ac", "1", "-b:a", "48k", str(mp3))
        return [(0.0, 1.0, texto)]

    monkeypatch.setattr(audio, "_edge", falso_edge)
    monkeypatch.setattr(audio.time, "sleep", lambda s: None)
    mp3 = tmp_path / "fala.mp3"
    cues = audio.sintetizar("Um.\n\nDois.\n\nTrês.", "voz-quebrada", mp3, pausa=0.5, voz_reserva="reserva")
    assert usadas.count("voz-quebrada") == 3 and usadas.count("reserva") == 3
    assert 3.6 < audio.duracao(mp3) < 4.6          # 3 blocos de 1 s + 2 pausas de 0,5 s
    assert cues[1][0] == pytest.approx(1.5, abs=0.15)   # 2º bloco começa depois da pausa
    assert [p.name for p in tmp_path.iterdir()] == ["fala.mp3"]   # temporários removidos
    vin = tmp_path / "vin.mp3"
    audio.vinheta(vin)
    assert 2.8 < audio.duracao(vin) < 3.3


def test_vozes_configuradas_existem():
    """No GitHub Actions (com internet) confere se as vozes do config.yaml existem no edge-tts."""
    import asyncio

    import pytest
    try:
        import edge_tts
        vozes = {v["ShortName"] for v in asyncio.run(asyncio.wait_for(edge_tts.list_voices(), 20))}
    except Exception as e:  # noqa: BLE001  (sem rede no ambiente local)
        pytest.skip(f"edge-tts inacessível: {e}")
    cfg = carregar_yaml("config.yaml")
    for chave in ("voz_tts", "voz_tts_secundaria", "voz_tts_reserva"):
        assert cfg[chave] in vozes, f"{chave}={cfg[chave]} não existe no edge-tts"
