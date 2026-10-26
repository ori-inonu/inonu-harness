# v0.14.0 — Verificação de pesquisa para o loop

Data de observação: 2026-10-26. Quatro workers Haiku verificaram em fontes primárias as afirmações que o [research.md da v0.10.0](../v0.10.0/research.md) deixou como "não verificado". Os textos das páginas da Anthropic e do Claude Code chegaram por WebFetch, que devolve texto extraído por modelo e não o HTML bruto; frases citadas devem ser conferidas na página antes de reutilizá-las. Inferências estão marcadas.

## Hook Stop do Claude Code (docs oficiais: hooks, hooks-guide, env-vars)

- Verificado: o Stop roda quando o agente principal termina de responder, mas não quando a parada veio de uma interrupção do usuário. A entrada traz `stop_hook_active` (verdadeiro quando já se continua por causa de um hook Stop), `last_assistant_message`, `background_tasks` e `session_crons`. A documentação recomenda ler `last_assistant_message` em vez do transcrito, porque o arquivo pode ainda não conter a mensagem final.
- Verificado: `decision: "block"` com `reason`, ou exit 2 com a mensagem no stderr, impedem a parada e entregam o motivo ao modelo. Depois de oito continuações consecutivas o Claude Code encerra o turno mesmo assim; o contador **zera a cada chamada de ferramenta** e o limite é `CLAUDE_CODE_STOP_HOOK_BLOCK_CAP` (padrão 8, `0` desliga).
- Verificado: o guia mostra o guarda de laço "sair cedo se `stop_hook_active`", que deixa a parada seguinte passar sem checar a condição. Timeout padrão de hooks de comando: 600 s.
- Inferência (não documentada): um verificador que falha com código diferente de 0 e 2, ou estoura o tempo, pode deixar o agente parar sem verificação, porque `onFailure` não se aplica ao Stop.
- Resumo de segunda mão (WebFetch), não confirmado no texto literal: campos do `SubagentStop`.

## Ralph e variantes (Huntley, snarktank/ralph, frankbria/ralph-claude-code)

- Nenhuma das três saídas revisadas lê o resultado de um teste, build ou git. O snarktank confia numa sentinela no stdout; o frankbria confia em `EXIT_SIGNAL` e em checkboxes escritos pelo próprio agente. O frankbria tem limite de chamadas por hora e timeout de 15 minutos por chamada, mas nenhum limite de iterações; o snarktank tem só o máximo de iterações (padrão 10), sem timeout por chamada.
- Os limiares do frankbria (sem progresso 3, mesmo erro 5, resfriamento de 30 minutos) são heurísticas; nenhuma avaliação delas foi encontrada. Tudo foi lido no código, nada foi executado.

## Anthropic (engenharia de harness para agentes longos; agentes eficazes)

- Verificado: agente inicializador na primeira sessão (script de inicialização, lista de funcionalidades em JSON com `passes`, arquivo de progresso, commit inicial) e agente de codificação nas demais, cada sessão começando do zero e apoiada em arquivos. A regra de que só o campo `passes` pode ser editado é uma instrução em prompt, não um mecanismo imposto.
- Inferência: nenhuma fonte dá limiar numérico de estagnação, máximo padrão de iterações ou esquema de log por iteração; todos esses valores são escolhas de projeto.

## OpenAI

- A página primária "harness engineering" retornou HTTP 403 em todas as variantes, e o Wayback foi recusado. **Seu texto não foi recuperado.** Só há fontes secundárias (talks e resumos) para: arquivos de instrução curtos apontando para docs, verificação como ciclo de feedback e tarefas de "limpeza". O único número obtido é o padrão de 10 turnos do Agents SDK (um padrão de código, não uma recomendação).

## Implicações para o desenho (inferência a partir do acima)

1. O sucesso vem só do código de saída de um verificador executado pelo runner, nunca da fala do agente.
2. Os limites são do runner (iterações, tempo por iteração, tempo total, janela de estagnação) e obrigatórios; o limite de 8 do hook Stop não basta como único freio.
3. Estagnação por assinatura das verificações que falham mais um hash do estado do repositório, com janela configurável (sem valor validado na literatura).
4. Um processo novo por iteração; estado só em arquivos e git.
5. Log JSONL por iteração com ids, códigos de saída e hashes, sem a saída dos comandos.
6. O runner nunca chama modelo nem serviço pago; o comando de cada passo é do chamador.

## Lacunas que continuam abertas

- Texto literal da página "harness engineering" da OpenAI.
- Texto literal da seção SubagentStop e do `onFailure` na documentação de hooks.
- Se `stop_hook_active` zera depois de uma chamada de ferramenta.
