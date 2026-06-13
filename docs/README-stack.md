# Hermes Ultimate Stack

This document covers the production stack pieces that sit around the native
Hermes process: Docker services, Caddy/TLS, Tailscale access, and vault backups.

## VPS deployment

Minimum VPS shape:

- Ubuntu 22.04 LTS or newer.
- 4 vCPU.
- 6 GB RAM.
- 80 GB NVMe storage.
- Public IPv4 with DNS records for `dashboard.<domain>`, `vnc.<domain>`, and
  `router.<domain>` pointing at the VPS.

Recommended operator flow:

```bash
git clone https://github.com/<user>/hermes-ultimate.git
cd hermes-ultimate

scripts/migrate-to-vps.sh user@vps.example.com \
  --repo-url https://github.com/<user>/hermes-ultimate.git \
  --domain example.com \
  --telegram-token "$TELEGRAM_BOT_TOKEN"
```

On the VPS, `migrate-to-vps.sh` runs the installer in VPS mode:

```bash
curl -fsSL https://raw.githubusercontent.com/<user>/hermes-ultimate/main/install.sh \
  | bash -s -- --mode vps --profile slim --non-interactive
```

### Caddy and TLS

Production Caddy lives in:

- `stack/caddy/Caddyfile`
- `stack/docker-compose.vps.yml`

Set these variables in `~/.hermes/stack.env` or the shell that runs compose:

```bash
ACME_EMAIL=admin@example.com
HERMES_DOMAIN=example.com
CADDY_BIND=0.0.0.0
CADDY_BASIC_AUTH_USER=admin
CADDY_BASIC_AUTH_HASH='<caddy bcrypt hash>'
TAILSCALE_ONLY=0
TAILSCALE_ALLOWED_CIDRS=100.64.0.0/10
```

Generate the basic-auth hash on the VPS:

```bash
docker run --rm caddy:2 caddy hash-password --plaintext 'change-me'
```

Start the VPS overlay:

```bash
docker compose \
  -f stack/docker-compose.yml \
  -f stack/docker-compose.decepticon-slim.yml \
  -f stack/docker-compose.vps.yml \
  up -d
```

Caddy proxies:

- `https://dashboard.<domain>` -> `localhost:8080`
- `https://vnc.<domain>` -> `localhost:6080`
- `https://router.<domain>` -> `localhost:20128`

`stack/docker-compose.vps.yml` uses host networking so Caddy can reach the
native Hermes dashboard and host-published compose ports through `localhost`.

### Tailscale

Install Tailscale and enable Tailscale SSH:

```bash
scripts/install-tailscale.sh
tailscale status
```

For unattended provisioning:

```bash
TAILSCALE_AUTH_KEY=tskey-auth-... \
scripts/install-tailscale.sh --hostname hermes-vps --advertise-tags tag:hermes
```

To expose Caddy only on a Tailscale address, set `CADDY_BIND` to the VPS
Tailscale IP and keep DNS internal to the tailnet. To keep public DNS while
blocking non-tailnet clients at Caddy, set:

```bash
TAILSCALE_ONLY=1
TAILSCALE_ALLOWED_CIDRS=100.64.0.0/10
```

### Vault backups

Create `/backups` and run the backup once:

```bash
sudo mkdir -p /backups
scripts/backup-vault.sh
ls /backups/vault-*.tar.gz
```

Install the daily cron entry:

```bash
sudo scripts/backup-vault.sh --install-cron
```

The job runs daily at 03:17, writes `/backups/vault-YYYY-MM-DD.tar.gz`, and
prunes `vault-*.tar.gz` archives older than 30 days.

### VPS verification

```bash
docker compose \
  -f stack/docker-compose.yml \
  -f stack/docker-compose.decepticon-slim.yml \
  -f stack/docker-compose.vps.yml \
  ps

curl -I https://dashboard.<domain>
curl -fsS http://localhost:8080/api/health
curl -fsS http://localhost:20128/api/health
curl -fsS http://localhost:6080/vnc.html >/dev/null
tailscale status
ls /backups/vault-*.tar.gz
```
