# Checkpoint M2

- **Estado:** concluído localmente; implementação, comparação fixture-backed, revisão independente e convergência finalizadas.
- **Objetivo:** expor decisões escolhidas ao chamador SDD por CLI manual e read-only, sem consumo automático.
- **Interface:** `python -m inonu_harness decisions --db <arquivo-existente> context --ids <id> [<id> ...]`.
- **Garantia de leitura:** o comando exige SQLite existente com schema versão 1, abre em `mode=ro` e ativa `query_only`; não cria diretório/arquivo nem executa DDL. A projeção só consulta IDs explícitos.
- **Comparação:** mesmo task packet, `task_id` e `config_id`; 3 critérios de contexto passam no tratamento e falham no controle. A duração do tratamento cobre a chamada CLI; o controle e a comparação temporal são `null`/incomparáveis.
- **Métricas ausentes:** runtime/modelo/tokens/custo ficam `null`; listas de ferramenta/falha/bloqueio/recuperação são do fixture e não representam execução de agente.
- **Revisão:** independente, sem achados.
- **Verificações:** CLI 4/4; avaliação de contexto 1/1; suíte completa 52/52; convergência nativa exit code 0; `git diff --check` passou; varredura sanitizada de 50 arquivos encontrou 0 arquivos com espaços finais ou padrões comuns de credenciais.
- **Limites:** CI hospedado e efeito sobre qualidade/produtividade do agente não foram avaliados. O comando exige schema versão 1; não inicializa bancos antigos. Texto nos campos allowlisted continua sob responsabilidade do chamador.
- **Resíduo de teste:** uma base SQLite temporária criada por uma primeira execução falha permanece fora do repositório. A política do shell recusou sua remoção e não foi contornada; nenhum banco pessoal foi aberto.
- **Branch:** `codex/m0-inonu-harness`; nenhuma alteração foi commitada ou publicada.
- **Próximo passo recomendado:** usar o comando manualmente em uma tarefa real selecionando IDs e revisar o JSON antes de anexá-lo. Se for importante medir efeito em resultados de agente, planejar depois um experimento separado com rubric e medições observáveis.
- **Fences preservados:** sem chamada JEV pelo produto/testes, sem mudança às oito etapas, hooks, runtime, schema, instalação, commit ou push.
