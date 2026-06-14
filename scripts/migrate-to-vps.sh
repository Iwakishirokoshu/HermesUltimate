#!/usr/bin/env bash
set -euo pipefail

IFS=$'\n\t'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd -P)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." >/dev/null 2>&1 && pwd -P)"

REMOTE=""
PROFILE="${HERMES_VPS_PROFILE:-slim}"
BRANCH="${HERMES_BRANCH:-main}"
REPO_URL="${HERMES_REPO_URL:-}"
INSTALL_URL="${HERMES_INSTALL_URL:-}"
LOCAL_HERMES_HOME="${HERMES_HOME:-$HOME/.hermes}"
LOCAL_VAULT_PATH="${HERMES_VAULT_PATH:-$HOME/HermesVault}"
REMOTE_HERMES_HOME="${HERMES_REMOTE_HOME:-~/.hermes}"
REMOTE_VAULT_PATH="${HERMES_REMOTE_VAULT_PATH:-~/HermesVault}"
DOMAIN="${HERMES_VPS_DOMAIN:-}"
TELEGRAM_BOT_TOKEN="${TELEGRAM_BOT_TOKEN:-}"
TELEGRAM_RED_BOT_TOKEN="${TELEGRAM_RED_BOT_TOKEN:-}"
WITH_SECOND_BOT=0
NON_INTERACTIVE=1
DRY_RUN=0
SSH_OPTS=()

usage() {
  cat <<'USAGE'
Migrate local Hermes Ultimate state to a VPS and bootstrap production mode.

Usage:
  scripts/migrate-to-vps.sh <user@host> [options]

Options:
  --domain <domain>             Public VPS domain for Telegram webhooks
  --profile <name>              Installer profile: slim|full|ultra-slim (default: slim)
  --repo-url <url>              Repository URL passed to install.sh
  --install-url <url>           Raw install.sh URL. Overrides URL inferred from repo-url/origin
  --branch <name>               Git branch for install.sh and repo clone (default: main)
  --vault-path <path>           Local vault path (default: ~/HermesVault)
  --remote-vault-path <path>    Remote vault path (default: ~/HermesVault)
  --hermes-home <path>          Local Hermes home (default: ~/.hermes)
  --remote-hermes-home <path>   Remote Hermes home (default: ~/.hermes)
  --telegram-token <token>      Main bot token used to switch webhook
  --telegram-red-token <token>  Optional red bot token used to switch webhook
  --with-second-bot             Pass --with-second-bot to install.sh
  --interactive                 Run remote installer wizard instead of --non-interactive
  --ssh-option <option>         Extra ssh/rsync option, repeatable (for example: -p 2222)
  --dry-run                     Print commands without executing them
  -h, --help                    Show this help

Environment mirrors the long flags: HERMES_VPS_DOMAIN, HERMES_REPO_URL,
HERMES_INSTALL_URL, HERMES_BRANCH, TELEGRAM_BOT_TOKEN, TELEGRAM_RED_BOT_TOKEN.
USAGE
}

log() {
  printf '[hermes-vps-migrate] %s\n' "$*"
}

warn() {
  printf '[hermes-vps-migrate] WARN: %s\n' "$*" >&2
}

die() {
  printf '[hermes-vps-migrate] ERROR: %s\n' "$*" >&2
  exit 1
}

quote() {
  printf '%q' "$1"
}

quote_remote_path() {
  case "$1" in
    "~") printf '~' ;;
    "~/"*) printf '~/%q' "${1:2}" ;;
    *) quote "$1" ;;
  esac
}

expand_local_path() {
  case "$1" in
    "~") printf '%s\n' "$HOME" ;;
    "~/"*) printf '%s/%s\n' "$HOME" "${1#~/}" ;;
    *) printf '%s\n' "$1" ;;
  esac
}

