#!/usr/bin/env bash
set -euo pipefail

IFS=$'\n\t'

MODE="vps"
PROFILE="slim"
BRANCH="${HERMES_BRANCH:-main}"
REPO_URL="${HERMES_REPO_URL:-https://github.com/Iwakishirokoshu/HermesUltimate.git}"
INSTALL_DIR="${HERMES_INSTALL_DIR:-/opt/hermes-ultimate}"
VAULT_PATH="${HERMES_VAULT_PATH:-$HOME/HermesVault}"
VNC_PASSWORD="${VNC_PASSWORD:-}"
GITHUB_TOKEN="${HERMES_GITHUB_TOKEN:-${GITHUB_TOKEN:-}}"
WITH_SECOND_BOT=0
WITH_TAILSCALE=0
NON_INTERACTIVE=0
START_STACK=1
GENERATED_VNC_PASSWORD=0
OS_ID=""
PKG_MANAGER=""

export PATH="$HOME/.local/bin:$HOME/.cargo/bin:$PATH"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" >/dev/null 2>&1 && pwd -P || pwd)"

usage() {
  cat <<'USAGE'
Hermes Ultimate installer

Usage:
  install.sh [options]

Options:
  --mode local|vps              Install mode. Default: vps
  --profile slim|full|ultra-slim
                                Stack profile. Default: slim
  --vnc-password <pw>           VNC password. Generated when omitted
  --with-second-bot             Enable second Telegram bot template flow
  --vault-path <path>           HermesVault path. Default: ~/HermesVault
  --repo-url <url>              Git repository URL for private forks
  --branch <name>               Git branch. Default: main
  --with-tailscale              Install and bring up Tailscale SSH on VPS
  --non-interactive             Skip post-install wizard and use env vars
  --defaults, --yes             Alias for --non-interactive
  --skip-stack                  Install Hermes native bits without Docker stack
  -h, --help                    Show this help
USAGE
}

log() {
  printf '[hermes-install] %s\n' "$*"
}

warn() {
  printf '[hermes-install] WARN: %s\n' "$*" >&2
}

die() {
  printf '[hermes-install] ERROR: %s\n' "$*" >&2
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

git_with_auth() {
  if [[ -n "$GITHUB_TOKEN" && "$REPO_URL" == https://github.com/* ]]; then
    git -c "http.https://github.com/.extraheader=AUTHORIZATION: bearer $GITHUB_TOKEN" "$@"
  else
    git "$@"
  fi
}

docker_compose() {
  local compose_cmd=(docker compose)
  if ! docker compose version >/dev/null 2>&1 && command -v docker-compose >/dev/null 2>&1; then
    compose_cmd=(docker-compose)
  fi

  if docker info >/dev/null 2>&1; then
    "${compose_cmd[@]}" "$@"
  elif command -v sudo >/dev/null 2>&1 && sudo docker info >/dev/null 2>&1; then
    sudo "${compose_cmd[@]}" "$@"
  else
    "${compose_cmd[@]}" "$@"
  fi
}

docker_cli() {
  if docker info >/dev/null 2>&1; then
    docker "$@"
  elif command -v sudo >/dev/null 2>&1 && sudo docker info >/dev/null 2>&1; then
    sudo docker "$@"
  else
    docker "$@"
  fi
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
      --mode)
        [[ $# -ge 2 ]] || die "--mode requires a value"
        MODE="$2"
        shift 2
        ;;
      --profile)
        [[ $# -ge 2 ]] || die "--profile requires a value"
        PROFILE="$2"
        shift 2
        ;;
      --vnc-password)
        [[ $# -ge 2 ]] || die "--vnc-password requires a value"
        VNC_PASSWORD="$2"
        shift 2
        ;;
      --with-second-bot)
        WITH_SECOND_BOT=1
        shift
        ;;
      --with-tailscale)
        WITH_TAILSCALE=1
        shift
        ;;
      --vault-path)
        [[ $# -ge 2 ]] || die "--vault-path requires a value"
        VAULT_PATH="$2"
        shift 2
        ;;
      --repo-url)
        [[ $# -ge 2 ]] || die "--repo-url requires a value"
        REPO_URL="$2"
        shift 2
        ;;
      --branch)
        [[ $# -ge 2 ]] || die "--branch requires a value"
        BRANCH="$2"
        shift 2
        ;;
      --non-interactive)
        NON_INTERACTIVE=1
        shift
        ;;
      --defaults|--yes|-y)
        NON_INTERACTIVE=1
        shift
        ;;
      --skip-stack)
        START_STACK=0
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

  case "$MODE" in
    local|vps) ;;
    *) die "--mode must be local or vps" ;;
  esac

  case "$PROFILE" in
    slim|full|ultra-slim) ;;
    *) die "--profile must be slim, full, or ultra-slim" ;;
  esac

  VAULT_PATH="$(expand_path "$VAULT_PATH")"
}

