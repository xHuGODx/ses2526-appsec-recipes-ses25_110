#!/usr/bin/env bash

set -euo pipefail

source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/common.sh"

require_basics
ensure_dirs

if [[ ! -f "${OPENAPI_PATH}" ]]; then
  printf 'OpenAPI file not found: %s\nRun export-openapi.sh first.\n' "${OPENAPI_PATH}" >&2
  exit 1
fi

log "Running OWASP ZAP against ${OPENAPI_PATH}"
docker run --rm \
  "${HOST_GATEWAY_ARG[@]}" \
  -v "${DAST_DIR}:/zap/wrk" \
  "${ZAP_IMAGE}" \
  zap-api-scan.py \
    -t /zap/wrk/generated/openapi.json \
    -f openapi \
    -O "${SCANNER_TARGET_BASE_URL}" \
    -a \
    -d \
    -I \
    -T "${ZAP_MAX_TIME_MINUTES:-15}" \
    -r /zap/wrk/results/zap/api/report.html \
    -w /zap/wrk/results/zap/api/report.md \
    -x /zap/wrk/results/zap/api/report.xml \
    -J /zap/wrk/results/zap/api/report.json

log "Running OWASP ZAP baseline scan against ${SCANNER_FRONTEND_BASE_URL}"
docker run --rm \
  "${HOST_GATEWAY_ARG[@]}" \
  -v "${DAST_DIR}:/zap/wrk" \
  "${ZAP_IMAGE}" \
  zap-baseline.py \
    -t "${SCANNER_FRONTEND_BASE_URL}" \
    -a \
    -d \
    -I \
    -j \
    -m "${ZAP_FRONTEND_SPIDER_MINUTES:-3}" \
    -T "${ZAP_MAX_TIME_MINUTES:-15}" \
    -r results/zap/frontend/report.html \
    -w results/zap/frontend/report.md \
    -x results/zap/frontend/report.xml \
    -J results/zap/frontend/report.json

log "ZAP reports stored in ${RESULTS_DIR}/zap"
