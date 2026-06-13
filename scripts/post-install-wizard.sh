#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd -P)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." >/dev/null 2>&1 && pwd -P)"

ENV_FILE="${HERMES_STACK_ENV:-$HOME/.hermes/stack.env}"
GATEWAY_FILE="${HERMES_GATEWAY_CONFIG:-$HOME/.hermes/gateway.yaml}"
CONFIG_FILE="${HERMES_CONFIG_FILE:-$HOME/.hermes/config.toml}"
SOULS_DIR="${HERMES_SOULS_DIR:-$HOME/.hermes/souls}"
WITH_SECOND_BOT=0

usage() {
  cat <<'USAGE'
Hermes Ultimate post-install wizard

Usage:
  scripts/post-install-wizard.sh [--with-second-bot]
USAGE
}

log() {
  printf '[hermes-wizard] %s\n' "$*" >&2
}

warn() {
  printf '[hermes-wizard] WARN: %s\n' "$*" >&2
}

die() {
  printf '[hermes-wizard] ERROR: %s\n' "$*" >&2
  exit 1
}

parse_args() {
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --with-second-bot)
        WITH_SECOND_BOT=1
        shift
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
}

ui_input() {
  local title="$1"
  local prompt="$2"
  local default="${3:-}"
  local value=""

  if command -v whiptail >/dev/null 2>&1; then
    value="$(whiptail --title "$title" --inputbox "$prompt" 12 78 "$default" 3>&1 1>&2 2>&3)" || return 1
  elif command -v dialog >/dev/null 2>&1; then
    value="$(dialog --title "$title" --inputbox "$prompt" 12 78 "$default" 3>&1 1>&2 2>&3)" || return 1
  else
    printf '%s\n%s\n> ' "$title" "$prompt" >&2
    IFS= read -r value
    if [[ -z "$value" && -n "$default" ]]; then
      value="$default"
    fi
  fi

  printf '%s\n' "$value"
}

ui_yesno() {
  local title="$1"
  local prompt="$2"

  if command -v whiptail >/dev/null 2>&1; then
    whiptail --title "$title" --yesno "$prompt" 12 78
    return $?
  fi
  if command -v dialog >/dev/null 2>&1; then
    dialog --title "$title" --yesno "$prompt" 12 78
    return $?
  fi

  local answer
  printf '%s\n%s [y/N]\n> ' "$title" "$prompt" >&2
  IFS= read -r answer
  case "${answer,,}" in
    y|yes) return 0 ;;
    *) return 1 ;;
  esac
}

get_env_var() {
  local key="$1"
  local file="${2:-$ENV_FILE}"
  if [[ -f "$file" ]]; then
    grep -E "^${key}=" "$file" | tail -n 1 | cut -d= -f2- || true
  fi
}

set_env_var() {
  local key="$1"
  local value="$2"
  local file="${3:-$ENV_FILE}"
  local tmp
  mkdir -p "$(dirname "$file")"
  touch "$file"
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
  chmod 600 "$file" || true
}

python_bin() {
  if [[ -x "$REPO_ROOT/.venv/bin/python" ]]; then
    printf '%s\n' "$REPO_ROOT/.venv/bin/python"
  elif [[ -x "$REPO_ROOT/.venv/Scripts/python.exe" ]]; then
    printf '%s\n' "$REPO_ROOT/.venv/Scripts/python.exe"
  elif command -v python3 >/dev/null 2>&1; then
    command -v python3
  else
    command -v python
  fi
}

hermes_bin() {
  if [[ -x "$REPO_ROOT/.venv/bin/hermes" ]]; then
    printf '%s\n' "$REPO_ROOT/.venv/bin/hermes"
  elif [[ -x "$REPO_ROOT/.venv/Scripts/hermes.exe" ]]; then
    printf '%s\n' "$REPO_ROOT/.venv/Scripts/hermes.exe"
  elif command -v hermes >/dev/null 2>&1; then
    command -v hermes
  else
    printf '%s\n' ""
  fi
}

validate_telegram_token() {
  local token="$1"
  local response
  response="$(curl -fsS "https://api.telegram.org/bot${token}/getMe")" || return 1
  LAST_TELEGRAM_RESPONSE="$response"
  TELEGRAM_VALIDATE_RESPONSE="$LAST_TELEGRAM_RESPONSE" "$(python_bin)" - <<'PY'
import json
import os
import sys

try:
    data = json.loads(os.environ["TELEGRAM_VALIDATE_RESPONSE"])
except Exception:
    sys.exit(1)
sys.exit(0 if data.get("ok") is True else 1)
PY
}

