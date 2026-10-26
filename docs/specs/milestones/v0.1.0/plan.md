# Plano M0

1. **Ambiente e fixtures** — confirmar contratos locais e conservar somente observações sanitizadas.
2. **F01 / P0** — doctor e manifesto declarativo, sem efeitos de escrita/configuração.
3. **F02 / P0** — baseline de fixtures locais e comparação de registros.
4. **F03 / P1** — serviço Decision Graph e armazenamento SQLite local.
5. **F04 / P1** — adaptador JEV por transporte injetável, mock e gate SDD desativado por padrão.
6. **F05** — CLI, rotina local, CI e atualização dos guias, sem mudar as oito etapas.
7. **F06** — revisão independente read-only; corrigir achados no ownership do coordenador.
8. **F07** — testes determinísticos e smoke local; registrar evidência de cada requisito.

O runtime de agente continua Codex. O workflow de desenvolvimento usa o Jevis nativo com workers deste chat; somente o coordenador faz chamadas Jev e controla convergência.

## Critério final

Concluir somente quando `spec.md` R01–R07 tiverem evidências, a suíte e o comando de baseline local passarem, o caminho SDD padrão permanecer inalterado, revisão independente não deixar achados abertos e o estado do Git não contiver dados locais/segredos. Não realizar commit ou publicação nesta missão.
