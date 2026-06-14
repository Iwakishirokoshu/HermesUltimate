"""Cloak browser dashboard API."""

from __future__ import annotations

import asyncio
import hmac
import json
import os
import re
import shlex
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import APIRouter, File, Form, HTTPException, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from hermes_cli import cloak_native
from tools.cloak._cdp_client import CDPError, cdp_http_url, cdp_version, list_targets
from tools.cloak._files import ensure_private_dir, write_private_bytes, write_private_text
from tools.cloak.cookies import cloak_cookies_import


router = APIRouter(tags=["cloak"])

PROFILE_RE = re.compile(r"^[A-Za-z0-9_.-]+$")


class ActiveProfileRequest(BaseModel):
    name: str


class CloakProfileCreate(BaseModel):
    name: str
    fingerprint_seed: int | None = None
    proxy: str | None = None
    timezone: str | None = None
    locale: str | None = None
    platform: str = "windows"
    user_agent: str | None = None
    screen_width: int = 1920
    screen_height: int = 1080
    gpu_vendor: str | None = None
    gpu_renderer: str | None = None
    hardware_concurrency: int | None = None
    humanize: bool = True
    human_preset: str = "default"
    headless: bool = False
    geoip: bool = False
    color_scheme: str | None = None
    launch_args: list[str] = Field(default_factory=list)
    notes: str | None = None
    assigned_to: str = "manual"
    auto_launch: bool = False


class CloakProfileUpdate(BaseModel):
    name: str | None = None
    fingerprint_seed: int | None = None
    proxy: str | None = None
    timezone: str | None = None
    locale: str | None = None
    platform: str | None = None
    user_agent: str | None = None
    screen_width: int | None = None
    screen_height: int | None = None
    gpu_vendor: str | None = None
    gpu_renderer: str | None = None
    hardware_concurrency: int | None = None
    humanize: bool | None = None
    human_preset: str | None = None
    headless: bool | None = None
    geoip: bool | None = None
    color_scheme: str | None = None
    launch_args: list[str] | None = None
    notes: str | None = None
    assigned_to: str | None = None
    auto_launch: bool | None = None


def _vault_root() -> Path:
    return Path(os.environ.get("HERMES_VAULT_PATH", "~/HermesVault")).expanduser().resolve()


def _cloak_root() -> Path:
    raw = os.environ.get("HERMES_CLOAK_PATH")
    if raw:
        return Path(raw).expanduser().resolve()
    return _vault_root() / "Sessions" / "cloak"


def _profiles_root() -> Path:
    return Path(
        os.environ.get("HERMES_BROWSER_PROFILES")
        or os.environ.get("HERMES_CLOAK_PROFILES")
        or (_cloak_root() / "profiles")
    ).expanduser().resolve()


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
    ensure_private_dir(path)
    ensure_private_dir(path / "cookies")
    return path


def _profile_entry(path: Path, active: str) -> dict[str, Any]:
    return {
        "name": path.name,
        "path": str(path),
        "active": path.name == active,
        "updated_at": datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).isoformat(),
    }


def _list_profiles() -> list[dict[str, Any]]:
    native_profiles = cloak_native.list_profiles()
    if native_profiles:
        return native_profiles
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


