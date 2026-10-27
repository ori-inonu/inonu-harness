# Pesquisa: Inonu Harness, v0.0.10 e além

> Correção de 2026-10-26: veja [a verificação em fonte primária](../v0.0.20/research-reverse-engineering.md). Os números e atribuições de engenheiros desta página foram conferidos e corrigidos onde divergiam.

## 1. Escopo e método

- **Data de observação:** 2026-10-26. Estrelas são snapshots de `gh api` nessa data e mudam diariamente. Não foram usadas contagens de diretórios de terceiros.
- **Fontes:** metadados via `gh api` (estrelas e licença SPDX), leitura de READMEs e páginas de documentação oficial (Anthropic, Claude Code, OpenAI Codex, Cursor, Google ADK, Microsoft, AWS), blogs de autores (Huntley, Husain, Böckeler, Willison, Ronacher, Hashimoto, Ball, Chase, Beck) e auditoria interna read-only do repositório Inonu (versão 0.0.9).
- **Não feito:** nenhum repositório externo foi clonado, instalado ou executado. Nenhum código foi copiado. Conteúdo buscado foi tratado como dado.
- **Limites:**
  - Mecanismos de vários repositórios foram lidos só no README. Quando não confirmados na fonte, estão marcados como "não verificado".
  - A página primária da OpenAI sobre harness engineering retornou HTTP 403. Usei apenas trechos de busca.
  - Não houve avaliação independente de nenhum método de recuperação ou de loop. Benchmarks citados são autorreportados pelos fornecedores.
  - A suíte de testes do Inonu não foi executada nesta pesquisa. A contagem de cerca de 99 testes vem de `grep`.

## 2. Tabela de repositórios

Estrelas observadas em 2026-10-26 via `gh api`, exceto onde indicado.

