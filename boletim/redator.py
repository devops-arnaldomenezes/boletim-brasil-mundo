"""Redação do boletim: resumo escrito por seção + roteiro de locução (podcast/vídeo).

Provedores de IA (config.yaml → provedor_ia):
  github    – GitHub Models, GRATUITO dentro do GitHub Actions (usa o GITHUB_TOKEN, sem cadastro extra)
  gemini    – Google Gemini, camada gratuita (segredo GEMINI_API_KEY)
  anthropic – Claude, pago (segredo ANTHROPIC_API_KEY)
Sem credencial disponível, cai num modo extrativo simples (sem IA).
"""
from __future__ import annotations

import json
import os
import re
import time
import urllib.error
import urllib.request

from .coletor import Noticia
from .util import log

SISTEMA = """Você é editor-chefe e locutor do boletim diário "{titulo}", um jornal em áudio e vídeo em português do Brasil.
Regras inegociáveis:
- Use SOMENTE os fatos presentes nas notícias fornecidas. Não invente números, nomes, datas ou declarações.
- Traduza para português do Brasil o conteúdo em outros idiomas.
- Atribua a informação à fonte ("segundo a Agência Brasil", "de acordo com a ONU News").
- Tom jornalístico, sóbrio e imparcial; diferencie fato de opinião; evite adjetivos de juízo.
- Agrupe notícias sobre o mesmo assunto; priorize impacto para o público brasileiro, depois Europa, EUA e Ásia.
- Texto do roteiro é para ser LIDO EM VOZ ALTA: frases curtas, números por extenso quando ajudar a leitura,
  sem markdown, sem listas, sem URLs, sem emojis. Siglas na primeira menção devem ser explicadas."""

PEDIDO_SECAO = """Data: {data}. Seção: "{secao}".
A seguir, {n} notícias coletadas nas últimas 24 horas (JSON). Produza a seção do boletim.

Responda APENAS com um JSON válido neste formato:
{{
  "itens": [{{"titulo": "título curto em português", "texto": "resumo de 2 a 4 frases", "regiao": "brasil|europa|eua|asia|global", "fontes": ["nome da fonte"], "links": ["url"]}}],
  "roteiro": "texto corrido para locução desta seção, com cerca de {palavras} palavras, começando com uma transição natural para a seção {secao}"
}}
Selecione de {min_itens} a {max_itens} itens mais relevantes.

Notícias:
{noticias}"""

PEDIDO_REVISAO = """Você é o revisor de checagem de fatos. Compare a seção gerada com as notícias-fonte.
Remova ou corrija qualquer afirmação (número, nome, data, citação) que NÃO esteja nas fontes, corrija atribuições
erradas e mantenha o tamanho aproximado do roteiro. Responda APENAS com o JSON corrigido, no mesmo formato.
Se estiver tudo correto, devolva o JSON igual.

Notícias-fonte:
{noticias}

Seção gerada:
{gerado}"""

PEDIDO_ABERTURA = """Data: {data}. Escreva a ABERTURA do boletim "{titulo}".
Cumprimente o ouvinte (bom dia), diga a data por extenso e apresente as principais manchetes do dia em forma de
escalada, com base nas notícias abaixo. Cerca de {palavras} palavras.
Responda APENAS com JSON: {{"itens": [{{"titulo": "...", "texto": "1 a 2 frases", "regiao": "...", "fontes": ["..."], "links": ["..."]}}], "roteiro": "..."}}
Notícias:
{noticias}"""

PEDIDO_ENCERRAMENTO = """Data: {data}. Escreva o ENCERRAMENTO do boletim "{titulo}".
Com base nos resumos das seções abaixo, faça uma recapitulação dos 5 pontos mais importantes do dia, cite o que
acompanhar nas próximas horas (apenas o que estiver nos resumos) e despeça-se, lembrando que o boletim é publicado
todos os dias às 6h. Cerca de {palavras} palavras.
Responda APENAS com JSON: {{"itens": [{{"titulo": "...", "texto": "...", "regiao": "global", "fontes": [], "links": []}}], "roteiro": "..."}}
Resumos:
{resumos}"""


def _json_noticias(itens: list[Noticia]) -> str:
    return json.dumps([{"titulo": n.titulo, "resumo": n.resumo[:450], "fonte": n.fonte, "regiao": n.regiao,
                        "link": n.link, "publicado": n.publicado[:16]} for n in itens], ensure_ascii=False)


