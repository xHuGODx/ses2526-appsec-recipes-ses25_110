#!/usr/bin/env bash

set -euo pipefail

source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/common.sh"

require_basics
ensure_dirs
require_cmd timeout

if [[ ! -f "${OPENAPI_PATH}" ]]; then
  printf 'OpenAPI file not found: %s\nRun export-openapi.sh first.\n' "${OPENAPI_PATH}" >&2
  exit 1
fi

ZAP_WORKDIR="/zap/wrk"
ZAP_RUNTIME_DIR="${CACHE_DIR}/zap-runtime"
mkdir -p "${ZAP_RUNTIME_DIR}"
chmod a+rwx "${ZAP_RUNTIME_DIR}" 2>/dev/null || true
ZAP_VOLUME_ARGS=(
  -v "${ZAP_RUNTIME_DIR}:${ZAP_WORKDIR}"
  -v "${GENERATED_DIR}:${ZAP_WORKDIR}/generated"
  -v "${RESULTS_DIR}:${ZAP_WORKDIR}/results"
)

log "Running OWASP ZAP against ${OPENAPI_PATH}"
timeout "${ZAP_API_TIMEOUT:-20m}" \
docker run --rm \
  "${HOST_GATEWAY_ARG[@]}" \
  "${ZAP_VOLUME_ARGS[@]}" \
  "${ZAP_IMAGE}" \
  zap-api-scan.py \
    -t "${ZAP_WORKDIR}/generated/openapi.json" \
    -f openapi \
    -O "${SCANNER_TARGET_BASE_URL}" \
    -a \
    -d \
    -I \
    -T "${ZAP_MAX_TIME_MINUTES:-15}" \
    -r "${ZAP_WORKDIR}/results/zap/api/report.html" \
    -w "${ZAP_WORKDIR}/results/zap/api/report.md" \
    -x "${ZAP_WORKDIR}/results/zap/api/report.xml" \
    -J "${ZAP_WORKDIR}/results/zap/api/report.json"

log "Running OWASP ZAP baseline scan against ${SCANNER_FRONTEND_BASE_URL}"
timeout "${ZAP_FRONTEND_TIMEOUT:-12m}" \
docker run --rm \
  "${HOST_GATEWAY_ARG[@]}" \
  "${ZAP_VOLUME_ARGS[@]}" \
  "${ZAP_IMAGE}" \
  zap-baseline.py \
    -t "${SCANNER_FRONTEND_BASE_URL}" \
    -a \
    -d \
    -I \
    -m "${ZAP_FRONTEND_SPIDER_MINUTES:-3}" \
    -T "${ZAP_MAX_TIME_MINUTES:-15}" \
    -r "results/zap/frontend/report.html" \
    -w "results/zap/frontend/report.md" \
    -x "results/zap/frontend/report.xml" \
    -J "results/zap/frontend/report.json"

log "ZAP reports stored in ${RESULTS_DIR}/zap"
