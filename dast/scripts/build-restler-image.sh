#!/usr/bin/env bash

set -euo pipefail

source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/common.sh"

require_basics
require_cmd git

if docker image inspect "${RESTLER_IMAGE}" >/dev/null 2>&1; then
  log "RESTler image already present: ${RESTLER_IMAGE}"
  exit 0
fi

restler_src_dir="${CACHE_DIR}/restler-src"

rm -rf "${restler_src_dir}"

log "Cloning RESTler source at ${RESTLER_REF}"
git clone https://github.com/microsoft/restler-fuzzer.git "${restler_src_dir}" >/dev/null 2>&1
git -C "${restler_src_dir}" checkout "${RESTLER_REF}" >/dev/null 2>&1

log "Building RESTler image ${RESTLER_IMAGE} from ${RESTLER_REF}"
docker build \
  -t "${RESTLER_IMAGE}" \
  "${restler_src_dir}"
