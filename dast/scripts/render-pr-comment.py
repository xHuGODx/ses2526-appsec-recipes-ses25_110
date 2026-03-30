#!/usr/bin/env python3

import json
import pathlib


ROOT = pathlib.Path(__file__).resolve().parents[1]
INPUT_PATH = ROOT / "results" / "llm" / "findings_table.json"
OUTPUT_PATH = ROOT / "results" / "llm" / "pr_comment.md"
MARKER = "<!-- dast-gemini-table -->"
MAX_ROWS = 20


def load_json(path: pathlib.Path):
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def text(value) -> str:
    if value is None:
        return ""
    if isinstance(value, list):
        value = ", ".join(str(item) for item in value)
    return str(value).replace("\n", " ").replace("|", "\\|").strip()


def truncate(value, limit: int) -> str:
    rendered = text(value)
    if len(rendered) <= limit:
        return rendered
    return rendered[: limit - 3] + "..."


def main() -> int:
    payload = load_json(INPUT_PATH)
    rows = payload.get("table", [])
    notes = payload.get("notes", [])
    shown_rows = rows[:MAX_ROWS]

    lines = [
        MARKER,
        "## DAST Gemini Table",
        "",
        f"Consolidated findings: **{len(rows)}**",
        "",
        "| Target | Scanners | Endpoint / URL | Method | Vulnerability | Severity | Confidence | Threat Model Relation | Suggested Mitigation |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]

    for row in shown_rows:
        lines.append(
            "| "
            + " | ".join(
                [
                    truncate(row.get("target"), 32),
                    truncate(row.get("scanners"), 40),
                    truncate(row.get("endpoint_url"), 60),
                    truncate(row.get("method"), 12),
                    truncate(row.get("vulnerability"), 80),
                    truncate(row.get("severity"), 16),
                    truncate(row.get("confidence"), 16),
                    truncate(row.get("threat_model_relation"), 80),
                    truncate(row.get("suggested_mitigation"), 120),
                ]
            )
            + " |"
        )

    if len(rows) > MAX_ROWS:
        lines.extend(
            [
                "",
                f"_Showing the first {MAX_ROWS} findings. See the HTML artifact for the full table._",
            ]
        )

    if notes:
        lines.extend(["", "### Notes"])
        for note in notes[:10]:
            lines.append(f"- {truncate(note, 240)}")

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(OUTPUT_PATH)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
