# Revisões editoriais

Registro da skill `revisar-edicao` (notas de 0 a 10 por checagem).

## 2026-11-09 (segunda)
Edição: 70 itens, 47,5 min, Gemini (1 falha de IA), seção Checagem vazia.

| Checagem | Nota | Observação |
|---|---|---|
| Precisão (8 itens sorteados) | 7 | 6 fiéis à fonte. "Apple reduziu o preço do MacBook Air" (a fonte fala de desconto no varejo, não da Apple). Clima: "colapso iminente" e "relatórios da ONU" sem respaldo direto nas fontes (Nature e Folha falam em ultrapassagem iminente de 1,5 °C). |
| Equilíbrio | 7 | Brasil 36%, EUA 24%, Ásia 20%, Europa 11%; América Latina e global 4% cada. Seção Checagem vazia (2º dia seguido); Saúde só 4 itens, um deles fora do tema (PM atira em van em Brasília). |
| Fontes oficiais/multilaterais | 4 | cerca de 15% dos itens identificados (meta 25%). Agência Gov, IBGE, FMI e STF seguem pausadas. |
| Locução | 9 | Números por extenso, sem URLs nem markdown. |
| Resumo escrito | 8 | Conclusão primeiro, 2 a 3 frases por item. |

Diagnóstico da Checagem: os 4 checadores com RSS (Lupa, G1 Fato ou Fake, Aos Fatos, Estadão Verifica) não publicaram
nada desde sexta 06/11; com janela de 26 h o fim de semana e a segunda ficam sem checagem.

Mudanças: janela própria de 72 h para fontes de checagem (`janela_horas` em `config/fontes.yaml`), sem repetir links
já lidos nas 3 edições anteriores (`coletor.links_publicados`); Aos Fatos e Estadão Verifica adicionados (validados no
Actions em 09/11). Precisão e fontes oficiais: acompanhar na próxima revisão antes de mexer em prompts/pesos.

## 2026-11-16 (segunda)
Edição: 77 itens, 37,8 min, Gemini (0 falhas de IA), publicada às 06:00. Checagem com só 2 itens.

| Checagem | Nota | Observação |
|---|---|---|
| Precisão (8 itens sorteados) | 7 | 5 fiéis à fonte (Unicamp/chorume, Alibaba Qwen4-Max, Inmet, Nvidia/Bessent, Leão XIV na Amazônia). Pet Genoma: o faturamento de uma empresa virou "empresas do setor faturam centenas de milhares". Seguros: a IA expandiu a sigla CQCS como "Centro de Qualificação em Serviços" (inventado). Apple/OpenEvidence com link digitado errado. |
| Equilíbrio | 7 | Brasil 37%, Europa 19%, EUA 16%, Ásia 16%, América Latina 10%, global 3%. A Europa está inflada: notícias do Iêmen de BBC World e France 24 saem marcadas "europa" (região da fonte, não do fato). Checagem com 1 checagem real (Lupa) + 1 item de outro tema. |
| Fontes oficiais/multilaterais | 3 | 10% dos itens de notícia (17% contando os números do dia do BCB/Câmara/Senado). Mesmas 4 fontes pausadas. |
| Locução | 9 | Números por extenso, sem URLs nem markdown. |
| Resumo escrito | 8 | Conclusão primeiro, 2 a 4 frases por item. |

Achado sistemático: de 10 a 16/11 a IA copiou com erro de 4 a 12 links por edição ("theverge.com" virou
"verge.com", "lula-em-2018" virou "lula-in-2018", URLs encurtadas). O link do texto/site quebrava e o item perdia o
cartão de citação com QR code.

Mudanças: `ilustracoes.citacoes` agora troca cada link da IA pelo link coletado mais parecido (mesmo domínio,
semelhança ≥ 0,9, ou prefixo único quando a IA encurta a URL); links de outras origens (BCB, agendas) ficam como
estão. Nas edições de 10 a 16/11 isso recuperaria 54 de 58 links quebrados, sem nenhuma troca errada nos casos
conferidos. Teste `test_citacao_corrige_link_digitado_errado_pela_ia`.

A acompanhar: região pelo fato e não pela fonte (Iêmen como "europa"); Checagem fraca às segundas, porque os
checadores quase não publicam no fim de semana e os itens de sexta já foram ao ar no sábado e no domingo.
