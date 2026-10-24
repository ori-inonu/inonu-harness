# Inonu Harness

Espaço público para configurar e discutir um harness de agentes guiado por SDD, evidências e decisões verificáveis.

## Direção atual

O fluxo existente usa as etapas de SDD inspiradas nas skills de Matt Pocock e encaminha decisões delimitadas ao JEV para reduzir interrupções ao operador. A proposta do Inonu é manter esse fluxo como base e estudar um Decision Graph persistente, que registre opções, evidências, dependências e revisões sem guardar raciocínio interno oculto dos modelos.

As ferramentas ficam em camadas separadas:

| Camada | Responsabilidade proposta |
| --- | --- |
| SDD | Organizar requisitos, fases, tarefas e critérios de aceite |
| JEV | Recomendar entre opções delimitadas |
| Decision Graph | Registrar decisões, relações, evidências e revisões |
| CodeGraph | Recuperar estrutura e impacto no código |
| RTK | Filtrar ruído de saída do terminal |
| Headroom | Gerenciar contexto e permitir recuperação do conteúdo original |
| Ponytail | Simplificar a solução dentro dos requisitos aprovados |
| Verificação | Confirmar comportamento com testes, compiladores e revisão independente |

Isso é uma hipótese de arquitetura, não uma implementação pronta. A comparação entre DeepSeek Harness e Pi também continua aberta; o mesmo fluxo SDD deve ser avaliado em ambos antes de escolher um runtime.

## Começar

1. Leia [AGENTS.md](AGENTS.md) para as regras deste repositório.
2. Leia [o fluxo SDD](docs/sdd-workflow.md) para decisões e execução.
3. Leia [a arquitetura proposta](docs/architecture.md) e [as integrações](docs/integrations.md).
4. Use [o plano de avaliação](docs/benchmark-plan.md) antes de afirmar ganhos de qualidade ou custo.
5. Consulte [decisões e questões abertas](docs/decisions.md) antes de ampliar o escopo.

CodeGraph 3.0.1 foi instalado para este ambiente, integrado ao MCP do Codex e inicializado neste repositório. O Codex precisa reiniciar ou recarregar para disponibilizar as ferramentas MCP na sessão. O índice fica em .codegraph/ e é ignorado pelo Git. Outros agentes instalam a própria CLI e configuração MCP; veja [integrações](docs/integrations.md).

## Estado

Este repositório contém o ponto de partida documental e de configuração. O Decision Graph Engine e o MCP inonu_decide ainda são propostas; nenhum runtime foi escolhido como base definitiva.

O repositório é público e ainda não declara uma licença. A visibilidade pública, por si só, não concede direitos de reutilização.
