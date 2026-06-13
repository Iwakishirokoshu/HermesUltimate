# FlowPilot — ChatGPT Account Automation Reference

**Repo:** https://github.com/QLHazyCoder/FlowPilot
**Type:** Chrome Extension (MV3), vanilla JS, Chinese developer
**Purpose:** Bulk registration of ChatGPT/OpenAI/Kiro/Grok accounts → handoff to API aggregator pools

## Architecture

- **Service Worker** (background) + Content Scripts + Side Panel
- `workflow-engine.js` — step execution, state, resume after pause
- `flow-registry.js` — flows: openai / kiro / grok
- `tab-runtime.js` — resilient command delivery to content scripts
- Storage: `chrome.storage.session` + `chrome.storage.local`

## Email Providers (11+)

| Provider | Notes |
|---|---|
| Hotmail/Outlook | Local Python helper + remote API |
| 2925.com | Web account pool, 24h cooldown after limit |
| iCloud Hide My Email | Alias generation |
| DuckDuckGo relay | Alias generation |
| Cloudflare Temp Email | API |
| Gmail `+tag` | Alias generation |
| QQ / 163 / 126 | Web automation |
| LuckMail | API |
| Custom pool | Your own email list |

## SMS Providers (5)

- **5sim** — full lifecycle: buy number by country/price, poll, reuse, ban/cancel
- **HeroSMS** — default
- NexSMS, MaDao, Custom URL

## IP Proxy

- PAC script via `chrome.proxy.settings.set`
- `webRequest.onAuthRequired` — auto-fill credentials
- Fail-close: blocks `chatgpt.com/openai.com` if proxy down
- DNS-over-HTTPS (Google) for proxy host resolution
- IP detection via 12+ endpoints (`ip-api.com`, `ipinfo.io`, `chatgpt.com/cdn-cgi/trace`, etc.)

## OpenAI Registration Flow (10 steps)

1. Open ChatGPT → click "Sign up"
2. Generate/supply email or buy phone number
3. Fill password
4. Get SMS/email OTP (polling)
5. Fill name, DOB
6. Wait for success
7. Open OAuth URL from aggregator
8. Get login OTP
9. Confirm OAuth consent
10. POST callback → aggregator API

## OAuth Chain (Account → API Pool)

```
Platform generates: https://auth.openai.com/authorize?...&redirect_uri=https://sub2api.com/callback
Browser opens (already logged in) → redirects to redirect_uri?code=AUTH_CODE
Extension intercepts code via chrome.webRequest
POST code to: /api/admin/oauth/exchange-code
Platform stores access_token+refresh_token → account in pool
```

Target platforms: **SUB2API**, **Codex2API**, **CPA**, **Kiro.rs**, **webchat2api** (Grok)

## Anti-Detection Mechanisms

| Mechanism | Implementation |
|---|---|
| Human delays | `operation-delay.js`, default 2s between actions |
| Random names/dates | `data/names.js` |
| Proxy rotation | IP auto-switch by success count |
| Cookie cleanup | `browsingData` clear before each registration |
| Cloudflare recovery | Auto-click "Retry" on block |
| Risk alert handling | 15-30 min pause at `max_check_attempts` |
| Phone reuse limit | Max 3 uses per number |

## Permissions Used

```
debugger, browsingData, cookies, proxy,
webRequest, webRequestAuthProvider,
declarativeNetRequest, scripting, tabs, storage, sidePanel
```

## What FlowPilot Does NOT Cover

- SheerID student verification
- Headless/Playwright (browser extension only)
- CAPTCHA solving (only manual bypass)

## Playwright Equivalent for OAuth Interception

```python
auth_code = None

def on_request(request):
    global auth_code
    if 'callback/openai' in request.url and 'code=' in request.url:
        import re
        m = re.search(r'code=([^&]+)', request.url)
        if m: auth_code = m.group(1)

page.on('request', on_request)
page.goto(oauth_url)
page.wait_for_function("() => window.location.href.includes('code=')", timeout=15000)
# auth_code is now set
```
