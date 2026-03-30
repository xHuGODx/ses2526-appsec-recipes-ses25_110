#!/usr/bin/env bash

set -euo pipefail

source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/common.sh"

require_basics
ensure_dirs

"${DAST_DIR}/scripts/run-zap-api.sh"
"${DAST_DIR}/scripts/run-zap-frontend.sh"