| Nome | Link | Estrelas | Licença | Categoria | Mecanismo-chave (verificado no README, salvo indicação) |
|---|---|---|---|---|---|
| affaan-m/ECC | https://github.com/affaan-m/ECC | 289.173 | MIT | Bundle de harness / instalador | Instalador guiado (`npx ecc-universal@2.2.3 install --guided`) que inventaria escopos antes de escrever e pede uma confirmação. Reexecutar o comando atualiza ou muda de escopo. Perfis de hooks; scanner AgentShield para hooks, MCP e permissões |
| github/spec-kit | https://github.com/github/spec-kit | 142.951 | MIT | SDD / extensões | CLI `specify` com `--integration`. Quatro pontos de extensão (integrations, extensions, presets, workflow overlays). Hooks antes e depois dos comandos. Resolução de override: core < preset < projeto local |
| bmad-code-org/BMAD-METHOD | https://github.com/bmad-code-org/BMAD-METHOD | 54.570 | NOASSERTION no GitHub; badge diz MIT (não resolvida) | Método SDD | Profundidade de processo proporcional ao tamanho da mudança. Canais estável e preview |
| SuperClaude-Org/SuperClaude_Framework | https://github.com/SuperClaude-Org/SuperClaude_Framework | 23.912 | MIT | Instalador por cópia | `superclaude install` copia comandos para a configuração. `--list` verifica. Plugin system planejado (issue #419), não entregue |
| Yeachan-Heo/oh-my-claudecode | https://github.com/Yeachan-Heo/oh-my-claudecode | 40.279 | MIT | Orquestrador multiagente | Instalação por marketplace (`/plugin marketplace add`). Internos não verificados |
| anomalyco/opencode | https://github.com/anomalyco/opencode | 221.720 | MIT | Runtime de agente (host alvo) | Instalador por script; runtime de hooks/MCP não verificado |
| OpenHands/OpenHands | https://github.com/OpenHands/OpenHands | 91.879 | MIT | Plataforma de agentes | Control plane com backends local, Docker e VM. ACP para outros agentes |
| aaif-goose/goose | https://github.com/aaif-goose/goose | 55.733 | Apache-2.0 | Runtime de agente | Mecânica de extensões não verificada |
| cline/cline | https://github.com/cline/cline | 70.862 | Apache-2.0 | Runtime de agente | Plan/Act com aprovação por edição. Feedback de linter e compilador |
| openai/codex | https://github.com/openai/codex | 130.977 (push 2026-10-23) | Apache-2.0 | Runtime de agente (host alvo) | Instalador com fallback de releases. Configuração não reverificada |
| Aider-AI/aider | https://github.com/Aider-AI/aider | 49.756 | Apache-2.0 | Mapa de repositório | Repo map com orçamento de tokens (ranking não verificado). Último push 2026-05-22 |
| ruvnet/ruflo | https://github.com/ruvnet/ruflo | 79.381 | MIT | Plataforma (alegações) | Não verificado. Tratar com baixa confiança |
| code-yeongyu/oh-my-openagent | https://github.com/code-yeongyu/oh-my-openagent | 70.343 | NOASSERTION | Orquestrador | Gatilho por palavra-chave ("ulw"), autodeclarado |
| hesreallyhim/awesome-claude-code | https://github.com/hesreallyhim/awesome-claude-code | 56.572 | NOASSERTION | Índice | Não é harness |
| snarktank/ralph | https://github.com/snarktank/ralph | 22.068 | MIT | Loop SDD | `ralph.sh` cria instância nova por iteração. `prd.json` com `passes`. Último push 2026-02-02 |
| frankbria/ralph-claude-code | https://github.com/frankbria/ralph-claude-code | 9.715 | MIT | Loop com controles | Saída por dupla condição (indicador e `EXIT_SIGNAL`). Disjuntor com fingerprint de erro. Limite de 100 chamadas/hora. Progresso = commits git. Métricas em JSONL |
| AnandChowdhary/continuous-claude | https://github.com/AnandChowdhary/continuous-claude | 1.387 | MIT | Loop com CI | Uma iteração por branch e PR. Só mescla com checks verdes. Limites de execuções, duração e custo |
| gastownhall/beads | https://github.com/gastownhall/beads | 28.216 | MIT | Grafo de tarefas / memória | `bd ready`, `bd update --claim` atômico, IDs por hash, `bd remember`/`bd prime`. Armazenamento Dolt |
| langchain-ai/langgraph | https://github.com/langchain-ai/langgraph | 43.923 | MIT | Orquestração de estado | Checkpoints por passo, `interrupt()` para humano |
| openai/openai-agents-python | https://github.com/openai/openai-agents-python | 30.293 | MIT | SDK de agentes | `max_turns` como limite (não verificado no código). Guardrails e tracing |
| huggingface/smolagents | https://github.com/huggingface/smolagents | 30.065 | Apache-2.0 | Agente em código | Término por chamada `final_answer` e limite de passos |
| SWE-agent/SWE-agent | https://github.com/SWE-agent/SWE-agent | 20.640 | MIT | Agente de código | Interface computador-agente (mecânica não verificada) |
| Significant-Gravitas/AutoGPT | https://github.com/Significant-Gravitas/AutoGPT | 187.755 | NOASSERTION | Agente autônomo | Não verificado |
| oraios/serena | https://github.com/oraios/serena | 30.727 | Conflito: README GPL-3.0-or-later; API NOASSERTION | Navegação de código | Ferramentas por símbolo sobre LSP, expostas por MCP. Sem grafo persistido |
| vitali87/code-graph-rag | https://github.com/vitali87/code-graph-rag | 5.284 | MIT | Grafo de código | Tree-sitter, SQLite embutido por padrão, MCP. Exige Python 3.12+ |
| getzep/graphiti | https://github.com/getzep/graphiti | 32.229 | Apache-2.0 | Grafo de memória temporal | Arestas com janela de validade. Contradição invalida em vez de apagar. Extração por LLM |
| mem0ai/mem0 | https://github.com/mem0ai/mem0 | 67.837 | Apache-2.0 | Camada de memória | Extração somente ADD. Recuperação híbrida. Benchmarks autorreportados |
| HKUDS/LightRAG | https://github.com/HKUDS/LightRAG | 40.340 | MIT | Graph RAG | Recuperação dual. Servidor em 127.0.0.1 por padrão |
| microsoft/graphrag | https://github.com/microsoft/graphrag | 36.449 | MIT | Graph RAG | Resumos de comunidade. README indica modo de manutenção |
| topoteretes/cognee | https://github.com/topoteretes/cognee | 32.766 | Apache-2.0 | Plataforma de memória | remember/recall/forget. Destilação de sessão |
| letta-ai/letta | https://github.com/letta-ai/letta | 25.260 | Apache-2.0 | Runtime stateful | Memória editada pelo agente. Mecânica não verificada |
| basicmachines-co/basic-memory | https://github.com/basicmachines-co/basic-memory | 4.357 | AGPL-3.0 | Grafo em Markdown + MCP | Fonte da verdade em arquivos Markdown. Licença copyleft |
| HumanLayer/12-factor-agents | https://github.com/humanlayer/12-factor-agents | 26,9 mil (WebFetch) | Código Apache-2.0; conteúdo CC BY-SA 4.0 | Princípios | Fator 8: controle de fluxo em código. Fator 12: só o título ("reducer sem estado") foi lido; o texto do fator não foi decodificado, então não o cite como fonte de um desenho específico |
| humanlayer/advanced-context-engineering-for-coding-agents | https://github.com/humanlayer/advanced-context-engineering-for-coding-agents | 2,8 mil (WebFetch) | não verificada | Fluxo pesquisa-plano-implementação | Conteúdo não lido |

