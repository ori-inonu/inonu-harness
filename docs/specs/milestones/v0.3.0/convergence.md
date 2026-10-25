# Convergência M2 — Consumidor CLI de contexto SDD

## Resultado

M2 está concluído no workspace local. O consumidor explícito é `python -m inonu_harness decisions --db <arquivo-existente> context --ids <id> [<id> ...]`. Ele retorna JSON do adaptador existente para IDs selecionados pelo chamador. O comando não injeta prompt nem descobre decisões automaticamente.

O caminho abre o SQLite existente em `mode=ro`, exige schema versão 1 e ativa `PRAGMA query_only`. Testes verificam que os bytes e o histórico permanecem iguais e que o banco/diretório não são criados quando o caminho não existe. Operações CLI de escrita continuam com o modo padrão.

## Comparação controlada

`fixtures/sdd_context/consumer-task.json` representa a tarefa local real de adicionar o consumidor. `tests/test_sdd_context_evaluation.py` constrói uma decisão em banco temporário e usa o CLI real para gerar contexto. Compara o mesmo task packet, `task_id` e `config_id` em duas condições: sem contexto e com a projeção serializada.

Três critérios derivados da saída passam com o contexto e falham sem ele: o contexto escolhido está presente, suas restrições/critério chegam à projeção e a recomendação continua sem autorização. `compare_runs` detecta a mudança dos critérios. Isso mede que o consumidor entrega os campos persistidos; não executa agente e não prova melhoria de qualidade ou produtividade.

A duração do tratamento foi medida em volta da chamada local do CLI. O controle não lê o grafo e por isso sua duração é `null`; a comparação de tempo fica explicitamente incomparável. Runtime/modelo/tokens/custo também são `null`. Listas de chamadas/falhas/bloqueios/recuperações vêm do fixture e não são observações de um agente.

## Revisão e verificações

- Revisão independente: nenhum achado.
- `python -m unittest discover -s tests -p test_cli.py -v`: 4/4 passaram.
- `python -m unittest discover -s tests -p test_sdd_context_evaluation.py -v`: 1/1 passou.
- `python -m unittest discover -s tests -v`: 52/52 passaram.
- Workflow nativo: exit code 0 para os dois recortes, suíte completa e `git diff --check`.
- Varredura sanitizada de 50 arquivos: nenhum espaço final nem padrão comum de credencial detectado.

## Limites e estado local

- O CI hospedado não foi executado.
- A avaliação não mede respostas de agentes, tokens, custo, produtividade nem velocidade.
- A integração é manual e precisa de uma base existente com schema versão 1; não inicializa bancos antigos.
- O comando não varre os textos allowlisted por segredos; revise o JSON antes de anexá-lo a uma tarefa.
- Uma base SQLite temporária criada por uma primeira execução falha continua fora do workspace. A política do shell recusou a remoção, então nenhuma tentativa de contorno foi feita.
- Nenhuma alteração foi commitada ou publicada.
