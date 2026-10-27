# Revisão independente M0

## Escopo e método

- Base fixa: `b5770eb9db795a02513a3b2b92a9f64352e692d7`; revisei o diff do working tree, incluindo arquivos novos, contra `docs/specs/milestones/v0.0.1/spec.md` (R01–R07), `AGENTS.md` e os testes relacionados.
- Revisei as duas dimensões separadamente: conformidade com as regras documentadas e aderência à especificação.
- `git diff --check b5770eb` passou. A suíte completa foi reportada pelo ticket F05 como 41 testes aprovados; não a repeti nesta revisão. O CI ainda não foi executado em um runner hospedado.
- A ferramenta de revisão do CodeGraph não resolveu `b5770eb` no projeto montado. Conferi dependências e chamadas pelo código atual e busca textual; não alego cobertura semântica do índice.

## Standards

Não encontrei violação confirmada das regras de privacidade e persistência em `AGENTS.md`: o relatório do Doctor usa campos allowlisted, não executa hooks e deixa acessibilidade MCP como `unknown`; a verificação local desta revisão confirmou que o caminho pessoal não aparece no JSON. A CI não usa credenciais nem serviços pagos. As fixtures contêm apenas marcadores sintéticos de teste.

## Spec

### P2 — O comparador aceita versões de schema que não suporta

- **Local:** `inonu_harness/baseline.py:279-287` (`_validate_result`); `compare_runs` em `inonu_harness/baseline.py:156-171`.
- **Critério:** R03 requer comparação de execuções compatíveis; R07 exige compatibilidade de schemas e rejeição de entradas inválidas.
- **Evidência:** a validação rejeita `schema_version < 1`, mas não limita o valor a `RESULT_SCHEMA_VERSION == 1`. Assim, `compare_runs` aceita duas execuções desconhecidas com a mesma versão como compatíveis.
- **Reprodução:** `python -c "from inonu_harness.baseline import run_fixture, compare_runs; r=run_fixture('fixtures/baseline/offline-smoke.json', execution_id='review'); r['schema_version']=2; c=compare_runs(r,r); print({'same_unsupported_version_accepted': c['compatible'], 'reason': c.get('reason')})"` imprimiu `{'same_unsupported_version_accepted': True, 'reason': None}`.
- **Impacto:** uma futura versão com semântica alterada pode ser comparada silenciosamente com a implementação atual. Rejeitar versões não suportadas antes da comparação.

### P3 — A proveniência da licença local de CodeGraph é mais forte que a evidência

- **Local:** `inonu_harness/doctor.py:392` e `inonu_harness/integrations.json:54-62`.
- **Critério:** R01/R02 pedem estado/procedência verificáveis e desconhecidos explícitos.
- **Evidência:** o Doctor declara `MIT` com fonte `verified_package_metadata` para `codegraph`, e o manifesto chama a licença `known`. A implementação usa valores estáticos e não identifica a origem do executável instalado. Já `docs/integrations.md:57-58` afirma que o mapeamento da distribuição local de `codegraph` para o repositório upstream não foi comprovado.
- **Impacto:** consumidores do JSON podem interpretar a licença upstream como comprovada para o binário instalado. Marcar a licença como do repositório upstream, ou deixar a atribuição à distribuição local como `unknown`.

## Limites da revisão

- O smoke de todos os comandos CLI e os 41 testes foram evidenciados pelo ticket de implementação, não repetidos nesta revisão; o coordenador executará a convergência determinística.
- A ação hospedada do GitHub Actions não foi executada. A revisão estática do YAML confirma somente que ela chama a suíte local sem dependências de runtime.

## Resolução pelo coordenador

- **P2 resolvido:** `_validate_result` agora aceita apenas `schema_version == 1`; uma regressão cobre a rejeição de execuções com schema 2. O comparador não declara compatíveis versões que não entende.
- **P3 resolvido:** o Doctor retorna licença da distribuição local do CodeGraph como `null` com proveniência `local_distribution_unverified`, separando MIT como licença do repositório upstream. O manifesto também marca o estado local como desconhecido.
- **Convergência do baseline:** o CLI aceita a forma `baseline run --fixture PATH` além da forma posicional e a fixture `fixtures/baseline/acceptance.json` cobre o comando de convergência revisado.
- **Verificação após correções:** `python -m unittest discover -s tests -v` passou com 43 testes; a invocação `python -m inonu_harness baseline run --fixture fixtures/baseline/acceptance.json --execution-id convergence-probe` e `git diff --check` passaram.
