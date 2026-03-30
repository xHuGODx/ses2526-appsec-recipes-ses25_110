#!/usr/bin/env python3

import argparse
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
        total += int(report.get("instances", report.get("alerts", 0)) or 0)
    return total


def zap_details(data: dict) -> dict:
    details = {}
    for target in ("api", "frontend"):
        report = data.get(target, {})
        details[target] = {
            "alert_types": int(report.get("alert_types", report.get("alerts", 0)) or 0),
            "instances": int(report.get("instances", 0) or 0),
        }
    return details


def schemathesis_findings(data: dict) -> int:
    return int(data.get("failures", 0) or 0) + int(data.get("errors", 0) or 0)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest_path")
    parser.add_argument(
        "--require-file",
        action="append",
        default=[],
        dest="required_files",
        help="Artifact path that must exist for the run to be considered valid.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    manifest_path = pathlib.Path(args.manifest_path)
    if not manifest_path.exists():
        print(f"Manifest not found: {manifest_path}", file=sys.stderr)
        return 2

    manifest = load_manifest(manifest_path)
    scanners = manifest.get("scanners", {})

    summary = {
        "zap": zap_findings(scanners.get("zap", {})),
        "schemathesis": schemathesis_findings(scanners.get("schemathesis", {})),
    }
    details = {
        "zap": zap_details(scanners.get("zap", {})),
    }
    total_findings = sum(summary.values())
    missing_artifacts = [
        path for path in args.required_files if not pathlib.Path(path).exists()
    ]

    print(
        json.dumps(
            {
                "findings": summary,
                "details": details,
                "total": total_findings,
                "missing_artifacts": missing_artifacts,
            },
            indent=2,
        )
    )
    if missing_artifacts:
        return 2
    return 1 if total_findings > 0 else 0


if __name__ == "__main__":
    raise SystemExit(main())
