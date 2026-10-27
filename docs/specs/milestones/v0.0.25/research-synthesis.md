# v0.0.25 — Engenharia reversa do GSD e de quatro fluxos de trabalho: síntese

Data: 2026-10-26. Pedido do dono: entender como o GSD (Get Shit Done) trabalha com milestones e extrair recursos úteis para o Inonu Harness, junto com gstack, OpenSpec, spec-kit e superpowers.

Método: doze áreas, cada uma lida por um leitor Haiku e conferida por um verificador Haiku independente, só por leitura (`gh api` GET; nada foi clonado nem executado), seguindo o método de evidência do LeanRea (cada afirmação marcada como vista, inferida ou desconhecida, com caminho e linhas). As notas completas estão nos arquivos `research-*.md` desta pasta; cada um termina com as correções do verificador, que prevalecem sobre as notas do leitor. Nenhum humano leu o código: "suportado" quer dizer que um segundo modelo encontrou o arquivo mostrando aquilo. Este texto é a síntese do coordenador sobre essas notas e sobre as correções.

## 1. O que é o GSD

`gsd-build/get-shit-done` (64.216 estrelas, MIT, commit `bdcaab2c`, pacote npm `get-shit-done-cc` 1.50.0-canary.0) é um sistema de meta-prompt, engenharia de contexto e desenvolvimento orientado por especificação. São 67 comandos finos (`commands/gsd/*.md`), cada um carrega um de 88 workflows em Markdown e pode lançar um de 33 agentes. A lógica determinística é pequena: uma CLI/SDK (`gsd-sdk query`, `gsd-tools`, módulos `milestone.cjs`, `phase.cjs`) que calcula estado, numeração, ondas e commits. A maior parte das "regras" é texto que o modelo segue. Detalhes: [instalação](research-gsd-install.md), [comandos](research-gsd-commands.md), [agentes](research-gsd-agents.md), [estado](research-gsd-state.md), [qualidade](research-gsd-quality.md), [fases](research-gsd-phases.md).

A memória do projeto fica em `.planning/` (PROJECT, REQUIREMENTS, ROADMAP, STATE, config.json, MILESTONES, `phases/NN-slug/` com CONTEXT, PLAN, SUMMARY, VERIFICATION e UAT). O STATE.md é lido primeiro depois de um contexto limpo. A pausa grava `HANDOFF.json` e `.continue-here.md`.

## 2. Ciclo de uma fase

Discutir (decisões em CONTEXT.md), pesquisar, planejar (PLAN.md com frontmatter YAML e 2 a 3 tarefas em XML), checar o plano (gsd-plan-checker, em laço com limite), executar (ondas calculadas por ordenação topológica de `depends_on`, planos da mesma onda em paralelo se os arquivos não colidirem, um commit atômico por tarefa, SUMMARY.md), verificar (gsd-verifier parte dos critérios de sucesso e dos must-haves e presume falha; devolve passed, gaps_found ou human_needed), aceitação do usuário (UAT) e fechamento de lacunas. O orquestrador é fino: cada subagente recebe contexto novo. Perfis de modelo (quality, balanced, budget, adaptive, inherit) vêm de um catálogo único.

## 3. Ciclo de um milestone (o ponto principal)

Detalhe completo, com 24 passos, em [research-gsd-milestones.md](research-gsd-milestones.md). Em blocos:

1. **Abrir** (`/gsd:new-milestone`): coleta metas e "seeds", propõe a versão, confirma o entendimento, atualiza PROJECT.md, zera o STATE (`state.milestone-switch`).
2. **Pesquisar e definir** (opcional): quatro pesquisadores em paralelo e um sintetizador; REQUIREMENTS.md com ids `CATEGORIA-NN`; o gsd-roadmapper cria o ROADMAP.md com cobertura de 100% dos requisitos (devolve ROADMAP CREATED ou ROADMAP BLOCKED).
3. **Executar** por fases. Os ids de requisito percorrem o PLAN (frontmatter), o SUMMARY (`requirements-completed`) e a tabela de rastreabilidade do REQUIREMENTS.md.
4. **Auditar** (`/gsd:audit-milestone`): matriz de três fontes (VERIFICATION, SUMMARY, REQUIREMENTS) e o agente gsd-integration-checker; grava `v<versão>-MILESTONE-AUDIT.md` com status passed, gaps_found ou tech_debt.
5. **Fechar lacunas**: `plan-milestone-gaps` cria fases inteiras (maior número + 1) ou `phase --insert` cria decimais N.M; nova auditoria depois.
6. **Auditoria de itens abertos** antes de fechar (depuração, tarefas rápidas, todos, UAT): resolver, reconhecer ou cancelar; os reconhecidos viram registro de adiados.
7. **Arquivar** (`milestone.complete`): `milestones/vX.Y-ROADMAP.md`, `vX.Y-REQUIREMENTS.md`, a auditoria, a entrada no `MILESTONES.md` (mais nova primeiro), STATE atualizado, diretórios de fases opcionalmente movidos; retrospectiva; tag git anotada opcional.
8. **Próximo milestone**: volta ao passo 1.