telegram_username_from_last_response() {
  TELEGRAM_VALIDATE_RESPONSE="${LAST_TELEGRAM_RESPONSE:-}" "$(python_bin)" - <<'PY'
import json
import os

try:
    data = json.loads(os.environ.get("TELEGRAM_VALIDATE_RESPONSE", "{}"))
    print(data.get("result", {}).get("username", ""))
except Exception:
    print("")
PY
}

prompt_valid_token() {
  local label="$1"
  local env_key="$2"
  local current
  current="$(get_env_var "$env_key")"
  while true; do
    local token
    token="$(ui_input "Telegram" "Enter ${label} Telegram bot token. It will be validated via getMe." "$current")"
    [[ -n "$token" ]] || die "${label} token is required"
    if validate_telegram_token "$token"; then
      set_env_var "$env_key" "$token"
      local username
      username="$(telegram_username_from_last_response)"
      if [[ -n "$username" ]]; then
        log "${label} bot validated: @$username"
      else
        log "${label} bot validated"
      fi
      printf '%s\n' "$token"
      return
    fi
    warn "Telegram token validation failed for ${label}; try again"
  done
}

detect_allowed_user_id() {
  local token="$1"
  local response
  response="$(curl -fsS "https://api.telegram.org/bot${token}/getUpdates")" || return 1
  TELEGRAM_UPDATES_RESPONSE="$response" "$(python_bin)" - <<'PY'
import json
import os

try:
    data = json.loads(os.environ["TELEGRAM_UPDATES_RESPONSE"])
    for item in reversed(data.get("result", [])):
        message = item.get("message") or item.get("edited_message") or {}
        user = message.get("from") or {}
        uid = user.get("id")
        if uid is not None:
            print(uid)
            raise SystemExit(0)
except Exception:
    pass
raise SystemExit(1)
PY
}

prompt_allowed_user() {
  local token="$1"
  local label="$2"
  local detected=""

  log "Ask the allowed Telegram user to send /start to the ${label} bot now."
  if detected="$(detect_allowed_user_id "$token")"; then
    ui_yesno "Telegram" "Use detected Telegram user id ${detected} for ${label} allowed_users?" && {
      printf '%s\n' "$detected"
      return
    }
  fi

  local user_id
  user_id="$(ui_input "Telegram" "Enter Telegram numeric user id for ${label} allowed_users." "$detected")"
  [[ -n "$user_id" ]] || die "Telegram user id is required"
  printf '%s\n' "$user_id"
}

render_gateway_yaml() {
  local main_token="$1"
  local red_token="$2"
  local main_user="$3"
  local red_user="$4"
  local template="$REPO_ROOT/stack/templates/gateway.yaml.j2"
  [[ -f "$template" ]] || die "gateway template not found: $template"
  mkdir -p "$(dirname "$GATEWAY_FILE")"

  GATEWAY_TEMPLATE="$template" \
  GATEWAY_OUTPUT="$GATEWAY_FILE" \
  TELEGRAM_BOT_TOKEN="$main_token" \
  TELEGRAM_RED_BOT_TOKEN="$red_token" \
  TELEGRAM_ALLOWED_USERS="$main_user" \
  TELEGRAM_RED_ALLOWED_USERS="$red_user" \
  WITH_SECOND_BOT="$WITH_SECOND_BOT" \
  "$(python_bin)" - <<'PY'
from pathlib import Path
import os

from jinja2 import Template

template = Path(os.environ["GATEWAY_TEMPLATE"]).read_text(encoding="utf-8")
out = Template(template).render(
    telegram_bot_token=os.environ["TELEGRAM_BOT_TOKEN"],
    telegram_red_bot_token=os.environ.get("TELEGRAM_RED_BOT_TOKEN", ""),
    telegram_allowed_users=[x for x in os.environ.get("TELEGRAM_ALLOWED_USERS", "").split(",") if x],
    telegram_red_allowed_users=[x for x in os.environ.get("TELEGRAM_RED_ALLOWED_USERS", "").split(",") if x],
    with_second_bot=os.environ.get("WITH_SECOND_BOT") == "1",
)
Path(os.environ["GATEWAY_OUTPUT"]).write_text(out, encoding="utf-8")
PY

  "$(python_bin)" - "$GATEWAY_FILE" <<'PY'
from pathlib import Path
import sys
import yaml

yaml.safe_load(Path(sys.argv[1]).read_text(encoding="utf-8"))
PY
  chmod 600 "$GATEWAY_FILE" || true
  log "wrote $GATEWAY_FILE"
}

