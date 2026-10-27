# Fluxo SDD e JEV

## Gate determinístico antes da convergência

Antes de fechar a etapa de convergência, execute `python -m inonu_harness check` no checkout. O comando compila `inonu_harness`, `scripts` e `tests` e roda a suíte de testes, imprimindo um JSON com o resultado de cada passo. Ele é o gate determinístico da convergência: a saída 0 é evidência para os critérios de verificação, mas não prova correção semântica nem substitui a revisão independente. O `check` verifica somente o layout deste checkout.

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

Os números de marcos e versões seguem o esquema de [docs/versioning.md](versioning.md): o marco `n` tem a versão `0.(n // 100).(n % 100)`, então o marco 24 é `0.0.24` e o marco 100 é `0.1.0`. Cada pasta `vX.Y.Z` leva o número do seu marco, e todos os manifestos carregam a versão do último marco entregue (entregar um marco os atualiza juntos, e `milestone new` propõe o seguinte). Os números anteriores deste repositório foram renumerados de `v0.N.0` para `v0.0.N`; o histórico do Git, os ids do Jev e os recibos mantêm os números antigos, e a tabela em [docs/versioning.md](versioning.md) os traduz. `1.0.0` é decisão do dono.

Para criar e conferir pastas de marcos, use `python -m inonu_harness milestone new [--title TEXT]`, que cria a pasta do próximo marco a partir das versões dos manifestos, e `python -m inonu_harness milestone check [VERSION ...] [--from VERSION]`, que confere a estrutura e a cobertura de requisitos por tarefas e só lê arquivos. O passo `milestones` do `check` roda quando `docs/specs/milestones` existe. Essa conferência prova cobertura, não que um requisito está cumprido; `checkpoint.md` continua sendo escrito à mão. Detalhes em [docs/milestones.md](milestones.md).

Para fechar um marco, depois de os manifestos declararem a versão dele e de a pasta passar pela conferência, use `python -m inonu_harness milestone close [VERSION] [--date YYYY-MM-DD]`. O `checkpoint.md` precisa nomear a versão do marco na primeira linha visível, ter a linha `Status:` e as seções `## Verification` e `## Limits`; a data não pode ser posterior a hoje. O comando só acrescenta a entrada do marco a `MILESTONES.md`, o índice dos marcos fechados: não cria tag, não move nem apaga arquivos e não prova que os testes passaram, pois essa evidência continua no checkpoint.

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

O comando imprime JSON somente para os IDs escolhidos e abre um banco existente em modo read-only; se o banco não existir ou não tiver schema compatível, o comando falha sem criá-lo ou atualizá-lo. O chamador pode anexar a saída à tarefa SDD depois de revisar o conteúdo. Não há descoberta automática nem injeção em prompt. Campos textuais permitidos continuam sob responsabilidade do chamador; a varredura opcional de `--refuse-secret-patterns` (abaixo) cobre apenas alguns formatos.

Use o comando `decisions packet` para reunir uma tarefa e as decisões selecionadas em um único pacote JSON. Crie um arquivo UTF-8 com exatamente `task_id`, `config_id` e `prompt`, todos como strings não vazias:

```json
{
  "task_id": "planning.storage",
  "config_id": "sdd.manual.v1",
  "prompt": "Resuma a tarefa e proponha o próximo passo manual."
}
```

Execute `python -m inonu_harness decisions --db ./local/decisions.sqlite packet --task-file ./task.json --ids decision-storage decision-retention`. O comando exige IDs explícitos, lê o banco existente em modo read-only e imprime `schema_version`, a tarefa validada e a projeção allowlisted das decisões na ordem solicitada. Revise o JSON e anexe-o manualmente à tarefa; o CLI não injeta contexto nem executa um agente. O texto `prompt` aparece na saída, então selecione apenas o conteúdo que pretende compartilhar.

Passe `--refuse-secret-patterns` a `context` ou `packet` sempre que a saída for anexada a um agente. A opção é desligada por padrão. Com ela, o comando varre exatamente o objeto que seria impresso, incluindo o `prompt` da tarefa, em busca de um conjunto restrito de formatos: blocos de chave privada PEM, identificadores de chave de acesso da AWS, tokens do GitHub, do Slack, de API do Google, do Stripe, da Anthropic e de estilo OpenAI, JWTs, cabeçalhos `Bearer` e atribuições como `api_key` ou `password` seguidas de um valor longo. Se houver correspondência, o comando não imprime nada no stdout, escreve uma linha no stderr com o nome da regra e o caminho (por exemplo `task.prompt`), nunca o valor, e sai com código 2. Sem a opção, a saída não muda. A varredura não detecta senhas em texto livre, tokens personalizados nem a maioria dos outros formatos, pode gerar falsos positivos e não substitui a revisão do conteúdo; ela não redige nada e não varre o banco.