### Numeração e versionamento no GSD

- O id do milestone é `v<major>.<minor>` livre (ex.: `v1.0`, `v1.1`), escolhido pelo usuário; o modelo propõe a próxima versão. Não existe calculadora da próxima versão nem normalizador do prefixo `v`.
- Fases inteiras **continuam** entre milestones (a menos de `--reset-phase-numbers`); fases inseridas são decimais `N.M`; números 999 e acima são o backlog. Diretórios: `NN-slug` e `NN.M-slug`; planos `NN-MM`; requisitos `CATEGORIA-NN`.
- Comparação com o nosso esquema: o Inonu numera o próprio milestone como versão (`v0.0.N`, regra do dono) e já calcula a próxima (`version --next`); o GSD separa milestone (versão do produto) de fase (contador contínuo). Não há nada no GSD que proteja um `1.0.0`; no Inonu a `1.0.0` é decisão do dono.

## 4. Onde o GSD é frágil (verificado)

Os verificadores independentes apontaram, com arquivos e linhas, falhas que o Inonu deve evitar:

- `new-milestone` apaga os diretórios de fases antes do passo que os arquivaria no modo `--reset-phase-numbers`: o caminho de recuperação (`/gsd:cleanup`) só arquiva o que ainda existe, então fica morto na ordem padrão.
- A auditoria do milestone é prosa de modelo, não código; as regras se contradizem (fase sem VERIFICATION é bloqueio, mas "ausente" vira parcial) e "parcial" não mapeia para nenhum status final.
- As "três fontes independentes" não são independentes: o SUMMARY copia a lista de requisitos do PLAN, e as caixas e células de status viram na execução e no fim da fase, antes de qualquer verificação. O template do próprio GSD define "Complete" como "verificado"; o código marca na execução. **Lição central para o Inonu: o status de um requisito deve ser calculado a partir de evidência verificada, nunca editado.**
- Dois formatos de ROADMAP em conflito; filtros de código esperam títulos `### Phase N:`, e uma seção só com caixas cai em "passa tudo".
- A tag git anotada é criada antes do commit que remove o REQUIREMENTS.md.
- O guarda "só remova fases após a atual" existe só no texto do workflow, não no código; o verificador de órfãos usa um `grep` por prefixo que pode casar `Phase 1` com `Phase 10` (a formatação do número não foi verificada, então isto é inferência); um gap é movido para "adiado" por correspondência textual do nome de fase.
- Muitos guardas de segurança são hooks consultivos, e o lock do planejamento força a quebra de um dono vivo após 10 segundos.

## 5. O que os outros quatro trazem

