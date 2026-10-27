# Decisões M3

## M3-D01 — Protocolo local e exploratório

- **Escolha local:** especificar um par futuro, text-only e descritivo, com tarefa e configuração constantes e somente a projeção explícita variando.
- **Estado do JEV:** o coordenador tentou `consensus_plan` duas vezes para o desenho do estudo; ambas foram recusadas como especificação inválida ou sensível. Não houve resposta consultiva de desenho e não foi executado `consensus_run`.
- **Justificativa:** a escolha documental é reversível, não executa código, não acessa dados do usuário, não faz chamadas externas e mantém o runtime e a cadeia SDD existentes. O protocolo também bloqueia execução se isolamento de ferramenta/arquivo não puder ser comprovado.
- **Limite:** esta escolha é local, não uma recomendação nem autorização JEV. Um par futuro continua exploratório; não promete ganho do Harness.

## M3-D02 — Contexto M2 como fixture, sem autorização

- **Fato de origem:** `m2-cli-consumer` foi criado a partir de fixture local e exibido pelo CLI M2; não foi lido de banco pessoal.
- **Conteúdo usado:** pergunta, restrições, critérios, estado `pending`, recomendação `cli-json` com proveniência `local-fixture` e versão `m2-fixture-1`, e `authorized_alternative_id: null`. O JSON completo e sua procedência estão em `spec.md`.
- **Interpretação:** a recomendação permanece consultiva. O rubric exige que o braço de tratamento preserve o estado pendente e a ausência de autorização.
- **Limite de M2:** a avaliação anterior só mediu entrega de campos do fixture, não qualidade de resposta de agente. M3 poderá reportar apenas observações diretas do rubric se o piloto vier a ser autorizado e executado depois.
