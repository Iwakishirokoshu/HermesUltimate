# Hermes vnc-cloak

`vnc-cloak` wraps the official CloakHQ/CloakBrowser image with the Hermes VNC,
noVNC, and CDP bridge.

The patched browser comes from `cloakhq/cloakbrowser`. Hermes adds:

- Xvfb/openbox/x11vnc/noVNC so the browser is visible at port `6080`.
- A stable CDP endpoint on port `9222`.
- Persistent profiles mounted at `/profiles/<CLOAK_PROFILE>`.
- Environment-driven launch controls for humanize, proxy, locale, timezone,
  fingerprint seed, viewport, and raw `--fingerprint-*` Chromium args.

## Configure

Set these in `~/.hermes/stack.env` on an installed machine, or in `stack/.env`
for local development:

```env
CLOAK_PROFILE=default
CLOAK_HUMANIZE=true
CLOAK_GEOIP=false
CLOAK_VIEWPORT=1920x1080
CLOAK_FINGERPRINT_SEED=
CLOAK_PROXY=
CLOAK_LOCALE=
CLOAK_TIMEZONE=
CLOAK_EXTRA_ARGS=
```

The C++ stealth patches are already inside the CloakHQ binary. Use
`CLOAK_EXTRA_ARGS` only for CloakBrowser fingerprint flags such as:

```env
CLOAK_EXTRA_ARGS=--fingerprint-noise=false --fingerprint-storage-quota=500
```

Profiles live under the host path in `HERMES_BROWSER_PROFILES`, defaulting to
`~/.hermes/browser-profiles`. Changing `CLOAK_PROFILE` switches the persistent
profile directory used by cookies, localStorage, cache, and extensions.
