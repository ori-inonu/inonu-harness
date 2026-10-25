# Fluxo SDD e JEV

## Caminho de trabalho

Use a cadeia:

1. **Constituição** — confirmar objetivo, escopo e limites.
2. **Pesquisa** — coletar evidências primárias e registrar incertezas.
3. **Especificação** — transformar decisões confirmadas em requisitos observáveis.
4. **Planejamento** — agrupar requisitos em fases com dependências.
5. **Tarefas** — criar tarefas finitas, IDs estáveis e critérios verificáveis.
6. **Implementação** — executar uma tarefa autorizada por vez.
7. **Revisão** — revisar o diff e usar uma revisão independente quando o risco justificar.
8. **Convergência** — fechar somente quando os critérios e verificações tiverem evidência.

Guarde artefatos de marcos em `docs/specs/milestones/vX.Y.Z/`. Use `decisions.md` para mapa, evidências, incertezas e decisões; `spec.md` para requisitos confirmados; `plan.md` e `tasks.md` para fases e tarefas; `checkpoint.md` para estado, evidências, bloqueios e próximo passo.

## Núcleo local M0

O Inonu acrescenta ferramentas locais a esse processo, sem substituir o Codex nem criar etapas SDD novas. Execute `python -m inonu_harness doctor` para um inventário JSON sanitizado, `python -m inonu_harness baseline run ...` para a fixture offline e `python -m inonu_harness decisions ...` para consultar o Decision Graph persistente.

O Decision Graph começa pendente. Revisões mantêm histórico; uma revisão marcada como mudança de premissa pode invalidar dependentes transitivos. Recomendações JEV são registros consultivos e não concedem autorização. A autorização exige evidência para cada critério requerido e, por si só, não executa ação externa.

O `SddDecisionGate` é uma fronteira opcional de biblioteca e começa desativada. Nesse estado, não chama o adaptador JEV nem acessa o grafo. O adaptador usa um transporte MCP injetado; o mock suporta os testes sem rede ou chamadas pagas. O CLI não configura um transporte JEV ao vivo. Ativar o gate em uma integração exige que o chamador forneça as interfaces locais e continue aplicando seus próprios limites de autorização. Não há mudança à sequência de oito etapas acima.

## Contexto de decisões opt-in

`SddDecisionContextAdapter` oferece uma leitura local e somente de leitura para um chamador que queira anexar decisões escolhidas ao contexto de uma tarefa. Ele começa desativado; nesse modo, `load_context(ids)` retorna `disabled` sem ler o grafo. Para habilitá-lo, o chamador precisa fornecer um `DecisionGraph` local. A lista não vazia de IDs é explícita, preserva sua ordem e não é descoberta automaticamente.

Exemplo de uso dentro de uma integração que já possui o grafo:

```python
from inonu_harness.sdd_adapter import SddDecisionContextAdapter

adapter = SddDecisionContextAdapter(enabled=True, graph=decision_graph)
result = adapter.load_context(["decision-storage", "decision-retention"])
if result.status == "ready":
    task_context_decisions = result.decisions
```

O resultado contém apenas pergunta, alternativas, restrições, critérios, dependências, estado, referências de evidência, recomendação, alternativa autorizada, invalidações e critérios validados. Histórico, timestamps, ator, razão livre de bloqueio e proveniência textual livre ficam fora da projeção. Recomendação e autorização permanecem separadas; o adaptador não grava, autoriza, chama JEV, injeta prompt nem altera o fluxo SDD. IDs inválidos retornam `invalid_request`; um ID válido que não exista propaga `DecisionNotFound`. A projeção não detecta segredos em texto permitido, então o chamador escolhe quais decisões são apropriadas para compartilhar com o agente.

Os testes de `fixtures/sdd_context/context-projection.json` exercitam o opt-in com SQLite temporário e registram uma avaliação offline. Essa avaliação cobre o contrato e o fixture local, sem medir qualidade de agente ou ganho de produtividade.

