# M4 — pacote manual de tarefa e contexto de decisão

## Problema e solução

O M2 oferece `decisions context --ids`, mas o chamador precisa transportar separadamente o texto da tarefa e o JSON das decisões selecionadas. Isso torna o pacote manual mais propenso a omitir ou misturar contexto.

Adicionar `decisions packet`: um comando opt-in que lê um arquivo de tarefa fornecido pelo chamador, carrega somente as decisões apontadas por IDs explícitos e imprime um único envelope JSON. O chamador continua responsável por revisar a saída e anexá-la à tarefa; o comando não injeta prompt nem executa um agente.

```powershell
python -m inonu_harness decisions --db ./local/decisions.sqlite packet --task-file ./task.json --ids decision-storage decision-retention
```

## Contrato

O arquivo de tarefa é UTF-8 JSON, um objeto com exatamente estes campos:

```json
{
  "task_id": "plan.storage",
  "config_id": "sdd-manual.v1",
  "prompt": "Resuma a tarefa e proponha o próximo passo manual."
}
```

Os três valores devem ser strings não vazias. Rejeite JSON inválido, raiz que não seja objeto, campos ausentes, tipos inválidos, strings vazias, chaves extras e chaves repetidas em qualquer objeto JSON do arquivo. Chaves duplicadas não usam a regra usual de `json.loads` que conserva o último valor: `decisions packet` retorna exit code 2, não emite pacote e usa o formato de erro sanitizado existente. O caminho do arquivo não é incluído no resultado nem em mensagens de erro. Essa regra é específica ao arquivo de tarefa de `decisions packet`; outros leitores JSON mantêm o comportamento anterior.

| Entrada | Resultado esperado |
| --- | --- |
| O objeto de exemplo e IDs existentes | Envelope JSON no stdout com `schema_version`, `task` e `decision_context`. |
| O objeto contém uma chave adicional | Exit code 2; não emitir pacote. |
| O objeto contém uma chave JSON duplicada | Exit code 2; não emitir pacote; erro sanitizado sem o caminho do arquivo. |
| JSON malformado ou `prompt` ausente/vazio | Exit code 2; não emitir pacote. |
| ID válido não existe no banco | Preservar o erro CLI atual e exit code 2. |

Para uma tarefa válida e IDs existentes, a saída contém somente `schema_version: 1`, a tarefa validada e `decision_context`, cujo `status` e `decisions` vêm de `SddDecisionContextAdapter.load_context(ids)`. Preserve a ordem solicitada e os campos da projeção existente; não recompute nem amplie a allowlist. A recomendação e `authorized_alternative_id` continuam separados.

A forma exata é `{ "schema_version": 1, "task": {"task_id": string, "config_id": string, "prompt": string}, "decision_context": {"status": "ready", "decisions": [...]}}`; `decisions` contém os objetos projetados pelo adaptador, sem campos adicionais.

IDs malformados ou repetidos mantêm o resultado `invalid_request` do adaptador. Um ID válido ausente mantém o erro CLI existente. Erro de arquivo, JSON ou schema retorna exit code 2 no formato de erro CLI existente.

Abra somente um banco SQLite já existente com schema versão 1, em modo read-only. Um banco ausente não é criado; nenhum dado ou histórico é alterado. O resultado é escrito somente em stdout. `decisions context` conserva o formato atual.

O comando repete o texto de `prompt` no JSON de saída. O chamador deve selecionar somente conteúdo que pretende revisar e anexar; o comando não varre nem remove segredos.

## Requisitos

- **M4-R01 — Opt-in explícito:** a chamada exige arquivo de tarefa e um ou mais IDs escolhidos pelo chamador; não descobre decisões.
- **M4-R02 — Entrada estrita:** aceitar somente `task_id`, `config_id` e `prompt`, strings não vazias; rejeitar entrada inválida, chaves extras e chaves JSON duplicadas.
- **M4-R03 — Pacote estável:** emitir envelope JSON versão 1 com tarefa e projeção allowlisted, mantendo ordem e separando recomendação de autorização.
- **M4-R04 — Leitura sem mutação:** usar SQLite read-only existente; preservar bytes e histórico; manter `decisions context` inalterado.
- **M4-R05 — Fluxo atual:** uso manual, sem injeção automática, serviço externo, dependência nova ou alteração das oito etapas SDD.
- **M4-R06 — Piloto M3:** registrar que o host atual não oferece evidência de isolamento text-only por subagente; não executar o piloto neste host.

## Test seam

Exercite o comportamento por `inonu_harness.cli.main(argv)`, com arquivo JSON e SQLite temporários. Inclua chaves JSON duplicadas e confirme exit code 2, stdout vazio e ausência do caminho do arquivo no erro. Confira o envelope e sua ordem usando valores de fixture conhecidos; compare bytes/histórico do banco antes e depois; confirme que banco ausente não aparece; execute também a chamada atual `decisions context` para proteger seu formato.

## Fora de escopo

Não executar o piloto M3, chamar JEV pelo produto, ler banco pessoal, ativar integração automática, modificar runtime/hooks/configuração global, adicionar dependências, mudar o Decision Graph ou alterar a sequência SDD.
