# Decisões M4

## M4-D01 — Novo subcomando `decisions packet`

- **Escolha:** adicionar um subcomando que combina um arquivo de tarefa validado com a projeção dos IDs explícitos, mantendo `decisions context` intacto.
- **Alternativas avaliadas:** subcomando novo; flag opcional no comando `context`; apenas documentação.
- **Evidência JEV:** `consensus_plan`/`consensus_run` para `inonu-m4-context-packet-seam`, hash `74b42fda029ad6066c45b94713a3247adaf150f0d3e7e979271599ac409c812c`; consenso consultivo apontou `packet_subcommand`. Foram observadas 12 chamadas e 11.492 tokens de entrada. A resposta orienta a escolha; não concede autorização.
- **Razão local:** o novo comando oferece um pacote com contrato próprio sem alterar a saída existente de `context`. A implementação reutiliza o adaptador de projeção e o caminho read-only existentes.

## M4-D02 — Piloto de respostas permanece bloqueado neste host

- **Fato:** o schema disponível de `collaboration.spawn_agent` não expõe um controle de bloqueio de ferramentas, rede, arquivos ou escrita por agente. O ambiente de trabalho reporta acesso irrestrito a arquivos.
- **Decisão:** não executar o piloto M3 aqui; instruções no prompt não provam isolamento técnico.
- **Limite:** a evidência descreve o host e a interface disponíveis nesta execução. Não afirma que outros hosts não possam impor isolamento.

## M4-D03 — Fonte do contrato e teste

- `SddDecisionContextAdapter.load_context(ids)` é a projeção existente, allowlisted e ordenada (`inonu_harness/sdd_adapter.py`).
- O CLI a abre pelo `_open_graph(..., read_only=True)` para `context`; o novo uso deve manter a mesma proteção (`inonu_harness/cli.py`, `inonu_harness/sqlite_store.py`).
- `tests/test_cli.py` já chama `main(argv)` com SQLite temporário e verifica formato, ordem e ausência de mutação; esse é o seam M4.
- O CodeGraph MCP não respondeu às consultas nesta execução. O CLI local `codegraph doctor` confirmou a versão 3.0.1 e suporte nativo; `deps`/`rdeps` concluíram e apontaram o caminho CLI–adaptador, `__main__.py` e os testes. A busca textual complementou a evidência.