generate_vnc_password() {
  if [[ -z "$VNC_PASSWORD" ]]; then
    if command -v openssl >/dev/null 2>&1; then
      VNC_PASSWORD="$(openssl rand -hex 12)"
    else
      VNC_PASSWORD="$(date +%s%N | sha256sum | cut -c1-24)"
    fi
    GENERATED_VNC_PASSWORD=1
  fi
}

detect_os() {
  local kernel
  kernel="$(uname -s)"
  case "$kernel" in
    Darwin)
      OS_ID="macos"
      PKG_MANAGER="brew"
      return
      ;;
    Linux)
      if [[ -r /etc/os-release ]]; then
        # shellcheck disable=SC1091
        . /etc/os-release
        OS_ID="${ID:-unknown}"
        local like="${ID_LIKE:-}"
        case "$OS_ID $like" in
          *ubuntu*|*debian*)
            PKG_MANAGER="apt"
            ;;
          *arch*)
            PKG_MANAGER="pacman"
            ;;
          *fedora*)
            PKG_MANAGER="dnf"
            ;;
          *)
            if grep -qiE 'microsoft|wsl' /proc/version 2>/dev/null; then
              warn "WSL2 detected with unrecognized distro '$OS_ID'; trying apt-compatible flow"
              PKG_MANAGER="apt"
            else
              die "unsupported Linux distro '$OS_ID'. Supported: Ubuntu, Debian, Arch, Fedora, macOS, WSL2"
            fi
            ;;
        esac
        return
      fi
      ;;
  esac

  die "unsupported OS '$kernel'. Supported: Ubuntu, Debian, Arch, Fedora, macOS, WSL2"
}

ensure_node_apt() {
  if command -v node >/dev/null 2>&1; then
    local major
    major="$(node -v | sed 's/^v//' | cut -d. -f1)"
    if [[ "$major" == "22" ]]; then
      return
    fi
  fi

  log "installing Node.js 22 via NodeSource"
  local setup_file="/tmp/hermes-nodesource-setup.sh"
  curl -fsSL https://deb.nodesource.com/setup_22.x -o "$setup_file"
  run_as_root bash "$setup_file"
  run_as_root apt-get install -y nodejs
}

apt_package_available() {
  local candidate
  candidate="$(apt-cache policy "$1" 2>/dev/null | awk '/Candidate:/ {print $2; exit}')"
  [[ -n "$candidate" && "$candidate" != "(none)" ]]
}

resolve_apt_package() {
  local fallback="$1"
  shift

  local candidate
  for candidate in "$@"; do
    if apt_package_available "$candidate"; then
      printf '%s\n' "$candidate"
      return
    fi
  done

  printf '%s\n' "$fallback"
}

install_deps_apt() {
  log "installing apt dependencies"
  run_as_root apt-get update

  local libasound_pkg
  libasound_pkg="$(resolve_apt_package libasound2 libasound2 libasound2t64)"

  run_as_root apt-get install -y \
    ca-certificates curl gnupg lsb-release git build-essential ripgrep ffmpeg jq openssl \
    xvfb x11vnc openbox websockify novnc x11-utils xclip \
    libnss3 libnspr4 libatk1.0-0 libatk-bridge2.0-0 libcups2 libdbus-1-3 \
    libdrm2 libxkbcommon0 libatspi2.0-0 libxcomposite1 libxdamage1 libxfixes3 \
    libxrandr2 libgbm1 libpango-1.0-0 libcairo2 "$libasound_pkg" libx11-xcb1 \
    libfontconfig1 libx11-6 libxcb1 libxext6 libxshmfence1 libglib2.0-0 \
    libgtk-3-0 libpangocairo-1.0-0 libcairo-gobject2 libgdk-pixbuf-2.0-0 \
    libxss1 libxtst6 fonts-liberation fonts-noto-color-emoji fonts-unifont \
    fonts-freefont-ttf fonts-wqy-zenhei

  if ! run_as_root apt-get install -y python3.11 python3.11-venv python3.11-dev; then
    warn "python3.11 packages unavailable; falling back to distro python3"
    run_as_root apt-get install -y python3 python3-venv python3-dev
  fi

  if [[ "$START_STACK" -eq 1 ]] && ! command -v docker >/dev/null 2>&1; then
    run_as_root apt-get install -y docker.io
  fi

  if [[ "$START_STACK" -eq 1 ]] && ! docker compose version >/dev/null 2>&1; then
    if run_as_root apt-get install -y docker-compose-plugin; then
      :
    elif run_as_root apt-get install -y docker-compose-v2; then
      :
    else
      warn "docker compose v2 package unavailable; trying legacy docker-compose"
      run_as_root apt-get install -y docker-compose
    fi
  fi

  ensure_node_apt
}

