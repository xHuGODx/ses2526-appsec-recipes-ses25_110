# DAST Setup Justification

## Goal

This setup is designed for a separate `AppSec repo` that stores only security automation. The application code is fetched temporarily from the software repo during execution.

## Selected Scanners

### 1. OWASP ZAP

Why it is included:
- scans both the API and the frontend
- catches common web issues such as missing security headers, exposed information, and unsafe responses
- produces machine-readable and human-readable reports

Why it fits this app:
- the backend exposes OpenAPI via Springdoc
- the frontend is a simple SPA that can still be assessed for baseline web issues
- it is easy to automate in Docker and easy to justify in an academic setting

### 2. Schemathesis

Why it is included:
- exercises the API directly from the OpenAPI contract
- finds schema violations, undocumented status codes, weak validation, and broken API behavior
- complements classic web scanning with contract-driven fuzzing

Why it fits this app:
- the OpenAPI spec is accessible at runtime
- the app exposes a compact but stateful REST API surface
- it gives strong evidence when implementation and specification diverge

## How They Complement Each Other

- `ZAP` covers the web-facing perspective for both API and frontend.
- `Schemathesis` covers the API contract and semantic behavior more deeply.
- findings that appear in both scanners gain confidence.
- findings that appear in only one scanner can still be valuable because the detection angle is different.

## Why Use an LLM After the Scanners

The LLM is used for reporting, not for raw evidence collection.

The pipeline keeps deterministic evidence first:
- `ZAP`: `report.json`, `report.html`
- `Schemathesis`: `junit.xml`, `events.ndjson`

Then it adds:
- normalized manifest generation
- LLM-based grouping and deduplication
- HTML rendering for the final table

## Trade-offs

- Docker-based execution improves reproducibility.
- separating `software repo` and `AppSec repo` avoids duplicating app code in the security repo.
- `ZAP` gives broader web coverage, but frontend exploration remains lighter than a browser-driven authenticated setup.
- `Schemathesis` is API-focused, so it does not assess frontend rendering behavior.
