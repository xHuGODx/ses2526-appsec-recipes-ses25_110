# Justificacao Do Setup DAST

## Objetivo

Este setup foi desenhado para um `AppSec repo` separado do software repo. O foco principal do DAST continua a ser o backend porque o risco dominante desta app esta nos endpoints REST e no modelo de dados exposto sem autenticacao, mas a superficie do frontend tambem entra agora na assessment. O codigo da app e obtido apenas de forma temporaria durante a execucao dos scans.

## Porque este combo

### 1. OWASP ZAP

Foi escolhido como scanner base de black-box para a API e para a SPA.

O que cobre melhor:
- passive + active scanning orientado a API
- deteccao de headers inseguros, informacao exposta, erros de servidor e classes web comuns
- relatorios exportaveis em `html`, `md`, `xml` e `json`

Porque faz sentido aqui:
- a app expõe OpenAPI via Springdoc, o que encaixa diretamente no `zap-api-scan.py`
- a SPA publicada em `5173` pode ser percorrida com spider + Ajax spider
- e facil de automatizar em Docker
- e um standard academico / industrial para demonstrar DAST de forma clara

### 2. Schemathesis

Foi escolhido como scanner API-first baseado no OpenAPI.

O que cobre melhor:
- property-based testing
- fuzzing positivo e negativo a partir do contrato da API
- deteccao de `500`, respostas fora do schema, validacoes mal fechadas e problemas de estado
- output rico em `junit`, `har`, `ndjson` e `vcr`

Porque faz sentido aqui:
- a API tem contrato OpenAPI acessivel
- cobre casos que scanners web classicos nao exercitam tao bem
- ajuda a apanhar inconsistencias entre especificacao, validacao e implementacao

### 3. RESTler

Foi escolhido como scanner stateful / sequence-aware para APIs REST.

O que cobre melhor:
- exploracao de sequencias de requests com dependencias produtor-consumidor
- `smoketest`, `fuzz-lean` e `fuzz` mais profundo
- deteccao de `5xx`, `use-after-free`, `resource hierarchy issues`, `payload bugs` e problemas em fluxos multi-step

Porque faz sentido aqui:
- esta app tem operacoes encadeadas entre pizzerias e pizzas
- scanners puramente request-by-request podem falhar bugs que so aparecem em sequencias validas
- acrescenta profundidade real ao DAST em cima do OpenAPI

## Como se complementam

- `ZAP` cobre bem a perspetiva classica de DAST web e API, incluindo spidering da SPA.
- `Schemathesis` cobre melhor invariantes do contrato e fuzzing semantico da API.
- `RESTler` cobre fluxos stateful e bugs que exigem sequencias de operacoes.

Na pratica:
- se os tres apontarem para a mesma familia de problema, a confianca sobe
- se apenas um encontrar algo, continua a haver valor porque cada um tem um angulo diferente
- o conjunto reduz a dependencia de um unico motor e ajuda a justificar melhor os findings no relatorio

## Porque usar varios scanners antes de passar a um LLM

Um LLM e util para:
- deduplicar findings
- agrupar resultados por endpoint, severidade e familia de vulnerabilidade
- mapear findings para `TM-*`, `AT-*` e `AS-*`
- resumir evidencias e propor mitigacoes

Mas o LLM nao deve substituir a evidencia crua. Por isso o setup guarda outputs estruturados:
- `ZAP`: `json`, `xml`, `html`, `md`
- `Schemathesis`: `junit`, `har`, `ndjson`, `vcr`
- `RESTler`: `Compile`, `Test`, `FuzzLean`, `ResponseBuckets`, `bug_buckets`

Tambem foi incluido um passo de manifest em `dast/results/llm/scan_manifest.json`, pensado para ser o ponto de entrada de uma fase posterior de agregacao com LLM.

## Trade-offs

- O setup privilegia reprodutibilidade com Docker em vez de instalacoes locais.
- A separacao entre `software repo` e `AppSec repo` reduz duplicacao, mas exige checkout temporario cross-repo nos workflows.
- `RESTler` e o scanner mais pesado e mais sensivel a detalhes do OpenAPI.
- `Schemathesis` e `RESTler` sao especialmente fortes para API; a SPA fica coberta sobretudo por `ZAP`, mas continua menos explorada do que ficaria num setup browser-heavy com autenticacao e journeys mais ricas.
- O modo `RESTler fuzz` profundo fica separado do fluxo principal porque e mais agressivo e tem maior risco de perturbar a aplicacao.
