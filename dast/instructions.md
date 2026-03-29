# Instructions

## O que este setup faz

Este diretório prepara um fluxo DAST para a app atual usando:
- `OWASP ZAP`
- `Schemathesis`
- `RESTler`

O setup cobre:
- backend Spring em `http://localhost:8080`
- frontend SPA em `http://localhost:5173`

O backend exporta OpenAPI em `http://localhost:8080/v3/api-docs`.

## Separacao entre repositorios

Este repo nao versiona o codigo da aplicacao.

O setup espera que o software repo exista:
- num checkout temporario do GitHub Actions, ou
- localmente em `../ses`, por omissao

Podes tambem apontar explicitamente para o repo da app:

```bash
APP_REPO_DIR=/caminho/para/ses
```

O `docker-compose.yml` usado para levantar `mysql`, `backend` e `frontend` vem sempre do software repo.

## Estrutura

O workflow `DAST PR` usa apenas `ZAP + Schemathesis`.
O `RESTler` fica reservado ao workflow nightly.

- `dast/scripts/run-all.sh`: levanta a app a partir do software repo, exporta o OpenAPI e corre os tres scanners
- `dast/scripts/run-restler-nightly.sh`: levanta a app e corre o fluxo RESTler pesado para nightly
- `dast/scripts/run-zap.sh`: corre `ZAP` para API e frontend
- `dast/scripts/run-schemathesis.sh`: corre `Schemathesis` para a API
- `dast/scripts/run-restler.sh`: corre `RESTler` em `compile + test + fuzz-lean`
- `dast/scripts/run-restler-deep.sh`: corre o modo `fuzz` agressivo do `RESTler`
- `dast/scripts/wait-for-api.sh`: espera pelo backend e pelo OpenAPI
- `dast/scripts/wait-for-frontend.sh`: espera pelo frontend
- `dast/scripts/build-findings-manifest.py`: agrega um manifest inicial para posterior triagem
- `dast/dast_justificacao.md`: explica porque este combo foi escolhido

## Pre-requisitos

- `docker`
- `docker compose`
- `curl`
- `python3`

Nao e preciso instalar os scanners no host. O setup corre-os em containers.

## Onde esta a app alvo

Por omissao:

```bash
APP_REPO_DIR=../ses
APP_COMPOSE_FILE=../ses/docker-compose.yml
```

Nos workflows GitHub Actions, o software repo e obtido por `actions/checkout` para uma pasta temporaria e estes valores sao passados por environment variables.

## Fluxo recomendado

### 1. Correr tudo

```bash
./dast/scripts/run-all.sh
```

Isto faz:
1. `docker compose -f <software-repo>/docker-compose.yml up -d --build mysql backend frontend`
2. espera pelo backend
3. espera pelo frontend
4. exporta e normaliza o OpenAPI para `dast/generated/openapi.json`
5. corre `ZAP` na API e na SPA
6. corre `Schemathesis` na API
7. corre `RESTler` na API
8. gera `dast/results/llm/scan_manifest.json`

### 2. Correr scanners individualmente

```bash
docker compose -f ../ses/docker-compose.yml up -d --build mysql backend frontend
./dast/scripts/wait-for-api.sh
./dast/scripts/wait-for-frontend.sh
./dast/scripts/export-openapi.sh
./dast/scripts/run-zap.sh
./dast/scripts/run-schemathesis.sh
./dast/scripts/run-restler.sh
```

### 3. RESTler profundo

Corre isto so depois de `run-restler.sh`:

```bash
./dast/scripts/run-restler-deep.sh
```

Podes ajustar a duracao:

```bash
RESTLER_TIME_BUDGET_HOURS=2 ./dast/scripts/run-restler-deep.sh
```

### 4. Nightly pesado

```bash
AUTO_STOP_STACK=true ./dast/scripts/run-restler-nightly.sh
```

Isto faz:
1. levanta a app a partir do software repo
2. exporta o OpenAPI
3. corre `RESTler compile + test + fuzz-lean`
4. corre `RESTler fuzz`
5. gera o manifest
6. faz `docker compose down -v` no fim se `AUTO_STOP_STACK=true`

## O que cada scanner faz aqui

- `ZAP`: `zap-api-scan.py` para a API e `zap-baseline.py` com `Ajax spider` para o frontend
- `Schemathesis`: fuzzing da API a partir do OpenAPI
- `RESTler`: compile, test e fuzzing stateful sobre a API

## Variaveis uteis

### URLs do alvo

