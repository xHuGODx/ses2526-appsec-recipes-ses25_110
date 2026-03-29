#!/usr/bin/env python3

import html
import json
import pathlib
from datetime import datetime, timezone


ROOT = pathlib.Path(__file__).resolve().parents[1]
INPUT_PATH = ROOT / "results" / "llm" / "findings_table.json"
OUTPUT_PATH = ROOT / "results" / "llm" / "findings_table.html"


def load_json(path: pathlib.Path):
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def cell(value) -> str:
    if value is None:
        return ""
    if isinstance(value, list):
        value = ", ".join(str(item) for item in value)
    return html.escape(str(value))


def main() -> int:
    payload = load_json(INPUT_PATH)
    rows = payload.get("table", [])
    notes = payload.get("notas", [])
    generated_at = payload.get("metadata", {}).get(
        "generated_at", datetime.now(timezone.utc).isoformat()
    )

    table_rows = []
    for row in rows:
        table_rows.append(
            "<tr>"
            f"<td>{cell(row.get('alvo'))}</td>"
            f"<td>{cell(row.get('scanners'))}</td>"
            f"<td>{cell(row.get('endpoint_url'))}</td>"
            f"<td>{cell(row.get('metodo'))}</td>"
            f"<td>{cell(row.get('vulnerabilidade'))}</td>"
            f"<td>{cell(row.get('severidade'))}</td>"
            f"<td>{cell(row.get('evidencia'))}</td>"
            f"<td>{cell(row.get('confianca'))}</td>"
            f"<td>{cell(row.get('relacao_threat_model'))}</td>"
            f"<td>{cell(row.get('mitigacao_sugerida'))}</td>"
            "</tr>"
        )

    notes_html = "".join(f"<li>{cell(note)}</li>" for note in notes)
    html_output = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>DAST LLM Findings Table</title>
  <style>
    body {{
      font-family: Arial, sans-serif;
      margin: 24px;
      color: #1f2937;
      background: #f8fafc;
    }}
    h1 {{
      margin-bottom: 8px;
    }}
    .meta {{
      color: #475569;
      margin-bottom: 16px;
    }}
    table {{
      border-collapse: collapse;
      width: 100%;
      background: #ffffff;
    }}
    th, td {{
      border: 1px solid #cbd5e1;
      padding: 10px;
      vertical-align: top;
      text-align: left;
      font-size: 14px;
    }}
    th {{
      background: #e2e8f0;
      position: sticky;
      top: 0;
    }}
    tbody tr:nth-child(even) {{
      background: #f8fafc;
    }}
    ul {{
      margin-top: 8px;
    }}
  </style>
</head>
<body>
  <h1>DAST LLM Findings Table</h1>
  <p class="meta">Generated at {cell(generated_at)} with {len(rows)} consolidated findings.</p>
  <table>
    <thead>
      <tr>
        <th>alvo</th>
        <th>scanner(s)</th>
        <th>endpoint/url</th>
        <th>metodo</th>
        <th>vulnerabilidade</th>
        <th>severidade</th>
        <th>evidencia</th>
        <th>confianca</th>
        <th>relacao com threat model</th>
        <th>mitigacao sugerida</th>
      </tr>
    </thead>
    <tbody>
      {''.join(table_rows)}
    </tbody>
  </table>
  <h2>Notas</h2>
  <ul>{notes_html}</ul>
</body>
</html>
"""

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(html_output, encoding="utf-8")
    print(OUTPUT_PATH)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
