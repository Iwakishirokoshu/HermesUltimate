# Hermes Ultimate Agent

Install a full Hermes stack on a fresh VPS, WSL2 Ubuntu, or local workstation:

```bash
curl -fsSL https://raw.githubusercontent.com/<user>/hermes-ultimate/main/install.sh | bash -s -- --mode local
```

Hermes Ultimate is the stock Hermes agent packaged with the local services needed to run it as a practical always-on assistant: Hermes Python runs natively, while the supporting stack runs through Docker Compose.

## What It Starts

- Hermes CLI, dashboard, and gateway installed into a local Python virtualenv.
- 9router on `http://localhost:20128` for model/provider routing.
- HermesVault at `~/HermesVault` by default.
- Vault API on `http://localhost:8090`.
- Browser/VNC cloak on `http://localhost:6080`.
- Optional Decepticon/LangGraph red-team backend on `http://localhost:2024`.
- Optional Neo4j graph backend on `http://localhost:7474`.
- Telegram gateway config for one bot, or two bots when `--with-second-bot` is used.

## Linux, macOS, WSL2

Default VPS-style install:

```bash
curl -fsSL https://raw.githubusercontent.com/<user>/hermes-ultimate/main/install.sh | bash
```

Local checkout install:

```bash
git clone https://github.com/<user>/hermes-ultimate.git
cd hermes-ultimate
bash install.sh --mode local --non-interactive --vnc-password test123
```

Private fork:

```bash
curl -fsSL https://raw.githubusercontent.com/<user>/hermes-ultimate/main/install.sh | bash -s -- \
  --repo-url https://github.com/<user>/hermes-ultimate.git \
  --branch main
```

## Windows

Run PowerShell as a normal user:

```powershell
powershell -ExecutionPolicy Bypass -File .\install.ps1 -Mode local -NonInteractive -VncPassword test123
```

The Windows installer uses `winget` for Docker Desktop, Git, Python 3.11, Node.js, ripgrep, ffmpeg, and jq. It uses Git Bash for the bash helper scripts and Docker Desktop for the compose stack.

## Installer Flags

```bash
--mode local|vps
--profile slim|full|ultra-slim
--vnc-password <password>
--with-second-bot
--vault-path <path>
--repo-url <url>
--branch <name>
--non-interactive
```

Defaults:

- `--mode vps`
- `--profile slim`
- `--branch main`
- `--vault-path ~/HermesVault`

Profiles:

- `slim`: core stack plus Decepticon/LangGraph and Neo4j.
- `ultra-slim`: core stack only, without Decepticon/Neo4j.
- `full`: reserved for a future full compose profile; currently falls back to `slim` when the full compose file is absent.

## First Run Wizard

Without `--non-interactive`, the installer launches:

```bash
bash scripts/post-install-wizard.sh
```

The wizard asks for:

- Telegram bot token.
- Optional second Telegram bot token for the red soul.
- Telegram allowed user id.
- 9router provider setup.
- Whether to copy default souls into `~/.hermes/souls`.

It writes:

- `~/.hermes/stack.env`
- `~/.hermes/gateway.yaml`
- `~/.hermes/config.toml`

## After Install

Useful URLs:

```text
Dashboard: http://localhost:8080
9router:   http://localhost:20128
VNC:       http://localhost:6080
LangGraph: http://localhost:2024
Neo4j:     http://localhost:7474
```

Useful commands:

```bash
hermes dashboard --host 0.0.0.0 --port 8080 --no-open --skip-build
hermes gateway
docker compose -f stack/docker-compose.yml -f stack/docker-compose.decepticon-slim.yml ps
```

## Generated Files

Secrets are generated per machine and should not be committed:

```text
~/.hermes/stack.env
~/.hermes/gateway.yaml
~/.hermes/config.toml
```

The compose stack reads `stack/.env`, which is symlinked to `~/.hermes/stack.env` by `scripts/gen-env.sh`.

## Development

From this checkout:

```bash
bash -n install.sh
bash -n scripts/gen-env.sh
bash -n scripts/post-install-wizard.sh
python -m pytest scripts/smoke-tests/test_souls_switch.py -v
python -m pytest scripts/smoke-tests/test_decepticon_backend_mock.py -v
```

Phase 7 installer smoke:

```bash
bash scripts/smoke-tests/test_install_idempotent.sh
```

## Notes

- Replace `<user>` in the one-liner with your GitHub account or organization.
- Docker Desktop must be running on Windows before the compose stack can start.
- Live Telegram validation requires that you message the bot with `/start` before the wizard calls `getUpdates`.
