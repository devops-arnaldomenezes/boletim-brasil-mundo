"""Regressões da edição de 05/11/2026: locução misturando inglês e português e manchetes do vídeo fora de sincronia
com o áudio."""
import json
import shutil
from pathlib import Path

import pytest

from boletim import coletor, idioma, video
from boletim.redator import Redator
from boletim.util import RAIZ, carregar_yaml

EDICAO_0511 = RAIZ / "edicoes" / "2026" / "11" / "05" / "noticias.json"


def _noticia(titulo, resumo, idioma_="pt", fonte="Fonte", link=None):
    return coletor.Noticia(titulo=titulo, resumo=resumo, link=link or f"https://ex.org/{abs(hash(titulo))}",
                           fonte=fonte, regiao="global", idioma=idioma_, tipo="imprensa",
                           publicado="2026-11-05T01:00:00+00:00")


def _redator(monkeypatch, cfg=None):
    for k in ("ANTHROPIC_API_KEY", "GITHUB_TOKEN", "GEMINI_API_KEY"):
        monkeypatch.delenv(k, raising=False)
    return Redator(cfg or carregar_yaml("config.yaml"))


def test_detecta_ingles_e_espanhol_sem_falso_positivo():
    assert idioma.eh_estrangeiro("UN peacekeeping chief warns of a security vacuum after the withdrawal")
    assert idioma.eh_estrangeiro("El presidente anunció hoy las medidas del gobierno con los ministros")
    assert not idioma.eh_estrangeiro("O dólar fechou em queda nesta quarta-feira, segundo a Agência Brasil.")
    assert not idioma.eh_estrangeiro("Segundo a BBC World, a ONU pediu cessar-fogo em Gaza.")
    assert not idioma.eh_estrangeiro("A Microsoft e a OpenAI anunciaram parceria, de acordo com o The Verge.")


def test_limpa_residuos_de_feed_e_corta_em_frase_completa():
    sujo = ("Companhia reduz dívida no trimestre. The post Simpar (SIMH3) lucra R$ 137 milhões appeared first on "
            "InfoMoney .")
    assert idioma.limpar_resumo(sujo) == "Companhia reduz dívida no trimestre."
    assert "AP" not in idioma.limpar_resumo("Joshua Wong em 2015. Vincent Yu/AP O ativista foi condenado.")
    longo = "Primeira frase com bastante conteúdo informativo aqui. " * 3 + "Segunda parte que seria cortada no meio"
    assert idioma.limpar_resumo(longo, 120).endswith(".")


def test_so_portugues_remove_frases_em_ingles_e_preserva_paragrafos():
    texto = ("Agora, Política.\n\nO Senado aprovou o projeto. The bill was sent to the president after the vote."
             "\n\nNa Europa, o BCE manteve os juros.")
    limpo, removidas = idioma.so_portugues(texto)
    assert removidas == 1 and "bill" not in limpo
    assert limpo.split("\n\n") == ["Agora, Política.", "O Senado aprovou o projeto.", "Na Europa, o BCE manteve os juros."]


def test_extrativo_nunca_le_noticia_em_ingles(monkeypatch):
    r = _redator(monkeypatch)
    itens = [_noticia("UN chief warns of security vacuum", "The world has more tools than ever to tackle the crisis.",
                      "en", "UN News"),
             _noticia("Dólar cai a R$ 5,45 após eleições nos EUA", "O dólar fechou em queda nesta quarta-feira.",
                      fonte="Agência Brasil"),
             _noticia("Ministério lança programa de vacinação", "A campanha começa na segunda-feira em todo o país.",
                      fonte="Agência Gov")]
    out = r._extrativo({"id": "economia", "titulo": "Economia"}, itens, "hoje", 500)
    assert [i["fontes"][0] for i in out["itens"]] == ["Agência Brasil", "Agência Gov"]
    pars = out["roteiro"].split("\n\n")
    assert pars[0] == "Agora, Economia." and len(pars) == 3  # um parágrafo por notícia (sincronia do vídeo)
    assert "UN" not in out["roteiro"] and "world" not in out["roteiro"]