install_deps_pacman() {
  log "installing pacman dependencies"
  run_as_root pacman -Sy --needed --noconfirm docker docker-compose git python python-virtualenv base-devel ripgrep ffmpeg curl jq nodejs npm openssl xorg-server-xvfb x11vnc openbox websockify xclip noto-fonts noto-fonts-emoji
}

install_deps_dnf() {
  log "installing dnf dependencies"
  run_as_root dnf install -y docker docker-compose-plugin git python3.11 python3.11-devel python3.11-pip gcc gcc-c++ make ripgrep ffmpeg curl jq nodejs npm openssl xorg-x11-server-Xvfb x11vnc openbox websockify xclip google-noto-emoji-fonts || \
    run_as_root dnf install -y docker docker-compose-plugin git python3 python3-devel python3-pip gcc gcc-c++ make ripgrep ffmpeg curl jq nodejs npm openssl xorg-x11-server-Xvfb x11vnc openbox websockify xclip google-noto-emoji-fonts
}

install_deps_brew() {
  command -v brew >/dev/null 2>&1 || die "Homebrew is required on macOS"
  log "installing Homebrew dependencies"
  brew update
  brew install git python@3.11 ripgrep ffmpeg curl jq node@22 uv || true
  brew link --overwrite --force node@22 >/dev/null 2>&1 || true
  if ! command -v docker >/dev/null 2>&1; then
    brew install --cask docker || warn "Docker Desktop cask install failed; install/start Docker Desktop manually"
  fi
}

install_deps() {
  case "$PKG_MANAGER" in
    apt) install_deps_apt ;;
    pacman) install_deps_pacman ;;
    dnf) install_deps_dnf ;;
    brew) install_deps_brew ;;
    *) die "no installer for package manager '$PKG_MANAGER'" ;;
  esac

  if [[ "$START_STACK" -eq 1 ]]; then
    if command -v systemctl >/dev/null 2>&1; then
      run_as_root systemctl enable --now docker >/dev/null 2>&1 || warn "could not start docker via systemctl"
    elif command -v service >/dev/null 2>&1; then
      run_as_root service docker start >/dev/null 2>&1 || warn "could not start docker via service"
    fi
  fi

  if ! command -v uv >/dev/null 2>&1; then
    log "installing uv"
    curl -LsSf https://astral.sh/uv/install.sh | sh
    export PATH="$HOME/.local/bin:$HOME/.cargo/bin:$PATH"
  fi

  command -v git >/dev/null 2>&1 || die "git is not available after dependency install"
  command -v curl >/dev/null 2>&1 || die "curl is not available after dependency install"
  command -v uv >/dev/null 2>&1 || die "uv is not available after dependency install"
  if [[ "$START_STACK" -eq 1 ]]; then
    command -v docker >/dev/null 2>&1 || die "docker is not available after dependency install"
    if ! docker compose version >/dev/null 2>&1 && ! command -v docker-compose >/dev/null 2>&1; then
      die "docker compose is not available"
    fi
  fi
}

resolve_repo_url_from_current_checkout() {
  local candidate="$1"
  if [[ -z "$REPO_URL" && -d "$candidate/.git" ]]; then
    REPO_URL="$(git -C "$candidate" config --get remote.origin.url || true)"
  fi
}

