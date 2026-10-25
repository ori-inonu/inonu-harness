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