@pytest.mark.skipif(not EDICAO_0511.exists(), reason="edição de 05/11 não versionada")
def test_regressao_edicao_05_11_sem_ia_sai_toda_em_portugues(monkeypatch):
    from boletim import classificador
    cfg = carregar_yaml("config.yaml")
    r = _redator(monkeypatch, cfg)
    grupos = classificador.agrupar(coletor.carregar(EDICAO_0511), [s["id"] for s in cfg["secoes"]], 18)
    segs = r.escrever("quinta-feira, 5 de novembro de 2026", grupos)
    for s in segs:
        assert idioma.so_portugues(s["roteiro"])[1] == 0, s["id"]
        assert "appeared first" not in s["roteiro"] and "The post" not in s["roteiro"]
        for it in s["itens"]:
            assert not idioma.eh_estrangeiro(f"{it['titulo']}. {it['texto']}"), it["titulo"]


def test_repescagem_recupera_secoes_quando_a_ia_volta(monkeypatch):
    cfg = {**carregar_yaml("config.yaml"), "repescagem_ia_s": [1, 1]}
    cfg["secoes"] = [s for s in cfg["secoes"] if s["id"] in ("politica", "economia", "encerramento")]
    r = _redator(monkeypatch, cfg)
    r.cliente, r.provedor = ("url", "token"), "gemini"
    monkeypatch.setattr("boletim.redator.time.sleep", lambda s: None)
    chamadas = {"n": 0}

    def falsa(pedido, max_tokens=4000):
        chamadas["n"] += 1
        if chamadas["n"] <= 2:  # cota estourada no começo da madrugada (como em 05/11)
            raise RuntimeError("Falha ao obter JSON do modelo")
        return {"itens": [{"titulo": "Senado aprova projeto", "texto": "Texto em português."}],
                "roteiro": "Na política, o Senado aprovou o projeto."}

    monkeypatch.setattr(r, "_chamar", falsa)
    grupos = {"politica": [_noticia("Senado aprova projeto", "Votação no plenário.")],
              "economia": [_noticia("Dólar cai", "Moeda recua.")]}
    segs = r.escrever("hoje", grupos)
    assert [s["id"] for s in segs] == ["politica", "economia", "encerramento"]
    assert not any(s.get("_extrativo") for s in segs)
    assert segs[0]["roteiro"].startswith("Na política")


def test_cota_diaria_esgotada_pula_o_modelo(monkeypatch):
    cfg = {**carregar_yaml("config.yaml"), "intervalo_ia_s": 0}
    r = _redator(monkeypatch, cfg)
    r.cliente, r.provedor = ("url", "token"), "gemini"
    monkeypatch.setattr("boletim.redator.time.sleep", lambda s: None)
    usados = []

    def falso_texto(sistema, pedido, max_tokens, modelo):
        usados.append(modelo)
        if modelo == "gemini-3.8-flash":
            raise RuntimeError('HTTP 429: {"quotaId": "GenerateRequestsPerDayPerProjectPerModel-FreeTier"}')
        return '{"itens": [], "roteiro": "ok"}'

    monkeypatch.setattr(r, "_texto", falso_texto)
    assert r._chamar("pedido")["roteiro"] == "ok"
    assert r._chamar("pedido")["roteiro"] == "ok"
    assert usados.count("gemini-3.8-flash") == 1  # não insiste no modelo sem cota


def test_vozes_sao_monolingues_ptbr():
    cfg = carregar_yaml("config.yaml")
    for chave in ("voz_tts", "voz_tts_secundaria", "voz_tts_reserva"):
        assert cfg[chave].startswith("pt-BR-") and "Multilingual" not in cfg[chave], chave


