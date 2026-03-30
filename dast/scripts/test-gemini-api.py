#!/usr/bin/env python3

import argparse
import json
import os
import sys
import urllib.error
import urllib.request


API_KEY = os.environ.get("GEMINI_KEY", "").strip()
MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Simple local smoke test for the Gemini generateContent API."
    )
    parser.add_argument(
        "--prompt",
        default="Reply with exactly: GEMINI_OK",
        help="Prompt to send to Gemini.",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=60,
        help="HTTP timeout in seconds.",
    )
    parser.add_argument(
        "--raw",
        action="store_true",
        help="Print the raw JSON API response instead of only the model text.",
    )
    return parser.parse_args()


def request_gemini(prompt: str, timeout: int) -> dict:
    body = {
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0,
        },
    }
    request = urllib.request.Request(
        url=f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent?key={API_KEY}",
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def extract_text(payload: dict) -> str:
    candidates = payload.get("candidates") or []
    if not candidates:
        raise ValueError(f"No candidates in response: {json.dumps(payload, indent=2)}")
    parts = candidates[0].get("content", {}).get("parts") or []
    text_chunks = [part.get("text", "") for part in parts if isinstance(part, dict)]
    text = "".join(text_chunks).strip()
    if not text:
        raise ValueError(f"No text content in response: {json.dumps(payload, indent=2)}")
    return text


def main() -> int:
    args = parse_args()
    if not API_KEY:
        print("Missing GEMINI_KEY in the environment.", file=sys.stderr)
        return 1

    try:
        payload = request_gemini(args.prompt, args.timeout)
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        print(f"Gemini API HTTP error: {exc.code}\n{body}", file=sys.stderr)
        return 1
    except Exception as exc:  # noqa: BLE001
        print(f"Gemini API request failed: {exc}", file=sys.stderr)
        return 1

    if args.raw:
        print(json.dumps(payload, indent=2, ensure_ascii=True))
        return 0

    try:
        print(extract_text(payload))
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