Para obter contexto manualmente no fluxo SDD, selecione os IDs e execute:

```powershell
python -m inonu_harness decisions --db ./.inonu-harness/decisions.sqlite context --ids decision-storage decision-retention
```

O comando imprime JSON somente para os IDs escolhidos e abre um banco existente em modo read-only; se o banco não existir ou não tiver schema compatível, o comando falha sem criá-lo ou atualizá-lo. O chamador pode anexar a saída à tarefa SDD depois de revisar o conteúdo. Não há descoberta automática nem injeção em prompt. Campos textuais permitidos continuam sob responsabilidade do chamador, pois não há varredura de segredos.

Use o comando `decisions packet` para reunir uma tarefa e as decisões selecionadas em um único pacote JSON. Crie um arquivo UTF-8 com exatamente `task_id`, `config_id` e `prompt`, todos como strings não vazias:

```json
{
  "task_id": "planning.storage",
  "config_id": "sdd.manual.v1",
  "prompt": "Resuma a tarefa e proponha o próximo passo manual."
}
```

Execute `python -m inonu_harness decisions --db ./local/decisions.sqlite packet --task-file ./task.json --ids decision-storage decision-retention`. O comando exige IDs explícitos, lê o banco existente em modo read-only e imprime `schema_version`, a tarefa validada e a projeção allowlisted das decisões na ordem solicitada. Revise o JSON e anexe-o manualmente à tarefa; o CLI não injeta contexto nem executa um agente. O texto `prompt` aparece na saída, então selecione apenas o conteúdo que pretende compartilhar.

Para executar a verificação local, use `python -m unittest discover -s tests -v`. O CI executa a mesma suíte sem segredos, serviços externos ou dependências de runtime.

## Decisões delimitadas

Use JEV quando houver uma escolha real entre opções. Envie uma especificação sanitizada com id, goal, facts, rails e de duas a oito options; cada opção contém id, label e what. Acrescente unknowns quando a evidência necessária estiver ausente.

Chame consensus_plan antes de consensus_run com o mesmo objeto de decisão. Deixe max_calls omitido salvo quando existir um limite positivo solicitado para aquela chamada. A recomendação do JEV é evidência consultiva: ela não concede autorização, não substitui um teste e não determina que uma tarefa terminou.

Uma pergunta do JEV feita junto com outras perguntas é avaliada de forma independente contra o mesmo estado. Se uma resposta depender de outra, coordene chamadas sucessivas e registre essa dependência.

Quando o JEV estiver indisponível, registre sem-jev, faça somente a escolha reversível de menor risco e continue o trabalho independente. Decisões sem evidência suficiente permanecem abertas.

## Roteamento adaptativo

| Situação | Ação |
| --- | --- |
| Regra objetiva e determinística | Resolver em código |
| Escolha delimitada entre opções conhecidas | Consultar JEV |
| Avaliações independentes | Agrupar na mesma chamada |
| Dependências entre decisões | Usar grafo e chamadas sucessivas |
| Evidência insuficiente | Pesquisar antes de decidir |
| Limite de autorização ou ação protegida | Bloquear essa ação |
| Teste contradiz uma decisão | Reabrir a decisão e revisar dependentes |

## Tarefas paralelas

Para trabalho SDD paralelo, mantenha um coordenador e use os agentes nativos do host. Cada agente recebe uma tarefa finita, um conjunto exclusivo de arquivos e critérios de aceite claros. Apenas o coordenador faz chamadas pagas ao JEV, resolve conflitos e verifica a convergência. Espere os agentes terminarem e valide as evidências reais antes de fechar tarefas.

## Limites

Não peça ao operador decisões rotineiras em uma execução autônoma; transforme-as em escolhas delimitadas para JEV quando a evidência existir. Preserve para aprovação humana qualquer ação sobre dinheiro real, carteiras, credenciais, autenticação, limites de risco, migrações de dados/esquema, billing, serviços pagos ou mudanças Git destrutivas. Registre o bloqueio e avance as tarefas independentes.
