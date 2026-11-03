# Arquitetura e plano do Boletim "Brasil e Mundo Hoje"

## 1. Objetivo
Agente que, todos os dias, consome fontes oficiais, governamentais, multilaterais (ONU, OMS, FMI, UNESCO)
e imprensa confiável, e publica às 6h (Brasília) um resumo em texto, um podcast de 30 a 45 minutos e um
vídeo com identidade visual por tema.

## 2. Fontes (config/fontes.yaml)
| Região | Oficiais / multilaterais | Imprensa e ciência |
|---|---|---|
| Brasil | Agência Brasil, Agência Gov, Senado, Câmara, STF, IBGE | BBC Brasil, DW Brasil, G1, Folha, Estadão, InfoMoney, Tecnoblog, Fiocruz, FAPESP |
| Global | ONU News (PT/EN), OMS, FMI, UNESCO | Nature |
| Europa | Comissão Europeia, Parlamento Europeu, BCE | BBC World, DW, Euronews, France 24, Guardian, RTP |
| EUA | Casa Branca, Federal Reserve, NIH | NPR, PBS, NYT, Ars Technica, MIT Tech Review, The Verge, TechCrunch |
| Ásia | — | NHK World, SCMP, CNA, The Hindu, Korea Herald, Al Jazeera |

Critérios: preferência para fontes primárias (governo, parlamento, bancos centrais, ONU) e veículos com
política editorial pública. Feeds pagos (Reuters, AP, Bloomberg) exigem contrato e ficaram de fora; podem ser
incluídos depois via API.

## 3. Pipeline
1. **Coleta** – RSS/Atom em paralelo, janela de 26h, deduplicação por similaridade de título (notícia citada
   por várias fontes ganha relevância).
2. **Classificação** – palavras-chave PT/EN + dica da fonte; pesos para fonte oficial/multilateral e Brasil;
   intercalação de regiões para garantir equilíbrio Brasil/Europa/EUA/Ásia.
3. **Redação (IA: GitHub Models grátis, Gemini grátis ou Claude pago)** – uma chamada por seção, com regras anti-alucinação (só fatos das fontes, atribuição
   explícita, tradução para PT-BR). Saída JSON: itens do resumo escrito + roteiro de locução dimensionado para
   a duração-alvo (38 min × 150 palavras/min ≈ 5.700 palavras).
4. **Áudio** – edge-tts (vozes neurais pt-BR, gratuitas), alternando locutor e locutora por seção, vinheta
   sonora gerada (sem direitos autorais), legendas sincronizadas.
5. **Vídeo** – ffmpeg: cada seção tem paleta própria com fundo em gradiente animado, cartão de abertura,
   manchete atual com região e fonte, forma de onda da voz, barra de progresso e legendas.
6. **Publicação** – texto versionado em `edicoes/AAAA/MM/DD/`; MP3/MP4 como assets de Release (não incham o
   git); site estático + feed de podcast no GitHub Pages.

## 4. Agendamento 24x7 às 6h
GitHub Actions com cron às 06:30 UTC (03:30 BRT). O cron do GitHub pode atrasar em horários de pico, por isso a
geração começa cedo e o job espera até 06:00 para publicar. Se falhar, o GitHub envia e-mail ao dono do repo.
Atenção: em repositório **privado**, a espera conta como minutos de Actions (cota grátis de 2.000 min/mês);
em repositório **público** os minutos são ilimitados. Para repo privado, mova o cron para ~08:15 UTC.

## 5. Viabilidade da versão em vídeo
| Opção | Custo | Qualidade | Situação |
|---|---|---|---|
| A. Motion graphics com ffmpeg (implementado) | zero | boa para "rádio visual" | **pronto** |
| B. Apresentador virtual (avatar falante: HeyGen, D-ID, Synthesia) | pago por minuto; 40 min/dia fica caro | alta | fase 2, pode ser usado só na abertura |
| C. Imagens por notícia (geração por IA ou fotos de agências) | baixo/médio | alta | fase 2; cuidado com direitos de imagem |

Tempo de render da opção A: ~0,45× a duração (≈18 min para 40 min de vídeo) num runner padrão.

## 6. Custos estimados
- GitHub Actions/Pages/Releases: gratuitos em repositório público.
- IA: padrão GitHub Models (gratuito, com limite diário de chamadas que cobre as ~8 chamadas do boletim).
  Gemini (camada gratuita) é a alternativa. Claude (pago): ~8 chamadas/dia (≈70 mil tokens de entrada e ≈20 mil de saída) — da ordem de centavos a menos de
  US$ 1/dia, conforme o modelo escolhido em `config.yaml`.
- edge-tts: gratuito, mas usa um serviço não oficial da Microsoft; se ficar instável, trocar por Azure Speech,
  Google Cloud TTS ou ElevenLabs (melhor qualidade, pago).

## 7. Próximos passos sugeridos
- Publicar automaticamente no YouTube e Spotify for Creators.
- Envio por e-mail/Telegram/WhatsApp às 6h.
- Avatar animado na abertura e no encerramento.
- Verificação cruzada: só destacar fatos confirmados por 2+ fontes.
