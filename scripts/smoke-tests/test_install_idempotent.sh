#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." >/dev/null 2>&1 && pwd -P)"
INSTALLER="${HERMES_INSTALLER:-$ROOT_DIR/install.sh}"
PROFILE="${HERMES_TEST_PROFILE:-slim}"
VNC_PASSWORD="${HERMES_TEST_VNC_PASSWORD:-test123}"
LOG_DIR="${HERMES_TEST_LOG_DIR:-$ROOT_DIR/.pytest_cache/install-idempotent}"

mkdir -p "$LOG_DIR"

run_install() {
  local label="$1"
  local log_file="$LOG_DIR/${label}.log"
  local start
  local end
  local duration

  start="$(date +%s)"
  if ! bash "$INSTALLER" \
    --mode local \
    --profile "$PROFILE" \
    --non-interactive \
    --vnc-password "$VNC_PASSWORD" >"$log_file" 2>&1; then
    echo "install ${label} failed; last 120 log lines:" >&2
    tail -n 120 "$log_file" >&2 || true
    return 1
  fi
  end="$(date +%s)"
  duration=$((end - start))
  echo "$duration"
}

first_duration="$(run_install first)"
second_duration="$(run_install second)"

echo "first_duration=${first_duration}s"
echo "second_duration=${second_duration}s"

if (( second_duration > first_duration )); then
  echo "WARN: second installer run was not faster than the first run" >&2
fi

echo "install idempotency smoke passed"