Ferramentas de referência (sem estrelas medidas): Anthropic `plugins/ralph-wiggum` em https://github.com/anthropics/claude-code/tree/main/plugins/ralph-wiggum. Stop hook com `--completion-promise` e `--max-iterations`, padrão ilimitado. Não medido.

## 3. Prescrições oficiais e de engenheiros

### Vendors (documentação primária)

- **Anthropic, harnesses para agentes de longa duração (2025-11-26):** https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents. Agente inicializador na primeira sessão e agente de codificação nas demais. Lista de funcionalidades em JSON com `passes`. Agentes só alteram o campo `passes` e não editam testes. Commit ao final de cada sessão. Teste ponta a ponta obrigatório.
- **Anthropic, engenharia de contexto (2025-09-29):** https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents. Compactação preserva decisões, bugs abertos e lista de arquivos. Anotações externas (NOTES.md). Subagentes devolvem resumos de 1.000 a 2.000 tokens.
- **Anthropic, escrita de ferramentas (2025-09-11):** https://www.anthropic.com/engineering/writing-tools-for-agents. Consolidar operações. `response_format` DETAILED ou CONCISE. Respostas de erro acionáveis. Eval com tarefas reais, verificador, conjunto reservado e revisão de transcrições. Limite de 25.000 tokens por resposta de ferramenta.
- **Anthropic, agentes eficazes (2024-12-19; a página diz que partes estão desatualizadas):** https://www.anthropic.com/research/building-effective-agents. Distinção fluxo de trabalho e agente. Padrões de encadeamento com portões, roteamento, paralelização, orquestrador-trabalhadores e avaliador-otimizador.
- **Claude Code, boas práticas:** https://code.claude.com/docs/en/best-practices. Verificação com critério de passa ou falha (testes, exit code). Escalonamento: instrução, `/goal` avaliado por outro modelo, hook Stop como portão determinístico, subagente revisor. `CLAUDE.md` curto. `/clear` entre tarefas. Modo `dontAsk` para execução sem supervisão.
- **Claude Code, hooks:** https://code.claude.com/docs/en/hooks. Eventos incluem SessionStart, PreToolUse, PostToolUse, Stop, SubagentStop, TaskCompleted e outros. Tipos de handler: command, http, mcp_tool, prompt e agent. Exit 2 bloqueia. `onFailure: block` (v2.1.295+). Guarda de loop `stop_hook_active` no Stop: não verificada no texto completo.
- **Claude Code, subagentes:** https://code.claude.com/docs/en/sub-agents. Frontmatter com `model` (sonnet, opus, haiku, inherit ou ID completo). Precedência: parâmetro por invocação, frontmatter, `CLAUDE_CODE_SUBAGENT_MODEL`, modelo principal. Profundidade padrão 3 (`CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH`). Até 20 concorrentes por padrão. Campos `maxTurns`, `tools`, `disallowedTools`, `permissionMode`, `isolation: worktree`. Esta é a mecânica para fixar workers em Haiku e manter Opus só no orquestrador.
- **Claude Code, skills:** https://code.claude.com/docs/en/skills. Divulgação progressiva. Descrição limitada a 1.536 caracteres. `SKILL.md` com menos de 500 linhas. `disable-model-invocation` para fluxos com efeito colateral.
- **OpenAI Codex, AGENTS.md:** https://learn.chatgpt.com/docs/agent-configuration/agents-md. Precedência de `AGENTS.override.md` e `AGENTS.md`. Concatenação da raiz à folha. Limite `project_doc_max_bytes` de 32 KiB.
- **OpenAI, harness engineering (about 2026-02-11):** https://openai.com/index/harness-engineering/. Página primária retornou 403. Mecanismos não verificados.
- **Cursor, evals de harness (2026-04-30):** https://cursor.com/blog/continually-improving-agent-harness. Classificação de erros de ferramenta por causa. Alertas por desvio de linha de base. Keep Rate como métrica de resultado. Guardrails removidos conforme os modelos melhoram.
- **Google ADK, compactação:** https://adk.dev/context/compaction/. Limiar de tokens, retenção de eventos brutos, intervalo e sobreposição. Resumidor configurável.
- **Microsoft Azure, padrões de orquestração:** https://learn.microsoft.com/azure/architecture/ai-ml/guide/ai-agent-design-patterns. Agente único por padrão. Só a introdução foi lida.
- **AWS Prescriptive Guidance, padrões agênticos:** https://docs.aws.amazon.com/prescriptive-guidance/latest/agentic-ai-patterns/introduction.html. Só resumo de busca.

