# Brasil e Mundo Hoje 🇧🇷🌎

Boletim diário automático com as notícias mais relevantes do Brasil e do mundo, com ênfase em
**política, economia, tecnologia, inteligência artificial, saúde e cultura**, cobrindo **Brasil, Europa,
Estados Unidos e Ásia**. Publicado todos os dias às **6h (horário de Brasília)** em três formatos:

| Formato | Onde |
|---|---|
| 📄 Texto (Markdown/HTML) | pasta [`edicoes/AAAA/MM/DD/`](edicoes/) e site no GitHub Pages |
| 🎧 Podcast (MP3, 30–45 min) | Releases `edicao-AAAA-MM-DD` + feed RSS `feed.xml` (assinável em apps de podcast) |
| 🎬 Vídeo (MP4 720p) | Releases `edicao-AAAA-MM-DD` |

A última edição está sempre em [`edicoes/ULTIMA.md`](edicoes/ULTIMA.md).

## Como funciona

```
 fontes.yaml (≈45 feeds oficiais, ONU/OMS/FMI, imprensa)
        │  coletor.py   — RSS/Atom das últimas 26h, deduplicação
        ▼
 classificador.py      — temas por palavras-chave PT/EN, relevância (fonte oficial, região, repercussão)
        ▼
 redator.py (IA)   — resumo por seção + roteiro de locução em PT-BR, só com fatos das fontes
        ▼
 audio.py (edge-tts)   — vozes neurais pt-BR alternadas por seção + vinheta + legendas SRT
        ▼
 video.py (ffmpeg)     — identidade visual por seção, manchetes animadas, onda de voz, legendas
        ▼
 publicador.py / site.py — Markdown, HTML, JSON, feed de podcast, GitHub Pages, Release
```

Agendamento: [`.github/workflows/boletim-diario.yml`](.github/workflows/boletim-diario.yml) roda às 03:30
(Brasília), gera tudo e **aguarda até as 6h** para publicar.

## Configuração (uma vez)

1. Nada de chave para começar: por padrão a IA é o **GitHub Models**, gratuito dentro do GitHub Actions
   (`provedor_ia: github` em `config/config.yaml`). Alternativas: `gemini` (segredo `GEMINI_API_KEY`,
   camada gratuita do Google AI Studio) ou `anthropic` (segredo `ANTHROPIC_API_KEY`, pago).
2. Em **Settings → Pages**, em *Source*, escolha **GitHub Actions**.
3. Em **Actions**, rode manualmente "Boletim diário" (*Run workflow*) para gerar a primeira edição.

## Rodar localmente

```bash
sudo apt install ffmpeg fonts-dejavu-core     # ou brew install ffmpeg
pip install -r requirements.txt
export ANTHROPIC_API_KEY=...                   # sem a chave, roda em modo extrativo (sem IA)
python -m boletim --midia _midia               # edição de hoje
python -m boletim --fixture tests/fixtures/noticias.json --sem-video   # teste offline
pytest -q
```

## Personalização

- **Fontes:** `config/fontes.yaml` (adicione/remova feeds; os que falham são ignorados).
- **Duração, voz, modelo, cores das seções:** `config/config.yaml`.
- **Temas:** palavras-chave em `boletim/classificador.py`.

Veja o desenho completo e a análise da versão em vídeo em [`docs/ARQUITETURA.md`](docs/ARQUITETURA.md).

> O conteúdo é gerado automaticamente a partir de fontes públicas e sempre cita a origem. Confira as fontes
> originais antes de tomar decisões com base no boletim.
