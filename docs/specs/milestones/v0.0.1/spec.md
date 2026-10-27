# Inonu Harness M0 — especificação

## Destino

Entregar um núcleo local, reproduzível e opcional para observar o ambiente, medir fixtures determinísticas e registrar decisões com histórico persistente. Codex e o fluxo SDD de oito etapas continuam sendo o runtime e o caminho padrão.

## Evidências de partida

- O repositório na base `b5770eb` contém documentação, sem código de aplicação, linguagem escolhida, pacote ou CI.
- O fluxo documentado em `docs/sdd-workflow.md` tem oito etapas; JEV é consultivo e não concede autorização.
- Neste host, `codex --version` reportou `codex-cli 0.164.0-alpha.11.1` e `python --version` reportou Python 3.14.7.
- A CLI reportou RTK 1.0.1, CodeGraph 3.0.1 e Headroom 0.41.0. Os MCPs `jev-sdd`, `codegraph` e `headroom` constam na configuração e nas ferramentas desta sessão.
- O JEV MCP aceitou `consensus_plan({spec})` e `consensus_run({spec})` nesta sessão. A resposta expôs recibo consultivo, líder, hash de especificação e medidor; não expõe uma autorização.
- `jev-sdd` não existe como comando autônomo no PATH. O servidor local do Jevis documenta o contrato MCP e usa uma variável de ambiente de credencial, cujo valor não foi lido nem copiado.
- A configuração global do Codex tem hooks. O diagnóstico deve inspecionar somente estrutura e compatibilidade, nunca expor comandos, prompts ou valores.

Estas observações descrevem este host e esta sessão, não todos os ambientes que instalarão o Inonu.

## Decisões registradas

- Implementar os utilitários em Python 3.11+ usando a biblioteca padrão. O recibo `m0-implementation-runtime` recomendou `python-stdlib`; a disponibilidade local foi verificada.
- Usar SQLite local como armazenamento M0. O recibo `m0-storage-choice` recomendou `sqlite`; SQLite oferece transações sem infraestrutura externa.
- Começar com módulos independentes de diagnóstico, baseline e grafo, com ownership de arquivos separado. O recibo `m0-work-scheduling` recomendou `parallel-frontier`.
- Esses recibos são recomendações. A autorização para implementar vem desta missão do usuário.

## Requisitos e aceite

### R01 — Diagnóstico sanitizado

`python -m inonu_harness doctor` produz JSON válido no stdout com plataforma, runtime Codex observável, skills encontradas, configuração global/local, MCPs registrados, ferramentas acessíveis apenas quando houver evidência, JEV, RTK, Headroom, CodeGraph, Ponytail e hooks. Cada skill informa origem, versão disponível, presença no filesystem e disponibilidade na sessão; esta última é `unknown` quando não puder ser verificada por uma interface oficial do host. Cada fato tem origem e estado (`installed`, `configured`, `operational`, `documented`, `not_found` ou `unknown`). O relatório omite segredos, valores de configuração, prompts, comandos de hooks e caminhos locais. Lacunas aparecem explicitamente como `unknown` com motivo.

### R02 — Manifesto declarativo

Um manifesto versionado separa para cada integração sua intenção, estado observado e não observado, problema, contrato de entrada/saída conhecido, capacidades candidatas, sobreposição, dependências, licença, teste de benefício e condição para implementação própria. Valores desconhecidos ficam explícitos.

### R03 — Baseline local

Fixtures determinísticas podem ser executadas sem rede ou chamadas pagas. Cada registro contém ID da execução/tarefa, configuração, runtime/modelo se observáveis, critérios de aceite, duração, tokens/custo quando observáveis, chamadas de ferramentas, falhas, bloqueios, recuperações e versões. Cada métrica leva sua origem; dados indisponíveis são `null`, nunca estimados. Um comando compara execuções compatíveis.

### R04 — Decision Graph persistente

O serviço cria e recupera decisões com ID estável, pergunta, alternativas, restrições, critérios requeridos, evidências com proveniência e dependências. Ele mantém revisões imutáveis, registra recomendação separadamente de autorização, lista pendentes/bloqueadas/invalidadas e consulta dependentes afetados. Mudança marcada como premissa relevante invalida dependentes transitivos de forma atômica.

O grafo rejeita ciclos, não autoriza pela resposta do JEV, não fecha sem cada critério requerido validado por evidência, exige chave de idempotência por mutação e rejeita reutilizar a mesma chave com payload diferente. Não guarda raciocínio interno de modelos.

### R05 — Adaptador JEV

Uma interface tipada valida escolhas delimitadas, limites/opções e proveniência. Um transporte MCP injetável chama `consensus_plan` e depois `consensus_run` com o mesmo spec, omitindo `max_calls`; o adaptador aceita somente uma recomendação que referencia opção existente e nunca altera autorização. Timeout, indisponibilidade, ausência de consenso e resposta inválida são resultados explícitos. Um mock determinístico cobre testes locais sem rede/pagamento.

### R06 — SDD opcional

Um adaptador do grafo fica desativado por padrão. Quando desativado, o caminho atual de SDD não chama nem depende do grafo. Quando ativado, persiste contexto/decisões por interfaces locais, sem alterar a sequência de oito etapas.

### R07 — Verificação

Testes cobrem persistência/reabertura, revisões/histórico, invalidação transitiva, ciclos, idempotência, evidência ausente, falhas do JEV, autorização separada, schemas e entradas inválidas. Uma rotina local e CI executam somente testes locais sem credenciais.

## Seams de teste

- `collect_environment(probe)` e o comando `doctor`: observam dados sanitizados; não podem provar acessibilidade de ferramentas MCP fora do catálogo do host.
- `run_fixture(fixture, clock, versions)` e `compare_runs`: verificam formato, procedência e comparação sem depender de tempos, tokens ou custos inventados.
- `DecisionGraph` sobre `DecisionStore`: verifica contratos de leitura/mutação com SQLite real temporário; reiniciar e reabrir verifica durabilidade.
- `JevAdapter` sobre `McpToolTransport`: um mock controla respostas do limite externo; valida timeout, erro, schema e escolha permitida.
- `SddDecisionGate(enabled)`: compara o caminho desativado com o adaptador ativado sem modificar as oito etapas existentes.

## Fora de escopo

- Alterar o runtime Codex, as skills originais de Matt Pocock, hooks ou MCPs globais.
- Instalar ferramentas, chamar serviços pagos em testes ou mudar credenciais.
- Autoexecução de operações protegidas, execução paralela do produto ou serviço remoto.
- Implementar RTK, Headroom, Ponytail, CodeGraph ou Sequential Thinking.
- Escolher DeepSeek Harness/Pi ou alterar a sequência SDD.
- Commit, push, PR, migração de dados existentes ou relatório local com caminhos privados.

## Lacunas declaradas

- O CLI local não pode provar que uma ferramenta MCP configurada foi carregada e está acessível por todos os clientes Codex; deve marcar esse fato `unknown` salvo quando recebido por interface oficial do host.
- O contrato MCP de entrada do JEV está confirmado; um transporte portátil para invocar ferramentas MCP fora do host não está confirmado. Implementar somente o transporte injetável e mock.
- A licença de Headroom e de qualquer implementação de Sequential Thinking não está confirmada pelo inventário local. Não copiar código.
- A versão da aplicação desktop Codex não é reportada pelo `codex --version`; registrar somente a versão da CLI observada.
