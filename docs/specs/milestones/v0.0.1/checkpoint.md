# Checkpoint M0

- **Estado:** M0 local concluído; F01–F07 e a revisão final da disponibilidade por skill concluídos; achados independentes P2/P3 corrigidos; 43 testes passaram após a correção.
- **Branch:** `codex/m0-inonu-harness` sobre `main` na base `b5770eb`.
- **Destino:** `spec.md` R01–R07.
- **Decisões JEV:** Python + biblioteca padrão, SQLite local e fronteira paralela de arquivos disjuntos; recibos em `decisions.md`.
- **Workflow:** F01–F07 e `R01-FOLLOWUP-IMPLEMENT`/`R01-FOLLOWUP-REVIEW` concluídos; achados P2/P3 corrigidos; a auditoria final acrescentou `session_availability: unknown` por skill, e a revisão adicional não encontrou falhas; verificações determinísticas passaram.
- **Ambiente observado:** Codex CLI 0.164.0, Python 3.14.7, RTK 1.0.1, CodeGraph 3.0.1, Headroom 0.41.0; MCP Jev/CodeGraph/Headroom presentes no catálogo desta sessão.
- **Limites:** nenhuma ferramenta instalada; nenhum valor secreto lido; sem commit/push. O doctor não pode afirmar carregamento real de skills nem acessibilidade MCP só com observação local. CI em runner hospedado não executada; os arquivos permanecem locais e sem commit.
- **Próxima ação:** M1 recomendado: ligar o Decision Graph ao contexto SDD de forma opt-in, depois medir utilidade em fixtures antes de ampliar automação ou conectar transporte JEV real.
