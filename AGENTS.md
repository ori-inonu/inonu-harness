# Inonu Harness

Este repositório documenta uma configuração e arquitetura em pesquisa; não presuma que as propostas já foram ativadas.

- Ao mudar fases, tarefas ou critérios, leia [docs/sdd-workflow.md](docs/sdd-workflow.md).
- Ao mudar arquitetura, runtime ou recuperação de evidências, leia [docs/architecture.md](docs/architecture.md) e [docs/decisions.md](docs/decisions.md).
- Ao instalar ou configurar ferramentas, leia [docs/integrations.md](docs/integrations.md).
- Ao fazer afirmações de qualidade, tokens ou custo, siga [docs/benchmark-plan.md](docs/benchmark-plan.md).
- Use CodeGraph para perguntas que cruzam arquivos, símbolos, dependências ou impacto de uma mudança; use busca textual para strings/logs e ferramentas determinísticas para provar comportamento.

Separe fatos verificados, decisões aceitas e hipóteses. JEV recomenda; regras determinísticas e autorização humana mantêm autoridade. Preserve evidências que afetem requisitos, decisões, contratos ou verificações. Não registre raciocínio interno oculto; registre decisões explícitas, opções, evidências, critérios e validação.

Mantenha o repositório público sem credenciais, dados privados, caminhos locais, logs ou índices CodeGraph. Ações financeiras, credenciais/autenticação, migrações, billing/serviços pagos, dependências de produção e alterações Git destrutivas ficam bloqueadas até autorização específica.

Conclua uma mudança somente quando cada critério de aceite tiver evidência, as verificações determinísticas aplicáveis passarem e a revisão não deixar falhas abertas. Não some percentuais de benchmarks independentes nem trate uma resposta do JEV como prova de sucesso.