def _profile_or_404(profile_id: str) -> dict[str, Any]:
    profile = cloak_native.get_profile(profile_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    return profile


def _cloak_ws_auth_ok(websocket: WebSocket) -> bool:
    if bool(getattr(websocket.app.state, "auth_required", False)):
        ticket = websocket.query_params.get("ticket", "")
        if not ticket:
            return False
        try:
            from hermes_cli.dashboard_auth.ws_tickets import consume_ticket

            consume_ticket(ticket)
            return True
        except Exception:
            return False

    expected = str(getattr(websocket.app.state, "session_token", "") or "")
    token = websocket.query_params.get("token", "")
    return bool(expected and token and hmac.compare_digest(token.encode(), expected.encode()))


@router.get("/api/cloak/profiles")
async def get_cloak_profiles() -> dict[str, Any]:
    default_profile = cloak_native.ensure_default_profile()
    profiles = _list_profiles()
    active = cloak_native.read_active_profile() or {
        "id": default_profile["id"],
        "name": default_profile["name"],
        "cdp_url": cloak_native.read_active_cdp_url(),
    }
    active_key = str(active.get("id") or active.get("name") or "")
    active_profile = next(
        (
            profile
            for profile in profiles
            if profile.get("id") == active_key
            or profile.get("name") == active_key
            or profile.get("active")
        ),
        active,
    )
    return {
        "profiles": profiles,
        "active": active_profile.get("name") or active_profile.get("id"),
        "active_profile": active_profile,
        "root": str(cloak_native.browser_profiles_root()),
        "manager_root": str(cloak_native.manager_root()),
        "dependencies": cloak_native.dependency_status(),
    }


@router.post("/api/cloak/profiles", status_code=201)
async def create_cloak_profile(body: CloakProfileCreate) -> dict[str, Any]:
    try:
        profile = cloak_native.create_profile(body.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return {"ok": True, "profile": profile}


@router.get("/api/cloak/profiles/{profile_id}")
async def get_cloak_profile(profile_id: str) -> dict[str, Any]:
    return {"profile": _profile_or_404(profile_id)}


@router.put("/api/cloak/profiles/{profile_id}")
async def update_cloak_profile(profile_id: str, body: CloakProfileUpdate) -> dict[str, Any]:
    profile = _profile_or_404(profile_id)
    if profile["status"] == "running":
        raise HTTPException(status_code=409, detail="Stop the profile before editing launch settings")
    updated = cloak_native.update_profile(profile["id"], body.model_dump(exclude_unset=True))
    return {"ok": True, "profile": updated}


@router.delete("/api/cloak/profiles/{profile_id}")
async def delete_cloak_profile(profile_id: str) -> dict[str, Any]:
    profile = _profile_or_404(profile_id)
    if profile.get("name") == "default":
        raise HTTPException(status_code=400, detail="The default profile cannot be deleted")
    return {"ok": cloak_native.delete_profile(profile["id"])}


@router.post("/api/cloak/profiles/{profile_id}/launch")
async def launch_cloak_profile(profile_id: str) -> dict[str, Any]:
    profile = _profile_or_404(profile_id)
    try:
        launched = await asyncio.to_thread(cloak_native.NATIVE_MANAGER.launch, profile["id"])
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return {"ok": True, "profile": launched}


@router.post("/api/cloak/profiles/{profile_id}/stop")
async def stop_cloak_profile(profile_id: str) -> dict[str, Any]:
    profile = _profile_or_404(profile_id)
    stopped = await asyncio.to_thread(cloak_native.NATIVE_MANAGER.stop, profile["id"])
    return {"ok": True, "stopped": stopped}


@router.post("/api/cloak/profiles/{profile_id}/activate")
async def activate_cloak_profile(profile_id: str) -> dict[str, Any]:
    profile = _profile_or_404(profile_id)
    if profile["status"] != "running":
        profile = await asyncio.to_thread(cloak_native.NATIVE_MANAGER.launch, profile["id"])
    cloak_native.write_active_profile(profile, profile.get("cdp_url"))
    return {"ok": True, "active": profile["name"], "profile": profile}


@router.get("/api/cloak/dependencies")
async def cloak_dependencies() -> dict[str, Any]:
    return cloak_native.dependency_status()


@router.get("/api/cloak/novnc/{asset_path:path}")
async def cloak_novnc_public_asset(asset_path: str) -> FileResponse:
    try:
        asset = cloak_native.novnc_asset_path(asset_path)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid noVNC path") from exc
    return FileResponse(asset)


@router.post("/api/cloak/profile/active")
async def set_cloak_active_profile(body: ActiveProfileRequest) -> dict[str, Any]:
    name = _validate_profile(body.name)
    profile = cloak_native.get_profile(name)
    if profile:
        if profile["status"] != "running":
            try:
                profile = await asyncio.to_thread(cloak_native.NATIVE_MANAGER.launch, profile["id"])
            except Exception as exc:
                raise HTTPException(status_code=503, detail=str(exc)) from exc
        cloak_native.write_active_profile(profile, profile.get("cdp_url"))
        return {"ok": True, "active": profile["name"], "path": profile["user_data_dir"], "profile": profile}

    profile_dir = _ensure_profile(name)
    marker = _active_marker()
    ensure_private_dir(marker.parent)
    write_private_text(marker, name + "\n")
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
    ensure_private_dir(target_dir)
    target = target_dir / _safe_upload_name(file.filename)

    content = await file.read()
    write_private_bytes(target, content)
    cdp_result = await cloak_cookies_import(str(target))
    return {
        "ok": True,
        "profile": profile_name,
        "path": str(target),
        "bytes": len(content),
        "cdp": cdp_result,
    }


@router.get("/api/cloak/profiles/{profile_id}/novnc/{asset_path:path}")
async def cloak_novnc_asset(profile_id: str, asset_path: str) -> FileResponse:
    _profile_or_404(profile_id)
    try:
        asset = cloak_native.novnc_asset_path(asset_path)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid noVNC path") from exc
    return FileResponse(asset)


async def _ws_to_ws(websocket: WebSocket, upstream: Any) -> None:
    while True:
        message = await websocket.receive()
        if message.get("type") == "websocket.disconnect":
            break
        if message.get("bytes") is not None:
            await upstream.send(message["bytes"])
        elif message.get("text") is not None:
            await upstream.send(message["text"])


async def _ws_from_ws(websocket: WebSocket, upstream: Any) -> None:
    while True:
        message = await upstream.recv()
        if isinstance(message, bytes):
            await websocket.send_bytes(message)
        else:
            await websocket.send_text(str(message))


@router.websocket("/api/cloak/profiles/{profile_id}/vnc-ws")
async def cloak_profile_vnc_ws(websocket: WebSocket, profile_id: str) -> None:
    if not _cloak_ws_auth_ok(websocket):
        await websocket.close(code=1008)
        return
    profile = cloak_native.get_profile(profile_id)
    if not profile or profile["status"] != "running" or not profile.get("novnc_port"):
        await websocket.close(code=4004)
        return
    requested = websocket.scope.get("subprotocols", [])
    subprotocol = "binary" if "binary" in requested else None
    await websocket.accept(subprotocol=subprotocol)
    try:
        import websockets
    except ImportError:
        await websocket.close(code=1011)
        return

    upstream_url = f"ws://127.0.0.1:{profile['novnc_port']}/websockify"
    try:
        async with websockets.connect(
            upstream_url,
            subprotocols=["binary"],
            max_size=None,
            ping_interval=None,
            compression=None,
        ) as upstream:
            to_upstream = asyncio.create_task(_ws_to_ws(websocket, upstream))
            from_upstream = asyncio.create_task(_ws_from_ws(websocket, upstream))
            done, pending = await asyncio.wait(
                {to_upstream, from_upstream},
                return_when=asyncio.FIRST_COMPLETED,
            )
            for task in pending:
                task.cancel()
            await asyncio.gather(*done, return_exceptions=True)
    except Exception:
        try:
            await websocket.close(code=1011)
        except Exception:
            pass


@router.websocket("/api/ws/cloak-activity")
async def cloak_activity(websocket: WebSocket) -> None:
    if not _cloak_ws_auth_ok(websocket):
        await websocket.close(code=1008)
        return
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
