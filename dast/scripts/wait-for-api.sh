#!/usr/bin/env bash

set -euo pipefail

source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/common.sh"

require_basics

WAIT_SECONDS="${WAIT_SECONDS:-180}"
deadline=$((SECONDS + WAIT_SECONDS))

log "Waiting for API schema at ${TARGET_SCHEMA_URL}"
until curl --fail --silent --show-error "${TARGET_SCHEMA_URL}" >/dev/null 2>&1; do
  if (( SECONDS >= deadline )); then
    printf 'Timed out waiting for API schema at %s\n' "${TARGET_SCHEMA_URL}" >&2
    exit 1
  fi
  sleep 2
done

log "Waiting for API endpoint at ${TARGET_READY_URL}"
until curl --fail --silent --show-error "${TARGET_READY_URL}" >/dev/null 2>&1; do
  if (( SECONDS >= deadline )); then
    printf 'Timed out waiting for API endpoint at %s\n' "${TARGET_READY_URL}" >&2
    exit 1
  fi
  sleep 2
done

log "API is reachable"
