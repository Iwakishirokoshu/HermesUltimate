#!/usr/bin/env bash
set -euo pipefail

AUTH_KEY="${TAILSCALE_AUTH_KEY:-}"
HOSTNAME="${TAILSCALE_HOSTNAME:-}"
ADVERTISE_TAGS="${TAILSCALE_ADVERTISE_TAGS:-}"
ACCEPT_ROUTES=0
ENABLE_SSH=1
DRY_RUN=0

usage() {
  cat <<'USAGE'
Install and bring up Tailscale for Hermes Ultimate VPS mode.

Usage:
  scripts/install-tailscale.sh [options]

Options:
  --auth-key <key>        Optional reusable/auth key for unattended tailscale up
  --hostname <name>       Optional Tailscale device hostname
  --advertise-tags <tags> Optional comma-separated tags, for example tag:hermes
  --accept-routes         Pass --accept-routes to tailscale up
  --no-ssh                Do not enable Tailscale SSH
  --dry-run               Print commands without executing them
  -h, --help              Show this help
USAGE
}

log() {
  printf '[hermes-tailscale] %s\n' "$*"
}

die() {
  printf '[hermes-tailscale] ERROR: %s\n' "$*" >&2
  exit 1
}

run_as_root() {
  if [[ "${EUID:-$(id -u)}" -eq 0 ]]; then
    "$@"
  elif command -v sudo >/dev/null 2>&1; then
    sudo "$@"
  else
    die "root privileges are required for: $*"
  fi
}

print_cmd() {
  printf '+'
  for arg in "$@"; do
    printf ' %q' "$arg"
  done
  printf '\n'
}

run_cmd() {
  if ((DRY_RUN)); then
    print_cmd "$@"
    return 0
  fi
  "$@"
}

parse_args() {
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --auth-key)
        [[ $# -ge 2 ]] || die "--auth-key requires a value"
        AUTH_KEY="$2"
        shift 2
        ;;
      --hostname)
        [[ $# -ge 2 ]] || die "--hostname requires a value"
        HOSTNAME="$2"
        shift 2
        ;;
      --advertise-tags)
        [[ $# -ge 2 ]] || die "--advertise-tags requires a value"
        ADVERTISE_TAGS="$2"
        shift 2
        ;;
      --accept-routes)
        ACCEPT_ROUTES=1
        shift
        ;;
      --no-ssh)
        ENABLE_SSH=0
        shift
        ;;
      --dry-run)
        DRY_RUN=1
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

install_tailscale() {
  if command -v tailscale >/dev/null 2>&1; then
    log "tailscale is already installed"
    return 0
  fi

  log "installing tailscale"
  if ((DRY_RUN)); then
    printf '+ curl -fsSL https://tailscale.com/install.sh | sh\n'
    return 0
  fi

  if [[ "${EUID:-$(id -u)}" -eq 0 ]]; then
    curl -fsSL https://tailscale.com/install.sh | sh
  elif command -v sudo >/dev/null 2>&1; then
    curl -fsSL https://tailscale.com/install.sh | sudo sh
  else
    die "sudo is required to install tailscale"
  fi
}

tailscale_up() {
  local args=(up)

  ((ENABLE_SSH)) && args+=(--ssh)
  ((ACCEPT_ROUTES)) && args+=(--accept-routes)
  [[ -n "$AUTH_KEY" ]] && args+=(--auth-key "$AUTH_KEY")
  [[ -n "$HOSTNAME" ]] && args+=(--hostname "$HOSTNAME")
  [[ -n "$ADVERTISE_TAGS" ]] && args+=(--advertise-tags "$ADVERTISE_TAGS")

  log "running tailscale ${args[*]}"
  if ((DRY_RUN)); then
    print_cmd sudo tailscale "${args[@]}"
    return 0
  fi

  run_as_root tailscale "${args[@]}"
}

main() {
  parse_args "$@"
  install_tailscale
  tailscale_up
  log "tailscale setup complete"
}

main "$@"
