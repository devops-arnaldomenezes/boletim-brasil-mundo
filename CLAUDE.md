# Boletim "Brasil e Mundo Hoje"

Agente que publica todo dia às 6h (Brasília) um boletim de notícias do Brasil e do mundo (ênfase em tecnologia,
IA, política, saúde, economia e cultura; Brasil, Europa, EUA e Ásia) em texto, podcast (30–45 min) e vídeo.
Comunique-se sempre em português do Brasil. Opere com autonomia: diagnostique, corrija, teste e publique sem
pedir confirmação para mudanças pequenas e reversíveis; peça ao dono só o que exige a conta dele (segredos,
configurações do repositório, cobrança).

## Como funciona
- Pipeline: `python -m boletim` (coleta RSS → classificação → redação IA → áudio edge-tts → vídeo ffmpeg + vinhetas
  Manim → publicação). Configuração em `config/config.yaml` e `config/fontes.yaml`.
- Publicação: texto em `edicoes/AAAA/MM/DD/` (`boletim.md`, `relatorio.json`, `noticias.json`, `roteiro.json`);
  MP3/MP4 nas Releases `edicao-AAAA-MM-DD`; site + feed de podcast no GitHub Pages; atalho `edicoes/ULTIMA.md`.
- Áudio/vídeo: locução em blocos com pausas, ritmo natural, vozes alternadas monolíngues pt-BR (Antonio e Francisca;
  nunca vozes *Multilingual*, que trocam para inglês) e tratamento a -16 LUFS. Locução 100% em PT-BR (`boletim/idioma.py`):
  sem IA, só notícias em português vão ao ar, e frases em inglês/espanhol são cortadas antes do TTS. As manchetes do
  vídeo seguem o tempo real de cada bloco falado (`audio.sintetizar(marcas=...)` → `video.tempos_itens`). Sem legendas nem `.srt` desde 05/11/2026 (`legendas: false`).
  Para ouvir mudanças de voz sem refazer a edição: workflow `amostra-voz.yml` (pré-release `amostra-voz`).
- Identidade visual: `marca/GUIA.md` (símbolo globo + órbita âmbar das 6h, azul-noite `#0B1F3A`, âmbar `#F5A623`,
  fonte Inter). Código em `boletim/marca.py`; PNGs por `marca/gerar_imagens.py`. Capa do podcast no feed.
- Memória do agente: `estado/estado.json` (saúde das fontes, ritmo de voz medido, fator de extensão da IA).

## Agendamento (camadas de redundância)
1. Workflow `boletim-diario.yml`: crons às 04:45, 06:30 e 08:15 UTC. O cron do GitHub tem falhado com frequência.
2. Tarefa agendada do Claude às 03:13 BRT ("Disparo do boletim"): dispara o workflow se a edição do dia não existir.
   O workflow aguarda até 06:00 BRT para publicar.
3. Tarefa agendada do Claude às 06:37 BRT ("Operação diária"): confere a edição e corrige falhas (skill `operar-boletim`).
4. Execução manual (`workflow_dispatch`) sempre refaz a edição do dia; agendada pula se a Release já existir.

## IA
- `provedor_ia: auto`: Claude (`ANTHROPIC_API_KEY`) → Gemini grátis (`GEMINI_API_KEY`, configurado) → GitHub Models.
- Gemini alterna modelos (`gemini-3.8-flash`, `gemini-3.7-flash`, `gemini-flash-lite-latest`); a cota gratuita dá
  503/429 e algumas seções caem no modo extrativo — esperado. `gemini-2.5-flash` foi descontinuado.
  GitHub Models responde só "OK" (inútil). Diagnóstico: workflow `diagnostico-ia.yml` (lista e testa modelos).
- Seções curtas são completadas com notícias reais; o fator de extensão é aprendido em `estado.json`.
- Se a IA cair, as seções ficam em espera e são refeitas na repescagem (`repescagem_ia_s`); modelo com cota diária
  esgotada (429 PerDay) é pulado até o fim da execução.

## Acionar o Claude pelo navegador
- Workflow `claude.yml` (anthropics/claude-code-action@v1, segredo `CLAUDE_CODE_OAUTH_TOKEN`): escreva `@claude`
  em issue/comentário, ou Actions → Claude → Run workflow (resposta só no log).

## Regras
- Nunca inventar notícia nem publicar conteúdo fictício como edição real. Não desativar testes. Não alterar segredos.
- Mudanças pequenas e testadas: `python -m pytest -q` e `python -m boletim --fixture tests/fixtures/noticias.json --sem-video`.
  A fixture sobrescreve `edicoes/<hoje>/`: restaure com `git checkout -- edicoes estado` antes de commitar.
- Não faça push na `main` enquanto o workflow do boletim estiver rodando (o commit do bot falharia).
- No contêiner do Claude Code na nuvem, sites de notícias e edge-tts são bloqueados (testes reais só no Actions);
  GraphQL do GitHub é bloqueado — dispare workflows com `gh api -X POST repos/.../actions/workflows/<arq>/dispatches`.
- Falhas abrem issue com o rótulo `falha-boletim`; feche-a quando a edição sair.

## Site
- GitHub Pages ativo desde 05/11/2026: https://devops-arnaldomenezes.github.io/boletim-brasil-mundo/ (deploy no fim do
  `boletim-diario.yml`; para republicar só o site, sem refazer a edição: workflow `site.yml`).
- Feeds: workflow `validar-fontes.yml` testa URLs no Actions (o contêiner do Claude não alcança sites de notícias).

Skills do projeto: `operar-boletim` (checagem diária e correção), `revisar-edicao` (qualidade editorial),
`curar-fontes` (manutenção dos feeds).
