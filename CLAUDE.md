# Boletim "Brasil e Mundo Hoje"

Agente que publica todo dia às 6h (Brasília) um boletim de notícias em texto, podcast (30–45 min) e vídeo.
Comunique-se em português do Brasil.

- Pipeline: `python -m boletim` (coleta → classificação → redação IA → áudio → vídeo → publicação).
- Agendamento: `.github/workflows/boletim-diario.yml` (cron 06:30 UTC, publica às 06:00 BRT).
- IA gratuita por padrão: GitHub Models (`provedor_ia` em `config/config.yaml`).
- Memória do agente: `estado/estado.json` (saúde das fontes, ritmo de locução medido).
- Cada edição: `edicoes/AAAA/MM/DD/` com `boletim.md`, `relatorio.json` (métricas), `noticias.json`, `roteiro.json`.
- MP3/MP4 ficam nas Releases `edicao-AAAA-MM-DD`; site e feed do podcast no GitHub Pages.
- Falhas abrem issue com o rótulo `falha-boletim`.

Regras: nunca inventar notícia nem publicar conteúdo fictício como edição real; não desativar testes;
mudanças pequenas e testadas (`pytest -q` e `python -m boletim --fixture tests/fixtures/noticias.json --sem-video`).

Skills do projeto: `operar-boletim` (checagem diária e correção), `revisar-edicao` (qualidade editorial),
`curar-fontes` (manutenção dos feeds).