### Engenheiros e autores

- **Hamel Husain, evals:** https://hamel.dev/blog/posts/evals/. Ler traces até parar de aprender. Rótulos binários. LLM-as-judge validado contra rótulos humanos (o post companheiro fala em 30 a 50 exemplos por rótulo, não "25 a 50", e prefere taxa de verdadeiros positivos e de verdadeiros negativos; o post principal cita precisão e revocação para classes desbalanceadas). Testes em níveis (cada mudança, cadência, A/B).
- **Birgitta Böckeler, engenharia de contexto:** https://martinfowler.com/articles/exploring-gen-ai/context-engineering-coding-agents.html. `CLAUDE.md` pequeno. Regras por caminho. Hooks para ações determinísticas. Revisão em contexto separado (esta prescrição é dela, não de Willison). Configuração de contexto não é testável por unidade, e ela avisa contra tratar o contexto como controle determinístico; ela recomenda hooks, não um portão de conclusão de tarefa.
- **Simon Willison, skills e agentes:** https://simonwillison.net/2025/Oct/16/claude-skills/. Divulgação progressiva. Preferir skills ou CLI a MCP por custo de contexto. Sandbox para execução de código aparece como uma chamada para trabalho futuro, não como prescrição.
- **Armin Ronacher, codificação agêntica (2025-06-12):** https://lucumr.pocoo.org/2025/6/12/agentic-coding/. Ferramentas rápidas, saída mínima, erros claros. Comandos críticos no Makefile. Preferir shell a MCP.
- **Mitchell Hashimoto, jornada de adoção (2026-02-05):** https://mitchellh.com/writing/my-ai-adoption-journey. Cada erro do agente vira uma correção durável: linha no AGENTS.md ou ferramenta de verificação.
- **Thorsten Ball, como construir um agente (2025-04-15):** https://ampcode.com/notes/how-to-build-an-agent. Término quando a resposta não tem chamadas de ferramenta.
- **Dex Horthy, 12-factor agents:** https://github.com/humanlayer/12-factor-agents. Fator 8 (controle de fluxo em código), fator 9 (condensar erros no contexto). O fator 12 (reducer) foi citado só pelo título.
- **Geoffrey Huntley, Ralph:** https://ghuntley.com/ralph/. `while :; do cat PROMPT.md | claude-code; done`. Estado em arquivos e git. Uma tarefa por iteração. Sem término interno (confirmado depois pelo post, lido via resumo, e pelo repositório do autor). 
- **Steve Yegge, Beads / Gas Town:** https://github.com/steveyegge/beads (redireciona para gastownhall/beads). Gas Town descrito por fontes secundárias como não revisado.
- **Harrison Chase, engenharia de contexto:** https://www.langchain.com/blog/the-rise-of-context-engineering. Falhas atribuídas a contexto ausente. Controle de baixo nível.
- **Kent Beck, augmented coding:** https://newsletter.kentbeck.com/p/augmented-coding-negative-feedback. Conteúdo pago; só trechos.
- **Boris Cherny, dicas do Claude Code:** via https://simonwillison.net/tags/agentic-engineering/. Dê ao agente uma forma de verificar o trabalho. Uma regra no CLAUDE.md por erro. Worktrees paralelos. Fonte primária não lida.
- **Andrej Karpathy, engenharia de contexto:** comentário secundário, não verificado na fonte primária.

