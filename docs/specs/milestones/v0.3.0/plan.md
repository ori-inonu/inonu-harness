# Plano M2

1. Adicionar o subcomando read-only `decisions context` e cobrir schema, IDs, histórico e ausência de criação/mutação do banco.
2. Adicionar a fixture da tarefa SDD local e a comparação determinística, no mesmo task/config, entre pacote sem contexto e pacote com a saída real do CLI.
3. Atualizar os guias de uso e baseline para explicar o opt-in manual e os limites do que foi medido.
4. Revisar o diff de forma independente e executar testes focados, suíte completa, comparação fixture-backed e verificações de diff.

Não alterar runtime, hooks, o fluxo de oito etapas, schema de decisões ou dados persistidos do usuário. Manter tudo local sem commit/push.
