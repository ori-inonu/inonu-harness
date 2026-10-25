# Arquitetura local implementada (M0–M4)

O Inonu complementa o runtime Codex e o fluxo SDD existente com ferramentas locais. O M0–M4 implementa diagnóstico, avaliação por fixtures, um Decision Graph persistente e consumo manual de contexto; não cria um runtime de agente nem uma nova etapa SDD.

## Componentes locais

| Componente | Comportamento implementado |
| --- | --- |
| Doctor e baseline (M0) | `doctor` emite inventário sanitizado e usa `unknown` quando não pode verificar um fato. `baseline` executa fixtures offline e compara resultados com proveniência. |
| Decision Graph (M0) | Armazena decisões em SQLite, com revisões, histórico, evidências, dependências e idempotência. Recomendações e autorizações são campos distintos. |
| Adaptador JEV e gate (M0) | `JevAdapter` valida escolhas delimitadas e chama `consensus_plan` e `consensus_run` pelo transporte MCP injetado; testes usam o mock. `SddDecisionGate` é opcional e começa desativado. |
| Contexto SDD (M1–M2) | `SddDecisionContextAdapter` expõe uma projeção allowlisted, somente de leitura, para IDs explícitos escolhidos pelo chamador. A CLI `decisions context` lê o banco existente em modo read-only. |
| Pacote manual (M4) | `decisions packet` combina um arquivo de tarefa estritamente validado com contexto dos IDs explícitos. A leitura é read-only e o pacote é revisado e anexado manualmente pelo chamador. Chaves JSON duplicadas no arquivo de tarefa são rejeitadas. |

O registro de autorização do grafo exige evidência para cada critério requerido. Uma recomendação JEV não altera esse estado, um recibo JEV não concede autoridade, e registrar autorização local não executa nem substitui a autorização necessária para uma operação externa.

O inventário de integrações registra que chamadas MCP do Jev funcionaram no chat coordenador em 2026-10-24. Esse fato descreve somente aquela sessão/host; não prova disponibilidade em outro cliente nem fornece transporte JEV portátil. A CLI local não configura transporte MCP ao vivo.

O M3 é um protocolo documental de avaliação exploratória. O piloto não foi executado porque não havia evidência de isolamento text-only verificável neste host.

## Limites e trabalho futuro

O adaptador de contexto não é um mecanismo geral de recuperação de símbolos, diffs ou conteúdo. O inventário de ambiente, o grafo e a verificação são componentes locais separados; não há um motor geral de contexto/evidências, runtime próprio ou serviço remoto implementado neste marco. Codex continua sendo o ambiente atual; DeepSeek Harness e Pi permanecem candidatos sem escolha aceita.

## Quando usar cada mecanismo

| Caso | Mecanismo |
| --- | --- |
| Regra determinística | Código |
| Escolha curta entre opções conhecidas | JEV |
| Várias avaliações independentes | Avaliar pelo fluxo JEV somente quando o contrato disponível aceitar essas avaliações |
| Decisões dependentes ou ramificadas | Decision Graph para persistência e dependências; JEV somente para comparação delimitada |
| Falta de evidência | Recuperação de evidências |
| Ação fora da autoridade concedida | Aprovação humana |
| Testes contradizem uma decisão | Reabrir o nó e investigar |

Não invoque modelos extras para uma condição que um if determinístico resolve com mais confiabilidade. Recomendações JEV são consultivas: não concedem autorização nem provam que uma tarefa terminou.

## Runtimes candidatos

Codex é o ambiente atual. DeepSeek Harness e Pi são candidatos de avaliação, não decisões aceitas; nenhum deles tem prioridade definida. Uma comparação deve usar o mesmo fluxo SDD, modelo, orçamento e conjunto de tarefas. Antes de permitir autoalterações do harness, use isolamento externo compatível com cada runtime.

## Engenharia reversa

Investigue cada projeto em três níveis: código, comportamento e resultados.

1. Extraia contratos: entradas, saídas, estados, erros e invariantes.
2. Reproduza comportamento com testes e cenários.
3. Isole o algoritmo essencial da integração específica de cada runtime.
4. Construa um adaptador ou componente próprio somente quando a evidência mostrar valor.
5. Compare o componente original e o adaptador com os mesmos casos, incluindo falhas e regressões.
6. Verifique licenças e dependências antes de incorporar código-fonte.

O objetivo é reaproveitar comportamento demonstrado, não manter forks completos por conveniência.
