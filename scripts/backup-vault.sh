#!/usr/bin/env bash
set -euo pipefail

VAULT_PATH="${HERMES_VAULT_PATH:-$HOME/HermesVault}"
BACKUP_DIR="${HERMES_BACKUP_DIR:-/backups}"
RETENTION_DAYS="${HERMES_BACKUP_RETENTION_DAYS:-30}"
INSTALL_CRON=0
DRY_RUN=0

usage() {
  cat <<'USAGE'
Back up HermesVault to a dated tarball and prune old vault backups.

Usage:
  scripts/backup-vault.sh [options]

Options:
  --vault-path <path>       Vault path to archive (default: ~/HermesVault)
  --backup-dir <path>       Backup directory (default: /backups)
  --retention-days <days>   Delete vault-*.tar.gz older than this (default: 30)
  --install-cron            Install a daily /etc/cron.d/hermes-vault-backup job
  --dry-run                 Print commands without writing archives or cron files
  -h, --help                Show this help
USAGE
}

log() {
  printf '[hermes-vault-backup] %s\n' "$*"
}

die() {
  printf '[hermes-vault-backup] ERROR: %s\n' "$*" >&2
  exit 1
}

expand_path() {
  case "$1" in
    "~") printf '%s\n' "$HOME" ;;
    "~/"*) printf '%s/%s\n' "$HOME" "${1:2}" ;;
    *) printf '%s\n' "$1" ;;
  esac
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

parse_args() {
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --vault-path)
        [[ $# -ge 2 ]] || die "--vault-path requires a value"
        VAULT_PATH="$2"
        shift 2
        ;;
      --backup-dir)
        [[ $# -ge 2 ]] || die "--backup-dir requires a value"
        BACKUP_DIR="$2"
        shift 2
        ;;
      --retention-days)
        [[ $# -ge 2 ]] || die "--retention-days requires a value"
        RETENTION_DAYS="$2"
        shift 2
        ;;
      --install-cron)
        INSTALL_CRON=1
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

  [[ "$RETENTION_DAYS" =~ ^[0-9]+$ ]] || die "--retention-days must be a non-negative integer"
  VAULT_PATH="$(expand_path "$VAULT_PATH")"
  BACKUP_DIR="$(expand_path "$BACKUP_DIR")"
}

backup_vault() {
  [[ -d "$VAULT_PATH" ]] || die "vault path not found: $VAULT_PATH"

  local stamp
  local archive
  local tmp_archive
  stamp="$(date +%F)"
  archive="$BACKUP_DIR/vault-${stamp}.tar.gz"
  tmp_archive="${archive}.tmp.$$"

  if ((DRY_RUN)); then
    print_cmd mkdir -p "$BACKUP_DIR"
    print_cmd tar czf "$archive" -C "$(dirname "$VAULT_PATH")" "$(basename "$VAULT_PATH")"
    print_cmd find "$BACKUP_DIR" -maxdepth 1 -type f -name 'vault-*.tar.gz' -mtime "+$RETENTION_DAYS" -delete
    return 0
  fi

  mkdir -p "$BACKUP_DIR"
  tar czf "$tmp_archive" -C "$(dirname "$VAULT_PATH")" "$(basename "$VAULT_PATH")"
  mv "$tmp_archive" "$archive"
  find "$BACKUP_DIR" -maxdepth 1 -type f -name 'vault-*.tar.gz' -mtime "+$RETENTION_DAYS" -delete
  log "created $archive"
}

install_cron() {
  local script_path
  script_path="$(cd "$(dirname "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd -P)/$(basename "${BASH_SOURCE[0]}")"

  local cron_line
  cron_line="17 3 * * * root HERMES_VAULT_PATH=$(printf '%q' "$VAULT_PATH") HERMES_BACKUP_DIR=$(printf '%q' "$BACKUP_DIR") HERMES_BACKUP_RETENTION_DAYS=$RETENTION_DAYS $(printf '%q' "$script_path") >> /var/log/hermes-vault-backup.log 2>&1"

  if ((DRY_RUN)); then
    printf '+ write /etc/cron.d/hermes-vault-backup: %s\n' "$cron_line"
    return 0
  fi

  local tmp
  tmp="$(mktemp)"
  {
    printf 'SHELL=/bin/bash\n'
    printf 'PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin\n'
    printf '%s\n' "$cron_line"
  } > "$tmp"
  run_as_root install -m 0644 "$tmp" /etc/cron.d/hermes-vault-backup
  rm -f "$tmp"
  log "installed /etc/cron.d/hermes-vault-backup"
}

main() {
  parse_args "$@"
  if ((INSTALL_CRON)); then
    install_cron
  else
    backup_vault
  fi
}

main "$@"