clone_repo() {
  local current_dir
  current_dir="$(pwd -P)"

  if [[ "$MODE" == "local" && -f "$current_dir/pyproject.toml" && -d "$current_dir/stack" ]]; then
    INSTALL_DIR="$current_dir"
    log "using current checkout for local mode: $INSTALL_DIR"
    return
  fi

  if [[ "$MODE" == "local" && -f "$SCRIPT_DIR/pyproject.toml" && -d "$SCRIPT_DIR/stack" ]]; then
    INSTALL_DIR="$SCRIPT_DIR"
    log "using script checkout for local mode: $INSTALL_DIR"
    return
  fi

  resolve_repo_url_from_current_checkout "$SCRIPT_DIR"
  [[ -n "$REPO_URL" ]] || die "repo URL is required for vps mode; pass --repo-url <url> or set HERMES_REPO_URL"

  if [[ -d "$INSTALL_DIR/.git" ]]; then
    log "updating existing checkout: $INSTALL_DIR"
    git_with_auth -C "$INSTALL_DIR" fetch origin "$BRANCH"
    git -C "$INSTALL_DIR" checkout "$BRANCH"
    git_with_auth -C "$INSTALL_DIR" pull --ff-only origin "$BRANCH"
    return
  fi

  if [[ -e "$INSTALL_DIR" ]]; then
    die "$INSTALL_DIR exists but is not a git checkout"
  fi

  log "cloning $REPO_URL#$BRANCH into $INSTALL_DIR"
  run_as_root mkdir -p "$INSTALL_DIR"
  run_as_root chown "$(id -u):$(id -g)" "$INSTALL_DIR"
  git_with_auth clone --branch "$BRANCH" "$REPO_URL" "$INSTALL_DIR"
}

python_for_uv() {
  if command -v python3.11 >/dev/null 2>&1; then
    printf '%s\n' "python3.11"
  else
    printf '%s\n' "python3"
  fi
}

install_hermes_native() {
  log "installing Hermes Python package natively"
  cd "$INSTALL_DIR"
  uv venv --clear --python "$(python_for_uv)"
  # shellcheck disable=SC1091
  source .venv/bin/activate
  uv pip install -e ".[all]"
  uv pip install "cloakbrowser[geoip]==0.3.31"
}

