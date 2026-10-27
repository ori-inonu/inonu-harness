# Decisões M0

## D01 — Linguagem local

- **Decisão:** Python 3.11+ e biblioteca padrão para os comandos locais; isso não substitui Codex como runtime de agente.
- **Evidência:** ambiente sem código de aplicação; Python 3.14.7 disponível; `sqlite3`, `tomllib` e `unittest` são módulos padrão do Python selecionado.
- **JEV:** `m0-implementation-runtime`, consenso `python-stdlib`, hash `39e0cdd2bea99048166073ff7bc7415a0acfe882c3e817679b1a5abc7b29c865`.

## D02 — Persistência

- **Decisão:** SQLite local, com domínio separado por interface de armazenamento.
- **Evidência:** requisitos de histórico, transações/idempotência e recuperação; SQLite já acompanha Python e não exige serviço.
- **JEV:** `m0-storage-choice`, consenso `sqlite`, hash `a09fbd37141c29e1e9f5cb4fb0b150bb801be41d09e7d454c5f7ca4c1ae1a173`.

## D03 — Escalonamento

- **Decisão:** paralelizar apenas doctor, baseline e grafo, com arquivos disjuntos; integrar dependentes depois.
- **Evidência:** os três módulos têm contratos separados; JEV/SDD depende do grafo e CLI/CI depende dos módulos.
- **JEV:** `m0-work-scheduling`, consenso `parallel-frontier`, hash `ce3d0273ff60dde3f0dbd3492c8f782e757abb5f39cb0ce4d99a1a3c0c720738`.

Os recibos JEV são recomendações. A missão do usuário autoriza a implementação dentro dos limites definidos em `spec.md`.

## Não decidido

- Invocação MCP real a partir de um processo Python independente do Codex: contrato de transporte portátil não foi verificado.
- Licença de Headroom e Sequential Thinking: não encontrada em evidência primária local.
- Acessibilidade de ferramentas MCP no runtime de cada agente: depende do host; o doctor local não deve inferir isso apenas da configuração.