## 4. Padrões transversais

1. **Verificação determinística antes de dar a tarefa por pronta.** Anthropic, Cursor e Husain convergem; Böckeler recomenda hooks determinísticos, não um portão de conclusão. Um portão com exit code vale mais que uma afirmação do modelo. O caso mais forte é o CI externo do continuous-claude. Snarktank e Anthropic ainda deixam o modelo marcar `passes`, o que é autorrelato.
2. **Estado externo ao modelo.** Arquivos de progresso, git, listas de funcionalidades em JSON e NOTES. Cada iteração começa com contexto limpo. Ralph, Anthropic e Beads seguem isso.
3. **Controle de fluxo em código.** Término por estado (passes, `bd ready`, `final_answer`) e não por texto livre. Ball, 12-factor e Chase concordam. Os limites (iterações, execuções, duração, custo, chamadas por hora) são obrigatórios nos bons exemplos. O padrão ilimitado do plugin Anthropic é a exceção.
4. **Saída de loop com duas condições.** frankbria exige indicador e sinal explícito. Stop hook de Anthropic usa uma frase exata. Nenhum dos dois distingue SUCESSO de BLOQUEADO. Uma decisão terminal estruturada resolve isso.
5. **Detecção de estagnação.** Fingerprint de erro repetido e contador de progresso por commit (frankbria). Progresso medido por fato e não por texto do modelo.
6. **Memória com validade, não apagamento.** Graphiti invalida arestas e mantém histórico. Mem0 faz só ADD e resolve na leitura. Beads usa `bd remember` com injeção no início da sessão. Para o Inonu, validade explícita e supersessão são compatíveis com a Decision Graph.
7. **Contexto limitado por orçamento.** Compactação com limiar, retenção bruta e sobreposição (ADK). Resumos de subagente de 1 a 2 mil tokens. Teto de 25 mil tokens por saída de ferramenta. Limite de 32 KiB no AGENTS.md (Codex). Descrição de skill até 1.536 caracteres (Claude).
8. **Instalação com pré-verificação e confirmação única.** ECC inventaria todos os escopos e pede uma confirmação. Reexecutar atualiza (idempotente por repetição). SuperClaude tem `--list` para verificar. Inonu já tem preview e recusa de arquivos não gerenciados. Falta desinstalação e atualização.
9. **Hooks para garantias, skills para conhecimento.** Böckeler e Anthropic. Hooks são determinísticos e skills são sob demanda. Regras de caminho carregam só quando o arquivo é aberto.
10. **Subagentes por modelo.** A documentação oficial permite fixar `model: haiku` por subagente e manter o modelo principal como orquestrador. Esse é o mecanismo para a instrução do usuário sobre workflows dinâmicos.
11. **Simplicidade primeiro.** Agente único por padrão. Multiagente só com isolamento ou especialização que se justifique (Anthropic, Azure).
12. **Revisão em contexto separado.** Böckeler e Anthropic propõem um revisor sem o raciocínio do autor (a atribuição a Willison estava errada).
13. **Observabilidade do próprio harness.** Cursor classifica erros e alerta por desvio. Ralph JSONL e frankbria registram métricas por iteração.

## 5. Matriz de lacunas do Inonu

Estado atual baseado na auditoria interna (versão 0.0.9). Prioridades: P1 bloqueia o objetivo de instalação única; P2 melhora segurança ou verificação; P3 é desejável.

