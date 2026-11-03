---
name: curar-fontes
description: Mantém a lista de feeds do boletim (config/fontes.yaml): substitui fontes pausadas, reforça seções fracas e mantém o equilíbrio Brasil/Europa/EUA/Ásia com fontes oficiais e confiáveis. Use quando relatorio.json mostrar fontes pausadas ou seções com poucos itens.
---

# Curar fontes

1. Leia `estado/estado.json` (`fontes.*.falhas_seguidas`) e o `relatorio.json` mais recente.
2. Para cada fonte pausada: procure o novo endereço RSS do mesmo veículo (página do site, `/feed`, `/rss`).
   Sem substituto, troque por outra fonte da mesma região e tipo.
3. Critérios de confiabilidade, nesta ordem: órgão oficial ou multilateral (governos, parlamentos, bancos
   centrais, ONU/OMS/FMI/UNESCO) → agência pública de notícias → veículo com política editorial e correções
   públicas. Nada de agregadores anônimos, blogs pessoais ou sites partidários.
4. Valide o feed antes de adicionar:
   ```bash
   python -c "import feedparser,sys; f=feedparser.parse(sys.argv[1]); print(len(f.entries), f.entries[0].title if f.entries else f.bozo_exception)" URL
   ```
5. Edite `config/fontes.yaml` (nome, url, regiao, idioma, tipo, categorias), zere a entrada da fonte em
   `estado/estado.json` se a URL mudou, rode `pytest -q` e faça commit com a justificativa.
