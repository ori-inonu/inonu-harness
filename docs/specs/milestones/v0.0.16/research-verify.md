# v0.0.16 — Fonte primária da OpenAI sobre engenharia de harness

Data de observação: 2026-10-26. A página "Alavancando o Codex em um mundo centrado no agente" (original em inglês: `https://openai.com/index/harness-engineering/`, publicada em 2026-02-11, de Ryan Lopopolo) devolvia HTTP 403 a todas as formas de fetch. Ela foi lida de ponta a ponta pelo navegador embutido do app (versão `pt-BR`), em modo somente leitura. O que segue é paráfrase; o texto integral pertence à OpenAI. Isso fecha a lacuna que o [v0.0.14 research-verify](../v0.0.14/research-verify.md) deixou aberta.

## O que a fonte afirma

- **Experimento:** cinco meses com uma equipe de três a sete engenheiros e nenhuma linha escrita à mão, cerca de um milhão de linhas e cerca de 1.500 PRs. Os autores avisam que o resultado depende da estrutura e das ferramentas daquele repositório e não deve ser tomado como generalizável.
- **Papel humano:** projetar ambiente, especificar intenção e construir ciclos de feedback. Quando o agente falha, a pergunta é "qual capacidade está faltando e como a tornamos legível e verificável para ele", não "tentar com mais afinco".
- **Loop de PR:** o agente revisa o próprio diff, pede revisões a outros agentes, responde ao feedback e itera até os revisores ficarem satisfeitos. Os autores chamam isso de Loop de Ralph Wiggum.
- **Instruções como índice:** um único `AGENTS.md` gigante falhou (consome contexto, vira "tudo é importante", apodrece e não se deixa verificar). O que funcionou foi um `AGENTS.md` curto, de cerca de 100 linhas, que aponta para um diretório `docs/` tratado como sistema de registro (design, planos de execução, especificações, referências, um documento de qualidade por domínio).
- **Verificação mecânica da documentação:** linters e tarefas de CI validam que a base de conhecimento está atualizada, interligada e bem estruturada; um agente recorrente de manutenção abre PRs de correção para documentação obsoleta.
- **Legibilidade para o agente:** o que não está no repositório, versionado, não existe para o agente. Dependências "chatas" e estáveis são mais fáceis de modelar; às vezes compensa reimplementar um subconjunto em vez de depender de uma biblioteca opaca.
- **Arquitetura imposta por código:** camadas fixas com direções de dependência validadas por linters e testes estruturais, escritos com mensagens de erro que **injetam instruções de correção** no contexto do agente. Impõe-se o limite de forma central e dá-se autonomia dentro dele.
- **Throughput e merge:** poucas travas de merge, PRs curtos, testes instáveis tratados com execuções de acompanhamento. Os autores dizem que isso seria irresponsável em ambiente de baixa vazão.
- **Entropia:** o agente replica padrões ruins que já existem. Limpar "lixo de IA" à mão (20% da semana) não escalou; eles passaram a codificar "princípios de ouro" e a rodar tarefas recorrentes que detectam desvio, atualizam notas de qualidade e abrem PRs de refatoração pequenos.
- **Perguntas em aberto da própria fonte:** como a coerência arquitetônica evolui ao longo de anos num sistema todo gerado por agentes.

## Implicações para o Inonu (inferência)

1. Um verificador do **arquivo de instruções** (tamanho, links que resolvem, imports `@arquivo` que existem) e da integridade dos links em `docs/` é uma verificação mecânica que o projeto ainda não tem.
2. Os achados devem trazer **texto de correção** para o agente, não só o código do erro.
3. Regras de arquitetura declaradas (por exemplo, "só biblioteca padrão") devem virar teste estrutural, não só frase no `AGENTS.md`.
4. Um agente de "jardinagem" da documentação e uma nota de qualidade por domínio são ideias da fonte, mas dependem de executar agentes, o que o Inonu não faz; ficam fora desta versão.

## Limites

- É uma fonte do próprio fornecedor, sem avaliação independente; não mede o quanto cada prática contribui.
- Não foi possível cotejar a versão em inglês com a lida em português.
