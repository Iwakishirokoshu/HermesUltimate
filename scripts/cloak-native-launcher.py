#!/usr/bin/env python3
"""Child process for native Hermes Cloak profile launches."""

from __future__ import annotations

import argparse
import json
import os
import shlex
import signal
import subprocess
import sys
import time
from pathlib import Path
from typing import Any


def _popen(cmd: list[str], *, env: dict[str, str], log_path: Path) -> subprocess.Popen:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log = open(log_path, "ab")
    return subprocess.Popen(cmd, env=env, stdout=log, stderr=log)


def _terminate(proc: subprocess.Popen | None) -> None:
    if not proc or proc.poll() is not None:
        return
    proc.terminate()
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
            proc.kill()


def _assert_started(proc: subprocess.Popen, name: str, log_path: Path, delay: float = 0.5) -> None:
    time.sleep(delay)
    if proc.poll() is None:
        return
    tail = ""
    try:
        tail = log_path.read_text(encoding="utf-8", errors="replace")[-1200:]
    except OSError:
        pass
    raise RuntimeError(f"{name} exited during startup. Log tail:\n{tail}")


def _clean_chrome_locks(profile_dir: Path) -> None:
    for name in ("SingletonLock", "SingletonSocket", "SingletonCookie"):
        path = profile_dir / name
        if path.exists() or path.is_symlink():
            path.unlink(missing_ok=True)


def _fingerprint_args(profile: dict[str, Any], cdp_port: int) -> list[str]:
    width = int(profile.get("screen_width") or 1920)
    height = int(profile.get("screen_height") or 1080)
    args = [
        "--no-sandbox",
        "--no-first-run",
        "--no-default-browser-check",
        "--disable-dev-shm-usage",
        "--password-store=basic",
        "--use-mock-keychain",
        "--disable-infobars",
        "--test-type",
        "--use-angle=swiftshader",
        f"--window-size={width},{height}",
        f"--remote-debugging-port={cdp_port}",
        "--remote-debugging-address=127.0.0.1",
        f"--fingerprint={profile.get('fingerprint_seed')}",
        f"--fingerprint-screen-width={width}",
        f"--fingerprint-screen-height={height}",
    ]
    optional_flags = {
        "platform": "fingerprint-platform",
        "gpu_vendor": "fingerprint-gpu-vendor",
        "gpu_renderer": "fingerprint-gpu-renderer",
        "hardware_concurrency": "fingerprint-hardware-concurrency",
    }
    for field, flag in optional_flags.items():
        value = profile.get(field)
        if value not in (None, ""):
            args.append(f"--{flag}={value}")
    for raw in profile.get("launch_args") or []:
        if isinstance(raw, str) and raw.strip():
            args.extend(shlex.split(raw))
    return args


def _launch_browser(config: dict[str, Any]):
    from cloakbrowser import launch_persistent_context

    profile = config["profile"]
    display = int(config["display"])
    cdp_port = int(config["cdp_port"])
    profile_dir = Path(profile["user_data_dir"]).expanduser().resolve()
    profile_dir.mkdir(parents=True, exist_ok=True)
    _clean_chrome_locks(profile_dir)

    os.environ["DISPLAY"] = f":{display}"
    width = int(profile.get("screen_width") or 1920)
    height = int(profile.get("screen_height") or 1080)
    options: dict[str, Any] = {
        "headless": bool(profile.get("headless", False)),
        "args": _fingerprint_args(profile, cdp_port),
        "viewport": {"width": width, "height": max(600, height - 96)},
        "humanize": bool(profile.get("humanize", True)),
        "human_preset": profile.get("human_preset") or "default",
        "geoip": bool(profile.get("geoip", False)),
    }
    for field, option in (
        ("proxy", "proxy"),
        ("timezone", "timezone"),
        ("locale", "locale"),
        ("user_agent", "user_agent"),
        ("color_scheme", "color_scheme"),
    ):
        value = profile.get(field)
        if value not in (None, ""):
            options[option] = value
    context = launch_persistent_context(str(profile_dir), **options)
    page = context.pages[0] if context.pages else context.new_page()
    page.goto("about:blank")
    return context


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    args = parser.parse_args()
    config = json.loads(Path(args.config).read_text(encoding="utf-8"))
    profile = config["profile"]
    display = int(config["display"])
    vnc_port = int(config["vnc_port"])
    novnc_port = int(config["novnc_port"])
    width = int(profile.get("screen_width") or 1920)
    height = int(profile.get("screen_height") or 1080)
    novnc_root = str(config.get("novnc_root") or "/usr/share/novnc")
    log_dir = Path(os.environ.get("HERMES_CLOAK_LOG_DIR", "~/.hermes/cloak/logs")).expanduser()
    env = os.environ.copy()
    env["DISPLAY"] = f":{display}"

    children: list[subprocess.Popen] = []
    context = None
    stopping = False

    def stop(_signum: int, _frame: object) -> None:
        nonlocal stopping
        stopping = True

    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)

    try:
        children.append(
            _popen(
                [
                    "Xvfb",
                    f":{display}",
                    "-screen",
                    "0",
                    f"{width}x{height}x24",
                    "-ac",
                    "+extension",
                    "GLX",
                    "+render",
                    "-noreset",
                ],
                env=env,
                log_path=log_dir / f"xvfb-{display}.log",
            )
        )
        time.sleep(0.5)
        children.append(_popen(["openbox"], env=env, log_path=log_dir / f"openbox-{display}.log"))
        children.append(
            _popen(
                [
                    "x11vnc",
                    "-display",
                    f":{display}",
                    "-forever",
                    "-shared",
                    "-localhost",
                    "-nopw",
                    "-rfbport",
                    str(vnc_port),
                ],
                env=env,
                log_path=log_dir / f"x11vnc-{display}.log",
            )
        )
        websockify_log = log_dir / f"websockify-{display}.log"
        websockify = _popen(
            [
                "websockify",
                "--web",
                novnc_root,
                f"127.0.0.1:{novnc_port}",
                f"127.0.0.1:{vnc_port}",
            ],
            env=env,
            log_path=websockify_log,
        )
        _assert_started(websockify, "websockify", websockify_log)
        children.append(websockify)
        context = _launch_browser(config)
        while not stopping:
            time.sleep(1)
            if any(child.poll() is not None for child in children):
                break
    finally:
        if context is not None:
            try:
                context.close()
            except Exception:
                pass
        for child in reversed(children):
            _terminate(child)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"cloak-native-launcher failed: {exc}", file=sys.stderr, flush=True)
        raise
