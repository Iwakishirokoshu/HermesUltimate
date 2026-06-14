#!/usr/bin/env python3
"""Launch the patched CloakHQ browser as the Hermes VNC/CDP browser."""

from __future__ import annotations

import os
import re
import shlex
import signal
import sys
import time
from pathlib import Path
from typing import Any

from cloakbrowser import binary_info, launch_persistent_context


TRUE_VALUES = {"1", "true", "yes", "y", "on"}
FALSE_VALUES = {"0", "false", "no", "n", "off"}
PROFILE_RE = re.compile(r"^[A-Za-z0-9_.-]+$")


def env_bool(name: str, default: bool) -> bool:
    raw = os.environ.get(name)
    if raw is None or raw.strip() == "":
        return default
    value = raw.strip().lower()
    if value in TRUE_VALUES:
        return True
    if value in FALSE_VALUES:
        return False
    raise ValueError(f"{name} must be a boolean, got {raw!r}")


def env_optional(name: str) -> str | None:
    raw = os.environ.get(name)
    if raw is None:
        return None
    raw = raw.strip()
    return raw or None


def parse_viewport(raw: str | None) -> dict[str, int]:
    value = raw or "1920x1080"
    for sep in ("x", "X", ","):
        if sep in value:
            width, height = value.split(sep, 1)
            return {"width": int(width.strip()), "height": int(height.strip())}
    raise ValueError("CLOAK_VIEWPORT must look like 1920x1080")


def parse_paths(raw: str | None) -> list[str] | None:
    if not raw:
        return None
    return [part.strip() for part in raw.split(os.pathsep) if part.strip()]


def add_arg(args: list[str], name: str, value: str | None) -> None:
    if value:
        args.append(f"--{name}={value}")


def build_proxy() -> str | dict[str, str] | None:
    inline = env_optional("CLOAK_PROXY")
    server = env_optional("CLOAK_PROXY_SERVER")
    if inline:
        return inline
    if not server:
        return None
    proxy: dict[str, str] = {"server": server}
    username = env_optional("CLOAK_PROXY_USERNAME")
    password = env_optional("CLOAK_PROXY_PASSWORD")
    bypass = env_optional("CLOAK_PROXY_BYPASS")
    if username:
        proxy["username"] = username
    if password:
        proxy["password"] = password
    if bypass:
        proxy["bypass"] = bypass
    return proxy


def build_chromium_args(viewport: dict[str, int]) -> list[str]:
    debug_port = int(os.environ.get("CLOAK_DEBUG_PORT", "9223"))
    args = [
        "--no-sandbox",
        f"--remote-debugging-port={debug_port}",
        "--remote-debugging-address=0.0.0.0",
        "--no-first-run",
        "--no-default-browser-check",
        "--disable-dev-shm-usage",
        "--password-store=basic",
        "--use-mock-keychain",
        f"--window-size={viewport['width']},{viewport['height']}",
    ]

    add_arg(args, "fingerprint", env_optional("CLOAK_FINGERPRINT_SEED"))
    add_arg(args, "fingerprint-webrtc-ip", env_optional("CLOAK_WEBRTC_IP"))
    add_arg(args, "fingerprint-storage-quota", env_optional("CLOAK_STORAGE_QUOTA"))
    add_arg(args, "fingerprint-noise", env_optional("CLOAK_FINGERPRINT_NOISE"))

    if env_bool("CLOAK_SYNC_SCREEN_FINGERPRINT", True):
        screen_width = env_optional("CLOAK_SCREEN_WIDTH") or str(viewport["width"])
        screen_height = env_optional("CLOAK_SCREEN_HEIGHT") or str(viewport["height"])
        add_arg(args, "fingerprint-screen-width", screen_width)
        add_arg(args, "fingerprint-screen-height", screen_height)
    else:
        add_arg(args, "fingerprint-screen-width", env_optional("CLOAK_SCREEN_WIDTH"))
        add_arg(args, "fingerprint-screen-height", env_optional("CLOAK_SCREEN_HEIGHT"))

    extra = env_optional("CLOAK_EXTRA_ARGS")
    if extra:
        args.extend(shlex.split(extra))
    return args


def launch_with_compat(profile_dir: Path, options: dict[str, Any]):
    current = dict(options)
    optional = [
        "humanize",
        "human_preset",
        "geoip",
        "stealth_args",
        "extension_paths",
        "color_scheme",
    ]
    while True:
        try:
            return launch_persistent_context(str(profile_dir), **current)
        except TypeError as exc:
            message = str(exc)
            removed = None
            for key in optional:
                if key in current and key in message:
                    removed = key
                    break
            if not removed:
                raise
            print(
                f"[cloakbrowser-launch] installed cloakbrowser does not accept {removed}; retrying without it",
                flush=True,
            )
            current.pop(removed, None)


def main() -> int:
    display = os.environ.get("DISPLAY", ":99")
    profile = os.environ.get("CLOAK_PROFILE", "default").strip() or "default"
    if not PROFILE_RE.fullmatch(profile):
        raise ValueError("CLOAK_PROFILE may contain only letters, numbers, dot, dash, and underscore")
    profile_dir = Path("/profiles") / profile
    profile_dir.mkdir(parents=True, exist_ok=True)
    for lock_name in ("SingletonLock", "SingletonSocket", "SingletonCookie"):
        lock = profile_dir / lock_name
        if lock.exists() or lock.is_symlink():
            lock.unlink(missing_ok=True)

    viewport = parse_viewport(env_optional("CLOAK_VIEWPORT"))
    options: dict[str, Any] = {
        "headless": env_bool("CLOAK_HEADLESS", False),
        "args": build_chromium_args(viewport),
        "viewport": viewport,
    }

    proxy = build_proxy()
    if proxy:
        options["proxy"] = proxy
    for env_name, option_name in (
        ("CLOAK_LOCALE", "locale"),
        ("CLOAK_TIMEZONE", "timezone"),
        ("CLOAK_USER_AGENT", "user_agent"),
        ("CLOAK_COLOR_SCHEME", "color_scheme"),
    ):
        value = env_optional(env_name)
        if value:
            options[option_name] = value

    options["humanize"] = env_bool("CLOAK_HUMANIZE", True)
    preset = env_optional("CLOAK_HUMAN_PRESET")
    if preset:
        options["human_preset"] = preset
    options["geoip"] = env_bool("CLOAK_GEOIP", False)
    options["stealth_args"] = env_bool("CLOAK_STEALTH_ARGS", True)
    extensions = parse_paths(env_optional("CLOAK_EXTENSION_PATHS"))
    if extensions:
        options["extension_paths"] = extensions

    print(f"[cloakbrowser-launch] DISPLAY={display}", flush=True)
    print(f"[cloakbrowser-launch] profile={profile_dir}", flush=True)
    print(f"[cloakbrowser-launch] binary={binary_info()}", flush=True)
    print(
        "[cloakbrowser-launch] options="
        f"headless={options['headless']} humanize={options.get('humanize')} "
        f"geoip={options.get('geoip')} viewport={viewport}",
        flush=True,
    )

    context = launch_with_compat(profile_dir, options)
    page = context.pages[0] if context.pages else context.new_page()
    page.goto("about:blank")

    stopping = False

    def stop(_signum: int, _frame: object) -> None:
        nonlocal stopping
        stopping = True

    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)

    while not stopping:
        time.sleep(1)

    context.close()
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"[cloakbrowser-launch] ERROR: {exc}", file=sys.stderr, flush=True)
        raise
