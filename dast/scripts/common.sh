#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
DAST_DIR="${ROOT_DIR}/dast"
CONFIG_DIR="${DAST_DIR}/config"
GENERATED_DIR="${DAST_DIR}/generated"
RESULTS_DIR="${DAST_DIR}/results"
CACHE_DIR="${DAST_DIR}/cache"
APP_REPO_DIR="${APP_REPO_DIR:-${ROOT_DIR}/../ses}"
APP_COMPOSE_FILE="${APP_COMPOSE_FILE:-${APP_REPO_DIR}/docker-compose.yml}"
COMPOSE_PROJECT_NAME="${COMPOSE_PROJECT_NAME:-ses-dast}"

TARGET_BASE_URL="${TARGET_BASE_URL:-http://localhost:8080}"
TARGET_SCHEMA_URL="${TARGET_SCHEMA_URL:-${TARGET_BASE_URL}/v3/api-docs}"
TARGET_READY_URL="${TARGET_READY_URL:-${TARGET_BASE_URL}/api/pizzerias}"
FRONTEND_BASE_URL="${FRONTEND_BASE_URL:-http://localhost:5173}"
FRONTEND_READY_URL="${FRONTEND_READY_URL:-${FRONTEND_BASE_URL}}"
SCANNER_TARGET_BASE_URL="${SCANNER_TARGET_BASE_URL:-http://host.docker.internal:8080}"
SCANNER_TARGET_SCHEMA_URL="${SCANNER_TARGET_SCHEMA_URL:-${SCANNER_TARGET_BASE_URL}/v3/api-docs}"
SCANNER_FRONTEND_BASE_URL="${SCANNER_FRONTEND_BASE_URL:-http://host.docker.internal:5173}"

OPENAPI_PATH="${OPENAPI_PATH:-${GENERATED_DIR}/openapi.json}"
RESTLER_SETTINGS_PATH="${RESTLER_SETTINGS_PATH:-${GENERATED_DIR}/restler-engine-settings.json}"

ZAP_IMAGE="${ZAP_IMAGE:-zaproxy/zap-stable:2.17.0}"
SCHEMATHESIS_IMAGE="${SCHEMATHESIS_IMAGE:-ses-schemathesis:4.14.2}"
RESTLER_IMAGE="${RESTLER_IMAGE:-ses-restler:6d984dee}"
RESTLER_REF="${RESTLER_REF:-6d984deedbc54aad957fa3da0c7e9e5df23a2aee}"

HOST_GATEWAY_ARG=(--add-host "host.docker.internal:host-gateway")
RESTLER_TRANSPORT_ARGS=()
if [[ "${SCANNER_TARGET_BASE_URL}" != https://* ]]; then
  RESTLER_TRANSPORT_ARGS=(--no_ssl)
fi

log() {
  printf '[dast] %s\n' "$*"
}

bool_enabled() {
  case "${1:-}" in
    1|true|TRUE|yes|YES|on|ON)
      return 0
      ;;
    *)
      return 1
      ;;
  esac
}

require_cmd() {
  if ! command -v "$1" >/dev/null 2>&1; then
    printf 'Missing required command: %s\n' "$1" >&2
    exit 1
  fi
}

ensure_dirs() {
  mkdir -p \
    "${GENERATED_DIR}" \
    "${RESULTS_DIR}" \
    "${RESULTS_DIR}/zap/api" \
    "${RESULTS_DIR}/zap/frontend" \
    "${RESULTS_DIR}/schemathesis" \
    "${RESULTS_DIR}/restler" \
    "${RESULTS_DIR}/llm" \
    "${CACHE_DIR}"

  chmod -R a+rwX \
    "${GENERATED_DIR}" \
    "${RESULTS_DIR}" \
    "${CACHE_DIR}"
}

