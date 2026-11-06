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
from .idioma import limpar_resumo, limpar_titulo, noticia_estrangeira, so_portugues
from .util import log

SISTEMA = """Você é editor-chefe e locutor do boletim diário "{titulo}", um jornal em áudio e vídeo em português do Brasil.
Regras inegociáveis:
- Use SOMENTE os fatos presentes nas notícias fornecidas. Não invente números, nomes, datas ou declarações.
- TODO o texto (títulos, resumos e roteiro) é em português do Brasil. Notícias em inglês ou outro idioma devem ser
  TRADUZIDAS e reescritas em português; nunca copie frases, títulos ou citações no idioma original. Mantenha apenas
  nomes próprios (pessoas, empresas, veículos) como são.
- Atribua a informação à fonte ("segundo a Agência Brasil", "de acordo com a ONU News").
- Tom jornalístico, sóbrio e imparcial; diferencie fato de opinião; evite adjetivos de juízo.
- Agrupe notícias sobre o mesmo assunto; priorize impacto para o público brasileiro, depois Europa, EUA e Ásia.
- Texto do roteiro é para ser LIDO EM VOZ ALTA: frases curtas, números por extenso quando ajudar a leitura,
  sem markdown, sem listas, sem URLs, sem emojis. Siglas na primeira menção devem ser explicadas.
- Escreva como um apresentador de rádio conversando com o ouvinte: linguagem simples e fluida, frases de 8 a 20
  palavras com ritmo variado, transições naturais e diferentes entre as notícias. Não comece frases seguidas
  do mesmo jeito, não repita o nome do programa nem a data a cada seção e prefira "segundo a fonte" no fim da frase.
- No roteiro, cada notícia fica em um parágrafo próprio, separado por uma linha em branco (\\n\\n no JSON)."""

