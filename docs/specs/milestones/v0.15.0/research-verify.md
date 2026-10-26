# v0.15.0 — Verificação do formato de plugin do Claude Code

Data de observação: 2026-10-26. Três workers Haiku leram as páginas oficiais de plugins do Claude Code (`code.claude.com/docs/en/plugins`, manifest reference, marketplaces, hooks, MCP, subagentes, skills) e os repositórios oficiais da Anthropic. O texto chegou por WebFetch (texto extraído por modelo, não HTML bruto); revise as frases antes de reutilizá-las. Nenhuma CLI `claude` está disponível nesta máquina, então `claude plugin validate` **não** foi executado.

## Verificado em fonte oficial

- **Manifesto:** `.claude-plugin/plugin.json` é opcional; só o campo `name` é obrigatório (kebab-case, sem espaços, `@`, `:` nem separadores de caminho). Campos comuns: `version`, `description`, `author` (objeto com `name`), `homepage` (precisa ser uma URL válida ou o plugin não carrega), `repository`, `license` (SPDX), `keywords`. Chaves desconhecidas no topo são descartadas; dentro de objetos estritos são erro.
- **Nomes reservados:** prefixos `claude-`, `anthropic-`, `anthropics-`, `cc-plugin-` e os nomes `claude`, `anthropic`, `claude-code` etc. O nome `inonu-harness` não dispara nenhum. Há nomes de marketplace reservados e as palavras `npm`, `pip`, `uv`, `cargo`, `github` e `gh`.
- **Layout:** só o manifesto fica dentro de `.claude-plugin/`; `skills/`, `agents/`, `commands/`, `hooks/hooks.json` e `.mcp.json` ficam na raiz do plugin. Pastas `skills/<nome>/SKILL.md` e arquivos `agents/*.md` são descobertos sozinhos; nenhuma chave de componente é obrigatória.
- **Marketplace:** `.claude-plugin/marketplace.json` exige `name`, `owner` (objeto com `name`) e `plugins[]`; cada entrada exige `name` e `source`. Um repositório pode ser marketplace e plugin ao mesmo tempo com `source: "./"`. O caminho relativo deve começar com `./`, não conter `..` e usar barras normais. O nome da entrada deve coincidir com o do `plugin.json`.
- **Instalação:** `/plugin marketplace add dono/repo` e `/plugin install nome@marketplace` (ou `claude plugin marketplace add` e `claude plugin install` no shell). Se `version` está definida, o usuário fica na cópia em cache até a string mudar; sem `version`, acompanha os commits.
- **Cópia em cache:** plugins vindos de marketplace git são **copiados** para um cache. Por isso o plugin precisa carregar os próprios arquivos (o pacote Python e os scripts) e a raiz do plugin é a raiz do repositório.
- **Variáveis:** `${CLAUDE_PLUGIN_ROOT}` (caminho absoluto do plugin instalado) é expandida em comandos e argumentos de hooks, em MCP stdio e **no corpo Markdown de skills, comandos e agentes**. `${CLAUDE_SKILL_DIR}` aponta para a pasta da skill, não para a raiz do plugin.
- **Agentes de plugin:** ignoram `hooks`, `mcpServers`, `permissionMode` e `initialPrompt` por segurança. Aceitam `name`, `description`, `model`, `effort`, `maxTurns`, `tools`, `disallowedTools`, `skills`, `memory`, `background`, `isolation`, `color` entre outros. O `model: haiku` do agente worker é aceito.
- **Python em plugin:** a documentação não cobre dependências Python (o plugin deve cuidar disso) e não diz qual launcher usar no Windows (`python`, `py` ou `python3`). O plugin oficial `hookify` usa `python3 ${CLAUDE_PLUGIN_ROOT}/hooks/<nome>.py`.

## Não encontrado ou não verificado

- A documentação não descreve um prompt de aprovação antes de os servidores MCP de um plugin de marketplace habilitado iniciarem, nem um prompt separado por hook de plugin de escopo de usuário. Por isso o plugin desta versão **não** inclui `.mcp.json` nem hooks.
- Não foi possível rodar `claude plugin validate`; a validade real do pacote só se confirma com a CLI (`claude plugin validate .`).
- Se a versão instalada do Claude Code do usuário aceita todos os campos (alguns exigem versões recentes).
