# Integrações

As configurações desta página têm estados diferentes: comandos oficiais verificados, sugestões da conversa compartilhada e pontos ainda não validados. Não aplique uma sugestão de Headroom/Ponytail até conferir o release instalado e o nome real das ferramentas MCP.

## Responsabilidade e estado

| Ferramenta | Papel proposto | Estado |
| --- | --- | --- |
| RTK | Filtrar saídas ruidosas de comandos de terminal | Comando Codex conferido; hook de projeto não aplicado |
| Headroom | Gerenciar contexto e permitir recuperação do conteúdo original | Perfil coding é uma proposta da conversa; nomes das variáveis ainda precisam ser validados |
| Ponytail | Simplificar escopo e implementação sem enfraquecer aceite e segurança | Usar full como política; variável de ambiente da conversa ainda não validada |
| CodeGraph | Indexar relações e recuperar evidência estrutural do repositório | CLI 3.0.1 instalada, MCP do Codex registrado e índice deste projeto criado |

## CodeGraph

A documentação oficial recomenda instalar a CLI pelo npm e verificar o runtime com codegraph doctor. A integração MCP do Codex é configurada no perfil local do agente; revise primeiro o plano de escrita do instalador. O Codex compartilha sua configuração MCP entre CLI e extensão, então cada agente configura a própria máquina.

~~~powershell
npm install -g @lzehrung/codegraph@3.0.1
codegraph doctor
codegraph install --target codex --dry-run
~~~

Depois de revisar os arquivos e o escopo que o dry-run propõe, a gravação pode ser aplicada localmente:

~~~powershell
codegraph install --target codex --yes
~~~

No diretório do repositório, inicialize o índice:

~~~powershell
codegraph init
codegraph status --root .
~~~

O índice e o cache ficam em .codegraph/ e não entram no Git. O comando init pode ajustar o .gitignore; este repositório já ignora essa pasta. Não inicie um servidor persistente em background: a integração MCP local deve ser controlada pelo agente.

Neste ambiente, a instalação 3.0.1 passou no doctor, o preview do Codex apontou apenas o skill CodeGraph e a seção MCP global, e o instalador verificou a configuração gravada. A sessão atual precisa recarregar o Codex para carregar as ferramentas MCP.

Referências: [instalação CodeGraph](https://github.com/lzehrung/codegraph/blob/main/docs/installation.md), [servidor MCP CodeGraph](https://github.com/lzehrung/codegraph/blob/main/docs/mcp.md), [release 3.0.1](https://github.com/lzehrung/codegraph/releases/tag/v3.0.1).

## RTK

A versão atual do guia RTK registra rtk init --codex para configurar este repositório e rtk init -g --codex para configurar o perfil global. Prefira o escopo do projeto quando quiser compartilhar o comportamento e evitar mudar outros repositórios. Revise o plano de escrita antes de aplicar:

~~~powershell
rtk init --codex --dry-run
~~~

O preview deste repositório propôs criar RTK.md, acrescentar uma referência a ele em AGENTS.md e alterar .codex/hooks.json. Não apliquei esse hook: o processador Codex do RTK registra um matcher Bash, enquanto os comandos desta sessão usam PowerShell. Ative-o apenas em um host em que as chamadas de shell passem por Bash. A reescrita do RTK continua sujeita às verificações nativas de permissão e sandbox do Codex.

A redução de saída e a estimativa de tokens do RTK não equivalem automaticamente a uma redução igual na fatura do modelo.

Referências: [Quick Start do RTK](https://github.com/rtk-ai/rtk/blob/develop/docs/guide/getting-started/quick-start.md), [hook do Codex](https://github.com/rtk-ai/rtk/blob/develop/hooks/codex/README.md).

## Headroom e Ponytail

A conversa propõe este ponto de partida, mas os comandos e as variáveis precisam ser confirmados na versão instalada antes de ativação:

~~~sh
HEADROOM_SAVINGS_PROFILE=coding
HEADROOM_COMPRESS_USER_MESSAGES=0
HEADROOM_PROTECT_TOOL_RESULTS=codegraph_explore
PONYTAIL_DEFAULT_MODE=full
headroom wrap codex --code-memory none
~~~

Não comprima com perda perguntas, requisitos, decisões, contratos ou evidências enviados ao JEV. Evite dupla compressão de saída RTK pelo Headroom e preserve um caminho para recuperar o conteúdo original em debugging, segurança, testes e alterações críticas. Confirme se codegraph_explore é o nome efetivamente exposto pelo MCP antes de protegê-lo por nome.

Ponytail é uma política de simplificação dentro do SDD, não um estágio de compressão de contexto. A proposta é detectar complexidade desnecessária no plano, implementar a menor solução completa em full e revisar a mudança sem remover critérios de aceite, acessibilidade, validação ou segurança. Não use ultra globalmente enquanto houver especificações aprovadas; reserve o questionamento de requisitos para uma etapa de descoberta deliberada.

## Separação de camadas

Use CodeGraph para estrutura do código, RTK para saída de terminal, Headroom para contexto e recuperação e Ponytail para simplicidade da solução. Não ative Serena, grafo nativo do Headroom e CodeGraph juntos sem medir a sobreposição.
