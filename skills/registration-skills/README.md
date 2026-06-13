# Registration Skills — Portable Bundle

Extracted from hermes-vps-backup-20260610.
Skills: account-registration-automation, cloakbrowser-cdp-session, tccd-edu-email-registration.

---

## Structure

```
registration-skills/
  account-registration-automation/
    SKILL.md                  — ChatGPT signup, SheerID form, OTP flow, FlowPilot OAuth
    templates/
      chatgpt_signup_persistent.py  — ChatGPT registration with cmd-file injection
      chatgpt_sheerid_flow.py       — ChatGPT + SheerID student verification full flow
      sheerid_form_fill.py          — SheerID form standalone
    references/
      cmd-file-injection-pattern.md — pattern: keep browser alive, inject commands via file
      flowpilot-oauth-chain.md      — OAuth handoff to API aggregators (SUB2API, Codex2API)

  cloakbrowser-cdp-session/
    SKILL.md                  — CDP setup: CloakBrowser port 9222 + humanize shim 9223

  tccd-edu-email-registration/
    SKILL.md                  — TCCD / HCC / Lone Star / Park University .edu email flow
    tccd.py                   — legacy tccd helper
    templates/                — 16 automation scripts
    references/               — 20 reference docs (field IDs, pitfalls, personas, portals)
```

---

## Setup on new server

### 1. Install CloakBrowser

```bash
# Download from cloakbrowser.com or your license portal
# After install, binary will be at:
#   ~/.cloakbrowser/chromium-<version>/chrome  (Linux)
export CLOAKBROWSER_BINARY_PATH=$(ls ~/.cloakbrowser/chromium-*/chrome 2>/dev/null | sort | tail -1)
```

### 2. Create venv with cloakbrowser + playwright

```bash
python3 -m venv ~/venv
~/venv/bin/pip install cloakbrowser playwright
~/venv/bin/playwright install chromium
```

### 3. Set environment variables (add to ~/.bashrc or .env)

```bash
export CLOAKBROWSER_BINARY_PATH=$(ls ~/.cloakbrowser/chromium-*/chrome | sort | tail -1)
export DISPLAY=:1                         # if running headless with Xvfb

# NotLetters API key (for OTP fetching)
# echo "YOUR_KEY" > NOTLETTERS_API_KEY

# Proxy (residential required for TCCD/Park, optional for HCC)
# export PROXY_SERVER="socks5://gw.foxyproxy.online:1002"
# export PROXY_USER="YOUR_USER"
# export PROXY_PASS="YOUR_PASS"

# Scripts location (CDP shim + cdp launcher)
export HERMES_HOME="$HOME"               # or wherever you put cloakbrowser_cdp.py
```

### 4. Run scripts

```bash
# All scripts are now self-discovering for the venv/binary paths.
# Just run with the right python:
~/venv/bin/python templates/tccd_full_application.py

# Or set env and run:
CLOAKBROWSER_BINARY_PATH=~/.cloakbrowser/chromium-146.0.7680.177.5/chrome \
  ~/venv/bin/python templates/tccd_full_application.py
```

### 5. CDP mode (humanize shim)

```bash
# Put cloakbrowser_cdp.py and cdp_humanize_shim.py in $HERMES_HOME
# Terminal 1:
DISPLAY=:1 python3 $HERMES_HOME/cloakbrowser_cdp.py acc_01

# Terminal 2:
~/venv/bin/python3 $HERMES_HOME/cdp_humanize_shim.py --listen 9223 --upstream-port 9222

# Connect hermes tools:
hermes config set browser.cdp_url http://127.0.0.1:9223
hermes config set browser.auto_local_for_private_urls false
```

---

## What was removed / made portable

| Was | Now |
|-----|-----|
| `/root/.cloakbrowser/chromium-146.0.7680.177.5/chrome` | auto-detect from `~/.cloakbrowser/chromium-*/chrome` |
| `/usr/local/lib/hermes-unlocked/venv/lib/python3.11/site-packages` | auto-detect from `~/venv` or `~/.cloakbrowser/venv` |
| `/home/hermes/.venv/bin/python3` | `~/venv/bin/python3` or any venv with cloakbrowser |
| `/root/cloakbrowser_cdp.py` | `$HERMES_HOME/cloakbrowser_cdp.py` |
| `os.environ["DISPLAY"] = ":1"` | `os.environ.setdefault("DISPLAY", ":1")` — respects existing env |

## What stays server-specific (intentionally)

- `references/personas.md` — real credentials, Gmail donors, SSNs. **Replace before use.**
- `templates/tccd_full_application.py` PERSONA dict — Sebastien Albrook data. Edit for new persona.
- Proxy credentials in `references/personas.md` — FoxyProxy fp_93b6ddf1 (expired). Replace with new.
- `/tmp/` paths for status/cmd files — fine for any Linux server, no change needed.

---

## Key pitfalls (from references/)

- **CloakBrowser binary**: must be auto-detected or set via env, NOT hardcoded path
- **venv**: must have `cloakbrowser` + `playwright` installed, NOT system python3
- **DISPLAY**: must be set to `:1` if using Xvfb (VNC) on headless server
- **Proxy**: residential required for TCCD/Park (SheerID rejects datacenter IPs)
- **reCAPTCHA**: manual solve via VNC — only 2 steps need it (Create Account + Login)
- **OTP codes expire in 5 min**: start OTP polling immediately after trigger
- **SheerID Year field**: `.fill()` → only 1 char (React); use `click + Ctrl+A + Delete + type(delay=80)`
- **SheerID docUpload**: both files in ONE curl call, second call = invalidStep
- **TCCD phone format**: `XXX-XXX-XXXX` with dashes, field `address1_telephone2`
