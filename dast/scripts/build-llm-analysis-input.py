#!/usr/bin/env python3

import json
import pathlib
import re
import xml.etree.ElementTree as ET
from datetime import datetime, timezone


ROOT = pathlib.Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results"
OUTPUT = RESULTS / "llm" / "analysis_input.json"
METHOD_RE = re.compile(r"\b(GET|POST|PUT|PATCH|DELETE|OPTIONS|HEAD)\b\s+(\S+)")
URL_RE = re.compile(r"https?://[^\s)\"'>]+")


def load_json(path: pathlib.Path):
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def truncate(value: str, limit: int = 1600) -> str:
    text = (value or "").strip()
    if len(text) <= limit:
        return text
    return text[: limit - 3] + "..."


def normalize_severity(risk_code, risk_desc: str) -> str:
    mapping = {
        "0": "info",
        "1": "low",
        "2": "medium",
        "3": "high",
        "4": "critical",
    }
    if risk_code is not None:
        key = str(risk_code)
        if key in mapping:
            return mapping[key]
    lowered = (risk_desc or "").lower()
    for level in ("critical", "high", "medium", "low", "info"):
        if level in lowered:
            return level
    return "unknown"


def extract_method_and_target(*parts):
    blob = "\n".join(part for part in parts if part)
    match = METHOD_RE.search(blob)
    if match:
        return match.group(1), match.group(2)
    url_match = URL_RE.search(blob)
    if url_match:
        return None, url_match.group(0)
    return None, None


def compact_evidence(items: list[tuple[str, str]]) -> str:
    chunks = [f"{key}: {value}" for key, value in items if value]
    return truncate("\n".join(chunks), 1800)


def parse_zap_report(report: pathlib.Path, target: str, limit: int = 80) -> list[dict]:
    if not report.exists():
        return []

    data = load_json(report)
    findings = []
    for site in data.get("site", []):
        for alert in site.get("alerts", []):
            instances = alert.get("instances") or [{}]
            for instance in instances:
                method = instance.get("method")
                url = instance.get("uri") or site.get("@name")
                evidence = compact_evidence(
                    [
                        ("evidence", instance.get("evidence")),
                        ("parameter", instance.get("param")),
                        ("attack", instance.get("attack")),
                        ("other_info", alert.get("otherinfo")),
                        ("description", alert.get("desc")),
                        ("solution", alert.get("solution")),
                    ]
                )
                findings.append(
                    {
                        "scanner": "zap",
                        "target": target,
                        "url": url,
                        "method": method,
                        "vulnerability": alert.get("name"),
                        "severity": normalize_severity(
                            alert.get("riskcode"), alert.get("riskdesc", "")
                        ),
                        "confidence": (alert.get("confidence") or "").lower() or "unknown",
                        "evidence": evidence,
                        "source": str(report.relative_to(ROOT)),
                    }
                )
                if len(findings) >= limit:
                    return findings
    return findings


def parse_schemathesis_junit(junit: pathlib.Path, limit: int = 80) -> list[dict]:
    if not junit.exists():
        return []

    root = ET.parse(junit).getroot()
    suites = root if root.tag == "testsuites" else [root]
    findings = []
    for suite in suites:
        for testcase in suite.findall(".//testcase"):
            failure = testcase.find("failure")
            error = testcase.find("error")
            node = failure or error
            if node is None:
                continue

            classname = testcase.attrib.get("classname", "")
            name = testcase.attrib.get("name", "")
            message = node.attrib.get("message", "")
            details = truncate((node.text or "").strip(), 2200)
            method, target = extract_method_and_target(classname, name, message, details)
            findings.append(
                {
                    "scanner": "schemathesis",
                    "target": "api",
                    "url": target,
                    "method": method,
                    "vulnerability": truncate(message or node.tag, 240),
                    "severity": "unknown",
                    "confidence": "medium",
                    "evidence": compact_evidence(
                        [
                            ("testcase", name),
                            ("classname", classname),
                            ("message", message),
                            ("details", details),
                        ]
                    ),
                    "source": str(junit.relative_to(ROOT)),
                }
            )
            if len(findings) >= limit:
                return findings
    return findings


def parse_schemathesis_events(events_path: pathlib.Path, limit: int = 60) -> list[dict]:
    if not events_path.exists():
        return []

    findings = []
    with events_path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                payload = json.loads(line)
            except json.JSONDecodeError:
                continue
            blob = json.dumps(payload, ensure_ascii=True, sort_keys=True)
            lowered = blob.lower()
            if not any(token in lowered for token in ("fail", "error", "check", "schema")):
                continue
            findings.append(
                {
                    "event_type": payload.get("event_type"),
                    "excerpt": truncate(blob, 1800),
                }
            )
            if len(findings) >= limit:
                break
    return findings


def parse_restler(limit: int = 12) -> dict:
    base = RESULTS / "restler"
    if not base.exists():
        return {"summaries": [], "bug_buckets": []}

    summaries = []
    for path in sorted(base.glob("**/ResponseBuckets/runSummary.json"))[:limit]:
        try:
            payload = load_json(path)
        except json.JSONDecodeError:
            continue
        summaries.append(
            {
                "source": str(path.relative_to(ROOT)),
                "summary": payload,
            }
        )

    bug_buckets = []
    for path in sorted(base.glob("**/bug_buckets/*.txt"))[:limit]:
        bug_buckets.append(
            {
                "source": str(path.relative_to(ROOT)),
                "excerpt": truncate(path.read_text(encoding="utf-8", errors="replace"), 2000),
            }
        )

    return {
        "summaries": summaries,
        "bug_buckets": bug_buckets,
    }


def main() -> int:
    manifest_path = RESULTS / "llm" / "scan_manifest.json"
    manifest = load_json(manifest_path) if manifest_path.exists() else {}

    payload = {
        "metadata": {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "root": str(ROOT),
            "manifest_path": str(manifest_path.relative_to(ROOT)) if manifest_path.exists() else None,
        },
        "manifest": manifest,
        "findings": {
            "zap": {
                "api": parse_zap_report(RESULTS / "zap" / "api" / "report.json", "api"),
                "frontend": parse_zap_report(
                    RESULTS / "zap" / "frontend" / "report.json", "frontend"
                ),
            },
            "schemathesis": {
                "junit_findings": parse_schemathesis_junit(
                    RESULTS / "schemathesis" / "junit.xml"
                ),
                "event_samples": parse_schemathesis_events(
                    RESULTS / "schemathesis" / "events.ndjson"
                ),
            },
            "restler": parse_restler(),
        },
    }

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=True)
        handle.write("\n")

    print(OUTPUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