| Capability | Estado atual no Inonu | Melhor referência | Lacuna | Prioridade | Risco / fence |
|---|---|---|---|---|---|
| Instalação única do conjunto | Instala só `SKILL.md` em `~/.agents/skills` e `~/.claude/skills`. Sem hooks, MCP, comandos, agentes ou settings | ECC (`install --guided`), SuperClaude (`install --list`) | Um manifesto que descreve todos os artefatos, com prévia e aplicação | P1 | Escrita em `~/.claude/settings.json` e registro de MCP são configurações globais de host: exigem autorização específica do dono |
| Desinstalação e atualização | Só reaplicar. Sem remoção | ECC (reexecução atualiza), SuperClaude | Remover apenas o que tem marca de propriedade e hash conhecido | P1 | Remoção de arquivos do usuário: confirmação explícita. Hash de posse é marcador local, não garantia |
| Registro de hooks | Nenhum | Claude Code hooks (PreToolUse, Stop, `onFailure: block`) | Gerar snippet de hook que chama o `check` do Inonu, somente prévia | P2 | Hooks executam comandos a cada evento: global, requer autorização. Hook que bloqueia pode travar sessões |
| Registro de MCP | Só descoberta via `doctor`. `integrations.json` é intenção | SuperClaude `mcp --servers` | Prévia do comando de registro, sem gravar | P2 | Configuração de MCP pode conter credenciais: fence. Não gravar tokens |
| Loop runner | Nenhum. Só comandos isolados | Ralph (fresh context), frankbria (duplo sinal, disjuntor), continuous-claude (CI como saída) | Loop com término por estado, máximo de iterações e registro JSONL | P3 | Loop com agente real envolve custo e execução: serviço pago e ações automáticas exigem autorização. Começar sem loop |
| Gate de verificação | `sdd audit` é somente leitura e não executa checks. Testes via unittest manual | Anthropic (verificação com exit code), continuous-claude | Comando `check` único que executa unittest e compilação, com exit code | P1 | Baixo risco. Stdlib |
| Memória (decisões) | Decisões com estados, histórico e supersessão em cascata. Sem busca e sem notas gerais | Graphiti (validade), Beads (`remember`/`prime`), mem0 (ADD) | Validade por janela e busca por tag | P2 | Mudança de esquema SQLite é migração: fence. Exige autorização |
| Pacote de conteúdo (skill, comandos, agentes) | Uma skill com 22 linhas | ECC (bundles), spec-kit (presets) | Manifesto declarativo de presets, sem código novo | P2 | Baixo |
| Roteamento de modelo por papel | Nenhum | Subagentes (`model` no frontmatter, `CLAUDE_CODE_SUBAGENT_MODEL`) | Gerar definições de subagente worker com `model: haiku` e verificar essa regra por `check` | P1 | Baixo; não toca configuração global se só gerar arquivo de projeto |
| Compactação e pacote de contexto | `packet` com projeção por lista explícita de IDs | Anthropic (compactação), ADK (limiares), Cursor | Limite de tamanho e regras para o que a compactação preserva | P3 | Baixo |
| Redação de segredos em pacotes | Só a responsabilidade do chamador (documentada) | Práticas de Anthropic e Ronacher (saídas mínimas) | Varredura de padrões de segredo nos campos permitidos | P2 | Credenciais: o próprio scanner deve ser testado com fixtures sintéticas |
| Avaliação de agentes | `baseline` offline sem agente real. Sem limiar de regressão | Husain (rótulos binários e juiz validado), Anthropic (tarefas com verificador) | Fixture de execução com resultado humano e comparação com limiar | P2 | Não executar agentes externos sem autorização |
| Telemetria de ferramentas | Nenhuma | Cursor (classificação de erros) | Registro JSONL local de resultados de check | P3 | Privacidade: sem dados pessoais |
| Empacotamento | `pyproject` sem `[project.scripts]` e sem licença | Padrão de pacote Python | Entrada de console `inonu` (stdlib) | P1 | Declarar licença é decisão do dono |
| Despacho de workflows | Nenhum | Subagentes com limites de profundidade e concorrência | Política escrita de quem orquestra e quem executa | P1 | Limites de profundidade e concorrência são parâmetros de execução: sem custo direto, mas exigem conferência |

## 6. Roadmap proposto por versões

Restrições: stdlib Python 3.11+; prévia por padrão; idempotente; reversível; sem código copiado; sem dependências de runtime novas; nada grava em configuração global sem autorização específica.

### v0.0.10: gate e manifesto somente leitura (fatia pequena)

Objetivo: dar ao usuário um comando único que verifica tudo e planeja a instalação, sem escrever fora do repositório.

