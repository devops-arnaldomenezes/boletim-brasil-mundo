"""Memória do agente entre execuções (estado/estado.json, versionado no repositório).

Permite que o boletim se ajuste sozinho:
- saúde das fontes: feeds que falham 7 dias seguidos são pausados e re-testados semanalmente;
- ritmo de locução medido: calibra o tamanho do roteiro para cair entre 30 e 45 minutos.
"""
from __future__ import annotations

import json
from datetime import date

from .util import RAIZ

ARQ = RAIZ / "estado" / "estado.json"
DIAS_PARA_PAUSAR = 7


def carregar() -> dict:
    if ARQ.exists():
        return json.loads(ARQ.read_text(encoding="utf-8"))
    return {"fontes": {}, "ppm_medido": None}


def salvar(estado: dict) -> None:
    ARQ.parent.mkdir(exist_ok=True)
    ARQ.write_text(json.dumps(estado, ensure_ascii=False, indent=1, sort_keys=True), encoding="utf-8")


def fonte_ativa(estado: dict, nome: str, hoje: date) -> bool:
    f = estado["fontes"].get(nome, {})
    if f.get("falhas_seguidas", 0) < DIAS_PARA_PAUSAR:
        return True
    return hoje.toordinal() % 7 == 0  # pausada: tenta de novo uma vez por semana


def registrar_fonte(estado: dict, nome: str, ok: bool, itens: int, hoje: date) -> None:
    f = estado["fontes"].setdefault(nome, {"falhas_seguidas": 0})
    if ok:
        f.update(falhas_seguidas=0, ultimo_ok=hoje.isoformat(), itens_ultimo=itens)
    else:
        f["falhas_seguidas"] = f.get("falhas_seguidas", 0) + 1


def registrar_ritmo(estado: dict, palavras: int, segundos: float) -> float:
    medido = palavras / (segundos / 60)
    anterior = estado.get("ppm_medido")
    estado["ppm_medido"] = round(medido if not anterior else 0.7 * anterior + 0.3 * medido, 1)
    return estado["ppm_medido"]


def pausadas(estado: dict) -> list[str]:
    return sorted(n for n, f in estado["fontes"].items() if f.get("falhas_seguidas", 0) >= DIAS_PARA_PAUSAR)


def registrar_extensao(estado: dict, escritas: int, pedidas: int) -> float:
    """Aprende quanto a IA costuma encurtar o texto e ajusta o pedido das próximas edições."""
    fator = estado.get("fator_extensao") or 1.0
    if escritas > 0 and pedidas > 0:
        alvo = fator * pedidas / escritas
        fator = max(1.0, min(2.5, 0.6 * fator + 0.4 * alvo))
    estado["fator_extensao"] = round(fator, 2)
    return estado["fator_extensao"]