Use `decisions as-of` para ver como uma decisão estava em um instante passado, por exemplo ao auditar uma autorização antiga: `python -m inonu_harness decisions --db ./local/decisions.sqlite as-of 2026-10-26T12:00:00Z --ids decision-storage`. O timestamp exige deslocamento explícito (`Z` ou `+HH:MM`); sem ele o comando sai com código 2. O comando lê apenas o histórico de revisões, abre o banco existente em modo read-only, não grava nada e não altera o schema. Cada item traz `state` (`existed` ou `not_yet_created`), a revisão vigente, `recorded_at`, `later_revision` e o snapshot no mesmo formato de `decisions show`. Os horários são os do relógio da máquina que gravou cada revisão e não são autenticados; o resultado é uma ajuda local de auditoria, não um livro-razão à prova de adulteração. Ele não mostra um estado anterior à primeira revisão.

Use `decisions ready` para listar as decisões pendentes cujas dependências declaradas diretas já estão autorizadas (isso não autoriza nem reserva nada; o grafo não exige que as dependências de uma decisão estejam autorizadas antes dela): `python -m inonu_harness decisions --db ./local/decisions.sqlite ready`. Uma decisão pendente está em `ready` quando todas as dependências declaradas estão autorizadas; sem dependências, ela já está pronta. As decisões pendentes que ainda esperam ficam em `waiting`, com `waiting_on` listando, na ordem declarada, cada dependência não autorizada e o seu `status` (`missing` quando o banco não tem essa decisão). Decisões bloqueadas, invalidadas ou autorizadas não aparecem. O comando abre o banco existente em modo read-only, não grava nada e não altera o schema. Ele não autoriza, não reserva, não agenda e não trata uma recomendação como aprovação. A saída traz o texto da pergunta de cada decisão, como `show`, e não varre credenciais; revise-a antes de anexá-la a um agente.

Para executar a verificação local, use `python -m unittest discover -s tests -v`. O CI executa a mesma suíte sem segredos, serviços externos ou dependências de runtime.

## Decisões delimitadas

Use JEV quando houver uma escolha real entre opções. Envie uma especificação sanitizada com id, goal, facts, rails e de duas a oito options; cada opção contém id, label e what. Acrescente unknowns quando a evidência necessária estiver ausente.

Nenhuma chamada ao JEV sai sem um documento escrito para a decisão, e o texto desse documento vai para `facts` como está, sem resumo. `python -m inonu_harness jev spec --decision PATH --doc PATH [--doc PATH ...] [--root DIR] [--max-facts N]` lê a decisão como objeto JSON e imprime a especificação em uma linha, pronta para `consensus_plan` e `consensus_run`. Para cada documento, na ordem dada, ele gera um fato de origem com o caminho relativo a `--root` e os 16 primeiros dígitos hexadecimais do SHA-256 do arquivo, seguido do texto em trechos de até 300 caracteres. Sem `--doc`, o comando sai com código 2 e nada na saída padrão. Ele também recusa com código 2 um arquivo que não seja UTF-8 regular dentro de `--root` (sem link simbólico, sem dois-pontos no nome, de até 64 KiB, sem NUL e sem repetição, mesmo por hard link), um documento sem texto, texto que case com os padrões de segredo (os do próprio juiz e alguns formatos comuns de token; não reconhece todo segredo, então não coloque credenciais em documentos), chaves desconhecidas na decisão e valores acima dos limites do JEV, contados em unidades UTF-16 como o servidor conta. Acima de `--max-facts` (80 por padrão) ele recusa e informa a contagem; nunca trunca. O comando não chama o JEV, não decide e não grava arquivo.

