#!/usr/bin/env bash

set -euo pipefail

source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/common.sh"

require_basics

WAIT_SECONDS="${WAIT_SECONDS:-180}"
deadline=$((SECONDS + WAIT_SECONDS))

log "Waiting for frontend at ${FRONTEND_READY_URL}"
until curl --fail --silent --show-error "${FRONTEND_READY_URL}" >/dev/null 2>&1; do
  if (( SECONDS >= deadline )); then
    printf 'Timed out waiting for frontend at %s\n' "${FRONTEND_READY_URL}" >&2
    exit 1
  fi
  sleep 2
done

log "Frontend is reachable"
