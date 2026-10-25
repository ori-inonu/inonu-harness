# Checkpoint M4 — 2026-10-25

**Estado:** concluído. O comando manual `decisions packet` está implementado, a falha encontrada na primeira revisão foi corrigida, a segunda revisão não encontrou problemas e as verificações determinísticas passaram.

## Implementação

- **M4-T01:** especificação, decisões, plano e tarefas registrados neste diretório.
- **M4-T02:** comando manual `decisions packet` combina task JSON validado com decisões explicitamente selecionadas e projeção allowlisted; abre SQLite em modo somente leitura. O comando `decisions context` permanece compatível.
- **Hardening:** a revisão inicial encontrou que `json.loads` aceitava chaves duplicadas. O leitor do task packet agora rejeita chaves duplicadas; os demais consumidores de JSON mantêm o comportamento anterior. Teste de regressão verifica erro sanitizado via `main(argv)`.
- **Documentação:** `docs/sdd-workflow.md` descreve seleção, revisão e anexação manual, sem injeção automática, e preserva as oito etapas do SDD.

## Revisão independente

A primeira revisão encontrou um achado P2 sobre chaves JSON duplicadas. Após a correção, uma segunda revisão independente confirmou a rejeição, a separação do comportamento de `compare_runs`, o tratamento sanitizado e a documentação manual; nenhum achado remanescente.

## Convergência

O grafo Jevis M4 terminou em `complete`; uma primeira tentativa ficou `blocked` porque a documentação ainda não continha literalmente `decisions packet`. Após a correção, o grafo de hardening e a convergência do M4 original terminaram em `complete`.

- `python -m unittest discover -s tests -p test_cli.py -v` — passou, **8 testes**.
- `python -m unittest discover -s tests -v` — passou, **56 testes**.
- `git diff --check` — passou; apenas avisos do Git sobre normalização LF/CRLF.
- `rg -n "decisions packet" docs/sdd-workflow.md` — passou.
- `rg -n "^1\." docs/sdd-workflow.md` — passou; etapa 1 presente.
- `rg -n "^8\." docs/sdd-workflow.md` — passou; etapa 8 presente.

## Bloqueio do piloto M3 neste host

O piloto text-only permanece bloqueado neste host: os controles nativos de agente disponíveis não oferecem uma restrição text-only verificável e o workspace está irrestrito. Isso descreve apenas este host; não estabelece as capacidades de outros hosts. O piloto não foi executado.

## Próximo passo recomendado

Executar o piloto de contexto somente em um host que comprove isolamento text-only. Até essa condição existir, usar o pacote manual com IDs explícitos e continuar reunindo avaliações locais determinísticas, sem afirmar ganhos de qualidade ou produtividade.
