# Tarefas M1

## M1-T01 — Contexto SDD opt-in e avaliação fixture-backed

**Bloqueado por:** nenhum.

**Entrega:** um chamador pode pedir uma projeção somente de leitura para IDs de decisão explícitos, e uma fixture local mede os critérios observáveis sem alegar ganho de desempenho de agente.

**Critérios de aceite:**

- [x] O adaptador começa desativado e não acessa o grafo nesse estado.
- [x] O modo ativado exige grafo, valida IDs, preserva a ordem pedida e propaga `DecisionNotFound` para ID ausente.
- [x] A projeção usa apenas os campos enumerados em `spec.md`; não inclui histórico, timestamps, ator ou proveniência livre.
- [x] A leitura não grava eventos, não chama JEV e não converte recomendação em autorização.
- [x] Fixture e teste geram um resultado baseline com os critérios medidos, duração da chamada e tokens/modelo/custo ausentes como `null`.
- [x] Guias documentam o adaptador como opt-in manual e mantêm as oito etapas SDD intactas.
- [x] Teste focado e suíte local passam.

## M1-T02 — Revisão independente

**Bloqueado por:** M1-T01.

**Entrega:** agente independente verifica fidelidade ao spec, privacidade e testes; devolve achados com severidade ou uma conclusão explícita sem achados.

Após M1-T02, o coordenador executa a convergência determinística e grava `convergence.md` e `checkpoint.md`.

**Resultado:** a primeira revisão encontrou um P2 na validação de identificadores malformados. O follow-up M1-ID-FIX alinhou o formato ao Decision Graph e acrescentou testes; a revisão independente M1-ID-REVIEW não encontrou novos achados. Veja `convergence.md`.

## Follow-up M1-ID-FIX — Formato de IDs

**Estado:** concluído. A validação do adaptador segue o padrão `[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}` já usado pelo Decision Graph. IDs malformados retornam `invalid_request`; IDs válidos ausentes continuam propagando `DecisionNotFound`.

**Verificação:** teste focado 5/5 e suíte local 48/48 passaram; revisão independente sem achados.
