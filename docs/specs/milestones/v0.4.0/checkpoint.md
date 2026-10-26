# Checkpoint M3

- **Estado:** M3 concluído como protocolo documental; M3-T01, revisão independente M3-T02 e convergência passaram.
- **Objetivo:** definir um protocolo exploratório para avaliar respostas de planejamento SDD com e sem a projeção local M2, sem executar o estudo.
- **Contexto revisado:** `m2-cli-consumer`, revisão 2, apenas fixture local; `pending`, recomendação `cli-json` de `local-fixture`/`m2-fixture-1`, `authorized_alternative_id: null`.
- **Decisor:** duas chamadas do coordenador a `consensus_plan` para o desenho foram recusadas; sem resposta Jev. A escolha documental reversível e sua justificativa estão em `decisions.md`.
- **Protocolo:** task packet idêntico, agentes novos, mesmo modelo/esforço, só a projeção varia; rubric de cinco critérios, avaliador parcialmente cego, isolamento text-only como pré-condição, pares inválidos excluídos e métricas sem fonte como `null`.
- **Revisão:** confirmou que controle e tratamento recebem o pacote comum idêntico e só o tratamento recebe a projeção. Uma instrução extra no controle foi removida antes da revisão final.
- **Convergência:** `git diff --check`, `rg -n '^1\.' docs/sdd-workflow.md` e `rg -n '^8\.' docs/sdd-workflow.md` passaram; as oito etapas continuam listadas.
- **Próximo passo possível:** executar o piloto somente em host que comprove sessões text-only sem ferramentas, rede, arquivos ou escrita. Essa capacidade não foi verificada neste marco; sem ela, o piloto fica bloqueado.
- **Fora deste marco:** executar o piloto, alegar efeito geral, alterar runtime/hooks/fluxo SDD, ler banco pessoal, usar serviço pago/externo, commitar ou publicar.
