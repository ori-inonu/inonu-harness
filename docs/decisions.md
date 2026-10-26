# Decisões e questões abertas

## Confirmado

- O Inonu complementa o fluxo SDD existente; as oito etapas documentadas em `docs/sdd-workflow.md` continuam sendo o caminho normal.
- Requisitos, evidências, decisões e verificações precisam ser preservados ao longo da execução.
- O repositório será público e não incluirá credenciais, caminhos pessoais, índices ou dados locais.
- O Decision Graph SQLite já está implementado, incluindo revisões, histórico, evidências, dependências e idempotência; recomendações e autorizações permanecem separadas.
- Os adaptadores de contexto SDD são opt-in e somente de leitura. `decisions context` e `decisions packet` usam IDs explícitos; o segundo também valida o arquivo de tarefa e rejeita chaves JSON duplicadas.
- O gate SDD é desativado por padrão. Recomendações JEV são consultivas, não concedem autoridade e não executam operações externas.
- Nenhum código-fonte de outra ferramenta foi copiado para este repositório.

## Observações históricas do host M0 (2026-10-24)

- `docs/integrations.md` registra chamadas Jev MCP funcionando no chat coordenador e CodeGraph MCP `orient` funcionando nessa mesma sessão. Isso não comprova disponibilidade em outros chats, clientes ou na CLI portátil.
- Naquele host, CodeGraph CLI 3.0.1 estava presente e um índice local foi inicializado. São fatos históricos daquela observação, não afirmações de disponibilidade atual ou universal.
- A CLI portátil do Inonu não implementa/configura transporte JEV ao vivo. O adaptador Python aceita um transporte injetado; o mock é a opção determinística local.

## Hipóteses e decisões ainda abertas

- DeepSeek Harness e Pi permanecem candidatos de avaliação; nenhum runtime alternativo está escolhido.
- O M3 define um piloto exploratório, mas ele não foi executado neste host porque não há evidência de isolamento text-only verificável. Uma execução futura depende de comprovar esse isolamento.
- Avaliar recuperação geral de contexto ou integrações adicionais somente quando houver um caso mensurável; o adaptador atual cobre apenas decisões explicitamente selecionadas.
- Escolher uma licença para o repositório. Até essa decisão, o repo permanece público sem declarar licença de reutilização.
