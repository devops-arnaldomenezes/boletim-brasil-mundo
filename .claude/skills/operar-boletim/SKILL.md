---
name: operar-boletim
description: Confere a edição diária do boletim Brasil e Mundo Hoje (execução do Actions, Release, site, métricas) e corrige falhas sozinho. Use na rotina diária pós-6h ou quando houver issue falha-boletim.
---

# Operar o boletim

Objetivo: garantir que a edição de hoje foi publicada às 6h e que a de amanhã vai funcionar, com o mínimo de
intervenção humana.

## 1. Verificar a edição de hoje
```bash
DATA=$(TZ=America/Sao_Paulo date +%F)
gh run list --workflow boletim-diario.yml --limit 3
gh release view "edicao-$DATA" --json assets -q '.assets[].name'
cat edicoes/$(TZ=America/Sao_Paulo date +%Y/%m/%d)/relatorio.json
gh issue list --label falha-boletim --state open
```
Saudável = run com sucesso, Release com `.mp3` e `.mp4`, `meta_duracao_ok: true`, todas as seções com itens.

## 2. Se a execução falhou
1. Leia o log: `gh run view <id> --log-failed | tail -100`.
2. Classifique: fonte/rede (transitório), limite da IA, bug no código, mudança de API externa.
3. Transitório e ainda antes das 9h → `gh workflow run boletim-diario.yml -f publicar_imediatamente=true`.
4. Bug → reproduza localmente com a fixture, corrija o mínimo, rode `pytest -q`, commit e push na `main`,
   e então dispare o workflow. Comente na issue o diagnóstico e feche-a quando a edição sair.
5. Limite da IA no GitHub Models repetido → troque `provedor_ia` para `gemini` só se o segredo
   `GEMINI_API_KEY` existir (`gh secret list`); senão registre na issue e avise o dono.

## 3. Ajustes automáticos (se a edição saiu, mas fora do padrão)
- `meta_duracao_ok: false` por 2 dias seguidos → ajuste `duracao_alvo_min` em `config/config.yaml`
  (o ritmo de voz já é calibrado sozinho em `estado/estado.json`).
- Seção com 0–2 itens → use a skill `curar-fontes` para reforçar aquela seção.
- `fontes_pausadas` não vazia → use `curar-fontes` para substituir os feeds mortos.

## 4. Particularidades conhecidas
- Dispare workflows via REST: `gh api -X POST repos/OWNER/REPO/actions/workflows/boletim-diario.yml/dispatches -f ref=main -F 'inputs[publicar_imediatamente]=true'`.
- Gemini 503/429 em parte das seções é normal na cota grátis (`falhas_ia` no relatorio.json). Só aja se `ia_ativa`
  for false ou todas as seções caírem no modo extrativo: rode `diagnostico-ia.yml` e atualize `modelos_ia.gemini`.
- Deploy do Pages com 404 = Pages não habilitado pelo dono; não é falha da edição (passo com continue-on-error).
- Não faça push enquanto o workflow do boletim roda.

## 5. Relato
Termine com um resumo de 3 linhas: status da edição, o que foi corrigido, o que precisa do dono (se algo).
Nunca publique conteúdo inventado e nunca desative testes para "ficar verde".
