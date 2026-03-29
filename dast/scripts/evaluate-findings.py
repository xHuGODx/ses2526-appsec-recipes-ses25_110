#!/usr/bin/env python3

import json
import pathlib
import sys


def load_manifest(path: pathlib.Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def zap_findings(data: dict) -> int:
    total = 0
    for target in ("api", "frontend"):
        report = data.get(target, {})
        total += int(report.get("alerts", 0) or 0)
    return total


def schemathesis_findings(data: dict) -> int:
    return int(data.get("failures", 0) or 0) + int(data.get("errors", 0) or 0)


def restler_findings(data: dict) -> int:
    total = int(data.get("bug_bucket_files", 0) or 0)
    for summary in data.get("response_summaries", {}).values():
        total += int(summary.get("bugCount", 0) or 0)
        total += int(summary.get("failedRequestsCount", 0) or 0)
        total += len(summary.get("errorBuckets", {}) or {})
    return total


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: evaluate-findings.py <manifest-path>", file=sys.stderr)
        return 2

    manifest_path = pathlib.Path(sys.argv[1])
    if not manifest_path.exists():
        print(f"Manifest not found: {manifest_path}", file=sys.stderr)
        return 2

    manifest = load_manifest(manifest_path)
    scanners = manifest.get("scanners", {})

    summary = {
        "zap": zap_findings(scanners.get("zap", {})),
        "schemathesis": schemathesis_findings(scanners.get("schemathesis", {})),
        "restler": restler_findings(scanners.get("restler", {})),
    }
    total_findings = sum(summary.values())

    print(json.dumps({"findings": summary, "total": total_findings}, indent=2))
    return 1 if total_findings > 0 else 0


if __name__ == "__main__":
    raise SystemExit(main())
