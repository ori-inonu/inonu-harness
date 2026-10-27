# Plano de avaliação

## Pergunta

A combinação reduz o custo por tarefa concluída corretamente sem aumentar defeitos, retrabalho ou perda de evidências?

## Primeira matriz

Execute as mesmas tarefas, com o mesmo runtime, modelo, esforço, limite e ambiente:

| Variante | Configuração |
| --- | --- |
| 1 — Baseline | Sem RTK, Headroom, CodeGraph ou Ponytail |
| 2 — RTK | Apenas filtragem de saída de terminal |
| 3 — RTK + Headroom | Filtragem de terminal e gestão de contexto |
| 4 — RTK + Headroom + CodeGraph | Adiciona recuperação estrutural do repositório |
| 5 — Stack completa | Adiciona Ponytail em modo full |

Essa primeira triagem mede o ganho incremental da combinação. Ela não isola o efeito individual de CodeGraph e Ponytail. Uma segunda matriz deve alternar esses fatores separadamente e incluir execuções repetidas para medir interações e variabilidade.

## Medidas por tarefa

Registre custo por tarefa aprovada, critérios de aceite cumpridos, testes aprovados, regressões, duração, tokens de entrada/saída, chamadas de ferramenta, recuperações do conteúdo original e decisões JEV alteradas após nova evidência. Guarde versões das ferramentas, modelo, prompt, configuração e estado inicial.

## Comparar o fluxo de decisão

Compare também três versões do mesmo fluxo SDD:

1. SDD com intervenções humanas.
2. SDD com recomendações JEV, como no fluxo atual.
3. SDD com Decision Graph e JEV.

Meça decisões corretas, retrabalho, custo, tempo e taxa de conclusão.

## Critério

Custo por tarefa concluída corretamente é a métrica principal. Tokens menores não compensam uma queda de qualidade. Não some percentuais publicados por ferramentas diferentes: seus conjuntos de tarefas, modelos e métodos não são comparáveis. Marque cada resultado como medição local ou benchmark publicado pelo mantenedor.

## Baseline local do contexto SDD

O fixture `fixtures/sdd_context/context-projection.json` verifica um contrato específico: IDs escolhidos e ordenados pelo chamador, decisões pendentes e invalidadas, recomendação sem autorização, projeção allowlisted, ausência de mutação e comportamento desativado por padrão. O teste usa um Decision Graph em SQLite temporário e a API existente `run_fixture`; não chama serviços externos.

A duração registrada cobre somente a chamada `SddDecisionContextAdapter.load_context`. A versão do Python vem do runtime local; runtime do agente, modelo, tokens de entrada/saída e custo permanecem nulos porque essa avaliação não os observa. As chamadas de ferramenta, falhas, bloqueios e recuperações refletem listas vazias do fixture, não medições de uma execução de agente. Os booleanos de aceite são calculados a partir da saída real do adaptador. Esse registro permite comparar regressões do contrato do adaptador; não sustenta conclusões sobre qualidade, economia, velocidade de desenvolvimento ou benefício do Harness.

Execute o recorte reproduzível com `python -m unittest discover -s tests -p test_sdd_context.py -v`. A suíte geral continua sendo `python -m unittest discover -s tests -v`.

## Comparação local do consumidor CLI M2

`fixtures/sdd_context/consumer-task.json` descreve a tarefa local de adicionar o consumidor CLI e uma decisão de teste sem dados do usuário. O teste executa a mesma tarefa (`task_id` e `config_id` iguais) em duas condições: sem contexto selecionado e com o JSON real retornado por `python -m inonu_harness decisions --db <arquivo-existente> context --ids m2-cli-consumer`. Ambos os resultados usam `run_fixture`; `compare_runs` confirma se os critérios de presença do contexto, entrega das restrições e separação entre recomendação e autorização mudaram.

A duração observada na condição com contexto limita-se à chamada local do CLI. A condição sem contexto não lê o grafo, então sua duração é `null` e a comparação de tempo fica incomparável; não é uma medição de economia. Runtime/modelo do agente, tokens e custo permanecem `null`. As listas de ferramentas, falhas, bloqueios e recuperações vêm do fixture e não são chamadas ou eventos observados. O teste reproduz a entrega dos campos em uma tarefa SDD local, sem executar um agente nem medir qualidade, produtividade ou velocidade de desenvolvimento.

Execute a comparação com `python -m unittest discover -s tests -p test_sdd_context_evaluation.py -v`. O arquivo do banco é temporário e criado pelo teste; nenhum banco pessoal é lido.

## Baseline local da auditoria SDD v0.8

O teste `tests/test_sdd_audit_cli.py` chama `load_audit_manifest` e `audit_manifest` nos cinco manifestos congelados em `fixtures/sdd_audit`, com as evidências compartilhadas em `fixtures/sdd_audit/evidence`. As linhas de aceite de cada fixture de baseline são calculadas a partir do relatório retornado, cobrindo o status de aprovação e se todos os requisitos foram cobertos:

| Caso sintético | Status esperado do relatório |
| --- | --- |
| `clear-change` | pass |
| `ambiguous-change` | fail |
| `reproducible-bug` | pass |
| `specification-delta` | pass |
| `protected-action` | fail |

O teste passa esse fixture calculado por `run_fixture` e também pelo comando `baseline run`; ambos mantêm o schema de resultado v1. A proveniência da medida de aceite identifica `local-audit` e referencia o caso. Isso mede resultados do contrato de auditoria sobre fixtures locais, não uma execução de agente. Runtime e modelo, tokens de entrada e saída, e custo permanecem `null`; listas de eventos do fixture não são telemetria. O tempo materializado pelo baseline cobre somente a chamada local de `run_fixture`, não o cálculo anterior do relatório. Os casos são sintéticos, e resultados com hashes válidos não autenticam que verificações tenham sido realmente executadas.

Reproduza esse recorte com `python -m unittest discover -s tests -p test_sdd_audit_cli.py -v`. Para o contrato completo e os limites do relatório, consulte a [especificação v0.0.8](specs/milestones/v0.0.8/spec.md).

## Gate de regressão do baseline (v0.0.13)

`baseline compare BEFORE AFTER --max-regression R` compara duas medições locais salvas. `R` é um número finito maior ou igual a 0 (`0.10` permite 10% de aumento). O resultado ganha `gate` com `pass`, `fail` ou `incomparable`, e o processo sai com 0, 1 ou 2. Uma regressão certa sempre vence (`fail`); se nenhuma for certa e a fonte de medição de uma métrica julgada mudou, o gate é `incomparable`. Arquivos ilegíveis, chaves JSON duplicadas e `R` inválido saem com 2 sem `gate`. A comparação usa aritmética decimal exata.

Julgam o resultado: critérios de aceite que passaram antes e faltam ou falham depois (sem tolerância); `input_tokens`, `output_tokens`, `cost_usd`, `failures`, `blocks` e `tool_calls` quando aumentam além da razão, ou saem de zero. Valores `null` não são preenchidos: ficam em `skipped` e não contam como aprovação nem regressão. `elapsed_seconds`, `recoveries`, `runtime`, `model` e `component_versions` não são julgados.

O gate compara duas medições locais salvas. Ele não estabelece qualidade do agente, produtividade nem benefício do Harness, e uma redução de tokens não compensa queda de aceite. Execute o recorte com `python -m unittest discover -s tests -p test_baseline_gate.py -v`.
