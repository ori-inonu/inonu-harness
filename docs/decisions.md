# Decisões e questões abertas

## Confirmado

- O Inonu começa pelo fluxo SDD existente; o JEV recebe escolhas delimitadas e retorna recomendações.
- Requisitos, evidências, decisões e verificações precisam ser preservados ao longo da execução.
- O repositório será público e não incluirá credenciais, caminhos pessoais, índices ou dados locais.
- CodeGraph 3.0.1 foi instalado, a integração MCP do Codex foi registrada e o índice local deste repositório foi inicializado.
- O índice .codegraph/ e o cache não entram no Git.
- Nenhum código-fonte de outra ferramenta foi copiado para este repositório.

## Hipóteses para testar

- Um Decision Graph pode persistir decisões e dependências e reabrir apenas o trabalho invalidado por evidência nova.
- DeepSeek Harness é um primeiro runtime experimental; Pi é um comparador de menor superfície. Nenhum está escolhido.
- CodeGraph, RTK, Headroom e Ponytail podem operar em camadas separadas sem reduzir a qualidade do SDD.

## Pendências

- Recarregar o Codex para carregar as ferramentas MCP recém-registradas.
- Confirmar as variáveis e opções válidas de Headroom na versão realmente instalada.
- Confirmar o nome de ferramenta MCP do CodeGraph antes de usar HEADROOM_PROTECT_TOOL_RESULTS.
- Ativar RTK apenas em hosts onde as chamadas passam pelo matcher Bash.
- Definir o esquema mínimo e os gatilhos para revisar decisões dependentes.
- Medir a matriz de ferramentas e a comparação entre runtimes com tarefas idênticas.
- Escolher uma licença para o repositório. Até essa decisão, o repo permanece público sem declarar licença de reutilização.
