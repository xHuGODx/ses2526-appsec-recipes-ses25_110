#!/usr/bin/env python3

import json
import pathlib
import xml.etree.ElementTree as ET


ROOT = pathlib.Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results"
OUTPUT = RESULTS / "llm" / "scan_manifest.json"


def load_json(path: pathlib.Path):
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def parse_zap_report(report: pathlib.Path) -> dict:
    if not report.exists():
        return {"present": False}

    data = load_json(report)
    alerts = []
    total_instances = 0
    for site in data.get("site", []):
      for alert in site.get("alerts", []):
        count = len(alert.get("instances", []))
        total_instances += count
        alerts.append(
            {
                "pluginid": alert.get("pluginid"),
                "name": alert.get("name"),
                "riskdesc": alert.get("riskdesc"),
                "confidence": alert.get("confidence"),
                "instances": count,
            }
        )

    return {
        "present": True,
        "report": str(report.relative_to(ROOT)),
        "alerts": len(alerts),
        "instances": total_instances,
        "top_alerts": alerts[:20],
    }


def parse_zap() -> dict:
    return {
        "api": parse_zap_report(RESULTS / "zap" / "api" / "report.json"),
        "frontend": parse_zap_report(RESULTS / "zap" / "frontend" / "report.json"),
    }


def parse_schemathesis() -> dict:
    junit = RESULTS / "schemathesis" / "junit.xml"
    if not junit.exists():
        return {"present": False}

    root = ET.parse(junit).getroot()
    suites = root if root.tag == "testsuites" else [root]
    tests = failures = errors = skipped = 0
    for suite in suites:
        tests += int(suite.attrib.get("tests", 0))
        failures += int(suite.attrib.get("failures", 0))
        errors += int(suite.attrib.get("errors", 0))
        skipped += int(suite.attrib.get("skipped", 0))

    return {
        "present": True,
        "junit_report": str(junit.relative_to(ROOT)),
        "tests": tests,
        "failures": failures,
        "errors": errors,
        "skipped": skipped,
    }

def parse_restler() -> dict:
    base = RESULTS / "restler"
    if not base.exists():
        return {"present": False}

    bug_bucket_files = list(base.glob("**/bug_buckets/*.txt"))
    summary_files = list(base.glob("**/ResponseBuckets/runSummary.json"))
    if not bug_bucket_files and not summary_files:
        return {"present": False}

    summaries = {}
    for path in summary_files[:6]:
        summaries[str(path.relative_to(ROOT))] = load_json(path)

    return {
        "present": True,
        "bug_bucket_files": len(bug_bucket_files),
        "response_summaries": summaries,
    }


def main() -> int:
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    manifest = {
        "scanners": {
            "zap": parse_zap(),
            "schemathesis": parse_schemathesis(),
            "restler": parse_restler(),
        }
    }

    with OUTPUT.open("w", encoding="utf-8") as handle:
        json.dump(manifest, handle, indent=2, ensure_ascii=True)
        handle.write("\n")

    print(OUTPUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
