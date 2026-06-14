"""Souls dashboard API."""

from __future__ import annotations

import json
import sqlite3
from dataclasses import asdict
from pathlib import Path
from typing import Any

import yaml
from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel

from hermes_cli.soul_router import SoulConfig, SoulRouter


router = APIRouter(tags=["souls"])
_soul_router = SoulRouter()
_subscribers: set[WebSocket] = set()


class SoulUpdate(BaseModel):
    yaml: str


def _soul_path(name: str) -> Path:
    if not name or Path(name).name != name or any(sep in name for sep in ("/", "\\")):
        raise HTTPException(status_code=400, detail="Invalid soul name")
    path = (_soul_router.souls_dir / f"{name}.yaml").resolve()
    root = _soul_router.souls_dir.resolve()
    if path.parent != root:
        raise HTTPException(status_code=400, detail="Invalid soul path")
    return path


def _load_raw_yaml(name: str) -> str:
    path = _soul_path(name)
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"Soul not found: {name}")
    try:
        return path.read_text(encoding="utf-8")
    except OSError as exc:
        raise HTTPException(status_code=500, detail=f"Unable to read soul: {exc}") from exc


def _serialize_soul(config: SoulConfig) -> dict[str, Any]:
    payload = asdict(config)
    raw_yaml = _load_raw_yaml(config.name)
    payload["yaml"] = raw_yaml
    payload["raw_yaml"] = raw_yaml
    return payload


def _active_souls() -> dict[str, str]:
    if not _soul_router.db_path.exists():
        return {}

    try:
        with sqlite3.connect(_soul_router.db_path) as conn:
            rows = conn.execute(
                "SELECT chat_id, soul_name FROM chat_soul ORDER BY chat_id"
            ).fetchall()
    except sqlite3.Error:
        return {}
    return {str(chat_id): str(soul_name) for chat_id, soul_name in rows}


def _souls_payload(chat_id: str = "default") -> dict[str, Any]:
    configs = []
    active = _active_souls()
    active_soul = _soul_router.get_active_soul(chat_id).name
    all_configs = _soul_router._load_configs()

    for name in sorted(all_configs):
        config = all_configs[name]
        item = _serialize_soul(config)
        active_chat_ids = [cid for cid, soul_name in active.items() if soul_name == name]
        item["active_chat_ids"] = active_chat_ids
        item["active"] = name == active_soul
        configs.append(item)

    return {
        "souls": configs,
        "active": active,
        "active_soul": active_soul,
        "active_chat_id": chat_id,
        "chat_id": chat_id,
    }


async def _broadcast_souls_changed() -> None:
    if not _subscribers:
        return

    message = json.dumps({"type": "souls_changed"})
    stale: list[WebSocket] = []
    for websocket in list(_subscribers):
        try:
            await websocket.send_text(message)
        except RuntimeError:
            stale.append(websocket)
    for websocket in stale:
        _subscribers.discard(websocket)


@router.get("/api/souls")
async def list_souls(chat_id: str = "default") -> dict[str, Any]:
    return _souls_payload(chat_id)


@router.get("/api/souls/{name}")
async def get_soul(name: str) -> dict[str, Any]:
    configs = _soul_router._load_configs()
    if name not in configs:
        raise HTTPException(status_code=404, detail=f"Soul not found: {name}")
    return _serialize_soul(configs[name])


@router.put("/api/souls/{name}")
async def update_soul(name: str, body: SoulUpdate) -> dict[str, Any]:
    path = _soul_path(name)

    try:
        parsed = yaml.safe_load(body.yaml) or {}
    except yaml.YAMLError as exc:
        raise HTTPException(status_code=400, detail=f"Invalid YAML: {exc}") from exc
    if not isinstance(parsed, dict):
        raise HTTPException(status_code=400, detail="Soul YAML must be a mapping")
    if str(parsed.get("name", "")) != name:
        raise HTTPException(status_code=400, detail="Soul YAML name must match URL")

    try:
        SoulConfig.from_mapping(parsed)
    except (KeyError, TypeError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=f"Invalid soul config: {exc}") from exc

    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(body.yaml.rstrip() + "\n", encoding="utf-8")
    except OSError as exc:
        raise HTTPException(status_code=500, detail=f"Unable to write soul: {exc}") from exc

    _soul_router._configs_cache = None
    await _broadcast_souls_changed()
    return {"ok": True, "soul": _serialize_soul(_soul_router._load_configs()[name])}


@router.websocket("/api/ws/souls")
async def souls_websocket(websocket: WebSocket) -> None:
    await websocket.accept()
    _subscribers.add(websocket)
    try:
        await websocket.send_text(json.dumps({"type": "ready"}))
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        _subscribers.discard(websocket)
