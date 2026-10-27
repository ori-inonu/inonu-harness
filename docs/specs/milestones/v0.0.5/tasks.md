# Tarefas M4

## M4-T01 — Especificar o pacote

**Bloqueado por:** nenhum.

**Arquivos:** `spec.md`, `decisions.md`, `plan.md` e `tasks.md` deste marco.

**Critérios:**

- [x] Problema, comando, entrada estrita e envelope JSON estão definidos.
- [x] SQLite read-only, comportamento de erros, stdout e compatibilidade com `context` estão definidos.
- [x] O seam público `main(argv)` e verificações com temporários estão registrados.
- [x] A decisão Jev consultiva e o bloqueio de isolamento deste host estão documentados.

## M4-T02 — Implementar pacote manual

**Bloqueado por:** M4-T01.

**Arquivos:** `inonu_harness/cli.py`, `tests/test_cli.py`, `docs/sdd-workflow.md`.

**Critérios de aceite:**

- [x] `decisions packet` valida o task JSON e emite `schema_version`, tarefa e projeção allowlisted na ordem solicitada.
- [x] JSON/tarefa inválidos e campos extras retornam exit code 2 sem revelar o caminho local; chaves duplicadas também são rejeitadas.
- [x] Banco existente mantém bytes e histórico; banco ausente não é criado.
- [x] `decisions context` mantém o formato e comportamento atuais.
- [x] Os testes atravessam `main(argv)` e a documentação mostra anexação manual, sem injeção automática.

## M4-T03 — Revisão independente

**Bloqueado por:** M4-T02.

**Critérios de aceite:**

- [x] Revisar validação de entrada, campos de saída e tratamento de erro.
- [x] Confirmar IDs explícitos, ordem, allowlist e distinção recomendação/autorização.
- [x] Confirmar read-only e compatibilidade com `decisions context`.
- [x] Corrigir achado P2 sobre chaves duplicadas; a segunda revisão não encontrou achados.

## M4-T04 — Convergência

**Bloqueado por:** M4-T03.

**Critérios de aceite:**

- [x] Teste focal (8 testes) e suíte geral (56 testes) passam; resultados registrados no checkpoint.
- [x] `git diff --check` passa e as etapas 1 e 8 continuam listadas em `docs/sdd-workflow.md`.
- [x] `checkpoint.md` registra a revisão, evidência de convergência e o bloqueio do piloto M3 neste host.
