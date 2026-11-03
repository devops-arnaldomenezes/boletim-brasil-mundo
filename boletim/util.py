import hashlib
import logging
import re
import unicodedata
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import yaml

RAIZ = Path(__file__).resolve().parent.parent
log = logging.getLogger("boletim")


def carregar_yaml(nome: str) -> dict:
    with open(RAIZ / "config" / nome, encoding="utf-8") as f:
        return yaml.safe_load(f)


def agora(fuso: str) -> datetime:
    return datetime.now(ZoneInfo(fuso))


def normalizar(texto: str) -> str:
    texto = unicodedata.normalize("NFKD", texto or "").encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9 ]+", " ", texto.lower()).strip()


def limpar_html(texto: str) -> str:
    texto = re.sub(r"<[^>]+>", " ", texto or "")
    texto = re.sub(r"&nbsp;|&#160;", " ", texto)
    return re.sub(r"\s+", " ", texto).strip()


def chave(texto: str) -> str:
    return hashlib.sha1(normalizar(texto).encode()).hexdigest()[:12]


DIAS = ["segunda-feira", "terça-feira", "quarta-feira", "quinta-feira", "sexta-feira", "sábado", "domingo"]
MESES = ["janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho", "agosto",
         "setembro", "outubro", "novembro", "dezembro"]


def data_extenso(d: datetime) -> str:
    return f"{DIAS[d.weekday()]}, {d.day} de {MESES[d.month - 1]} de {d.year}"
