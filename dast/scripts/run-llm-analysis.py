#!/usr/bin/env python3

import json
import os
import pathlib
import re
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone


ROOT = pathlib.Path(__file__).resolve().parents[1]
INPUT_PATH = ROOT / "results" / "llm" / "analysis_input.json"
OUTPUT_PATH = ROOT / "results" / "llm" / "findings_table.json"
INSTRUCTIONS_PATH = ROOT / "instructions.md"
MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")
API_KEY = os.environ.get("GEMINI_KEY", "").strip()
PROMPT_RE = re.compile(r"Prompt operacional sugerido:\s*```text\n(.*?)\n```", re.S)


def clean_response(text: str) -> str:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        first_break = cleaned.find("\n")
        cleaned = cleaned[first_break + 1 :] if first_break != -1 else cleaned[3:]
    if cleaned.endswith("```"):
        cleaned = cleaned[: cleaned.rfind("```")]
    return cleaned.strip()


def load_json(path: pathlib.Path):
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def extract_prompt(instructions_path: pathlib.Path) -> str:
    content = instructions_path.read_text(encoding="utf-8")
    match = PROMPT_RE.search(content)
    if match:
        return match.group(1).strip()
    return (
        "Recebeste outputs de ZAP, Schemathesis e RESTler sobre a mesma aplicacao, "
        "incluindo API e frontend. Agrupa resultados equivalentes, nao inventes "
        "evidencias, preserva a origem de cada finding e produz uma tabela final com: "
        "alvo, scanner(s), endpoint/url, metodo, vulnerabilidade, severidade, "
        "evidencia, confianca, relacao com threat model e mitigacao sugerida."
    )


def build_user_prompt(payload: dict) -> str:
    operational_prompt = extract_prompt(INSTRUCTIONS_PATH)
    response_contract = {
        "table": [
            {
                "alvo": "api|frontend|shared",
                "scanners": ["zap", "schemathesis", "restler"],
                "endpoint_url": "string or null",
                "metodo": "string or null",
                "vulnerabilidade": "string",
                "severidade": "critical|high|medium|low|info|unknown",
                "evidencia": "string",
                "confianca": "high|medium|low",
                "relacao_threat_model": "string",
                "mitigacao_sugerida": "string",
            }
        ],
        "notas": ["string"],
    }
    return (
        "Segue estritamente estas instrucoes:\n"
        f"{operational_prompt}\n\n"
        "Responde apenas com JSON valido. Nao uses markdown. "
        "Nao inventes endpoints, metodos ou evidencias. "
        "Se um campo nao estiver suportado pelos dados, usa null ou 'unknown'.\n\n"
        "O formato de resposta deve ser:\n"
        f"{json.dumps(response_contract, ensure_ascii=True, indent=2)}\n\n"
        "Dados para analise:\n"
        f"{json.dumps(payload, ensure_ascii=True, indent=2)}"
    )


def gemini_request(prompt: str) -> dict:
    body = {
        "systemInstruction": {
            "parts": [
                {
                    "text": (
                        "You are an AppSec analyst. Produce a deduplicated, evidence-based JSON table. "
                        "Only use the supplied scanner evidence."
                    )
                }
            ]
        },
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.2,
            "responseMimeType": "application/json",
        },
    }
    request = urllib.request.Request(
        url=f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent?key={API_KEY}",
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=120) as response:
        return json.loads(response.read().decode("utf-8"))


def normalize_row(row: dict) -> dict:
    def pick(*keys, default=None):
        for key in keys:
            if key in row and row[key] not in ("", None, []):
                return row[key]
        return default

    scanners = pick("scanners", "scanner(s)", "scanner")
    if isinstance(scanners, str):
        scanners = [part.strip() for part in scanners.split(",") if part.strip()]
    elif not isinstance(scanners, list):
        scanners = []

    return {
        "alvo": pick("alvo", "target", default="unknown"),
        "scanners": scanners,
        "endpoint_url": pick("endpoint_url", "endpoint/url", "endpoint", "url"),
        "metodo": pick("metodo", "method"),
        "vulnerabilidade": pick("vulnerabilidade", "vulnerability", default="unknown"),
        "severidade": str(pick("severidade", "severity", default="unknown")).lower(),
        "evidencia": pick("evidencia", "evidence", default=""),
        "confianca": str(pick("confianca", "confidence", default="unknown")).lower(),
        "relacao_threat_model": pick(
            "relacao_threat_model",
            "relacao com threat model",
            "threat_model_relation",
            default="unknown",
        ),
        "mitigacao_sugerida": pick(
            "mitigacao_sugerida",
            "mitigacao sugerida",
            "mitigation",
            default="unknown",
        ),
    }


def normalize_payload(raw_payload: dict) -> dict:
    rows = raw_payload if isinstance(raw_payload, list) else raw_payload.get("table", [])
    if not isinstance(rows, list):
        rows = []
    normalized_rows = [normalize_row(row) for row in rows if isinstance(row, dict)]
    notes = raw_payload.get("notas", []) if isinstance(raw_payload, dict) else []
    if not isinstance(notes, list):
        notes = []
    return {
        "metadata": {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "model": MODEL,
            "input_path": str(INPUT_PATH.relative_to(ROOT)),
        },
        "table": normalized_rows,
        "notas": [str(note) for note in notes[:20]],
    }


def main() -> int:
    if not API_KEY:
        print("Missing GEMINI_KEY", file=sys.stderr)
        return 1
    if not INPUT_PATH.exists():
        print(f"Missing analysis input: {INPUT_PATH}", file=sys.stderr)
        return 1

    prompt = build_user_prompt(load_json(INPUT_PATH))
    try:
        response = gemini_request(prompt)
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        print(f"Gemini API HTTP error: {exc.code}\n{body}", file=sys.stderr)
        return 1
    except Exception as exc:  # noqa: BLE001
        print(f"Gemini API request failed: {exc}", file=sys.stderr)
        return 1

    try:
        raw_text = response["candidates"][0]["content"]["parts"][0]["text"]
    except (KeyError, IndexError, TypeError) as exc:
        print(f"Unexpected Gemini response shape: {exc}\n{json.dumps(response, indent=2)}", file=sys.stderr)
        return 1

    cleaned = clean_response(raw_text)
    try:
        parsed = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        print(f"Gemini returned non-JSON payload: {exc}\n{cleaned}", file=sys.stderr)
        return 1

    normalized = normalize_payload(parsed)
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_PATH.open("w", encoding="utf-8") as handle:
        json.dump(normalized, handle, indent=2, ensure_ascii=True)
        handle.write("\n")

    print(OUTPUT_PATH)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
