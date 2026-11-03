---
name: revisar-edicao
description: Revisa a qualidade editorial de uma edição do boletim (precisão contra as fontes, equilíbrio regional e temático, clareza para locução) e ajusta prompts ou classificação. Use após uma edição ou quando o dono reclamar de conteúdo.
---

# Revisar edição

Entrada: `edicoes/AAAA/MM/DD/` (`roteiro.json`, `noticias.json`, `relatorio.json`, `boletim.md`).

## Checagens
1. **Precisão:** sorteie 8 itens de `roteiro.json`; cada número, nome e citação deve existir em `noticias.json`
   (título ou resumo da fonte citada). Qualquer afirmação sem suporte = falha grave.
2. **Equilíbrio:** conte itens por região (brasil, europa, eua, asia, global) e por seção. Meta: Brasil ≥ 30%,
   cada uma das outras regiões ≥ 10%, nenhuma seção vazia.
3. **Fontes oficiais:** ao menos 25% dos itens vindos de fontes `oficial` ou `multilateral`.
4. **Locução:** roteiro sem markdown, URLs, listas ou siglas sem explicação; frases curtas.
5. **Resumo escrito:** conclusão primeiro, 2 a 4 frases por item (princípios de resumo executivo).

## Ações
- Falhas de precisão → reforce `SISTEMA`/`PEDIDO_REVISAO` em `boletim/redator.py`.
- Desequilíbrio → ajuste `PESO_REGIAO`/`PALAVRAS` em `boletim/classificador.py` ou fontes em `config/fontes.yaml`.
- Valide com `pytest -q` e a fixture antes de fazer commit. Registre o resultado em `docs/revisoes.md`
  (data, nota de 0 a 10 por checagem, mudanças feitas).
