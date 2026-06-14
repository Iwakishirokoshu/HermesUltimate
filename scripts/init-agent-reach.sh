#!/usr/bin/env bash
set -euo pipefail

agent_reach_bin="${AGENT_REACH_BIN:-agent-reach}"

if ! command -v "$agent_reach_bin" >/dev/null 2>&1; then
  if [[ -x ".venv/Scripts/agent-reach.exe" ]]; then
    agent_reach_bin="$(pwd)/.venv/Scripts/agent-reach.exe"
  elif [[ -x ".venv/bin/agent-reach" ]]; then
    agent_reach_bin="$(pwd)/.venv/bin/agent-reach"
  fi
fi

if ! command -v "$agent_reach_bin" >/dev/null 2>&1 && [[ ! -x "$agent_reach_bin" ]]; then
  echo "agent-reach not found. Install hermes with: uv pip install -e \".[all]\"" >&2
  exit 1
fi

hermes_home="${HERMES_HOME:-$HOME/.hermes}"
status_file="$hermes_home/reach-status.json"

mkdir -p "$hermes_home"

if "$agent_reach_bin" init --help >/dev/null 2>&1; then
  "$agent_reach_bin" init
else
  echo "agent-reach init is not available; continuing with doctor"
fi

doctor_json="$("$agent_reach_bin" doctor --json)"
printf '%s\n' "$doctor_json" > "$status_file"

python - "$status_file" <<'PY'
import json
import sys
from pathlib import Path

path = Path(sys.argv[1])
data = json.loads(path.read_text(encoding="utf-8"))
if not isinstance(data, dict) or len(data) < 5:
    raise SystemExit(f"reach doctor returned {len(data) if isinstance(data, dict) else 0} channels")
print(f"Agent-Reach status written to {path} ({len(data)} channels)")
PY
