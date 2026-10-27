# Plano M4

1. Fixar o contrato do task JSON, o envelope JSON, erros e limites read-only em `spec.md`.
2. Implementar `decisions packet` reutilizando o adaptador existente; adicionar testes no seam público CLI e documentar uso manual em `docs/sdd-workflow.md`.
3. Fazer revisão independente da validação de entrada, projeção, leitura read-only e compatibilidade de `decisions context`.
4. Executar os testes focal e geral, `git diff --check` e confirmar que as oito etapas SDD continuam presentes; registrar resultados em `checkpoint.md`.

O piloto de agente M3 não faz parte deste plano porque este host não comprovou isolamento text-only. O pacote M4 apenas imprime conteúdo para revisão e uso manual.
