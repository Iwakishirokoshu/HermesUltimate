#!/usr/bin/env bash
set -euo pipefail

vault_path="${HERMES_VAULT_PATH:-$HOME/HermesVault}"

mkdir -p \
  "$vault_path/Wiki/Hot" \
  "$vault_path/Wiki/Warm" \
  "$vault_path/Wiki/Cold" \
  "$vault_path/Wiki/Findings" \
  "$vault_path/Wiki/References/SecondBrain" \
  "$vault_path/Engagements" \
  "$vault_path/Sessions" \
  "$vault_path/.meta"

: > "$vault_path/INDEX.md"
: > "$vault_path/.meta/access.log"
: > "$vault_path/.meta/health.json"

echo "HermesVault initialized at $vault_path"
