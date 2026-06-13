"""HermesVault dashboard API."""

from __future__ import annotations

import json
import os
import re
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel


router = APIRouter(prefix="/api/vault", tags=["vault"])

WIKILINK_RE = re.compile(r"\[\[([^\]|#]+)(#[^\]|]+)?(\|[^\]]+)?\]\]")
TIERS = {"Hot", "Warm", "Cold"}


class PromoteRequest(BaseModel):
    path: str
    tier: str


def _vault_root() -> Path:
    return Path(os.environ.get("HERMES_VAULT_PATH", "~/HermesVault")).expanduser().resolve()


def _safe_path(path: str) -> Path:
    raw = Path(str(path or "").replace("\\", "/"))
    if not str(path).strip() or raw.is_absolute() or ".." in raw.parts:
        raise HTTPException(status_code=400, detail="path must stay inside vault")
    root = _vault_root()
    target = (root / raw).resolve()
    try:
        target.relative_to(root)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="path escapes vault") from exc
    return target


def _relative(path: Path) -> str:
    return path.resolve().relative_to(_vault_root()).as_posix()


def _iso(timestamp: float) -> str:
    return datetime.fromtimestamp(timestamp, timezone.utc).isoformat()


def _markdown_files() -> list[Path]:
    root = _vault_root()
    if not root.exists():
        return []
    return sorted(path for path in root.rglob("*.md") if path.is_file())


def _summary(path: Path) -> str:
    if not path.is_file() or path.suffix.lower() != ".md":
        return ""
    try:
        text = path.read_text(encoding="utf-8-sig", errors="replace")
    except OSError:
        return ""
    for line in text.splitlines():
        clean = line.strip().lstrip("#").strip()
        if clean:
            return clean[:220]
    return ""


def _tree_entry(path: Path) -> dict[str, Any]:
    return {
        "name": path.name,
        "path": _relative(path),
        "type": "directory" if path.is_dir() else "file",
        "size": path.stat().st_size if path.is_file() else None,
        "updated_at": _iso(path.stat().st_mtime),
        "summary": _summary(path),
    }


def _computed_health() -> dict[str, Any]:
    files = _markdown_files()
    paths_by_key: set[str] = set()
    stems: dict[str, list[str]] = defaultdict(list)
    for file_path in files:
        rel = _relative(file_path)
        paths_by_key.add(rel)
        paths_by_key.add(rel.removesuffix(".md"))
        paths_by_key.add(file_path.stem)
        stems[file_path.stem.lower()].append(rel)

    total_links = 0
    valid_links = 0
    dead_pages: list[dict[str, Any]] = []
    for file_path in files:
        try:
            content = file_path.read_text(encoding="utf-8-sig", errors="replace")
        except OSError:
            continue
        for match in WIKILINK_RE.finditer(content):
            total_links += 1
            target = match.group(1)
            if target in paths_by_key:
                valid_links += 1
                continue
            dead_pages.append(
                {
                    "name": target,
                    "path": _relative(file_path),
                    "type": "file",
                    "summary": f"Broken link: {target}",
                }
            )

    duplicates = [
        {"canonical": key, "paths": sorted(values)}
        for key, values in sorted(stems.items())
        if len(values) > 1
    ]
    return {
        "ok": True,
        "vault": str(_vault_root()),
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "pages": len(files),
        "hit_rate": 1.0 if total_links == 0 else valid_links / total_links,
        "dead_pages": dead_pages,
        "duplicates": duplicates,
    }


def _load_health() -> dict[str, Any]:
    health_path = _vault_root() / ".meta" / "health.json"
    if not health_path.is_file():
        return _computed_health()
    try:
        data = json.loads(health_path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError) as exc:
        data = _computed_health()
        data["health_error"] = f"Invalid vault health cache: {exc}"
        return data
    if not isinstance(data, dict):
        data = _computed_health()
        data["health_error"] = "Invalid vault health cache shape"
        return data
    data.setdefault("ok", True)
    data.setdefault("vault", str(_vault_root()))
    return data


def _target_for_tier(source: Path, tier: str) -> Path:
    if tier not in TIERS:
        raise HTTPException(status_code=400, detail="tier must be Hot, Warm, or Cold")

    rel_parts = list(source.relative_to(_vault_root()).parts)
    if len(rel_parts) >= 3 and rel_parts[0] == "Wiki" and rel_parts[1] in TIERS:
        rel_parts[1] = tier
        return _vault_root().joinpath(*rel_parts)
    return _vault_root() / "Wiki" / tier / source.name


def _replace_wikilinks(old_rel: str, new_rel: str) -> int:
    old_target = old_rel.removesuffix(".md")
    new_target = new_rel.removesuffix(".md")
    aliases = {old_rel, old_target, Path(old_rel).stem}
    changed = 0

    def repl(match: re.Match[str]) -> str:
        target, anchor, label = match.group(1), match.group(2) or "", match.group(3) or ""
        if target not in aliases:
            return match.group(0)
        return f"[[{new_target}{anchor}{label}]]"

    for file_path in _markdown_files():
        try:
            original = file_path.read_text(encoding="utf-8-sig", errors="replace")
        except OSError:
            continue
        updated = WIKILINK_RE.sub(repl, original)
        if updated != original:
            file_path.write_text(updated, encoding="utf-8")
            changed += 1
    return changed


@router.get("/health")
async def get_vault_health() -> dict[str, Any]:
    return _load_health()


@router.get("/tree")
async def get_vault_tree(folder: str = Query(default="")) -> dict[str, Any]:
    root = _vault_root()
    base = _safe_path(folder) if folder else root
    if not base.exists():
        return {"folder": folder, "entries": [], "root": str(root)}
    if base.is_file():
        return {"folder": folder, "entries": [_tree_entry(base)], "root": str(root)}

    entries = [_tree_entry(path) for path in base.iterdir() if not path.name.startswith(".")]
    entries.sort(key=lambda item: (item["type"] != "directory", str(item["name"]).lower()))
    return {"folder": folder, "entries": entries, "root": str(root)}


@router.post("/promote")
async def promote_vault_entry(request: PromoteRequest) -> dict[str, Any]:
    source = _safe_path(request.path)
    if not source.is_file():
        raise HTTPException(status_code=404, detail="file not found")
    target = _target_for_tier(source, request.tier)
    if target.exists() and target.resolve() != source.resolve():
        raise HTTPException(status_code=409, detail=f"target already exists: {_relative(target)}")

    old_rel = _relative(source)
    target.parent.mkdir(parents=True, exist_ok=True)
    source.rename(target)
    new_rel = _relative(target)
    updated_links = _replace_wikilinks(old_rel, new_rel)

    return {
        "ok": True,
        "path": new_rel,
        "old_path": old_rel,
        "tier": request.tier,
        "updated_links": updated_links,
    }
