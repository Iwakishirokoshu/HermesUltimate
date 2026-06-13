#!/usr/bin/env bash
set -euo pipefail

base_url="${NINEROUTER_PUBLIC_URL:-http://localhost:20128}"

curl -fsS "${base_url}/health" >/dev/null || curl -fsS "${base_url}/api/health" >/dev/null