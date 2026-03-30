#!/usr/bin/env bash

set -euo pipefail

source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/common.sh"

require_basics
ensure_dirs
require_cmd timeout

ZAP_WORKDIR="/zap/wrk"
ZAP_RUNTIME_DIR="${CACHE_DIR}/zap-runtime"
mkdir -p "${ZAP_RUNTIME_DIR}"
chmod a+rwx "${ZAP_RUNTIME_DIR}" 2>/dev/null || true
ZAP_VOLUME_ARGS=(
  -v "${ZAP_RUNTIME_DIR}:${ZAP_WORKDIR}"
  -v "${GENERATED_DIR}:${ZAP_WORKDIR}/generated"
  -v "${RESULTS_DIR}:${ZAP_WORKDIR}/results"
)

frontend_mode="${ZAP_FRONTEND_MODE:-baseline}"

if [[ "${frontend_mode}" == "full" ]]; then
  log "Running OWASP ZAP Full Scan against ${SCANNER_FRONTEND_BASE_URL}"
  timeout "${ZAP_FRONTEND_TIMEOUT:-20m}" \
  docker run --rm \
    "${HOST_GATEWAY_ARG[@]}" \
    "${ZAP_VOLUME_ARGS[@]}" \
    "${ZAP_IMAGE}" \
    zap-full-scan.py \
      -t "${SCANNER_FRONTEND_BASE_URL}" \
      -d \
      -I \
      -m "${ZAP_FRONTEND_SPIDER_MINUTES:-5}" \
      -T "${ZAP_FRONTEND_MAX_TIME_MINUTES:-20}" \
      -r "results/zap/frontend/report.html" \
      -J "results/zap/frontend/report.json"
else
  log "Running OWASP ZAP Baseline Scan against ${SCANNER_FRONTEND_BASE_URL}"
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
      -T "${ZAP_FRONTEND_MAX_TIME_MINUTES:-15}" \
      -r "results/zap/frontend/report.html" \
      -J "results/zap/frontend/report.json"
fi

log "ZAP frontend reports stored in ${RESULTS_DIR}/zap/frontend"
