"""Cloak browser dashboard API."""

from __future__ import annotations

import asyncio
import json
import os
import re
import shlex
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import APIRouter, File, Form, HTTPException, UploadFile, WebSocket, WebSocketDisconnect
from pydantic import BaseModel

from tools.cloak._cdp_client import CDPError, cdp_http_url, cdp_version, list_targets
from tools.cloak.cookies import cloak_cookies_import


router = APIRouter(tags=["cloak"])

PROFILE_RE = re.compile(r"^[A-Za-z0-9_.-]+$")


class ActiveProfileRequest(BaseModel):
    name: str


def _vault_root() -> Path:
    return Path(os.environ.get("HERMES_VAULT_PATH", "~/HermesVault")).expanduser().resolve()


def _cloak_root() -> Path:
    raw = os.environ.get("HERMES_CLOAK_PATH")
    if raw:
        return Path(raw).expanduser().resolve()
    return _vault_root() / "Sessions" / "cloak"


def _profiles_root() -> Path:
    return _cloak_root() / "profiles"


def _active_marker() -> Path:
    return _cloak_root() / "active_profile"


def _validate_profile(name: str) -> str:
    value = str(name or "").strip()
    if not value or not PROFILE_RE.fullmatch(value):
        raise HTTPException(status_code=400, detail="Invalid profile name")
    return value


def _profile_dir(name: str) -> Path:
    profile = _validate_profile(name)
    return (_profiles_root() / profile).resolve()


def _read_active_profile() -> str:
    marker = _active_marker()
    if marker.is_file():
        try:
            value = marker.read_text(encoding="utf-8").strip()
            if value and PROFILE_RE.fullmatch(value):
                return value
        except OSError:
            pass
    return "default"


def _ensure_profile(name: str) -> Path:
    path = _profile_dir(name)
    root = _profiles_root().resolve()
    try:
        path.relative_to(root)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid profile path") from exc
    path.mkdir(parents=True, exist_ok=True)
    (path / "cookies").mkdir(parents=True, exist_ok=True)
    return path


def _profile_entry(path: Path, active: str) -> dict[str, Any]:
    return {
        "name": path.name,
        "path": str(path),
        "active": path.name == active,
        "updated_at": datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).isoformat(),
    }


def _list_profiles() -> list[dict[str, Any]]:
    active = _read_active_profile()
    _ensure_profile(active)
    root = _profiles_root()
    return [
        _profile_entry(path, active)
        for path in sorted(root.iterdir(), key=lambda item: item.name.lower())
        if path.is_dir() and PROFILE_RE.fullmatch(path.name)
    ]


def _restart_chromium(profile_dir: Path) -> dict[str, Any]:
    raw = os.environ.get("CLOAK_RESTART_COMMAND", "").strip()
    if not raw:
        return {
            "ok": False,
            "status": "skipped",
            "message": "Set CLOAK_RESTART_COMMAND to restart Chromium with this profile.",
        }

    env = os.environ.copy()
    env["CLOAK_USER_DATA_DIR"] = str(profile_dir)
    env["CHROME_USER_DATA_DIR"] = str(profile_dir)
    try:
        completed = subprocess.run(
            shlex.split(raw),
            env=env,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=20,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"ok": False, "status": "error", "message": str(exc)}

    return {
        "ok": completed.returncode == 0,
        "status": "restarted" if completed.returncode == 0 else "error",
        "returncode": completed.returncode,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
    }


def _safe_upload_name(filename: str | None) -> str:
    raw = Path(filename or "cookies.json").name
    clean = re.sub(r"[^A-Za-z0-9_.-]+", "_", raw).strip("._-")
    return clean or "cookies.json"


@router.get("/api/cloak/profiles")
async def get_cloak_profiles() -> dict[str, Any]:
    active = _read_active_profile()
    return {"profiles": _list_profiles(), "active": active, "root": str(_profiles_root())}


@router.post("/api/cloak/profile/active")
async def set_cloak_active_profile(body: ActiveProfileRequest) -> dict[str, Any]:
    name = _validate_profile(body.name)
    profile_dir = _ensure_profile(name)
    marker = _active_marker()
    marker.parent.mkdir(parents=True, exist_ok=True)
    marker.write_text(name + "\n", encoding="utf-8")
    restart = _restart_chromium(profile_dir)
    return {"ok": True, "active": name, "path": str(profile_dir), "restart": restart}


@router.post("/api/cloak/cookies/import")
async def import_cloak_cookies(
    file: UploadFile = File(...),
    profile: str | None = Form(default=None),
) -> dict[str, Any]:
    profile_name = _validate_profile(profile or _read_active_profile())
    profile_dir = _ensure_profile(profile_name)
    target_dir = profile_dir / "cookies" / "imports"
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / _safe_upload_name(file.filename)

    content = await file.read()
    target.write_bytes(content)
    cdp_result = await cloak_cookies_import(str(target))
    return {
        "ok": True,
        "profile": profile_name,
        "path": str(target),
        "bytes": len(content),
        "cdp": cdp_result,
    }


@router.websocket("/api/ws/cloak-activity")
async def cloak_activity(websocket: WebSocket) -> None:
    await websocket.accept()
    try:
        while True:
            try:
                version, targets = await asyncio.gather(
                    asyncio.to_thread(cdp_version),
                    asyncio.to_thread(list_targets),
                )
                page_targets = [target for target in targets if target.get("type") == "page"]
                state = "active" if page_targets else "idle"
                payload = {
                    "state": state,
                    "cdp_url": cdp_http_url(),
                    "browser": version.get("Browser"),
                    "targets": len(page_targets),
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
            except CDPError as exc:
                payload = {
                    "state": "error",
                    "error": str(exc),
                    "cdp_url": cdp_http_url(),
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
            await websocket.send_text(json.dumps(payload))
            await asyncio.sleep(2)
    except WebSocketDisconnect:
        pass
