# Tickets M0

Cada tarefa abaixo tem ownership de arquivo exclusivo. Os três primeiros tickets são a fronteira independente; F04 e F05 aguardam seus contratos. Nenhuma tarefa pode instalar ferramentas, ler/exibir segredos, chamar JEV, criar serviços, ou fazer commit/push.

## F01-T01 — Doctor e manifesto sanitizado

**Bloqueado por:** nenhum.

**Entrega:** `python -m inonu_harness doctor` descreve o host com JSON sanitizado, proveniência e `unknown` explícito; manifesto separa intenção, instalação, configuração e operação.

**Ownership:** `inonu_harness/doctor.py`, `inonu_harness/integrations.json`, `tests/test_doctor.py`, `tests/fixtures/doctor/*.json`.

- [ ] Configuração local/global é lida sem imprimir valores ou caminhos pessoais.
- [ ] Skills, MCPs, JEV, ferramentas e hooks têm status/origem/versão ou motivo de desconhecido; presença de uma skill no filesystem não prova disponibilidade na sessão ativa, que deve ficar `unknown` quando não verificável pelo host.
- [ ] Compatibilidade de hook Bash/PowerShell é classificada sem executar comandos.
- [ ] Fixtures validam sanitização e schema.

## F02-T01 — Baseline e comparação

**Bloqueado por:** nenhum.

**Entrega:** fixtures locais produzem registros JSON reproduzíveis com métricas ausentes como `null` e proveniência por campo; registros compatíveis podem ser comparados.

**Ownership:** `inonu_harness/baseline.py`, `tests/test_baseline.py`, `fixtures/baseline/*.json`.

- [ ] Fixture determinística executa sem rede/pagamento.
- [ ] Formato inclui critérios, tempo, runtime/modelo, tokens/custo, ferramentas, falhas, bloqueios, recuperações e versões.
- [ ] Cada medida informa origem; ausência não vira estimativa.
- [ ] Comparação rejeita tarefas/configurações incompatíveis e ignora métricas não observáveis.

## F03-T01 — Decision Graph persistente

**Bloqueado por:** nenhum.

**Entrega:** serviço de decisões persiste e recupera registros e histórico via interface de armazenamento implementada em SQLite.

**Ownership:** `inonu_harness/decision_graph.py`, `inonu_harness/sqlite_store.py`, `tests/test_decision_graph.py`.

- [ ] Criar/listar/obter mantém ID, alternativas, restrições, evidências, critérios e dependências.
- [ ] Revisão preserva versões e invalida dependentes transitivos quando premissa muda.
- [ ] Ciclos e reuso conflitante de idempotência são rejeitados; retry idêntico não duplica eventos.
- [ ] Recomendação não autoriza; fechamento exige todos os critérios e evidências.
- [ ] Pendentes, bloqueadas e invalidadas podem ser consultadas.
- [ ] Fechar/abrir o banco preserva estado e histórico.

## F04-T01 — Adaptador JEV e gate SDD opcional

**Bloqueado por:** F03-T01.

**Entrega:** `JevAdapter` tipado conversa com um transporte MCP injetável, e `SddDecisionGate` deixa o fluxo padrão desativado e intacto.

**Ownership:** `inonu_harness/jev.py`, `inonu_harness/sdd_adapter.py`, `tests/test_jev.py`, `tests/test_sdd_adapter.py`.

- [ ] Plano e execução usam o mesmo spec; chamada real omite `max_calls`.
- [ ] Opção recomendada pertence às alternativas e guarda versão/proveniência disponível.
- [ ] Timeout, indisponibilidade, resposta inválida e sem consenso são explícitos.
- [ ] Nenhum resultado do JEV altera autorização.
- [ ] Mock testa sucesso/falhas sem rede.
- [ ] Gate desativado não depende do armazenamento nem modifica as oito etapas.

## F05-T01 — CLI, CI e documentação

**Bloqueado por:** F01-T01, F02-T01, F03-T01 e F04-T01.

**Entrega:** comandos reproduzíveis, suíte local/CI sem credenciais e guias compatíveis com o estado operacional real.

**Ownership:** `inonu_harness/__init__.py`, `inonu_harness/__main__.py`, `inonu_harness/cli.py`, `pyproject.toml`, `.github/workflows/ci.yml`, `README.md`, `docs/integrations.md`, `docs/sdd-workflow.md`.

- [ ] CLI executa doctor, baseline e compare usando Python da biblioteca padrão.
- [ ] CI roda a suíte em ambiente limpo sem segredos, serviço remoto ou instalação global.
- [ ] Guias distinguem instalação/configuração/operação; documentam contratos, sobreposição, licença, teste e condição de implementação própria das ferramentas.
- [ ] Testes existem antes da implementação de cada comportamento novo e passam.

## F06-T01 — Revisão independente

**Bloqueado por:** F05-T01.

**Entrega:** revisão read-only dos critérios, privacidade, invariantes, testes e diff; achados classificados e ligados a evidência.

**Ownership:** `docs/specs/milestones/v0.1.0/review.md`.

- [ ] Revisão vem de agente que não implementou módulos.
- [ ] Todos os achados têm severidade, arquivo/área e reprodução ou justificativa.
- [ ] Achados bloqueadores são resolvidos pelo coordenador antes da convergência.

## F07-T01 — Convergência

**Bloqueado por:** F06-T01 e resolução dos achados bloqueadores.

**Entrega:** relatório final de testes e smoke local, com lacunas nomeadas.

**Ownership:** `docs/specs/milestones/v0.1.0/convergence.md`.

- [ ] Suíte completa passa e comando de baseline local gera JSON legível por máquina.
- [ ] Doctor não imprime segredos/caminhos e assinala inacessibilidade MCP desconhecida.
- [ ] Critérios R01–R07 apontam para resultados determinísticos ou bloqueio explícito.
- [ ] Sem commit, push, PR ou mudança global.
