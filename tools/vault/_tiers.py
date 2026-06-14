from __future__ import annotations

from typing import Any


TIER_FOLDERS = {
    "hot": "Wiki/Hot",
    "warm": "Wiki/Warm",
    "cold": "Wiki/Cold",
    "findings": "Wiki/Findings",
}


def _clean_path(value: str) -> str:
    return str(value or "").replace("\\", "/").strip("/")


def normalize_tier(tier: str | None) -> str:
    cleaned = str(tier or "").strip().lower()
    return cleaned if cleaned in TIER_FOLDERS else ""


def tier_folder(tier: str | None) -> str:
    return TIER_FOLDERS.get(normalize_tier(tier), "")


def scoped_folder(folder: str = "", tier: str | None = "") -> str:
    prefix = tier_folder(tier)
    cleaned = _clean_path(folder)
    if not prefix:
        return cleaned
    if not cleaned:
        return prefix
    if cleaned == prefix or cleaned.startswith(prefix + "/"):
        return cleaned
    if cleaned.startswith("Wiki/"):
        return cleaned
    return f"{prefix}/{cleaned}"


def _result_path(item: Any) -> str:
    if not isinstance(item, dict):
        return ""
    for key in ("path", "file", "relpath", "name", "title"):
        value = item.get(key)
        if value:
            return _clean_path(str(value))
    return ""


def _matches_tier(item: Any, prefix: str) -> bool:
    path = _result_path(item)
    return bool(path and (path == prefix or path.startswith(prefix + "/")))


def filter_search_results(data: Any, tier: str | None = "", limit: int | None = None) -> Any:
    prefix = tier_folder(tier)
    if not prefix or not isinstance(data, dict):
        return data

    out = dict(data)
    for key in ("results", "items", "matches"):
        rows = out.get(key)
        if isinstance(rows, list):
            filtered = [item for item in rows if _matches_tier(item, prefix)]
            if limit is not None:
                filtered = filtered[: max(0, int(limit))]
            out[key] = filtered
            out["tier"] = normalize_tier(tier)
            out["tier_prefix"] = prefix
            return out
    return out
