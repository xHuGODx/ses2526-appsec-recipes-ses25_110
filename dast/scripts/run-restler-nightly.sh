#!/usr/bin/env bash

set -euo pipefail

source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/common.sh"

require_basics
setup_cleanup_trap

log "Cleaning previous nightly outputs"
clean_generated
clean_results
ensure_dirs

start_or_reuse_app_stack

"${DAST_DIR}/scripts/wait-for-api.sh"
"${DAST_DIR}/scripts/wait-for-frontend.sh"
"${DAST_DIR}/scripts/export-openapi.sh"
"${DAST_DIR}/scripts/run-restler.sh"
"${DAST_DIR}/scripts/run-restler-deep.sh"
python3 "${DAST_DIR}/scripts/build-findings-manifest.py"

log "Nightly RESTler flow complete. Reports are in ${RESULTS_DIR}"