parse_args() {
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --domain)
        [[ $# -ge 2 ]] || die "--domain requires a value"
        DOMAIN="$2"
        shift 2
        ;;
      --profile)
        [[ $# -ge 2 ]] || die "--profile requires a value"
        PROFILE="$2"
        shift 2
        ;;
      --repo-url)
        [[ $# -ge 2 ]] || die "--repo-url requires a value"
        REPO_URL="$2"
        shift 2
        ;;
      --install-url)
        [[ $# -ge 2 ]] || die "--install-url requires a value"
        INSTALL_URL="$2"
        shift 2
        ;;
      --branch)
        [[ $# -ge 2 ]] || die "--branch requires a value"
        BRANCH="$2"
        shift 2
        ;;
      --vault-path)
        [[ $# -ge 2 ]] || die "--vault-path requires a value"
        LOCAL_VAULT_PATH="$2"
        shift 2
        ;;
      --remote-vault-path)
        [[ $# -ge 2 ]] || die "--remote-vault-path requires a value"
        REMOTE_VAULT_PATH="$2"
        shift 2
        ;;
      --hermes-home)
        [[ $# -ge 2 ]] || die "--hermes-home requires a value"
        LOCAL_HERMES_HOME="$2"
        shift 2
        ;;
      --remote-hermes-home)
        [[ $# -ge 2 ]] || die "--remote-hermes-home requires a value"
        REMOTE_HERMES_HOME="$2"
        shift 2
        ;;
      --telegram-token)
        [[ $# -ge 2 ]] || die "--telegram-token requires a value"
        TELEGRAM_BOT_TOKEN="$2"
        shift 2
        ;;
      --telegram-red-token)
        [[ $# -ge 2 ]] || die "--telegram-red-token requires a value"
        TELEGRAM_RED_BOT_TOKEN="$2"
        WITH_SECOND_BOT=1
        shift 2
        ;;
      --with-second-bot)
        WITH_SECOND_BOT=1
        shift
        ;;
      --interactive)
        NON_INTERACTIVE=0
        shift
        ;;
      --ssh-option)
        [[ $# -ge 2 ]] || die "--ssh-option requires a value"
        SSH_OPTS+=("$2")
        shift 2
        ;;
      --dry-run)
        DRY_RUN=1
        shift
        ;;
      -h|--help)
        usage
        exit 0
        ;;
      -*)
        die "unknown option: $1"
        ;;
      *)
        if [[ -n "$REMOTE" ]]; then
          die "only one remote target is allowed"
        fi
        REMOTE="$1"
        shift
        ;;
    esac
  done

  [[ -n "$REMOTE" ]] || die "missing <user@host>"
  case "$PROFILE" in
    slim|full|ultra-slim) ;;
    *) die "--profile must be slim, full, or ultra-slim" ;;
  esac

  LOCAL_HERMES_HOME="$(expand_local_path "$LOCAL_HERMES_HOME")"
  LOCAL_VAULT_PATH="$(expand_local_path "$LOCAL_VAULT_PATH")"
}

require_tools() {
  local missing=()
  for tool in ssh rsync curl; do
    command -v "$tool" >/dev/null 2>&1 || missing+=("$tool")
  done
  if ((${#missing[@]} > 0)); then
    die "missing required tools: ${missing[*]}"
  fi
}

origin_url() {
  git -C "$REPO_ROOT" config --get remote.origin.url 2>/dev/null || true
}

infer_install_url_from_repo() {
  local url="$1"
  local path=""
  case "$url" in
    https://github.com/*)
      path="${url#https://github.com/}"
      ;;
    git@github.com:*)
      path="${url#git@github.com:}"
      ;;
    ssh://git@github.com/*)
      path="${url#ssh://git@github.com/}"
      ;;
  esac
  [[ -n "$path" ]] || return 1
  path="${path%.git}"
  printf 'https://raw.githubusercontent.com/%s/%s/install.sh\n' "$path" "$BRANCH"
}

resolve_install_url() {
  if [[ -n "$INSTALL_URL" ]]; then
    return
  fi

  if [[ -z "$REPO_URL" ]]; then
    REPO_URL="$(origin_url)"
  fi

  if [[ -n "$REPO_URL" ]]; then
    if INSTALL_URL="$(infer_install_url_from_repo "$REPO_URL")"; then
      return
    fi
  fi

  die "unable to infer install.sh URL; pass --install-url or --repo-url"
}

run_cmd() {
  if ((DRY_RUN)); then
    printf '+'
    for arg in "$@"; do
      printf ' %q' "$arg"
    done
    printf '\n'
    return 0
  fi
  "$@"
}

remote_shell() {
  local command="$1"
  if ((DRY_RUN)); then
    printf '+ ssh'
    for opt in "${SSH_OPTS[@]}"; do
      printf ' %q' "$opt"
    done
    printf ' %q %q\n' "$REMOTE" "$command"
    return 0
  fi
  ssh "${SSH_OPTS[@]}" "$REMOTE" "$command"
}

remote_mkdirs() {
  local cmd
  cmd="mkdir -p $(quote_remote_path "$REMOTE_HERMES_HOME") $(quote_remote_path "$REMOTE_HERMES_HOME/browser-profiles") $(quote_remote_path "$REMOTE_VAULT_PATH")"
  remote_shell "$cmd"
}

rsync_dir() {
  local source="$1"
  local target="$2"
  shift 2

  if [[ ! -d "$source" ]]; then
    warn "skipping missing directory: $source"
    return 0
  fi

  local rsync_args=(-az --info=progress2)
  if ((${#SSH_OPTS[@]} > 0)); then
    local ssh_command="ssh"
    local opt
    for opt in "${SSH_OPTS[@]}"; do
      ssh_command+=" $(quote "$opt")"
    done
    rsync_args+=(-e "$ssh_command")
  fi

  run_cmd rsync "${rsync_args[@]}" "$@" "$source/" "$REMOTE:$target/"
}

sync_state() {
  log "creating remote directories"
  remote_mkdirs

  log "syncing $LOCAL_HERMES_HOME -> $REMOTE:$REMOTE_HERMES_HOME"
  rsync_dir "$LOCAL_HERMES_HOME" "$REMOTE_HERMES_HOME" --exclude 'browser-profiles/'

  log "syncing $LOCAL_HERMES_HOME/browser-profiles -> $REMOTE:$REMOTE_HERMES_HOME/browser-profiles"
  rsync_dir "$LOCAL_HERMES_HOME/browser-profiles" "$REMOTE_HERMES_HOME/browser-profiles"

  log "syncing $LOCAL_VAULT_PATH -> $REMOTE:$REMOTE_VAULT_PATH"
  rsync_dir "$LOCAL_VAULT_PATH" "$REMOTE_VAULT_PATH"
}

install_remote() {
  local cmd
  cmd="curl -fsSL $(quote "$INSTALL_URL") | bash -s --"
  cmd+=" --mode vps"
  cmd+=" --profile $(quote "$PROFILE")"
  cmd+=" --vault-path $(quote_remote_path "$REMOTE_VAULT_PATH")"
  cmd+=" --branch $(quote "$BRANCH")"
  [[ -n "$REPO_URL" ]] && cmd+=" --repo-url $(quote "$REPO_URL")"
  ((WITH_SECOND_BOT)) && cmd+=" --with-second-bot"
  ((NON_INTERACTIVE)) && cmd+=" --non-interactive"
  log "running remote installer"
  remote_shell "$cmd"
}

bot_id_from_token() {
  local token="$1"
  [[ "$token" == *:* ]] || return 1
  printf '%s\n' "${token%%:*}"
}

set_webhook() {
  local token="$1"
  local label="$2"
  [[ -n "$token" ]] || return 0

  if [[ -z "$DOMAIN" ]]; then
    warn "skipping $label webhook: --domain not provided"
    return 0
  fi

  local bot_id
  bot_id="$(bot_id_from_token "$token")" || die "$label token does not look like a Telegram bot token"

  local webhook_url="https://${DOMAIN}/tg/${bot_id}"
  log "setting $label webhook -> $webhook_url"
  run_cmd curl -fsS \
    "https://api.telegram.org/bot${token}/setWebhook" \
    --data-urlencode "url=${webhook_url}" \
    -d "drop_pending_updates=true"
}

switch_webhooks() {
  if [[ -z "$TELEGRAM_BOT_TOKEN" && -z "$TELEGRAM_RED_BOT_TOKEN" ]]; then
    warn "no Telegram tokens supplied; webhook switch skipped"
    return 0
  fi
  set_webhook "$TELEGRAM_BOT_TOKEN" "main bot"
  set_webhook "$TELEGRAM_RED_BOT_TOKEN" "red bot"
}

main() {
  parse_args "$@"
  if ((DRY_RUN == 0)); then
    require_tools
  fi
  resolve_install_url
  log "target: $REMOTE"
  log "install URL: $INSTALL_URL"
  sync_state
  install_remote
  switch_webhooks
  log "migration complete; verify bot replies from the VPS before stopping local gateway"
}

main "$@"