open_or_print_9router() {
  local password
  password="$(get_env_var NINEROUTER_INITIAL_PASSWORD)"
  local url
  url="$(get_env_var NINEROUTER_PUBLIC_URL)"
  [[ -n "$url" ]] || url="http://localhost:20128"

  cat <<MSG

9router setup:
  URL:      $url
  Login:    admin
  Password: $password

Add your LLM providers in the 9router UI, then return here.
MSG

  if command -v xdg-open >/dev/null 2>&1; then
    xdg-open "$url" >/dev/null 2>&1 || true
  elif command -v open >/dev/null 2>&1; then
    open "$url" >/dev/null 2>&1 || true
  fi

  ui_input "9router" "Press Enter after providers are configured." "" >/dev/null
}

copy_default_souls() {
  if ui_yesno "Souls" "Apply default Hermes souls (default + red) into $SOULS_DIR?"; then
    mkdir -p "$SOULS_DIR"
    cp -n "$REPO_ROOT"/souls/*.yaml "$SOULS_DIR"/
    log "default souls copied to $SOULS_DIR"
  else
    log "custom souls selected; leaving $SOULS_DIR unchanged"
  fi
}

render_config_toml() {
  local template="$REPO_ROOT/stack/templates/hermes-config.toml.j2"
  [[ -f "$template" ]] || die "Hermes config template not found: $template"
  mkdir -p "$(dirname "$CONFIG_FILE")"

  local ninerouter_url
  local ninerouter_api_key
  ninerouter_url="$(get_env_var NINEROUTER_PUBLIC_URL)"
  [[ -n "$ninerouter_url" ]] || ninerouter_url="$(get_env_var NINEROUTER_URL)"
  [[ -n "$ninerouter_url" ]] || ninerouter_url="http://localhost:20128"
  ninerouter_api_key="$(get_env_var NINEROUTER_API_KEY)"

  HERMES_CONFIG_TEMPLATE="$template" \
  HERMES_CONFIG_OUTPUT="$CONFIG_FILE" \
  NINEROUTER_URL="$ninerouter_url" \
  NINEROUTER_API_KEY="$ninerouter_api_key" \
  "$(python_bin)" - <<'PY'
from pathlib import Path
import os

from jinja2 import Template

out = Template(Path(os.environ["HERMES_CONFIG_TEMPLATE"]).read_text(encoding="utf-8")).render(
    ninerouter_url=os.environ["NINEROUTER_URL"],
    ninerouter_api_key=os.environ["NINEROUTER_API_KEY"],
)
Path(os.environ["HERMES_CONFIG_OUTPUT"]).write_text(out, encoding="utf-8")
PY
  chmod 600 "$CONFIG_FILE" || true
  log "wrote $CONFIG_FILE"
}

run_final_setup() {
  local hermes
  hermes="$(hermes_bin)"
  if [[ -z "$hermes" ]]; then
    warn "hermes executable not found; skipping hermes setup --portal"
    return
  fi
  log "running hermes setup --portal"
  "$hermes" setup --portal || warn "hermes setup --portal returned non-zero; inspect output above"
}

main() {
  parse_args "$@"
  [[ -f "$ENV_FILE" ]] || die "$ENV_FILE is missing; run scripts/gen-env.sh first"

  local main_token
  local red_token=""
  local main_user
  local red_user=""

  main_token="$(prompt_valid_token "main" TELEGRAM_BOT_TOKEN)"
  main_user="$(prompt_allowed_user "$main_token" "main")"

  if [[ "$WITH_SECOND_BOT" -eq 1 ]]; then
    red_token="$(prompt_valid_token "red" TELEGRAM_RED_BOT_TOKEN)"
    red_user="$(prompt_allowed_user "$red_token" "red")"
  fi

  render_gateway_yaml "$main_token" "$red_token" "$main_user" "$red_user"
  open_or_print_9router
  copy_default_souls
  render_config_toml
  run_final_setup
  log "post-install wizard complete"
}

if [[ "${BASH_SOURCE[0]}" == "$0" ]]; then
  main "$@"
fi
