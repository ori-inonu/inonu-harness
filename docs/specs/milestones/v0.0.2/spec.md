# Inonu Harness M1 — SDD Decision Context

## Problema

O M0 guarda decisões persistentes, mas o fluxo SDD não oferece uma interface de leitura para anexar decisões escolhidas explicitamente ao contexto de uma tarefa. A integração atual é um gate opcional para recomendações JEV, não uma projeção de contexto.

## Solução confirmada

Adicionar um adaptador local, tipado e somente de leitura que devolve os registros atuais de decisão selecionados pelo chamador. Ele começa desativado, não lê o grafo quando desativado, não chama JEV e não altera o runtime nem as oito etapas do SDD.

O chamador fornece IDs explícitos. A projeção preserva a ordem solicitada e inclui apenas campos úteis ao contexto: ID e revisão, pergunta, alternativas, restrições, critérios requeridos, dependências, estado, referências de evidência (`source`, `reference`, `criterion_id`, `version`), recomendação (`alternative_id`, `source`, `version`), alternativa autorizada, IDs que invalidaram a decisão e critérios validados. Ela omite histórico, timestamps, ator da autorização, razão livre de bloqueio e proveniência livre da recomendação/evidência. Essa allowlist reduz a superfície de contexto; não detecta segredos em texto livre, então o chamador continua responsável por selecionar decisões apropriadas.

## Requisitos

### M1-R01 — Opt-in sem efeito por padrão

- A construção padrão deixa o adaptador desativado.
- Uma chamada desativada retorna `disabled` sem acessar o grafo.
- Ativar exige a interface local do Decision Graph.

### M1-R02 — Projeção explícita e somente de leitura

- O adaptador aceita uma lista não vazia de IDs válidos, sem espaços externos ou duplicatas.
- A saída contém somente as decisões pedidas, na ordem pedida, usando estado atual.
- ID inexistente propaga `DecisionNotFound`; entrada estruturalmente inválida retorna `invalid_request`.
- Recomendação e autorização continuam campos distintos; leitura não altera decisão nem histórico.

### M1-R03 — Avaliação offline reproduzível

- Um fixture determinístico cobre decisões pendentes e invalidadas, preservação da recomendação separada da autorização, seleção explícita e modo desativado.
- O teste gera um registro pela API existente de baseline. A duração mede a chamada do adaptador; modelo, tokens e custo ficam `null` por não serem observados.
- O resultado mede contrato e cobertura do fixture, não qualidade de agente, produtividade ou economia.

### M1-R04 — SDD preservado

- A documentação mostra como um chamador opt-in pode obter o contexto local.
- Nenhum hook, injeção de prompt, descoberta automática, transporte JEV ou etapa SDD nova é introduzido.
- A suíte CI existente inclui os novos testes locais sem segredos ou serviços externos.

## Seam de teste

`SddDecisionContextAdapter.load_context(ids)` é o seam público. Os testes exercitam a projeção por meio do Decision Graph com SQLite temporário e a avaliação fixture-backed pela API `run_fixture`; somente a garantia de que o modo desativado não lê dependências usa um objeto sentinela.

## Fora de escopo

- Modificar as oito etapas SDD, o runtime Codex, hooks ou configuração global.
- Injetar decisões automaticamente em prompts ou descobrir decisões sem IDs explícitos.
- Chamar Jev, habilitar transporte MCP real ou adicionar comandos CLI.
- Medir qualidade, tokens, custo ou produtividade de execuções de agentes.
- Alterar esquemas persistidos, migrar dados ou introduzir dependências.
