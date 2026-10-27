# v0.0.20 — Engenharia reversa a partir do código-fonte

Data de observação: 2026-10-26. A pesquisa da v0.0.10 leu vários repositórios só pelo README. Esta etapa leu o **código-fonte** (e os arquivos de dados) dos projetos de referência, com o commit fixado, usando somente `gh api` e `raw.githubusercontent.com` em leitura. Nada foi clonado, instalado ou executado, e nenhum código foi copiado; os mecanismos abaixo são paráfrases, e as implementações do Inonu são próprias. Cinco workers Haiku fizeram a leitura (385 chamadas de ferramenta); a síntese e as decisões são do coordenador.

## O que foi lido

| Tema | Projeto e commit fixado | Licença | Arquivos lidos em código |
| --- | --- | --- | --- |
| Instalador de bundle | `affaan-m/ECC` `25278e7d7b6c` (289 mil estrelas) | MIT | 50 (instalador, estado, hooks, scanners, manifestos) |
| Extensões e integrações | `github/spec-kit` `fdad05f44aa3` | MIT | 40 (registro de integrações, manifestos, resolução de overrides) |
| Grafos de memória | `getzep/graphiti` `5c27edfa8d3e`; `gastownhall/beads` `249d7cde74dc` | Apache-2.0; MIT | 46 |
| Plugins oficiais | `anthropics/claude-code` `a5b0f2e03aba`; `anthropics/claude-plugins-official` `582679441921` | n/d | 91 (manifestos, hooks, agentes, CI) |
| Engenheiros | `humanlayer/12-factor-agents` `d20c728368bf`; `ghuntley/how-to-ralph-wiggum` `88d488a148af`; páginas de Huntley, Husain, Böckeler, Willison e Ronacher | Apache-2.0 / CC BY-SA 4.0 (12-factor) | 20 (os blogs foram lidos por resumo de modelo, não por texto bruto) |

## O que os projetos fazem que o Inonu não faz

**Instalador (ECC, spec-kit).**
- Seleção por dados: perfis, módulos e componentes com resolução de dependências em profundidade e detecção de ciclo (ECC); cada integração declarada como dado, com um renderizador por agente (spec-kit).
- Estado de instalação com cópias exatas das entradas gerenciadas e **digests pós-escrita**, que permitem distinguir "ausente", "alterado pelo usuário" e "não verificável" (ECC); o registro de arquivos *observados* versus *produzidos*, para que um desinstalar nunca apague conteúdo do usuário (spec-kit).
- Texto de consentimento que lista, antes de qualquer escrita, o que um hook pode fazer (ECC).
- Em hooks: três controles de execução (habilitado, perfil, lista de ids desativados), política explícita de falha fechada para barreiras e aberta para telemetria, e fingerprints de metadados dos hooks verificados no CI (ECC).
- Recusa de sobrescrever arquivo alterado, varredura de órfãos após atualização e manutenção de arquivos modificados na remoção (spec-kit).

**Grafos de memória (Graphiti, Beads).**
- Dois eixos de tempo por fato (quando valeu e quando foi registrado) e invalidação de um fato contradito sem apagá-lo (Graphiti); o Inonu tem só o eixo de registro e a invalidação por premissa declarada.
- Fila de prontos: a próxima tarefa é uma consulta determinística sobre um estado derivado, e não um julgamento do agente (Beads); reivindicação atômica com lease e batimento (Beads).
- Injeção de memórias na abertura da sessão com tetos de contagem e de bytes e um aviso de elisão (Beads).

**Plugins oficiais da Anthropic.**
- Um hook só **bloqueia** com saída 2 e a mensagem em stderr; qualquer outro código é erro não bloqueante. Hooks oficiais separam "achado" (2) de "falha de infraestrutura" (1).
- Agentes oficiais declaram uma lista explícita de ferramentas; sem ela o texto do arquivo é o único limite.
- A CI oficial valida manifestos, hooks e agentes em camadas determinísticas.

