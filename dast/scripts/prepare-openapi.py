#!/usr/bin/env python3

import json
import pathlib
import sys


def main() -> int:
    if len(sys.argv) != 4:
        print("usage: prepare-openapi.py <input-json> <output-json> <base-url>", file=sys.stderr)
        return 1

    input_path = pathlib.Path(sys.argv[1])
    output_path = pathlib.Path(sys.argv[2])
    base_url = sys.argv[3].rstrip("/")

    with input_path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)

    data["servers"] = [{"url": base_url}]

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2, ensure_ascii=True)
        handle.write("\n")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