def test_tempos_itens_seguem_a_locucao_real():
    itens = [{"titulo": "Senado aprova reforma tributária", "texto": "Votação final no plenário do Senado."},
             {"titulo": "Dólar recua frente ao real", "texto": "Moeda americana fecha em queda com juros."},
             {"titulo": "Vacina contra dengue ampliada", "texto": "Ministério amplia faixa etária da vacinação."}]
    marcas = [(3.0, 6.0, "Agora, os destaques da política e da economia."),  # transição: sem manchete nova
              (6.5, 30.0, "O Senado aprovou a reforma tributária em votação final no plenário."),
              (30.5, 32.0, "É um passo importante."),                      # comentário curto: mantém a manchete
              (32.5, 70.0, "Na saúde, o ministério ampliou a faixa etária da vacina contra a dengue."),
              (70.5, 90.0, "E o dólar recua frente ao real, com a moeda americana em queda.")]
    t = video.tempos_itens(itens, marcas, 92.0, inicio=3.0)
    assert t[0] == (6.5, 32.5)
    assert t[2] == (32.5, 70.5)   # narrado antes do item 1: a ordem segue o áudio, não a lista
    assert t[1] == (70.5, 92.0)


def test_tempos_itens_item_nao_narrado_e_fallback():
    itens = [{"titulo": "Senado aprova reforma tributária", "texto": "Votação no plenário."},
             {"titulo": "Eclipse visto na Ásia", "texto": "Fenômeno astronômico raro."}]
    t = video.tempos_itens(itens, [(3.0, 20.0, "O Senado aprovou a reforma tributária no plenário.")], 21.0)
    assert t == [(3.0, 21.0), None]
    uniforme = video.tempos_itens(itens, [(3.0, 20.0, "Bom dia a todos.")], 23.0)
    assert uniforme == [(3.0, 13.0), (13.0, 23.0)]


@pytest.mark.skipif(not shutil.which("ffmpeg"), reason="ffmpeg ausente")
def test_marcas_do_audio_e_video_sincronizado(tmp_path, monkeypatch):
    from boletim import audio

    async def falso_edge(texto, voz, mp3, rate):  # 1 s de áudio por bloco
        audio._ff("-f", "lavfi", "-i", "sine=f=440:d=1", "-ar", "24000", "-ac", "1", "-b:a", "48k", str(mp3))
        return [(0.0, 1.0, texto)]

    monkeypatch.setattr(audio, "_edge", falso_edge)
    mp3, marcas = tmp_path / "fala.mp3", []
    audio.sintetizar("Senado aprova reforma tributária no plenário.\n\nDólar recua frente ao real hoje.", "v", mp3,
                     pausa=0.5, marcas=marcas)
    assert len(marcas) == 2
    assert marcas[0][0] == pytest.approx(0.0, abs=0.05) and marcas[1][0] == pytest.approx(1.5, abs=0.2)
    assert marcas[-1][1] == pytest.approx(audio.duracao(mp3), abs=0.05)
    seg = {"id": "economia", "titulo": "Economia", "cor": "#0E3B2E", "cor2": "#1E7A5A",
           "itens": [{"titulo": "Senado aprova reforma tributária", "texto": "No plenário.", "regiao": "brasil",
                      "fontes": ["Agência Senado"]},
                     {"titulo": "Dólar recua frente ao real", "texto": "Hoje.", "regiao": "brasil",
                      "fontes": ["Agência Brasil"]}]}
    d = audio.duracao(mp3)
    tempos = video.tempos_itens(seg["itens"], marcas, d, inicio=0.0)
    assert tempos[0][0] < tempos[1][0] == pytest.approx(marcas[1][0])
    mp4 = tmp_path / "v.mp4"
    video.render_segmento(seg, mp3, None, d, mp4, "Brasil e Mundo Hoje", "hoje", "320x180", tempos=tempos)
    assert mp4.stat().st_size > 1000
