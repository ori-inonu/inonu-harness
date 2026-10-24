# Arquitetura em estudo

## Hipótese central

O Inonu deve aproveitar capacidades específicas por meio de contratos pequenos, sem acoplar o fluxo SDD a um runtime ou reconstruir ferramentas antes de demonstrar a necessidade. A proposta principal é um Decision Graph Engine; ele ainda não está implementado.

## Componentes propostos

| Componente | Entrada e saída |
| --- | --- |
| SDD | Requisitos, fases, tarefas e aceite |
| Context & Evidence Engine | Referências para símbolos, dependências, diffs e conteúdo recuperável |
| Decision Graph | Nós persistentes com opções, restrições, evidências, dependências e revisões |
| JEV | Recomendação tipada para opções já delimitadas |
| Decision Validator | Regras determinísticas, evidência suficiente, conflitos e gates de autorização |
| Runtime | Execução das tarefas com contratos portáveis |
| Verification Engine | Testes, compilação, avaliação e revisão independente |

Uma decisão pode guardar ID, pergunta, opções, referências de contexto, restrições, decisão-pai, revisão, status e resultado de validação. Guarde evidências e decisões explícitas, não raciocínio interno oculto do modelo.

Quando uma evidência nova invalida uma premissa, marque a decisão como revisável e localize as decisões dependentes. Preserve o histórico e o motivo da revisão.

## Quando usar cada mecanismo

| Caso | Mecanismo |
| --- | --- |
| Regra determinística | Código |
| Escolha curta entre opções conhecidas | JEV |
| Várias avaliações independentes | Uma chamada JEV |
| Decisões dependentes ou ramificadas | Decision Graph e modelo de raciocínio; JEV quando agregar uma comparação delimitada |
| Falta de evidência | Recuperação de evidências |
| Ação fora da autoridade concedida | Aprovação humana |
| Testes contradizem uma decisão | Reabrir o nó e investigar |

Não invoque modelos extras para uma condição que um if determinístico resolve com mais confiabilidade.

## Runtimes candidatos

Codex é o ambiente atual. DeepSeek Harness e Pi são candidatos de avaliação, não decisões aceitas. A hipótese da conversa é testar DeepSeek Harness primeiro e manter Pi como comparador minimalista. A escolha deve esperar uma execução comparável do mesmo fluxo SDD, modelo, orçamento e conjunto de tarefas. Antes de permitir autoalterações do harness, use isolamento externo compatível com cada runtime.

## Engenharia reversa

Investigue cada projeto em três níveis: código, comportamento e resultados.

1. Extraia contratos: entradas, saídas, estados, erros e invariantes.
2. Reproduza comportamento com testes e cenários.
3. Isole o algoritmo essencial da integração específica de cada runtime.
4. Construa um adaptador ou componente próprio somente quando a evidência mostrar valor.
5. Compare o componente original e o adaptador com os mesmos casos, incluindo falhas e regressões.
6. Verifique licenças e dependências antes de incorporar código-fonte.

O objetivo é reaproveitar comportamento demonstrado, não manter forks completos por conveniência.
