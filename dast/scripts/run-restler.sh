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

python3 - "${CONFIG_DIR}/restler/engine_settings.json" "${RESTLER_SETTINGS_PATH}" "${SCANNER_TARGET_BASE_URL#http://}" <<'PY'
import json
import sys

template_path, output_path, host = sys.argv[1:4]
with open(template_path, "r", encoding="utf-8") as fh:
    data = json.load(fh)
data["host"] = host
with open(output_path, "w", encoding="utf-8") as fh:
    json.dump(data, fh, indent=2)
    fh.write("\n")
PY

log "Running RESTler compile, test and fuzz-lean"
rm -rf "${RESULTS_DIR}/restler/Compile" "${RESULTS_DIR}/restler/Test" "${RESULTS_DIR}/restler/FuzzLean"

docker run --rm \
  "${HOST_GATEWAY_ARG[@]}" \
  -v "${DAST_DIR}:/work" \
  -w /work/results/restler \
  "${RESTLER_IMAGE}" \
  /RESTler/restler/Restler compile --api_spec /work/generated/openapi.json

docker run --rm \
  "${HOST_GATEWAY_ARG[@]}" \
  -v "${DAST_DIR}:/work" \
  -w /work/results/restler \
  "${RESTLER_IMAGE}" \
  /RESTler/restler/Restler test \
    --grammar_file Compile/grammar.py \
    --dictionary_file Compile/dict.json \
    --settings /work/generated/restler-engine-settings.json

docker run --rm \
  "${HOST_GATEWAY_ARG[@]}" \
  -v "${DAST_DIR}:/work" \
  -w /work/results/restler \
  "${RESTLER_IMAGE}" \
  /RESTler/restler/Restler fuzz-lean \
    --grammar_file Compile/grammar.py \
    --dictionary_file Compile/dict.json \
    --settings /work/generated/restler-engine-settings.json

log "RESTler outputs stored in ${RESULTS_DIR}/restler"
