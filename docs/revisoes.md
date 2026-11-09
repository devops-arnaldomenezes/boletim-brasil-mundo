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
