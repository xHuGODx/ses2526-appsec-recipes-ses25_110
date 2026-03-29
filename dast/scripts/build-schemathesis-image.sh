#!/usr/bin/env bash

set -euo pipefail

source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/common.sh"

require_basics

if docker image inspect "${SCHEMATHESIS_IMAGE}" >/dev/null 2>&1; then
  log "Schemathesis image already present: ${SCHEMATHESIS_IMAGE}"
  exit 0
fi

log "Building Schemathesis image ${SCHEMATHESIS_IMAGE}"
docker build \
  -t "${SCHEMATHESIS_IMAGE}" \
  "${DAST_DIR}/docker/schemathesis"
