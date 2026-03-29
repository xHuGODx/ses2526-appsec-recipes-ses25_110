# DAST Instructions

## Scope

This DAST setup uses two scanners:
- `ZAP`
- `Schemathesis`

Coverage:
- `ZAP` scans the API and the frontend
- `Schemathesis` scans the API only

## Repository Layout

This repository stores only security automation and configuration.

Main entry points:
- `dast/scripts/run-all.sh`
- `dast/scripts/run-zap.sh`
- `dast/scripts/run-schemathesis.sh`
- `.github/workflows/nightly-dast.yml`

## Local Execution

Expected layout:
- software repo at `../ses`, or
- set `APP_REPO_DIR=/path/to/software-repo`

Useful variables:
- `APP_REPO_DIR`
- `APP_COMPOSE_FILE`
- `TARGET_BASE_URL`
- `FRONTEND_BASE_URL`
- `SCANNER_TARGET_BASE_URL`
- `SCANNER_FRONTEND_BASE_URL`
- `AUTO_STOP_STACK=true`
- `SKIP_START_APP_STACK=true`

Main local flow:
1. start or reuse the application stack from the software repo
2. wait for the API and frontend
3. export OpenAPI
4. run `ZAP`
5. run `Schemathesis`
6. build the findings manifest

### Full DAST Run

```bash
./dast/scripts/run-all.sh
```

### ZAP Only

```bash
./dast/scripts/run-zap.sh
```

### Schemathesis Only

```bash
./dast/scripts/run-schemathesis.sh
```

## Outputs

Generated files:
- `dast/generated/openapi.json`

Scanner outputs:
- `dast/results/zap`
- `dast/results/schemathesis`

Aggregator outputs:
- `dast/results/llm/scan_manifest.json`
- `dast/results/llm/analysis_input.json`
- `dast/results/llm/findings_table.json`
- `dast/results/llm/findings_table.html`

## LLM Reporting

The deterministic aggregator is not replaced.

Flow:
1. `build-findings-manifest.py` reads the scanner outputs and writes `scan_manifest.json`
2. `build-llm-analysis-input.py` prepares a normalized input payload
3. `run-llm-analysis.py` calls Gemini and writes a JSON findings table
4. `render-llm-report.py` renders that table to HTML

The Gemini step uses `GEMINI_KEY`.

Prompt operational suggestion:

```text
You received ZAP and Schemathesis outputs for the same application, covering both API and frontend. Group equivalent results, do not invent evidence, preserve the source of each finding, and produce a final table with: target, scanner(s), endpoint/url, method, vulnerability, severity, evidence, confidence, threat model relation, and suggested mitigation.
```

## Notes

- `ZAP` is the only scanner that covers the frontend.
- `Schemathesis` is API-only and contract-driven.
- `run-all.sh` does not stop the stack by default; use `AUTO_STOP_STACK=true` if you want automatic cleanup.
