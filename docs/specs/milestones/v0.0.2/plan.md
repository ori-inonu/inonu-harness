# Plano M1

1. Implementar a projeção tipada e o teste de comportamento com SQLite temporário e fixture local.
2. Atualizar os guias SDD e benchmark para documentar o uso explícito e os limites da medição.
3. Fazer revisão independente do diff e dos critérios M1.
4. Executar a suíte completa, a avaliação fixture-backed, `git diff --check` e uma varredura sanitizada dos arquivos novos.

Cada fase mantém o runtime e o fluxo SDD existentes. Nenhuma chamada JEV faz parte da implementação ou dos testes.