## Onde o Inonu está à frente

- **Reversão transacional:** o ECC mantém um diário de propriedade mas deixa a árvore pela metade numa falha; o `bundle apply` do Inonu restaura todos os arquivos tocados e reporta se o rollback foi completo.
- **Snapshots completos por revisão e `as-of`:** o Graphiti sobrescreve as arestas e o Beads guarda eventos e commits; o Inonu recupera qualquer estado passado sem repetir eventos.
- **Recomendação separada de autorização:** nenhuma das duas referências tem um portão de aprovação com evidência por critério.
- **Término do loop por código:** o loop de Huntley não tem término interno; o do Inonu para por estado verificado, com limites obrigatórios e detecção de estagnação.

## Lacunas, em ordem de prioridade

| Id | Prioridade | Lacuna | Evidência |
| --- | --- | --- | --- |
| G1 | P1 (defeito) | O hook Stop do `bundle apply --with-stop-hook` roda `check`, que sai com 1 ao falhar; um hook Stop só bloqueia com 2, então ele **nunca bloquearia nada**. Também roda a suíte do próprio Inonu em todo projeto, não o verificador do projeto, não tem timeout declarado nem limite de bloqueios. | Plugins oficiais (semântica de saída), documentação de hooks do Claude Code (v0.0.14) |
| G2 | P2 | O ledger guarda hashes das entradas, mas não digests pós-escrita nem as entradas verbatim; `bundle status` não distingue uma entrada MCP alterada pelo usuário da nossa. | ECC (`install-state`), spec-kit (gate de hash) |
| G3 | P2 | A prévia do hook não diz o que ele faz. | ECC (`hook-consent`) |
| G4 | P2 | Não existe "o que está pronto para decidir": `pending()` lista só por status. | Beads (fila de prontos) |
| G5 | P3 | Não há renderizador do contexto com tetos e aviso de elisão. | Beads (`prime`), ECC |
| G6 | P3 | O agente worker não declara `tools`, então a prosa é o único limite. | Agentes oficiais |
| G7 | P3 | Os passos do `check` são fixos; `docs lint` e a varredura de segredos só entram por testes. | Inspeção interna |
| G8 | P3, **bloqueada** | Tempo de validade e hash de conteúdo na evidência exigem mudança de esquema (migração). | Graphiti, Beads |

## Correções à pesquisa da v0.0.10

A verificação contra fontes primárias achou atribuições erradas ou fracas na [pesquisa anterior](../v0.0.10/research.md), já corrigidas lá: o tamanho de amostra de Husain (30 a 50 por rótulo, não 25 a 50) e a métrica (taxa de verdadeiros positivos e negativos no post companheiro); a revisão em contexto separado é de Böckeler e não de Willison; o sandbox em Willison é uma chamada para trabalho e não uma prescrição; o fator 12 de Horthy foi citado só pelo título; e Böckeler recomenda hooks determinísticos, não um portão de conclusão de tarefa.

## Limites desta pesquisa

- Nada foi executado: os ramos de falha aberta, as janelas de escrita parcial e os comportamentos de rollback citados vêm da leitura do código, sem teste.
- Os conteúdos dos testes dos projetos e vários módulos grandes foram lidos só até o cabeçalho; as listas completas estão nos arquivos fixados.
- Os posts de Huntley, Husain, Böckeler, Willison e Ronacher foram lidos por resumo de um modelo pequeno; o texto bruto só foi localizado para os repositórios. Os números de Husain, as frases de Böckeler e a redação de Huntley precisam de conferência no texto bruto antes de serem citados.
- O comportamento do runtime do Claude Code (expansão da variável de raiz do plugin em corpos de skill, layout do cache) continua vindo da documentação, sem observação em sessão.
- São fontes dos próprios projetos, sem avaliação independente do quanto cada prática contribui.
