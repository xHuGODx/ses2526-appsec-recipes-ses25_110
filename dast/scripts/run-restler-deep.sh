#!/usr/bin/env bash

set -euo pipefail

source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/common.sh"

require_basics
ensure_dirs

"${DAST_DIR}/scripts/build-restler-image.sh"

if [[ ! -f "${OPENAPI_PATH}" ]]; then
  printf 'OpenAPI file not found: %s\nRun export-openapi.sh first.\n' "${OPENAPI_PATH}" >&2
  exit 1
fi

if [[ ! -f "${RESULTS_DIR}/restler/Compile/grammar.py" ]]; then
  printf 'RESTler grammar not found. Run run-restler.sh first.\n' >&2
  exit 1
fi

python3 - "${CONFIG_DIR}/restler/engine_settings.json" "${RESTLER_SETTINGS_PATH}" "${SCANNER_TARGET_BASE_URL}" <<'PY'
import json
from urllib.parse import urlparse
import sys

template_path, output_path, target_base_url = sys.argv[1:4]
parsed = urlparse(target_base_url)
if not parsed.hostname:
    raise SystemExit(f"Invalid SCANNER_TARGET_BASE_URL: {target_base_url}")

with open(template_path, "r", encoding="utf-8") as fh:
    data = json.load(fh)
data["host"] = parsed.hostname
if parsed.port is not None:
    data["target_port"] = parsed.port
else:
    data.pop("target_port", None)
data["no_ssl"] = parsed.scheme != "https"
data["use_ssl"] = parsed.scheme == "https"
with open(output_path, "w", encoding="utf-8") as fh:
    json.dump(data, fh, indent=2)
    fh.write("\n")
PY

log "Running RESTler deep fuzz mode"
docker run --rm \
  "${HOST_GATEWAY_ARG[@]}" \
  -v "${DAST_DIR}:/work" \
  -w /work/results/restler \
  "${RESTLER_IMAGE}" \
  /RESTler/restler/Restler fuzz \
    --grammar_file Compile/grammar.py \
    --dictionary_file Compile/dict.json \
    --settings /work/generated/restler-engine-settings.json \
    "${RESTLER_TRANSPORT_ARGS[@]}" \
    --time_budget "${RESTLER_TIME_BUDGET_HOURS:-1}"

log "RESTler deep fuzz output stored in ${RESULTS_DIR}/restler/Fuzz"