1. **`python -m inonu_harness check`** executa `unittest discover` e `py_compile` sobre os módulos. Sai com 0 somente se ambos passarem. Teste: um arquivo com erro de sintaxe em fixture faz o comando sair com código diferente de 0.
2. **`python -m inonu_harness bundle plan --host {codex,claude,both} [--home DIR]`** imprime JSON com os artefatos previstos (skill, snippet de hook, comando de registro MCP) e não grava nada. Teste: um hash da árvore de `--home` antes e depois do comando é igual.
3. **O plano marca o registro de hook e de MCP como "somente texto, não aplicado"** e marca `accessibility` como `unknown`. Teste: a saída contém `"applied": false` para cada item de configuração global.
4. **Gerador de definições de subagente worker** em `bundle plan`, com `model: haiku` no frontmatter. Teste: `check` falha se um worker gerado tiver `model` diferente de `haiku` ou se o orquestrador for `opus` fora do arquivo de orquestração.
5. **Entrada de console em `pyproject.toml`** (`[project.scripts] inonu = "inonu_harness.cli:main"`), sem dependências. Teste: `python -m build` local não é exigido; teste verifica que o módulo expõe `main` e que a chamada retorna código de saída 0 para `--help`.

Fora do escopo da v0.0.10: escrita em qualquer configuração de host, registro de MCP, hooks ativos, loop runner, mudança de esquema SQLite, licença.

### v0.0.11: aplicação controlada e desinstalação

1. `bundle apply` grava somente artefatos com marca de posse e hash conhecido. Recusa se houver arquivo não gerenciado (já é o padrão do instalador atual).
2. `bundle remove` remove só artefatos com marca e hash íntegros. Exige confirmação explícita.
3. `bundle status` compara o estado gravado com o disco e reporta `drift`.
4. Testes com `--home` isolado, sem tocar no home real.

Fence: `apply` em `~/.claude/settings.json` e no registro de MCP exige autorização específica do dono antes de implementar.

### v0.0.12: memória com validade e busca

1. Campos `valid_from` e `valid_to` na Decision Graph, com supersessão. Migração de esquema exige autorização.
2. `decisions search --tag T` com índice simples (sem dependência nova; SQLite FTS5 se disponível, com teste de fallback).
3. Teste: uma decisão supersedida não aparece em `context` sem a flag de histórico.

### v0.0.13: avaliação com limiar

1. Fixture de execução com resultado rotulado por humano (binário).
2. `baseline compare --max-regression X` sai com 1 quando a métrica piora além do limiar.
3. Relatório de precisão e revocação para qualquer juiz automático.

### v0.0.14: loop com término por estado (somente depois de v0.13)

1. Lista de tarefas com `passes` controlada pelo verificador, não pelo agente.
2. Limites obrigatórios: iterações, duração e chamadas.
3. Registro JSONL por iteração.
4. Fence: qualquer execução com agente real e custo exige autorização.

## 7. Hipóteses e incógnitas

**Hipóteses (inferências, não verificadas):**
- H1. Um manifesto com prévia e aplicação separadas atende ao objetivo de instalação única sem nova dependência.
- H2. A regra de roteamento Haiku para workers e Opus para orquestrador pode ser verificada por `check` lendo o frontmatter gerado. Não foi testado com o host.
- H3. Validade explícita na Decision Graph resolve a consulta "o que decidimos antes" melhor que busca por texto. Não medido.
- H4. Um `check` com exit code como única porta de conclusão reduz falsas conclusões. Não medido.

**Incógnitas:**
- Esquema real de hooks (tipos de evento completos) e a guarda `stop_hook_active` no texto completo da documentação de hooks. Não verificado.
- Como ECC, oh-my-claudecode e SuperClaude desinstalam. Não confirmado em fonte primária.
- Licença do BMAD-METHOD (NOASSERTION) e do Serena (conflito entre README e API). Verificar arquivo LICENSE antes de qualquer reuso de ideia com código; ideias não exigem licença, mas código exige.
- Status do plugin de SuperClaude (issue #419) após a data de observação.
- Se o Haiku 5.5 atende ao papel de worker em todas as tarefas do fluxo SDD. Não avaliado nesta pesquisa.
- Se o repositório Inonu deve declarar licença. Decisão do dono, fora do alcance da pesquisa.
- Número real de testes e cobertura da suíte atual. Não executado.
- Se `basic-memory` (AGPL) e `serena` (GPL) são compatíveis com a distribuição pretendida. Não avaliado.
