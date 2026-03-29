#!/usr/bin/env bash

set -euo pipefail

source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/common.sh"

require_basics
ensure_dirs

raw_schema="$(mktemp)"
trap 'rm -f "${raw_schema}"' EXIT

log "Downloading OpenAPI from ${TARGET_SCHEMA_URL}"
curl --fail --silent --show-error "${TARGET_SCHEMA_URL}" > "${raw_schema}"

python3 "${DAST_DIR}/scripts/prepare-openapi.py" "${raw_schema}" "${OPENAPI_PATH}" "${SCANNER_TARGET_BASE_URL}"

log "Normalized OpenAPI written to ${OPENAPI_PATH}"
