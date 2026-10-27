# Decisões M1

## M1-D01 — Interface de contexto

- **Decisão recomendada:** adaptador de contexto somente de leitura, opt-in, com IDs explícitos.
- **Evidência:** `SddDecisionGate` atual só registra recomendações JEV; `DecisionGraph` já expõe `get`, `list`, `history` e estados atuais. O adaptador de leitura mantém essa responsabilidade separada.
- **JEV:** `inonu-m1-context-seam`; consenso `readonly-context`; hash `5ff60f73060ecdf3b213300daf46a7808ea2f28dac112ae73b2e696566676a3d`; 8 chamadas reportadas pelo medidor. A recomendação é consultiva.

## M1-D02 — Campos expostos

- **Decisão local:** usar uma projeção allowlistada dos campos atuais necessários ao contexto; omitir histórico, timestamps, identidade do ator e proveniência livre. O chamador escolhe os IDs e os textos projetados não são varridos por um detector de segredos.
- **Evidência:** o registro completo contém campos de auditoria que o consumidor de contexto não precisa. Reduzir a saída é reversível e evita expor esses campos sem benefício confirmado.
- **JEV:** `inonu-m1-context-projection`; sem consenso após 12 chamadas. Portanto, esta escolha vem do coordenador sob a regra de menor risco reversível, não de uma autoridade do JEV.

## Limite ainda desconhecido

Não há API local confirmada que consuma o contexto no runtime Codex. M1 entrega apenas o adaptador chamado explicitamente por um consumidor futuro; não declara que o agente já recebe os dados automaticamente.