init_dirs() {
  log "initializing user directories"
  mkdir -p "$HOME/.hermes" "$VAULT_PATH" "$HOME/.hermes/browser-profiles" "$HOME/.hermes/cloak" "$HOME/.hermes/souls" "$HOME/.hermes/logs"

  shopt -s nullglob
  local existing_souls=("$HOME/.hermes/souls"/*.yaml)
  local bundled_souls=("$INSTALL_DIR"/souls/*.yaml)
  if [[ ${#existing_souls[@]} -eq 0 && ${#bundled_souls[@]} -gt 0 ]]; then
    cp "${bundled_souls[@]}" "$HOME/.hermes/souls/"
  fi
  shopt -u nullglob
}

init_vault() {
  log "initializing HermesVault"
  cd "$INSTALL_DIR"
  HERMES_VAULT_PATH="$VAULT_PATH" bash scripts/init-vault.sh
}

gen_env() {
  if [[ "$START_STACK" -eq 0 ]]; then
    log "skipping stack env generation (--skip-stack)"
    return
  fi

  cd "$INSTALL_DIR"
  [[ -f scripts/gen-env.sh ]] || die "scripts/gen-env.sh is missing; run after T-701 is present"
  log "generating stack environment"
  HERMES_VAULT_PATH="$VAULT_PATH" \
    VNC_PASSWORD="$VNC_PASSWORD" \
    WITH_SECOND_BOT="$WITH_SECOND_BOT" \
    bash scripts/gen-env.sh
}

install_tailscale() {
  if [[ "$WITH_TAILSCALE" -eq 0 ]]; then
    return
  fi

  cd "$INSTALL_DIR"
  [[ -f scripts/install-tailscale.sh ]] || die "scripts/install-tailscale.sh is missing; cannot run --with-tailscale"
  log "installing Tailscale"
  bash scripts/install-tailscale.sh
}

compose_args() {
  printf '%s\0' -f stack/docker-compose.yml
  case "$PROFILE" in
    slim)
      printf '%s\0' -f stack/docker-compose.decepticon-slim.yml
      ;;
    full)
      if [[ -f stack/docker-compose.decepticon-full.yml ]]; then
        printf '%s\0' -f stack/docker-compose.decepticon-full.yml
      else
        warn "full profile compose file is not present; using slim profile"
        printf '%s\0' -f stack/docker-compose.decepticon-slim.yml
      fi
      ;;
    ultra-slim)
      ;;
  esac
}

start_stack() {
  if [[ "$START_STACK" -eq 0 ]]; then
    log "skipping Docker stack startup (--skip-stack)"
    return
  fi

  cd "$INSTALL_DIR"
  log "starting Docker stack with profile '$PROFILE'"
  if ! docker_cli network inspect hermes-net >/dev/null 2>&1; then
    docker_cli network create hermes-net >/dev/null
  fi
  local args=()
  while IFS= read -r -d '' item; do
    args+=("$item")
  done < <(compose_args)
  docker_compose "${args[@]}" config >/dev/null
  docker_compose "${args[@]}" up -d --build
  if [[ -x scripts/disable-9router-auth.sh ]]; then
    if docker info >/dev/null 2>&1; then
      bash scripts/disable-9router-auth.sh || warn "could not disable 9router auth; run scripts/disable-9router-auth.sh manually"
    elif command -v sudo >/dev/null 2>&1 && sudo docker info >/dev/null 2>&1; then
      sudo -E bash scripts/disable-9router-auth.sh || warn "could not disable 9router auth; run scripts/disable-9router-auth.sh manually"
    else
      warn "could not access Docker to disable 9router auth; run scripts/disable-9router-auth.sh manually"
    fi
  fi
}

wait_url() {
  local name="$1"
  local url="$2"
  local timeout="${3:-120}"
  local start
  start="$(date +%s)"
  while true; do
    if curl -fsS "$url" >/dev/null 2>&1; then
      log "$name is ready at $url"
      return 0
    fi
    if (( "$(date +%s)" - start >= timeout )); then
      return 1
    fi
    sleep 2
  done
}

wait_any_url() {
  local name="$1"
  local timeout="$2"
  shift 2
  local start
  start="$(date +%s)"
  while true; do
    local url
    for url in "$@"; do
      if curl -fsS "$url" >/dev/null 2>&1; then
        log "$name is ready at $url"
        return 0
      fi
    done
    if (( "$(date +%s)" - start >= timeout )); then
      return 1
    fi
    sleep 2
  done
}

wait_healthy() {
  if [[ "$START_STACK" -eq 0 ]]; then
    return
  fi

  log "waiting for stack health"
  wait_any_url "9router" 120 "http://localhost:20128/health" "http://localhost:20128/api/health" "http://localhost:20128" || die "9router did not become healthy"
  wait_url "vault-api" "http://localhost:8090/health" 120 || die "vault-api did not become healthy"
  if [[ "$PROFILE" != "ultra-slim" ]]; then
    wait_url "langgraph" "http://localhost:2024/health" 120 || die "langgraph did not become healthy"
    wait_url "neo4j" "http://localhost:7474" 120 || die "neo4j did not become healthy"
  fi
}

start_dashboard() {
  if curl -fsS "http://localhost:8080/api/status" >/dev/null 2>&1 || curl -fsS "http://localhost:8080" >/dev/null 2>&1; then
    log "dashboard already responds on http://localhost:8080"
    return
  fi

  local hermes_bin="$INSTALL_DIR/.venv/bin/hermes"
  [[ -x "$hermes_bin" ]] || die "Hermes executable not found at $hermes_bin"

  log "starting Hermes dashboard on http://localhost:8080"
  nohup "$hermes_bin" dashboard --host 127.0.0.1 --port 8080 --no-open >"$HOME/.hermes/logs/dashboard.log" 2>&1 &
  echo "$!" > "$HOME/.hermes/dashboard.pid"
  wait_any_url "dashboard" 120 "http://localhost:8080/api/status" "http://localhost:8080" || die "dashboard did not become healthy"
}

run_wizard() {
  if [[ "$NON_INTERACTIVE" -eq 1 ]]; then
    log "non-interactive mode: skipping post-install wizard"
    return
  fi
  if [[ "$START_STACK" -eq 0 ]]; then
    log "skipping post-install wizard because Docker stack is disabled"
    return
  fi

  cd "$INSTALL_DIR"
  [[ -f scripts/post-install-wizard.sh ]] || die "scripts/post-install-wizard.sh is missing; run with --non-interactive or add T-702"
  log "starting post-install wizard"
  if [[ "$WITH_SECOND_BOT" -eq 1 ]]; then
    bash scripts/post-install-wizard.sh --with-second-bot
  else
    bash scripts/post-install-wizard.sh
  fi
}

print_summary() {
  cat <<SUMMARY

Hermes Ultimate install complete.

Dashboard:      http://localhost:8080
9router:        http://localhost:20128
Cloak manager:  Dashboard -> Browser
LangGraph:      http://localhost:2024
Vault path:     $VAULT_PATH
Install dir:    $INSTALL_DIR
Logs:           $HOME/.hermes/logs
SUMMARY

  if [[ "$WITH_SECOND_BOT" -eq 1 ]]; then
    cat <<'SUMMARY'

Second Telegram bot mode was requested. Configure TELEGRAM_RED_BOT_TOKEN via the wizard or ~/.hermes/stack.env.
SUMMARY
  fi
}

main() {
  parse_args "$@"
  generate_vnc_password
  detect_os
  install_deps
  clone_repo
  install_hermes_native
  init_dirs
  init_vault
  gen_env
  install_tailscale
  start_stack
  wait_healthy
  start_dashboard
  run_wizard
  print_summary
}

main "$@"
