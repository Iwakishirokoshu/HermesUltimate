"""Agent-Reach dashboard API."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException


router = APIRouter(prefix="/api/reach", tags=["reach"])


def _reach_status_path() -> Path:
    hermes_home = os.environ.get("HERMES_HOME")
    if hermes_home:
        return Path(hermes_home).expanduser() / "reach-status.json"
    return Path.home() / ".hermes" / "reach-status.json"


def _agent_reach_bin() -> str | None:
    found = shutil.which("agent-reach")
    if found:
        return found

    scripts_dir = Path(sys.executable).resolve().parent
    exe_name = "agent-reach.exe" if os.name == "nt" else "agent-reach"
    candidate = scripts_dir / exe_name
    if candidate.exists():
        return str(candidate)
    return None


def _load_cached(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError) as exc:
        raise HTTPException(status_code=500, detail=f"Invalid reach status cache: {exc}") from exc
    if not isinstance(data, dict):
        raise HTTPException(status_code=500, detail="Invalid reach status cache shape")
    return data


def _run_live_doctor() -> dict[str, Any]:
    agent_reach = _agent_reach_bin()
    if not agent_reach:
        raise HTTPException(status_code=503, detail="agent-reach executable not found")

    try:
        completed = subprocess.run(
            [agent_reach, "doctor", "--json"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=45,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
    except subprocess.TimeoutExpired as exc:
        raise HTTPException(status_code=504, detail="agent-reach doctor timed out") from exc
    except OSError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    if completed.returncode != 0:
        detail = completed.stderr.strip() or completed.stdout.strip() or "agent-reach doctor failed"
        raise HTTPException(status_code=502, detail=detail[:2000])

    try:
        data = json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=502, detail=f"agent-reach doctor returned invalid JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise HTTPException(status_code=502, detail="agent-reach doctor returned unexpected JSON shape")
    return data


def _write_cache(path: Path, data: dict[str, Any]) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    except OSError:
        pass


@router.get("/doctor")
async def get_reach_doctor(live: bool = False) -> dict[str, Any]:
    status_path = _reach_status_path()
    source = "cache"
    data = None if live else _load_cached(status_path)
    if data is None:
        source = "live"
        data = _run_live_doctor()
        _write_cache(status_path, data)

    return {
        "ok": True,
        "source": source,
        "path": str(status_path),
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "channels": data,
    }
