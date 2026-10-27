# Convergência M0

## Execuções verificadas

| Verificação | Resultado |
| --- | --- |
| `python -m unittest discover -s tests -v` | exit 0; 43 testes passaram. |
| `python -m inonu_harness doctor` | exit 0; JSON válido, schema 1, 6 MCPs registrados e acessibilidade de todos marcada `unknown`. A versão desktop também fica `unknown`. |
| Doctor após a lacuna R01 | exit 0; 100 skills com origem/versão e `session_availability: unknown`; 100 incertezas por skill; os 6 MCPs seguem com acessibilidade `unknown`; o caminho do perfil local não aparece no JSON. |
| `python -m inonu_harness baseline run --fixture fixtures/baseline/acceptance.json --execution-id convergence-before` | exit 0; fixture determinística executada. |
| Segunda execução da mesma fixture e `python -m inonu_harness baseline compare <resultado-anterior.json> <resultado-posterior.json>` | exit 0; execuções compatíveis. Os arquivos de comparação foram temporários. Tokens e custo permaneceram `null`. |
| Workflow nativo `inonu-m0-r01-skill-availability-v2` | terminal `complete`; implementação e revisão independente submetidas; comandos de convergência passaram: 43 testes e `git diff --check`. |
| `git diff --check` | exit 0. |
| Varredura sanitizada do working tree | 37 arquivos de texto examinados; nenhum caminho do perfil local ou padrão de credencial em documentação/configuração; nenhuma linha com espaços finais. Nenhum conteúdo bruto da configuração foi impresso. |
| `git status --short --branch --untracked-files=all` | branch local `codex/m0-inonu-harness`; 33 caminhos alterados ou novos ao fim da auditoria; sem upstream indicado. Não houve commit ou push nesta execução. |

## Evidência por requisito

- **R01 — Diagnóstico:** `test_doctor.py` cobre schema, allowlist, proveniência, campos `unknown`, conflitos, classificação estrutural de hooks e disponibilidade por skill. O CLI real passou; cada uma das 100 skills encontradas tem `session_availability: unknown` com origem e motivo fixos, porque o probe local não comprova o carregamento na sessão. Acessibilidade MCP e versão desktop também permanecem `unknown` quando não observáveis por interface local oficial.
- **R02 — Manifesto:** `integrations.json` distingue intenção e estado. `test_manifest_separates_intent_from_environment_observations` passou. Para CodeGraph, a licença da distribuição local é `unknown`; MIT aparece apenas como licença upstream, pois o mapeamento do executável instalado não foi provado. `docs/integrations.md` registra contratos, sobreposições, licenças, testes e gatilhos para implementação própria.
- **R03 — Baseline:** dez testes de `test_baseline.py` passaram, incluindo rejeição do schema não suportado. Execução e comparação CLI passaram; cada medição mantém origem, e tokens/custo indisponíveis ficaram nulos.
- **R04 — Decision Graph:** 14 testes de `test_decision_graph.py` passaram. Cobrem persistência/reabertura, histórico, idempotência, ciclos, evidência por critério, autorização explícita e invalidação transitiva. O smoke CLI de F05 verificou create, recommend, authorize, review, list e show; recomendar não autorizou e revisar preservou o histórico.
- **R05 — Adaptador JEV:** oito testes cobrem plan/run com o mesmo spec, schema, opções permitidas, timeout, indisponibilidade, recusa e mock. Não houve chamada JEV ao vivo; o transporte MCP portátil permanece não implementado.
- **R06 — SDD opcional:** cinco testes de `test_sdd_adapter.py` passaram. O gate desativado não acessa grafo nem adaptador; ativado, grava recomendação sem autorizar. A sequência existente de oito etapas foi mantida.
- **R07 — Verificação:** 43 testes locais passaram; `pyproject.toml` não declara dependências de runtime e a CI executa a mesma suíte sem credenciais ou serviços pagos. A CI em runner hospedado não foi executada.
- **Segurança e escopo da missão:** o trabalho permaneceu na branch local `codex/m0-inonu-harness`; não houve commit, push, publicação, instalação global, alteração de configuração global, migração de dados reais ou modificação de produção. Nenhum valor secreto foi lido ou incluído. A varredura final examinou 37 arquivos de texto: não encontrou caminhos do perfil ou padrões de credencial nos documentos/configuração e não encontrou espaços finais.

## Revisão e limites restantes

A revisão independente identificou dois achados, ambos corrigidos antes desta convergência: comparações com versões de schema desconhecidas agora são rejeitadas, e a procedência da licença local de CodeGraph foi rebaixada para desconhecida. As regressões correspondentes fazem parte dos 43 testes.

Na auditoria final de R01, uma revisão independente adicional não encontrou falhas na disponibilidade por skill. Ela conferiu o normalizador, as incertezas emitidas, os testes e os critérios atualizados. Como esses arquivos ainda não são rastreados pelo Git, o reviewer registrou que `git diff` não mostrava o patch; a revisão avaliou o conteúdo atual contra os critérios. O smoke do Doctor confirmou os 100 registros e a ausência do caminho do perfil.

O estado do Git confirma que o trabalho permanece local e sem commit. Nenhuma publicação foi feita nesta execução; a ausência de upstream no `git status` não prova que nenhum branch de mesmo nome exista em um remoto, cujo estado não foi inspecionado. A versão do app desktop, a acessibilidade MCP fora da sessão atual, o transporte JEV portátil, o mapeamento da distribuição CodeGraph e a execução hospedada da CI continuam sem verificação.
