# Fluxo SDD e JEV

## Caminho de trabalho

Use a cadeia:

1. **Constituição** — confirmar objetivo, escopo e limites.
2. **Pesquisa** — coletar evidências primárias e registrar incertezas.
3. **Especificação** — transformar decisões confirmadas em requisitos observáveis.
4. **Planejamento** — agrupar requisitos em fases com dependências.
5. **Tarefas** — criar tarefas finitas, IDs estáveis e critérios verificáveis.
6. **Implementação** — executar uma tarefa autorizada por vez.
7. **Revisão** — revisar o diff e usar uma revisão independente quando o risco justificar.
8. **Convergência** — fechar somente quando os critérios e verificações tiverem evidência.

Guarde artefatos de marcos em docs/milestones/vX.Y.Z/. Use decisions.md para mapa, evidências, incertezas e decisões; spec.md para requisitos confirmados; plan.md e tasks.md para fases e tarefas; checkpoint.md para estado, evidências, bloqueios e próximo passo.

## Decisões delimitadas

Use JEV quando houver uma escolha real entre opções. Envie uma especificação sanitizada com id, goal, facts, rails e de duas a oito options; cada opção contém id, label e what. Acrescente unknowns quando a evidência necessária estiver ausente.

Chame consensus_plan antes de consensus_run com o mesmo objeto de decisão. Deixe max_calls omitido salvo quando existir um limite positivo solicitado para aquela chamada. A recomendação do JEV é evidência consultiva: ela não concede autorização, não substitui um teste e não determina que uma tarefa terminou.

Uma pergunta do JEV feita junto com outras perguntas é avaliada de forma independente contra o mesmo estado. Se uma resposta depender de outra, coordene chamadas sucessivas e registre essa dependência.

Quando o JEV estiver indisponível, registre sem-jev, faça somente a escolha reversível de menor risco e continue o trabalho independente. Decisões sem evidência suficiente permanecem abertas.

## Roteamento adaptativo

| Situação | Ação |
| --- | --- |
| Regra objetiva e determinística | Resolver em código |
| Escolha delimitada entre opções conhecidas | Consultar JEV |
| Avaliações independentes | Agrupar na mesma chamada |
| Dependências entre decisões | Usar grafo e chamadas sucessivas |
| Evidência insuficiente | Pesquisar antes de decidir |
| Limite de autorização ou ação protegida | Bloquear essa ação |
| Teste contradiz uma decisão | Reabrir a decisão e revisar dependentes |

## Tarefas paralelas

Para trabalho SDD paralelo, mantenha um coordenador e use os agentes nativos do host. Cada agente recebe uma tarefa finita, um conjunto exclusivo de arquivos e critérios de aceite claros. Apenas o coordenador faz chamadas pagas ao JEV, resolve conflitos e verifica a convergência. Espere os agentes terminarem e valide as evidências reais antes de fechar tarefas.

## Limites

Não peça ao operador decisões rotineiras em uma execução autônoma; transforme-as em escolhas delimitadas para JEV quando a evidência existir. Preserve para aprovação humana qualquer ação sobre dinheiro real, carteiras, credenciais, autenticação, limites de risco, migrações de dados/esquema, billing, serviços pagos ou mudanças Git destrutivas. Registre o bloqueio e avance as tarefas independentes.