clean_dir_contents() {
  local dir="$1"
  mkdir -p "${dir}"

  if find "${dir}" -mindepth 1 ! -name '.gitkeep' -exec rm -rf -- {} + 2>/dev/null; then
    touch "${dir}/.gitkeep"
    return 0
  fi

  log "Local cleanup failed for ${dir}; retrying via Docker for container-owned files"
  docker run --rm \
    -v "${dir}:/work" \
    alpine:3.20 \
    sh -lc 'find /work -mindepth 1 ! -name .gitkeep -exec rm -rf -- {} +'
  touch "${dir}/.gitkeep"
}

clean_generated() {
  clean_dir_contents "${GENERATED_DIR}"
}

clean_results() {
  clean_dir_contents "${RESULTS_DIR}"
}

clean_path() {
  local path="$1"
  local parent_dir
  local target_name

  parent_dir="$(dirname "${path}")"
  target_name="$(basename "${path}")"
  mkdir -p "${parent_dir}"

  if rm -rf -- "${path}" 2>/dev/null; then
    return 0
  fi

  log "Local cleanup failed for ${path}; retrying via Docker for container-owned files"
  docker run --rm \
    -e TARGET_NAME="${target_name}" \
    -v "${parent_dir}:/work" \
    alpine:3.20 \
    sh -lc 'rm -rf -- "/work/${TARGET_NAME}"'
}

clean_paths() {
  local path
  for path in "$@"; do
    clean_path "${path}"
  done
}

require_basics() {
  require_cmd docker
  if ! docker compose version >/dev/null 2>&1; then
    printf 'Missing required command: docker compose\n' >&2
    exit 1
  fi
  require_cmd curl
  require_cmd python3
}

require_app_checkout() {
  if [[ ! -d "${APP_REPO_DIR}" ]]; then
    printf 'Application repository directory not found: %s\n' "${APP_REPO_DIR}" >&2
    exit 1
  fi

  if [[ ! -f "${APP_COMPOSE_FILE}" ]]; then
    printf 'Application docker-compose file not found: %s\n' "${APP_COMPOSE_FILE}" >&2
    exit 1
  fi
}

compose() {
  require_app_checkout
  docker compose -f "${APP_COMPOSE_FILE}" -p "${COMPOSE_PROJECT_NAME}" "$@"
}

setup_cleanup_trap() {
  if bool_enabled "${AUTO_STOP_STACK:-false}" && ! bool_enabled "${SKIP_START_APP_STACK:-false}"; then
    trap 'stop_app_stack' EXIT
  fi
}

start_or_reuse_app_stack() {
  if bool_enabled "${SKIP_START_APP_STACK:-false}"; then
    log "Skipping application startup because SKIP_START_APP_STACK=true"
    return 0
  fi

  start_app_stack
}

start_app_stack() {
  require_app_checkout

  if ! require_free_ports 8080 5173; then
    log "Ports 8080 and/or 5173 are already in use; attempting to reuse the existing Compose stack"
  fi

  log "Starting application stack from ${APP_COMPOSE_FILE}"
  if ! compose up -d --build mysql backend frontend; then
    printf 'This DAST setup expects the target docker-compose to publish the backend on 8080 and the frontend on 5173.\n' >&2
    printf 'Adjust the target compose file or override the target URLs before running the scan.\n' >&2
    exit 1
  fi
}

stop_app_stack() {
  if [[ ! -f "${APP_COMPOSE_FILE}" ]]; then
    return 0
  fi

  log "Stopping application stack from ${APP_COMPOSE_FILE}"
  compose down -v --remove-orphans
}

port_is_available() {
  python3 - "$1" <<'PY'
import socket
import sys

port = int(sys.argv[1])
sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
try:
    sock.bind(("0.0.0.0", port))
except OSError:
    raise SystemExit(1)
finally:
    sock.close()
PY
}

require_free_ports() {
  local port
  for port in "$@"; do
    if ! port_is_available "${port}"; then
      printf 'Required host port %s is already in use.\n' "${port}" >&2
      return 1
    fi
  done
}
