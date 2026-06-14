#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd -P)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." >/dev/null 2>&1 && pwd -P)"

STACK_DIR="${HERMES_STACK_DIR:-$REPO_ROOT/stack}"
TEMPLATE_PATH="${HERMES_STACK_TEMPLATE:-$REPO_ROOT/stack/.env.template}"
ENV_FILE="${HERMES_STACK_ENV:-$HOME/.hermes/stack.env}"
VAULT_PATH="${HERMES_VAULT_PATH:-$HOME/HermesVault}"
VNC_PASSWORD_VALUE="${VNC_PASSWORD:-}"

usage() {
  cat <<'USAGE'
Generate Hermes Ultimate stack environment.

Usage:
  scripts/gen-env.sh [--vnc-password <pw>] [--vault-path <path>]
USAGE
}

log() {
  printf '[hermes-gen-env] %s\n' "$*"
}

warn() {
  printf '[hermes-gen-env] WARN: %s\n' "$*" >&2
}

die() {
  printf '[hermes-gen-env] ERROR: %s\n' "$*" >&2
  exit 1
}

expand_path() {
  case "$1" in
    "~") printf '%s\n' "$HOME" ;;
    "~/"*) printf '%s/%s\n' "$HOME" "${1#~/}" ;;
    *) printf '%s\n' "$1" ;;
  esac
}

parse_args() {
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --vnc-password)
        [[ $# -ge 2 ]] || die "--vnc-password requires a value"
        VNC_PASSWORD_VALUE="$2"
        shift 2
        ;;
      --vault-path)
        [[ $# -ge 2 ]] || die "--vault-path requires a value"
        VAULT_PATH="$2"
        shift 2
        ;;
      -h|--help)
        usage
        exit 0
        ;;
      *)
        die "unknown argument: $1"
        ;;
    esac
  done

  VAULT_PATH="$(expand_path "$VAULT_PATH")"
  ENV_FILE="$(expand_path "$ENV_FILE")"
}

rand_hex() {
  local bytes="$1"
  if command -v openssl >/dev/null 2>&1; then
    openssl rand -hex "$bytes"
    return
  fi
  if command -v python3 >/dev/null 2>&1; then
    python3 -c 'import secrets, sys; print(secrets.token_hex(int(sys.argv[1])))' "$bytes"
    return
  fi
  date +%s%N | cksum | awk '{print $1}'
}

set_env_var() {
  local key="$1"
  local value="$2"
  local file="$3"
  local tmp
  tmp="$(mktemp)"
  awk -v key="$key" -v value="$value" '
    BEGIN { seen = 0 }
    $0 ~ "^" key "=" {
      print key "=" value
      seen = 1
      next
    }
    { print }
    END {
      if (!seen) {
        print key "=" value
      }
    }
  ' "$file" > "$tmp"
  mv "$tmp" "$file"
}

ensure_stack_env() {
  [[ -f "$TEMPLATE_PATH" ]] || die "template not found: $TEMPLATE_PATH"
  mkdir -p "$(dirname "$ENV_FILE")"

  if [[ ! -f "$ENV_FILE" ]]; then
    log "creating $ENV_FILE from $TEMPLATE_PATH"
    cp "$TEMPLATE_PATH" "$ENV_FILE"
    set_env_var "NINEROUTER_JWT_SECRET" "$(rand_hex 32)" "$ENV_FILE"
    set_env_var "NINEROUTER_INITIAL_PASSWORD" "$(rand_hex 16)" "$ENV_FILE"
    set_env_var "NINEROUTER_API_KEY" "$(rand_hex 32)" "$ENV_FILE"
    set_env_var "NINEROUTER_BASE_URL" "http://localhost:20128/v1" "$ENV_FILE"
    set_env_var "NEO4J_PASSWORD" "$(rand_hex 16)" "$ENV_FILE"
    if [[ -z "$VNC_PASSWORD_VALUE" ]]; then
      VNC_PASSWORD_VALUE="$(rand_hex 12)"
    fi
    set_env_var "VNC_PASSWORD" "$VNC_PASSWORD_VALUE" "$ENV_FILE"
    set_env_var "HERMES_VAULT_PATH" "$VAULT_PATH" "$ENV_FILE"
    set_env_var "HERMES_BROWSER_PROFILES" "$HOME/.hermes/browser-profiles" "$ENV_FILE"
    set_env_var "HERMES_CLOAK_MANAGER_PATH" "$HOME/.hermes/cloak" "$ENV_FILE"
    set_env_var "CLOAK_CDP_URL" "auto" "$ENV_FILE"
    set_env_var "BROWSER_CDP_URL" "auto" "$ENV_FILE"
    set_env_var "CLOAK_PROFILE" "default" "$ENV_FILE"
    set_env_var "CLOAK_DEBUG_PORT" "9223" "$ENV_FILE"
    set_env_var "CLOAK_HEADLESS" "false" "$ENV_FILE"
    set_env_var "CLOAK_HUMANIZE" "true" "$ENV_FILE"
    set_env_var "CLOAK_GEOIP" "false" "$ENV_FILE"
    set_env_var "CLOAK_STEALTH_ARGS" "true" "$ENV_FILE"
    set_env_var "CLOAK_VIEWPORT" "1920x1080" "$ENV_FILE"
    set_env_var "CLOAK_SYNC_SCREEN_FINGERPRINT" "true" "$ENV_FILE"
  else
    log "$ENV_FILE already exists; leaving existing secrets unchanged"
  fi

  chmod 600 "$ENV_FILE"
}

ensure_stack_symlink() {
  mkdir -p "$STACK_DIR"
  local link_path="$STACK_DIR/.env"

  if [[ -e "$link_path" && ! -L "$link_path" ]]; then
    warn "$link_path exists and is not a symlink; leaving it unchanged"
    return
  fi

  ln -sfn "$ENV_FILE" "$link_path"
  log "linked $link_path -> $ENV_FILE"
}

main() {
  parse_args "$@"
  ensure_stack_env
  ensure_stack_symlink
  log "stack environment ready"
}

main "$@"
