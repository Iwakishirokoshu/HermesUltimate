"""Decepticon dashboard API."""

from __future__ import annotations

import inspect
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from hermes_cli.backends import decepticon_backend


router = APIRouter(prefix="/api/decepticon", tags=["decepticon"])


class OpsRequest(BaseModel):
    kind: str


def _vault_root() -> Path:
    return Path(os.environ.get("HERMES_VAULT_PATH", "~/HermesVault")).expanduser().resolve()


def _engagements_root() -> Path:
    return _vault_root() / "Engagements"


def _safe_child(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
    except ValueError:
        return False
    return True


def _iso_from_mtime(timestamp: float) -> str:
    return datetime.fromtimestamp(timestamp, timezone.utc).isoformat()


def _read_status(path: Path) -> str | None:
    for candidate in (
        path / ".meta" / "status.json",
        path / "status.json",
        path / ".status.json",
    ):
        if not candidate.is_file():
            continue
        try:
            data = json.loads(candidate.read_text(encoding="utf-8-sig"))
        except (OSError, json.JSONDecodeError):
            continue
        if isinstance(data, dict):
            value = data.get("status") or data.get("state")
            if value:
                return str(value)
    return None


def _read_summary(path: Path) -> str:
    candidates = [
        path / "SUMMARY.md",
        path / "README.md",
        path / "summary.md",
        path / "scope.md",
    ]
    candidates.extend(sorted(path.glob("*.md"))[:3])

    for candidate in candidates:
        if not candidate.is_file():
            continue
        try:
            text = candidate.read_text(encoding="utf-8-sig", errors="replace")
        except OSError:
            continue
        lines = [
            line.strip().lstrip("#").strip()
            for line in text.splitlines()
            if line.strip()
        ]
        if lines:
            return " ".join(lines)[:280]
    return ""


def _engagement_entry(path: Path, root: Path) -> dict[str, Any]:
    files = [item for item in path.rglob("*") if item.is_file()]
    mtimes = [item.stat().st_mtime for item in files]
    mtimes.append(path.stat().st_mtime)

    rel = path.relative_to(root).as_posix()
    return {
        "name": path.name,
        "path": f"Engagements/{rel}",
        "status": _read_status(path) or ("active" if files else "empty"),
        "updated_at": _iso_from_mtime(max(mtimes)),
        "files": len(files),
        "summary": _read_summary(path),
    }


@router.get("/engagements")
async def get_decepticon_engagements() -> dict[str, Any]:
    root = _engagements_root()
    if not root.exists():
        return {"engagements": [], "root": str(root)}
    if not root.is_dir():
        raise HTTPException(status_code=500, detail=f"Engagements path is not a directory: {root}")

    engagements: list[dict[str, Any]] = []
    for path in sorted(root.iterdir(), key=lambda item: item.name.lower()):
        if not path.is_dir() or path.name.startswith(".") or not _safe_child(path, root):
            continue
        engagements.append(_engagement_entry(path, root))

    engagements.sort(key=lambda item: item.get("updated_at") or "", reverse=True)
    return {"engagements": engagements, "root": str(root)}


@router.post("/ops")
async def start_decepticon_ops(body: OpsRequest) -> dict[str, Any]:
    try:
        result = decepticon_backend.start_ops(body.kind)
        if inspect.isawaitable(result):
            result = await result
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    if not isinstance(result, dict):
        return {"ok": True, "status": "submitted", "message": str(result)}
    return result
