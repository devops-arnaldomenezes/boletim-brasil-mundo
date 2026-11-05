"""Garante que a locução saia 100% em português do Brasil.

Em 05/11/2026 a IA gratuita ficou indisponível, seis seções caíram no modo extrativo e a locução leu resumos de
feeds em inglês (e legendas de foto, "The post ... appeared first on ..."). Este módulo detecta texto em inglês
por palavras funcionais, limpa resíduos de feed e filtra frases em inglês antes do TTS."""
from __future__ import annotations

import re

from .util import normalizar

# Palavras funcionais exclusivas de cada idioma (as ambíguas, como "a", "as", "no", "do", "com", ficam de fora).
_EN = set("the of and to in is are was were for on with that this by from at be has have had will would its it's "
          "after over says said new who which what their they been not but than into about amid against".split())
_ES = set("el los las del y con una pero sus tras segun han hasta muy ese esa".split())
_PT = set("de da do das dos que em para com os uma um por nao mais foi ao aos pela pelo pelas pelos sao seu sua "
          "seus suas como tambem entre sobre apos ja ainda segundo isso esta este estao foram nas nos".split())


def contagem(texto: str) -> tuple[int, int, int]:
    """(palavras funcionais em inglês, em espanhol, em português)."""
    palavras = normalizar(texto).split()
    return sum(p in _EN for p in palavras), sum(p in _ES for p in palavras), sum(p in _PT for p in palavras)


def eh_estrangeiro(texto: str) -> bool:
    """Frase/texto predominantemente em inglês ou espanhol."""
    en, es, pt = contagem(texto)
    return (en >= 2 and en > pt) or (es >= 2 and es > pt)


eh_ingles = eh_estrangeiro  # nome antigo


def noticia_estrangeira(n) -> bool:
    """Notícia de feed em outro idioma (en, es...) ou cujo texto não está em português, mesmo em feed marcado pt.
    Sem IA não há tradução, então ela não pode ir para a locução."""
    if str(getattr(n, "idioma", "pt")).lower() not in ("pt", "pt-br"):
        return True
    return eh_estrangeiro(f"{n.titulo}. {limpar_resumo(n.resumo, 300)}")


_RESIDUOS = [
    re.compile(r"The post .*? appeared first on .*?(\.|$)", re.I | re.S),
    re.compile(r"\b(O post|A postagem) .*? apareceu primeiro em .*?(\.|$)", re.I | re.S),
    re.compile(r"\b(Foto|Imagem|Crédito|Reprodução)\s*:\s*[^.]*?(?=\s[A-ZÁÉÍÓÚ]|$)"),
    # créditos de foto: "Vincent Yu/AP", "Kayo Magalhães / Câmara dos Deputados"
    re.compile(r"(?:^|\s)[A-ZÁÉÍÓÚ][\wÀ-ú]+(?: [A-ZÁÉÍÓÚ][\wÀ-ú]+)* ?/ ?(?:AP|AFP|Reuters|EFE|Getty Images|"
               r"Agência Brasil|Agência Senado|Câmara dos Deputados|Divulgação|Reprodução)\b"),
    re.compile(r"^\d{1,2}h\s+"),  # carimbo de hora no início ("2h Habitação. ...")
    re.compile(r"\b(Leia mais|Continue lendo|Saiba mais|Read more)\b.*$", re.I),
    re.compile(r"\[\s*(…|\.\.\.)\s*\]"),
]


def limpar_resumo(texto: str, limite: int = 260) -> str:
    """Remove resíduos de feed e corta numa frase completa (nunca no meio da palavra)."""
    t = texto or ""
    for r in _RESIDUOS:
        t = r.sub(" ", t)
    t = re.sub(r"\s+", " ", t).strip()
    if len(t) <= limite:
        return t if not t or t[-1] in ".!?" else t + "."
    corte = t[:limite]
    fim = max(corte.rfind(". "), corte.rfind("! "), corte.rfind("? "))
    if fim >= 60:
        return corte[: fim + 1]
    return corte[: corte.rfind(" ")].rstrip(",;:") + "."


def limpar_titulo(titulo: str) -> str:
    return re.sub(r"^\d{1,2}h\s+", "", (titulo or "").strip()).rstrip(".")


def so_portugues(roteiro: str) -> tuple[str, int]:
    """Remove do roteiro as frases em inglês/espanhol (preserva os parágrafos). Retorna (texto, frases removidas)."""
    removidas, pars = 0, []
    for par in re.split(r"\n\s*\n", roteiro.strip()):
        frases = re.split(r"(?<=[.!?])\s+", par.strip())
        boas = [f for f in frases if f and not eh_estrangeiro(f)]
        removidas += len([f for f in frases if f]) - len(boas)
        if boas:
            pars.append(" ".join(boas))
    return "\n\n".join(pars), removidas
