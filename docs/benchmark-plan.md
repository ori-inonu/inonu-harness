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
