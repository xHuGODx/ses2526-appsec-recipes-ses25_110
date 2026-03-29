#!/usr/bin/env bash

set -euo pipefail

source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/common.sh"

require_basics
ensure_dirs

"${DAST_DIR}/scripts/build-schemathesis-image.sh"

if [[ ! -f "${OPENAPI_PATH}" ]]; then
  printf 'OpenAPI file not found: %s\nRun export-openapi.sh first.\n' "${OPENAPI_PATH}" >&2
  exit 1
fi

log "Running Schemathesis against ${SCANNER_TARGET_BASE_URL}"
docker run --rm \
  "${HOST_GATEWAY_ARG[@]}" \
  -v "${DAST_DIR}:/work" \
  "${SCHEMATHESIS_IMAGE}" \
  run /work/generated/openapi.json \
    --url "${SCANNER_TARGET_BASE_URL}" \
    --phases "${SCHEMATHESIS_PHASES:-examples,coverage,fuzzing,stateful}" \
    --checks all \
    --mode all \
    --max-failures "${SCHEMATHESIS_MAX_FAILURES:-100}" \
    --continue-on-failure \
    --report junit \
    --report-junit-path /work/results/schemathesis/junit.xml \
    --output-sanitize=false \
    --request-timeout "${SCHEMATHESIS_REQUEST_TIMEOUT:-10}" \
    --max-response-time "${SCHEMATHESIS_MAX_RESPONSE_TIME:-5}" \
    --seed "${SCHEMATHESIS_SEED:-1337}"

log "Schemathesis reports stored in ${RESULTS_DIR}/schemathesis"