- **GSD 2** (`gsd-build/gsd-2`, arquivado): estado num banco SQLite (milestones M###, slices S##, tarefas T## como linhas; o Markdown é projeção com hash), funções puras de decisão e tabela ordenada de regras de despacho, detector de travamento por janela deslizante, timeouts em três níveis, trava de sessão com PID, worktree por milestone com squash. É a direção de "mover o que era prompt para código" — a que o Inonu já segue. [Notas](research-gsd-2.md).
- **gstack** (`garrytan/gstack`): sprint Pensar, Planejar, Construir, Revisar, Testar, Entregar, Refletir; esqueletos `.tmpl` que geram SKILL.md; recibos de verificação chaveados pelo hash da árvore git; confiar em comandos de verificação declarados no repositório só a partir da revisão base; contrato de execução sem supervisão com uma linha de resultado e manifesto com hash. Não tem milestone; tem "trens de merge" e uma tabela de adiamentos. [Notas](research-gstack.md).
- **OpenSpec** (`Fission-AI/OpenSpec` 1.15.0): `openspec/specs` (comportamento atual) e `openspec/changes/<nome>/` (proposal, design, tasks, deltas ADDED/MODIFIED/REMOVED/RENAMED); `archive` valida, mescla os deltas em memória, grava e move para `archive/AAAA-MM-DD-nome`. Veredito de três estados em que "não verificado" nunca passa. [Notas](research-openspec.md).
- **spec-kit** (`github/spec-kit`, 1.0.0 em 2026-08-21): constitution, specify, clarify, plan, tasks, analyze, implement, converge; pasta por feature selecionada por `.specify/feature.json` (não pelo nome do branch); extensões, presets e motor de workflow com portões. [Notas](research-spec-kit.md).
- **superpowers** (`obra/superpowers` 7.0.1): brainstorming com portão rígido, plano com cabeçalho (Spec, Global Constraints, Review Focus), subagente novo por tarefa com revisor separado, ledger por plano ignorado pelo git, tarefa só completa com teste saindo 0 e revisões aprovadas, laço de correção com 5 rodadas. Sem milestone e sem ids de requisito. [Notas](research-superpowers.md).

## 6. Recursos a adotar, por apoio entre fontes

Cada linha cita as áreas em que o recurso apareceu e as correções do verificador; esforço S, M ou L; nenhum toca tema cercado, salvo onde indicado. Todos têm forma determinística no Inonu (um comando, um check, uma regra de lint ou de auditoria).

| # | Recurso | Fontes | Esforço | Forma no Inonu |
| --- | --- | --- | --- | --- |
| A | **Cobertura requisito → tarefa**: todo `R<n>` da spec reivindicado por pelo menos uma tarefa, toda tarefa reivindica ao menos um id, sem id órfão ou duplicado | GSD (plan-checker dimensão 1, cobertura do roadmap, comandos, milestones), superpowers, spec-kit (analyze) | S | regra na auditoria SDD que lê `spec.md` e `tasks.md`; roda no `check` |
| B | **Status de requisito derivado de evidência**, e auditoria de milestone com matriz em código (passed, unsatisfied, orphaned; sem evidência é não satisfeito) | GSD (lição central), OpenSpec (três estados), superpowers (exit 0 mais evidência), gstack | M | comando que grava `audit.md` do milestone a partir de registros de verificação; a matriz tem teste unitário |
| C | **Portão de fechamento com adiados registrados**: itens abertos resolvidos ou reconhecidos com motivo; tabela de adiados no checkpoint | GSD (complete-milestone, pré-fechamento), gstack (tabela de adiamentos), spec-kit | S | verificação de fechamento; exit 1 se houver item aberto sem reconhecimento |
| D | **Índice de milestones** mais novo primeiro (`MILESTONES.md`), ponteiro do milestone ativo e guarda de `1.0.0` | GSD (MILESTONES.md), spec-kit (`feature.json`), nosso `version --next` | S | formato de arquivo mais regra de lint (ordem e links) |
| E | **Fechamento de lacunas só por acréscimo**: tarefas novas com id decimal depois da que falhou; nunca renumerar; remoção recusada com evidência | GSD (fases decimais, `insert`), spec-kit (converge) | S | alocador de ids e regra de lint |
| F | **Pausa e retomada** com arquivo de passagem de esquema fixo, consumido uma vez | GSD (HANDOFF.json), gsd-2, superpowers (ledger) | S | esquema JSON mais comando; liga com o hook de parada |
| G | **Identidade do ledger**: o ledger nomeia o milestone e recusa um ledger de outro | superpowers, GSD (estado) | S | linha de identidade no registro do milestone |
| H | **Ondas e guarda de colisão de arquivos** para workers paralelos | GSD (fases, agentes, comandos) | M | planejador de ondas sobre `tasks.md` (ownership por tarefa) |
| I | **Detector de travamento com regras nomeadas** no loop runner | gsd-2, GSD (agentes: parada por contagem de máquina) | S | regras nomeadas sobre o registro por iteração que já existe |
| J | **Recibo de verificação chaveado pelo hash da árvore** | gstack, claw-code (pesquisa anterior), nosso G11 | M | já calculamos o hash da árvore; falta gravar e consultar |
| K | **Esquema de chaves obrigatórias por tipo de artefato SDD** | GSD (estado), OpenSpec (validação) | S | regra na auditoria |
| L | **Lint de papéis nas definições de worker** (lista de ferramentas por papel; sem despacho aninhado) | GSD (agentes), superpowers | S (o lint); a mudança no agente instalado continua cercada | regra de lint; não altera o agente do dono |
| M | **Captura antes de sobrescrever arquivos gerenciados editados** e linha de base pristina com mesclagem de três vias | GSD (instalação) | M | estende o ledger de posse do `bundle`; já temos backup e `modified` |
| N | **Delta de especificação** (baseline versus mudança) | OpenSpec | L | mudança de modelo; adiar |

Fora de alcance por serem cercados ou pagos: migrações de instalador com estado pinado por checksum (L, schema), ledger de despacho com claim único (M), avaliação paga com ensaio pré-registrado (M). Ficam para quando o dono autorizar.

## 7. Proposta de milestones (cada um com brief e consulta ao Jev antes de implementar)

- **v0.0.25 — Cobertura e auditoria de milestone**: A, B e K na auditoria SDD (regras em código, teste de matriz, `audit.md` computado). É a base: sem ela os demais recursos não têm o que fechar.
- **v0.0.26 — Fechamento de milestone**: C, D e G (adiados, índice `MILESTONES.md`, identidade do ledger, guarda de `1.0.0`).
- **v0.0.27 — Lacunas por acréscimo e retomada**: E e F.
- **v0.0.28 — Workers em paralelo**: H e L, com I e J no loop runner.

A ordem é uma proposta; a escolha de cada escopo passa pelo juiz Jev com um brief escrito, como combinado.

## 8. Limites

- Leitura estática de um commit; nada foi executado, então comportamento em tempo de execução não foi observado.
- Os leitores comparam com uma descrição curta do Inonu, não com o código; os verificadores corrigiram várias comparações. Antes de construir qualquer item, o coordenador confere a lacuna no código do Inonu.
- O GSD 1.x está em canary e o gsd-2 está arquivado: os números de comandos e agentes valem para o commit citado.
- Quatro leitores tocaram arquivos grandes por fatias (o instalador do GSD tem cerca de 11.300 linhas); "lido" não significa lido por inteiro, e cada arquivo termina listando o que não foi lido.