def _extrair_json(texto: str) -> dict:
    m = re.search(r"\{.*\}", texto, re.S)
    if not m:
        raise ValueError("Resposta sem JSON")
    return json.loads(m.group(0))


class Redator:
    def __init__(self, cfg: dict):
        self.cfg = cfg
        escolha = cfg.get("provedor_ia", "auto")
        # "auto": usa o primeiro provedor com credencial disponível, nesta ordem
        ordem = ["anthropic", "gemini", "github"] if escolha == "auto" else [escolha]
        self.falhas_ia = 0
        self.cliente = None
        self.provedor = ordem[0]
        for prov in ordem:
            if prov == "anthropic" and os.environ.get("ANTHROPIC_API_KEY"):
                import anthropic
                self.cliente = anthropic.Anthropic()
            elif prov == "gemini" and os.environ.get("GEMINI_API_KEY"):
                self.cliente = ("https://generativelanguage.googleapis.com/v1beta/openai/chat/completions",
                                os.environ["GEMINI_API_KEY"])
            elif prov == "github" and os.environ.get("GITHUB_TOKEN"):
                self.cliente = ("https://models.github.ai/inference/chat/completions", os.environ["GITHUB_TOKEN"])
            if self.cliente:
                self.provedor = prov
                log.info("Provedor de IA: %s", prov)
                break
        if not self.cliente:
            log.warning("Sem credencial para o provedor '%s': usando modo extrativo (sem IA).", self.provedor)

    # ------------------------------------------------------------------ IA
    def _texto(self, sistema: str, pedido: str, max_tokens: int) -> str:
        modelo = self.cfg["modelos_ia"][self.provedor]
        if self.provedor == "anthropic":
            resp = self.cliente.messages.create(model=modelo, max_tokens=max_tokens, system=sistema,
                                                messages=[{"role": "user", "content": pedido}])
            return "".join(b.text for b in resp.content if getattr(b, "type", "") == "text")
        url, token = self.cliente  # API compatível com OpenAI (GitHub Models / Gemini)
        corpo = json.dumps({"model": modelo, "max_tokens": max_tokens, "temperature": 0.3,
                            "messages": [{"role": "system", "content": sistema},
                                         {"role": "user", "content": pedido}]}).encode()
        req = urllib.request.Request(url, data=corpo, headers={"Authorization": f"Bearer {token}",
                                                               "Content-Type": "application/json",
                                                               "Accept": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=180) as r:
                bruto = r.read().decode("utf-8", "replace")
                status = r.status
        except urllib.error.HTTPError as e:
            raise RuntimeError(f"HTTP {e.code}: {e.read().decode('utf-8', 'replace')[:400]}") from e
        try:
            return json.loads(bruto)["choices"][0]["message"]["content"]
        except (json.JSONDecodeError, KeyError, IndexError) as e:
            raise RuntimeError(f"Resposta inesperada (HTTP {status}): {bruto[:400]!r}") from e

    def _chamar(self, pedido: str, max_tokens: int = 4000) -> dict:
        sistema = SISTEMA.format(titulo=self.cfg["titulo"])
        for tentativa in range(3):
            try:
                texto = self._texto(sistema, pedido, max_tokens)
            except Exception as e:  # noqa: BLE001  (limite de uso, rede etc.)
                log.warning("Erro na IA (tentativa %d): %s", tentativa + 1, e)
                time.sleep(20 * (tentativa + 1))
                continue
            try:
                return _extrair_json(texto)
            except (ValueError, json.JSONDecodeError) as e:
                log.warning("JSON inválido (tentativa %d): %s", tentativa + 1, e)
        raise RuntimeError("Falha ao obter JSON do modelo")

    # -------------------------------------------------------------- público
    def escrever(self, data_extenso: str, grupos: dict[str, list[Noticia]]) -> list[dict]:
        """Retorna lista de segmentos: {id, titulo, cor, cor2, itens, roteiro}."""
        secoes = self.cfg["secoes"]
        total_palavras = self.cfg["duracao_alvo_min"] * self.cfg["palavras_por_minuto"]
        miolo = [s for s in secoes if s["id"] not in ("destaques", "encerramento")]
        p_abertura, p_fim = int(total_palavras * 0.10), int(total_palavras * 0.07)
        p_secao = int((total_palavras - p_abertura - p_fim) / max(len(miolo), 1))

        segmentos = []
        for s in secoes:
            itens = grupos.get(s["id"], [])
            if s["id"] == "encerramento":
                continue
            if not itens:
                log.warning("Seção %s sem notícias; pulando.", s["id"])
                continue
            orcamento = p_abertura if s["id"] == "destaques" else p_secao
            if self.cliente and self.falhas_ia < 2:  # disjuntor: após 2 falhas, segue sem IA
                if s["id"] == "destaques":
                    pedido = PEDIDO_ABERTURA.format(data=data_extenso, titulo=self.cfg["titulo"],
                                                    palavras=p_abertura, noticias=_json_noticias(itens))
                else:
                    pedido = PEDIDO_SECAO.format(data=data_extenso, secao=s["titulo"], n=len(itens),
                                                 palavras=p_secao, min_itens=5, max_itens=9,
                                                 noticias=_json_noticias(itens))
                try:
                    conteudo = self._chamar(pedido)
                except RuntimeError as e:
                    log.error("IA indisponível na seção %s (%s); usando modo extrativo.", s["id"], e)
                    self.falhas_ia += 1
                    conteudo = self._extrativo(s, itens, data_extenso, orcamento)
                if self.cfg.get("revisao_ia", True) and not conteudo.get("_extrativo"):
                    try:
                        revisado = self._chamar(PEDIDO_REVISAO.format(
                            noticias=_json_noticias(itens), gerado=json.dumps(conteudo, ensure_ascii=False)))
                        if revisado.get("roteiro") and len(revisado["roteiro"]) > 0.6 * len(conteudo["roteiro"]):
                            conteudo = revisado
                    except RuntimeError as e:
                        log.warning("Revisão da seção %s falhou; mantendo versão original: %s", s["id"], e)
            else:
                conteudo = self._extrativo(s, itens, data_extenso, orcamento)
            log.info("Seção %-12s %4d palavras", s["id"], len(conteudo["roteiro"].split()))
            segmentos.append({**s, **conteudo})

        fim = next((s for s in secoes if s["id"] == "encerramento"), None)
        if fim:
            if self.cliente and not self.falhas_ia:
                resumos = "\n".join(f"[{seg['titulo']}] " + " | ".join(i["titulo"] + ": " + i["texto"]
                                                                       for i in seg["itens"]) for seg in segmentos)
                try:
                    conteudo = self._chamar(PEDIDO_ENCERRAMENTO.format(data=data_extenso, titulo=self.cfg["titulo"],
                                                                       palavras=p_fim, resumos=resumos))
                except RuntimeError as e:
                    log.error("IA indisponível no encerramento (%s).", e)
                    self.falhas_ia += 1
                    conteudo = None
            else:
                conteudo = None
            if conteudo is None:
                conteudo = {"itens": [], "roteiro": f"Este foi o {self.cfg['titulo']} de {data_extenso}. "
                            "O próximo boletim será publicado amanhã, às seis da manhã. Até lá!"}
            segmentos.append({**fim, **conteudo})
        return segmentos

    # ------------------------------------------------------------ fallback
    def _extrativo(self, s: dict, itens: list[Noticia], data_extenso: str, palavras: int = 0) -> dict:
        # Sem IA, a meta de duração é atingida lendo mais notícias reais coletadas (no mínimo 8, se houver).
        sel, total = [], 0
        for n in itens:
            if len(sel) >= 8 and total >= palavras:
                break
            sel.append(n)
            total += len(f"{n.fonte} {n.titulo} {n.resumo[:240]}".split()) + 1
        lista = [{"titulo": n.titulo, "texto": (n.resumo[:300] or n.titulo), "regiao": n.regiao,
                  "fontes": [n.fonte], "links": [n.link]} for n in sel]
        if s["id"] == "destaques":
            abertura = f"Bom dia! Este é o {self.cfg['titulo']}, edição de {data_extenso}. Os destaques de hoje. "
        else:
            abertura = f"Agora, {s['titulo']}. "
        corpo = " ".join(f"Segundo {n.fonte}: {n.titulo}. {n.resumo[:240]}" for n in sel)
        return {"itens": lista, "roteiro": abertura + corpo, "_extrativo": True}
