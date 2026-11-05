# Guia de marca — Brasil e Mundo Hoje

![Símbolo](simbolo-512.png)

## Conceito
Um globo dentro de uma órbita âmbar que funciona como mostrador de relógio: começa às 9h, passa por 12h e 3h e
termina num sol na posição das **6 horas**, o horário em que o boletim sai. O ponto verde marca o Brasil no globo.

## Arquivos
| Arquivo | Uso |
|---|---|
| `simbolo.svg`, `simbolo-512.png`, `simbolo-96.png` | ícone, favicon, canto do vídeo |
| `logo.svg` (fundo escuro), `logo-claro.svg` (fundo claro) | cabeçalho do site e materiais |
| `capa-podcast.png` (3000×3000) | capa do feed do podcast (Spotify, Apple, etc.) |

Os SVGs são gerados por `boletim/marca.py`; os PNGs, por `python marca/gerar_imagens.py` (precisa de Chrome).

## Cores
| Nome | Hex | Uso |
|---|---|---|
| Azul-noite | `#0B1F3A` | fundos, cabeçalhos, abertura do vídeo |
| Âmbar-aurora | `#F5A623` | destaque: órbita, fios, barra de progresso, "HOJE" |
| Verde-Brasil | `#00A86B` | detalhe pontual (ponto do Brasil) |
| Papel | `#F7F4EE` | fundo claro do site |
| Tinta | `#14213D` | texto sobre fundo claro |
| Cinza | `#5B6675` | texto secundário |

Seções do vídeo (família de tons profundos, definida em `config/config.yaml`): Manchetes azul, Política vinho,
Economia esmeralda, Tecnologia cobalto, IA violeta, Saúde petróleo, Cultura terracota, Encerramento azul-noite.

## Tipografia
**Inter** (licença livre OFL): ExtraBold para o nome e títulos, Medium/Regular para textos. No vídeo vem do pacote
`fonts-inter`; no site, do Google Fonts. Reserva: DejaVu Sans.

## Regras rápidas
- Nome sempre como **BRASIL E MUNDO** (branco ou tinta) + **HOJE** (âmbar).
- Âmbar é destaque, nunca fundo de grandes áreas; texto sobre âmbar em azul-noite.
- Não distorcer o símbolo nem trocar as cores da órbita e do globo.
