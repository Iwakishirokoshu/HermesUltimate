#!/usr/bin/env bash
set -euo pipefail

display="${DISPLAY:-:99}"

until xdpyinfo -display "${display}" >/dev/null 2>&1; do
  sleep 0.25
done

exec python /opt/vnc-cloak/cloakbrowser-launch.py