O documento descreve o problema, o que o código faz hoje e as restrições, sem afirmar a resposta: se ele afirmar a resposta, o juiz recebe a conclusão e não o contexto. As opções são neutras e incluem "não fazer nada" quando isso for uma escolha real. O comando não verifica se o documento vaza a resposta; essa revisão continua humana. Se o JEV devolver apenas `internal error`, um limite pode ter sido violado, porque o servidor não informa qual; confira os limites antes de repetir a chamada.

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

## Escolha de ferramentas

Escolha o recurso pela pergunta. Consulte o [inventário de integrações](integrations.md) para contratos detalhados e disponibilidade observada por host.

| Necessidade | Use | Limite ou fallback |
| --- | --- | --- |
| Encontrar texto exato, logs ou chaves de configuração; ler um arquivo conhecido | `rg` e leitura direta | Use um comando ou teste determinístico para provar comportamento. |
| Encontrar símbolos, chamadas, dependências ou impacto entre arquivos | CodeGraph MCP quando responsivo; CLI local quando instalada | Se ambos faltarem, use busca textual e leitura direta. Resultados do grafo não provam execução. |
| Reduzir saída de um comando | RTK em rotas suportadas | Se a saída compactada omitir detalhe necessário, repita com `rtk bypass <command>`; não presuma que hooks ou proxy estejam ativos. |
| Analisar documento, log ou JSON excepcionalmente longo fora do terminal | Headroom sob demanda com `headroom_compress` | Recupere o trecho original com `headroom_retrieve` ou releia a fonte antes de confirmar fatos. |
| Escolher entre alternativas de engenharia delimitadas | JEV pelo protocolo em [Decisões delimitadas](#decisões-delimitadas) | A recomendação é consultiva; evidência determinística e autorização humana mantêm autoridade. |
| Anexar decisões persistentes a uma tarefa | Decision Graph `context` ou `packet` com IDs explícitos, conforme [Contexto de decisões opt-in](#contexto-de-decisões-opt-in) | A leitura é opt-in e somente de leitura; revise o pacote manualmente. Não há descoberta nem injeção automática. |
| Implementar uma mudança delimitada | Ponytail e reutilização do que já existe | Reduza o escopo sem remover critérios de aceite, segurança ou verificações necessárias. |

## Tarefas paralelas

Para trabalho SDD paralelo, mantenha um coordenador e use os agentes nativos do host. Cada agente recebe uma tarefa finita, um conjunto exclusivo de arquivos e critérios de aceite claros. Apenas o coordenador faz chamadas pagas ao JEV, resolve conflitos e verifica a convergência. Espere os agentes terminarem e valide as evidências reais antes de fechar tarefas.

## Limites

Não peça ao operador decisões rotineiras em uma execução autônoma; transforme-as em escolhas delimitadas para JEV quando a evidência existir. Preserve para aprovação humana qualquer ação sobre dinheiro real, carteiras, credenciais, autenticação, limites de risco, migrações de dados/esquema, billing, serviços pagos ou mudanças Git destrutivas. Registre o bloqueio e avance as tarefas independentes.

## Auditoria local opcional de artefatos

Use `python -m inonu_harness sdd audit MANIFEST [--root ROOT]` quando quiser conferir os vínculos declarados de um marco. O comando emite JSON: código de saída 0 indica contrato aprovado, 1 indica achados e 2 indica entrada inválida. Sem `--root`, caminhos de evidência são resolvidos a partir do diretório do manifesto. Os exemplos sintéticos compartilham evidências em `fixtures/sdd_audit/evidence`, então use:

```powershell
python -m inonu_harness sdd audit fixtures/sdd_audit/clear-change/manifest.json --root fixtures/sdd_audit
```

Essa auditoria é uma checagem opcional durante a revisão de artefatos, sem alterar as oito etapas acima. Ela confere esquema, vínculos explícitos e bytes locais contra SHA-256, sem executar comandos, chamar serviços, gravar estado ou conceder autorização. Mudanças nos bytes produzem `evidence_changed`; hashes iguais não provam que os resultados são verdadeiros, que uma verificação foi executada ou que o conteúdo satisfaz semanticamente os requisitos. O relatório não interpreta Markdown, não encontra requisitos omitidos e não autentica quem produziu uma evidência. Os cinco casos congelados (`clear-change`, `ambiguous-change`, `reproducible-bug`, `specification-delta` e `protected-action`) são sintéticos e não descrevem execuções de agentes. Consulte [a especificação v0.0.8](specs/milestones/v0.0.8/spec.md) para o contrato completo.
