# Decisões M2

## M2-D01 — Consumidor explícito

- **Decisão local:** implementar um subcomando CLI que imprime JSON para IDs escolhidos pelo chamador. A invocação manual é o opt-in; não existe ativação por configuração nem injeção no runtime.
- **Recomendação Jev:** `cli_json`, consenso consultivo no `inonu-m2-consumer-surface`; hash `6fa5b4eeb0869cae838153b597df13f8e6d07d030cf8228dc85b54f27498f0d2`; 9 chamadas reportadas pelo medidor. O receipt não é autorização.
- **Justificativa:** usa a superfície de CLI já existente e permite testar a projeção por um consumidor visível sem criar outra abstração.

## M2-D02 — Abertura SQLite read-only

- **Decisão local:** o comando de contexto usa a mesma implementação SQLite com uma opção read-only, validando que o banco existente já tem schema conhecido. Não cria banco nem executa DDL para esse caminho.
- **Justificativa:** o construtor atual inicializa schema; reutilizá-lo sem adaptação permitiria que um comando de leitura criasse ou alterasse um arquivo.
- **Limite:** comandos de escrita existentes continuam usando o construtor padrão e não mudam.

## M2-D03 — Escopo da comparação

- **Decisão local:** comparar o mesmo task packet com e sem a projeção por critérios de entrega de contexto, usando a baseline existente.
- **Justificativa:** é reproduzível e sem chamadas pagas; distingue a entrega de campos do efeito em respostas de agentes, que M2 não mede.
