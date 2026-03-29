#!/usr/bin/env bash

set -euo pipefail

source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/common.sh"

require_basics
setup_cleanup_trap

log "Cleaning previous scanner outputs"
clean_generated
clean_results
ensure_dirs

failed_steps=0

run_step() {
  local name="$1"
  shift

  if ! "$@"; then
    log "${name} exited non-zero; continuing so the remaining scanners still run"
    failed_steps=$((failed_steps + 1))
  fi
}

start_or_reuse_app_stack

"${DAST_DIR}/scripts/wait-for-api.sh"
"${DAST_DIR}/scripts/wait-for-frontend.sh"
"${DAST_DIR}/scripts/export-openapi.sh"
"${DAST_DIR}/scripts/build-schemathesis-image.sh"
"${DAST_DIR}/scripts/build-restler-image.sh"
run_step "ZAP" "${DAST_DIR}/scripts/run-zap.sh"
run_step "Schemathesis" "${DAST_DIR}/scripts/run-schemathesis.sh"
run_step "RESTler" "${DAST_DIR}/scripts/run-restler.sh"
run_step "Manifest build" python3 "${DAST_DIR}/scripts/build-findings-manifest.py"

if (( failed_steps > 0 )); then
  log "DAST run completed with ${failed_steps} non-zero step(s). Reports are in ${RESULTS_DIR}"
  exit 1
fi

log "DAST run complete. Reports are in ${RESULTS_DIR}"