```bash
APP_REPO_DIR=../ses
APP_COMPOSE_FILE=../ses/docker-compose.yml
COMPOSE_PROJECT_NAME=ses-dast

TARGET_BASE_URL=http://localhost:8080
TARGET_SCHEMA_URL=http://localhost:8080/v3/api-docs
FRONTEND_BASE_URL=http://localhost:5173

SCANNER_TARGET_BASE_URL=http://host.docker.internal:8080
SCANNER_TARGET_SCHEMA_URL=http://host.docker.internal:8080/v3/api-docs
SCANNER_FRONTEND_BASE_URL=http://host.docker.internal:5173
```

As variaveis `TARGET_*` e `FRONTEND_*` sao usadas pelos scripts corridos no host.
As variaveis `SCANNER_*` sao usadas pelos scanners em container.
Se mudares portas, tens de manter os dois lados coerentes.

`APP_REPO_DIR` e `APP_COMPOSE_FILE` dizem aos scripts onde esta o checkout temporario da aplicacao.
Usa `SKIP_START_APP_STACK=true` se quiseres apontar os scanners para uma stack ja levantada manualmente.

### Schemathesis

```bash
SCHEMATHESIS_PHASES=examples,coverage,fuzzing,stateful
SCHEMATHESIS_MAX_FAILURES=100
SCHEMATHESIS_REQUEST_TIMEOUT=10
SCHEMATHESIS_MAX_RESPONSE_TIME=5
```

### ZAP

```bash
ZAP_MAX_TIME_MINUTES=15
ZAP_FRONTEND_SPIDER_MINUTES=3
ZAP_API_TIMEOUT=20m
ZAP_FRONTEND_TIMEOUT=12m
```

O scan frontend usa `zap-baseline.py` sem Ajax spider para reduzir flakiness no GitHub Actions.
Os dois comandos ZAP sao corridos com `timeout`, para um arranque preso do ZAP nao bloquear o workflow indefinidamente.

### RESTler

```bash
RESTLER_TIME_BUDGET_HOURS=1
RESTLER_IMAGE=ses-restler:6d984dee
RESTLER_REF=6d984deedbc54aad957fa3da0c7e9e5df23a2aee
```

Quando os scripts geram `dast/generated/restler-engine-settings.json`, o `SCANNER_TARGET_BASE_URL` e separado em:
- `host`: apenas hostname
- `target_port`: porta, quando existe
- `no_ssl`: `true` para `http`, `false` para `https`
- `use_ssl`: `true` para `https`, `false` para `http`

Exemplo:
- `SCANNER_TARGET_BASE_URL=http://host.docker.internal:8080`
- `host=host.docker.internal`
- `target_port=8080`
- `no_ssl=true`
- `use_ssl=false`

Nao coloques `host:port` dentro de `host`, porque o RESTler trata `host` como hostname literal.
Para endpoints `http://`, os scripts passam tambem `--no_ssl` ao RESTler para evitar tentativas TLS contra um alvo plain HTTP.

## Resultados

Os outputs ficam em:
- `dast/results/zap/api`
- `dast/results/zap/frontend`
- `dast/results/schemathesis`
- `dast/results/restler`
- `dast/results/llm/scan_manifest.json`

## Como usar depois com um LLM

Fluxo sugerido:
1. correr os tres scanners
2. usar `dast/results/llm/scan_manifest.json` como indice inicial
3. anexar tambem os reports crus mais importantes
4. pedir ao LLM para:
   - deduplicar findings
   - agrupar por alvo, endpoint e vulnerabilidade
   - distinguir findings confirmados vs ruído
   - mapear para `TM-*`, `AT-*` e `AS-*`
   - sugerir mitigacoes

Prompt operacional sugerido:

```text
Recebeste outputs de ZAP, Schemathesis e RESTler sobre a mesma aplicacao,
incluindo API e frontend. Agrupa resultados equivalentes, nao inventes evidencias,
preserva a origem de cada finding e produz uma tabela final com: alvo, scanner(s),
endpoint/url, metodo, vulnerabilidade, severidade, evidencia, confianca, relacao
com threat model e mitigacao sugerida.
```

## Notas

- `Schemathesis` e `RESTler` sao API-only.
- `ZAP` cobre API e frontend.
- `RESTler` e o scanner mais sensivel ao OpenAPI e o mais agressivo quando usado em `fuzz`.
- `run-all.sh` nao faz `docker compose down` por omissao; usa `AUTO_STOP_STACK=true` se quiseres cleanup automatico.
- Usa `SKIP_START_APP_STACK=true` se a app ja estiver levantada fora destes scripts e so quiseres correr os scanners.
- Se `8080` ou `5173` estiverem ocupados, tens de libertar esses ports ou arrancar o alvo manualmente noutras portas e ajustar as variaveis acima.
- Se quiseres limpar tudo no fim:

```bash
docker compose -f ../ses/docker-compose.yml down -v
```
