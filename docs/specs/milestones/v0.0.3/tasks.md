# Tarefas M2

## M2-T01 — Consumidor CLI read-only

**Bloqueado por:** nenhum.

**Arquivos:** `inonu_harness/cli.py`, `inonu_harness/sqlite_store.py`, `tests/test_cli.py`.

**Critérios de aceite:**

- [x] `decisions context` exige IDs explícitos e serializa o `SddDecisionContextResult` existente.
- [x] O caminho de contexto abre somente bancos existentes com schema conhecido, sem criação nem inicialização/alteração de schema.
- [x] Bytes do banco e histórico permanecem iguais antes/depois da leitura.
- [x] IDs inválidos retornam `invalid_request`; um ID válido ausente mantém o erro CLI existente.
- [x] Testes das operações de escrita existentes continuam passando.

## M2-T02 — Comparação de tarefa SDD

**Bloqueado por:** M2-T01.

**Arquivos:** `fixtures/sdd_context/consumer-task.json`, `tests/test_sdd_context_evaluation.py`, `docs/sdd-workflow.md`, `docs/benchmark-plan.md`.

**Critérios de aceite:**

- [x] O fixture representa a tarefa local real de implementar o consumidor e suas restrições confirmadas.
- [x] O teste envia o mesmo task packet sem contexto e com a saída JSON real do CLI.
- [x] Critérios da condição com contexto são derivados da projeção; `compare_runs` reconhece a diferença sob task/config iguais.
- [x] Duração é limitada à leitura local do CLI; runtime/modelo/tokens/custo não observados permanecem `null`.
- [x] Documentação não afirma que a avaliação mede qualidade ou produtividade do agente e preserva as oito etapas.

## M2-T03 — Revisão independente

**Bloqueado por:** M2-T01 e M2-T02.

**Critérios de aceite:**

- [x] Verifica a garantia read-only real do armazenamento e a ausência de alteração do fluxo existente.
- [x] Verifica se a comparação é controlada e se nenhuma métrica não observada foi fabricada.
- [x] Retorna achados com severidade e evidência, ou ausência explícita de achados.

Após M2-T03, o coordenador executa convergência determinística e atualiza `checkpoint.md` e `convergence.md`.

**Resultado:** concluído localmente, sem achados na revisão independente. A comparação mostra que três critérios de entrega de contexto passam na condição CLI e falham no controle sem contexto; isso mede disponibilidade de campos, não o desempenho de um agente.