PEDIDO_SECAO = """Data: {data}. Seção: "{secao}".
A seguir, {n} notícias coletadas nas últimas 24 horas (JSON). Produza a seção do boletim.

Responda APENAS com um JSON válido neste formato:
{{
  "itens": [{{"titulo": "título curto em português", "texto": "resumo de 2 a 4 frases", "regiao": "brasil|latam|europa|eua|asia|global", "fontes": ["nome da fonte"], "links": ["url"]}}],
  "roteiro": "texto corrido para locução desta seção, começando com uma transição natural para a seção {secao}"
}}
Selecione de {min_itens} a {max_itens} itens mais relevantes.
IMPORTANTE: o roteiro DEVE ter NO MÍNIMO {palavras} palavras (a duração do programa depende disso).
Dedique cerca de {por_item} palavras a cada item: o fato, o contexto e por que importa, sempre com base nas fontes.

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


def _normalizar(conteudo) -> dict:
    """Garante o formato esperado da resposta da IA (itens com titulo/texto/regiao/fontes/links e roteiro).

    A IA às vezes omite campos (04/11/2026: item sem "texto" derrubou a edição). Itens sem título nem texto
    são descartados; nada é inventado, apenas os campos ausentes ficam vazios."""
    if not isinstance(conteudo, dict):
        raise RuntimeError("Resposta da IA não é um objeto JSON")
    itens = []
    for i in conteudo.get("itens") or []:
        if not isinstance(i, dict):
            continue
        titulo, texto = str(i.get("titulo") or "").strip(), str(i.get("texto") or "").strip()
        if not titulo and not texto:
            continue
        fontes, links = i.get("fontes") or [], i.get("links") or []
        itens.append({**i, "titulo": titulo or texto[:80], "texto": texto, "regiao": i.get("regiao") or "global",
                      "fontes": fontes if isinstance(fontes, list) else [str(fontes)],
                      "links": links if isinstance(links, list) else [str(links)]})
    roteiro = conteudo.get("roteiro")
    return {**conteudo, "itens": itens, "roteiro": roteiro.strip() if isinstance(roteiro, str) else ""}


class Redator:
    def __init__(self, cfg: dict):
        self.cfg = cfg
        escolha = cfg.get("provedor_ia", "auto")
        # "auto": usa o primeiro provedor com credencial disponível, nesta ordem
        ordem = ["anthropic", "gemini", "github"] if escolha == "auto" else [escolha]
        self.falhas_ia = 0
        self.falhas_seguidas = 0
        self.esgotados: set[str] = set()
        self.palavras_ia = [0, 0]  # [escritas pela IA, pedidas] para calibrar o fator de extensão
        self.intervalo = float(cfg.get("intervalo_ia_s", 8))
        self._ultima = 0.0
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
    def _modelos(self) -> list[str]:
        m = self.cfg["modelos_ia"][self.provedor]
        return m if isinstance(m, list) else [m]

    def _texto(self, sistema: str, pedido: str, max_tokens: int, modelo: str) -> str:
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
            raise RuntimeError(f"HTTP {e.code}: {e.read().decode('utf-8', 'replace')[:3000]}") from e
        try:
            return json.loads(bruto)["choices"][0]["message"]["content"]
        except (json.JSONDecodeError, KeyError, IndexError) as e:
            raise RuntimeError(f"Resposta inesperada (HTTP {status}): {bruto[:400]!r}") from e

    def _chamar(self, pedido: str, max_tokens: int = 4000) -> dict:
        sistema = SISTEMA.format(titulo=self.cfg["titulo"])
        for tentativa in range(4):
            # modelos com a cota DIÁRIA esgotada ficam de fora até o fim da execução (não adianta insistir)
            modelos = [m for m in self._modelos() if m not in self.esgotados]
            if not modelos:
                raise RuntimeError("cota diária esgotada em todos os modelos")
            espera = self.intervalo - (time.monotonic() - self._ultima)
            if espera > 0:  # respeita o limite por minuto das camadas gratuitas
                time.sleep(espera)
            self._ultima = time.monotonic()
            # alterna entre os modelos configurados: se um está sobrecarregado (503), tenta o próximo
            modelo = modelos[tentativa % len(modelos)]
            try:
                texto = self._texto(sistema, pedido, max_tokens, modelo)
            except Exception as e:  # noqa: BLE001  (limite de uso, rede etc.)
                erro = str(e)
                log.warning("Erro na IA (tentativa %d, %s): %s", tentativa + 1, modelo, erro[:200])
                if "HTTP 429" in erro and re.search(r"PerDay|per day|daily", erro, re.I):
                    log.warning("Cota diária do modelo %s esgotada; seguindo com os demais.", modelo)
                    self.esgotados.add(modelo)
                    continue
                pedida = re.search(r'"retryDelay":\s*"(\d+)', erro)  # o Gemini informa quanto esperar
                base = 30 if "HTTP 429" in erro else (5 if len(modelos) > 1 else 30)
                time.sleep(min(int(pedida.group(1)) + 2, 120) if pedida else base * (tentativa + 1))
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

        fator = float(self.cfg.get("fator_extensao") or 1.0)  # aprendido em estado.json
        segmentos, pendentes = [], []
        for s in secoes:
            itens = grupos.get(s["id"], [])
            if s["id"] == "encerramento":
                continue
            if not itens:
                log.warning("Seção %s sem notícias; pulando.", s["id"])
                continue
            orcamento = p_abertura if s["id"] == "destaques" else p_secao
            conteudo = None
            if self.cliente and self.falhas_seguidas < 2:  # disjuntor: após 2 falhas seguidas, deixa para a repescagem
                conteudo = self._secao_ia(s, itens, data_extenso, orcamento, p_secao, fator)
            if conteudo is None:
                conteudo = self._extrativo(s, itens, data_extenso, orcamento)
                if self.cliente:
                    pendentes.append(len(segmentos))
            segmentos.append({**s, **conteudo, "_itens_fonte": itens, "_orcamento": orcamento})

        # Repescagem: a cota gratuita do Gemini costuma voltar em minutos (503/429). Em vez de publicar seções
        # extrativas, espera e tenta de novo (o workflow começa horas antes das 6h, há tempo de sobra).
        for espera in (self.cfg.get("repescagem_ia_s") or []) if pendentes else []:
            log.info("Repescagem da IA em %ds para %d seções: %s", espera, len(pendentes),
                     ", ".join(segmentos[k]["id"] for k in pendentes))
            time.sleep(espera)
            self.falhas_seguidas = 0
            for k in list(pendentes):
                seg = segmentos[k]
                conteudo = self._secao_ia(seg, seg["_itens_fonte"], data_extenso, seg["_orcamento"], p_secao, fator)
                if conteudo is None:
                    break
                segmentos[k] = {**seg, **conteudo}
                segmentos[k].pop("_extrativo", None)
                pendentes.remove(k)
            if not pendentes:
                break

        for k, seg in enumerate(segmentos):
            itens, orcamento = seg.pop("_itens_fonte"), seg.pop("_orcamento")
            conteudo = self._completar(seg, {c: seg[c] for c in ("itens", "roteiro", "_extrativo") if c in seg},
                                       itens, orcamento)
            seg.update(conteudo)
            seg["roteiro"] = self._garantir_portugues(seg["id"], seg["roteiro"])
            log.info("Seção %-12s %4d palavras%s", seg["id"], len(seg["roteiro"].split()),
                     " (extrativo)" if seg.get("_extrativo") else "")

        fim = next((s for s in secoes if s["id"] == "encerramento"), None)
        if fim:
            if self.cliente and self.falhas_seguidas < 2:
                resumos = "\n".join(f"[{seg['titulo']}] " + " | ".join(i.get("titulo", "") + ": " + i.get("texto", "")
                                                                       for i in seg["itens"]) for seg in segmentos)
                try:
                    conteudo = _normalizar(self._chamar(PEDIDO_ENCERRAMENTO.format(
                        data=data_extenso, titulo=self.cfg["titulo"], palavras=p_fim, resumos=resumos)))
                    if not conteudo["roteiro"]:
                        conteudo = None
                except RuntimeError as e:
                    log.error("IA indisponível no encerramento (%s).", e)
                    self.falhas_ia += 1
                    conteudo = None
            else:
                conteudo = None
            if conteudo is not None:
                conteudo["roteiro"] = self._garantir_portugues("encerramento", conteudo["roteiro"])
            if conteudo is None or not conteudo["roteiro"]:
                conteudo = {"itens": [], "roteiro": f"Este foi o {self.cfg['titulo']} de {data_extenso}. "
                            "O próximo boletim será publicado amanhã, às seis da manhã. Até lá!"}
            segmentos.append({**fim, **conteudo})
        return segmentos

    def _secao_ia(self, s: dict, itens: list[Noticia], data_extenso: str, orcamento: int, p_secao: int,
                  fator: float) -> dict | None:
        """Escreve a seção com a IA (e revisão, se ativa). Retorna None se a IA falhar."""
        if s["id"] == "destaques":
            pedido = PEDIDO_ABERTURA.format(data=data_extenso, titulo=self.cfg["titulo"],
                                            palavras=int(orcamento * fator), noticias=_json_noticias(itens))
        else:
            pedir = int(p_secao * fator)
            pedido = PEDIDO_SECAO.format(data=data_extenso, secao=s["titulo"], n=len(itens),
                                         palavras=pedir, min_itens=7, max_itens=10,
                                         por_item=max(60, pedir // 9), noticias=_json_noticias(itens))
        try:
            conteudo = _normalizar(self._chamar(pedido))
            if not conteudo["roteiro"]:
                raise RuntimeError("resposta sem roteiro")
        except RuntimeError as e:
            log.error("IA indisponível na seção %s (%s); usando modo extrativo por ora.", s["id"], e)
            self.falhas_ia += 1
            self.falhas_seguidas += 1
            return None
        self.falhas_seguidas = 0
        self.palavras_ia[0] += len(conteudo["roteiro"].split())
        self.palavras_ia[1] += orcamento
        revisar = self.cfg.get("revisao_ia", "auto")
        revisar = (self.provedor == "anthropic") if revisar == "auto" else bool(revisar)
        if revisar:
            try:
                revisado = _normalizar(self._chamar(PEDIDO_REVISAO.format(
                    noticias=_json_noticias(itens), gerado=json.dumps(conteudo, ensure_ascii=False))))
                if revisado.get("roteiro") and len(revisado["roteiro"]) > 0.6 * len(conteudo["roteiro"]):
                    conteudo = revisado
            except RuntimeError as e:
                log.warning("Revisão da seção %s falhou; mantendo versão original: %s", s["id"], e)
        return conteudo

    @staticmethod
    def _garantir_portugues(secao: str, roteiro: str) -> str:
        """Última barreira antes do TTS: nenhuma frase em inglês é lida (05/11/2026)."""
        texto, removidas = so_portugues(roteiro)
        if removidas:
            log.warning("Seção %s: %d frase(s) em inglês removida(s) da locução.", secao, removidas)
        return texto

    def _completar(self, s: dict, conteudo: dict, itens: list[Noticia], orcamento: int) -> dict:
        """Se a IA escreveu bem menos que o orçamento, completa com outras notícias reais da seção."""
        faltam = int(orcamento * 0.85) - len(conteudo["roteiro"].split())
        if conteudo.get("_extrativo") or faltam < 80 or s["id"] == "destaques":
            return conteudo
        usados = {i.get("titulo", "") for i in conteudo.get("itens", [])}
        links = {l for i in conteudo.get("itens", []) for l in i.get("links", [])}
        resto = [n for n in itens if n.link not in links and n.titulo not in usados]
        if not resto:
            return conteudo
        extra = self._extrativo(s, resto, "", faltam)
        texto = extra["roteiro"].split("\n\n", 1)[1] if "\n\n" in extra["roteiro"] else ""
        if not texto:
            return conteudo
        log.info("Seção %s curta; completando com %d notícias extras.", s["id"], len(extra["itens"]))
        return {**conteudo, "itens": conteudo["itens"] + extra["itens"],
                "roteiro": conteudo["roteiro"] + f"\n\nOutras notícias de {s['titulo'].lower()}.\n\n" + texto}

    # ------------------------------------------------------------ fallback
    @staticmethod
    def _par_extrativo(n: Noticia, resumo: str) -> str:
        return f"{limpar_titulo(n.titulo)}, segundo {n.fonte}. {resumo}".strip()

    def _extrativo(self, s: dict, itens: list[Noticia], data_extenso: str, palavras: int = 0) -> dict:
        """Sem IA: lê notícias reais coletadas, só as que já estão em português (sem IA não há tradução), uma por
        parágrafo, com o resumo limpo e cortado em frase completa. A meta de duração é buscada lendo mais notícias
        (no mínimo 8, se houver)."""
        sel, total = [], 0
        for n in itens:
            if noticia_estrangeira(n):
                continue
            if len(sel) >= 8 and total >= palavras:
                break
            resumo = limpar_resumo(n.resumo)
            if resumo and resumo.rstrip(".").lower() in n.titulo.lower():
                resumo = ""
            sel.append((n, resumo))
            total += len(self._par_extrativo(n, resumo).split())
        lista = [{"titulo": limpar_titulo(n.titulo), "texto": r or n.titulo, "regiao": n.regiao,
                  "fontes": [n.fonte], "links": [n.link]} for n, r in sel]
        if s["id"] == "destaques":
            abertura = f"Bom dia! Este é o {self.cfg['titulo']}, edição de {data_extenso}. Os destaques de hoje."
        else:
            abertura = f"Agora, {s['titulo']}."
        pars = [self._par_extrativo(n, r) for n, r in sel]
        return {"itens": lista, "roteiro": "\n\n".join([abertura, *pars]), "_extrativo": True}
