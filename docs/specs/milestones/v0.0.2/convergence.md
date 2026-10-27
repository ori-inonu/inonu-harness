# Convergência M1 — SDD Decision Context

## Resultado

M1 está concluído no workspace local. O adaptador é opt-in, somente de leitura e recebe IDs explicitamente selecionados. O modo desativado não acessa o grafo. A projeção preserva ordem e procedência allowlistada, mantém recomendações separadas de autorizações e não adiciona um consumidor automático nem muda as oito etapas SDD.

## Revisão

A primeira revisão independente encontrou um P2: IDs com formato inválido, como `bad id`, passavam pela validação e eram classificados como inexistentes. O follow-up M1-ID-FIX alinhou a validação ao padrão do Decision Graph (`[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}`) e acrescentou casos para espaço interno, caractere inicial inválido e comprimento acima de 128. IDs bem formados ausentes continuam gerando `DecisionNotFound`. A segunda revisão independente concluiu sem achados.

## Verificações executadas

| Verificação | Resultado |
| --- | --- |
| `python -m unittest discover -s tests -p test_sdd_context.py -v` | passou, 5 testes |
| `python -m unittest discover -s tests -v` | passou, 48 testes |
| Convergência do workflow nativo | exit code 0 para ambos os comandos de teste e `git diff --check` |
| Espaços finais e padrões comuns de credenciais | 0 ocorrências em 42 arquivos alterados ou novos |

## Baseline observável

O teste calcula seis resultados de aceite a partir da saída real do adaptador e passa um intervalo de `perf_counter` limitado à chamada `load_context` para o runner de baseline. A execução registra a versão Python observada. Runtime do agente, modelo, tokens e custo são `null`; ferramentas, falhas, bloqueios e recuperações são listas do fixture e não eventos observados de um agente. O fixture verifica regressões do contrato e não mede ganho de qualidade, produtividade ou velocidade.

## Fora da evidência

- O CI hospedado não foi executado neste workspace.
- Nenhum consumidor do runtime Codex injeta esse contexto automaticamente.
- A allowlist reduz campos, mas os campos textuais permitidos não são varridos para detectar segredos; o chamador continua escolhendo os IDs apropriados.
- Nenhuma mudança foi commitada ou publicada.
