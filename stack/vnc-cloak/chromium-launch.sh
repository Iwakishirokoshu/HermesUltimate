#!/usr/bin/env bash
set -euo pipefail

display="${DISPLAY:-:99}"
profile="${CLOAK_PROFILE:-default}"
profile_dir="/profiles/${profile}"

mkdir -p "${profile_dir}"

until xdpyinfo -display "${display}" >/dev/null 2>&1; do
  sleep 0.25
done

exec chromium \
  --no-sandbox \
  --remote-debugging-port=9222 \
  --remote-debugging-address=0.0.0.0 \
  --user-data-dir="${profile_dir}" \
  --window-size=1920,1080 \
  --start-maximized \
  --no-first-run \
  --no-default-browser-check \
  --disable-dev-shm-usage \
  --disable-blink-features=AutomationControlled \
  --disable-features=IsolateOrigins,site-per-process \
  --disable-site-isolation-trials \
  --disable-web-security \
  --password-store=basic \
  --use-mock-keychain \
  about:blank
