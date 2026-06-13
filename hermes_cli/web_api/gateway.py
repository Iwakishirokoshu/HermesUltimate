"""Gateway bots dashboard API."""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any

import yaml
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from hermes_cli.config import get_hermes_home


router = APIRouter(prefix="/api/gateway", tags=["gateway"])

_BOT_ID_RE = re.compile(r"^[A-Za-z0-9_.@:-]+$")


class GatewayBotUpdate(BaseModel):
    default_soul: str | None = None
    allowed_users: list[str] | None = None


def _gateway_yaml_path() -> Path:
    return get_hermes_home() / "gateway.yaml"


def _load_gateway_yaml() -> dict[str, Any]:
    path = _gateway_yaml_path()
    if not path.exists():
        return {}

    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as exc:
        raise HTTPException(status_code=500, detail=f"Invalid gateway.yaml: {exc}") from exc
    except OSError as exc:
        raise HTTPException(status_code=500, detail=f"Unable to read gateway.yaml: {exc}") from exc

    if not isinstance(data, dict):
        raise HTTPException(status_code=500, detail="gateway.yaml must be a mapping")
    return data


def _write_gateway_yaml(data: dict[str, Any]) -> None:
    path = _gateway_yaml_path()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            yaml.safe_dump(data, sort_keys=False, allow_unicode=True),
            encoding="utf-8",
        )
    except OSError as exc:
        raise HTTPException(status_code=500, detail=f"Unable to write gateway.yaml: {exc}") from exc


def _validate_bot_id(bot_id: str) -> str:
    bot_id = str(bot_id or "").strip()
    if not bot_id or not _BOT_ID_RE.fullmatch(bot_id):
        raise HTTPException(status_code=400, detail="Invalid bot id")
    return bot_id


def _coerce_string_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        chunks = value.replace("\n", ",").split(",")
    elif isinstance(value, (list, tuple, set)):
        chunks = list(value)
    else:
        chunks = [value]
    return [str(item).strip() for item in chunks if str(item).strip()]


def _coerce_bool(value: Any, default: bool = True) -> bool:
    if value is None:
        return default
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"1", "true", "yes", "on"}:
            return True
        if lowered in {"0", "false", "no", "off"}:
            return False
        return default
    return bool(value)


def _mask_token(value: Any) -> str:
    token = str(value or "").strip()
    if not token:
        return "not set"
    if len(token) <= 8:
        return "****"
    return f"{token[:4]}...{token[-4:]}"


def _nested_mapping(value: Any, key: str) -> dict[str, Any]:
    nested = value.get(key) if isinstance(value, dict) else None
    return nested if isinstance(nested, dict) else {}


def _bot_id_from_entry(entry: dict[str, Any], index: int, total: int) -> str:
    for key in ("id", "username", "name"):
        raw = str(entry.get(key) or "").strip()
        if raw:
            return raw.lstrip("@")
    return "telegram" if total == 1 else f"telegram-{index + 1}"


def _bot_candidates(entry: dict[str, Any], index: int, total: int) -> set[str]:
    primary = _bot_id_from_entry(entry, index, total)
    candidates = {primary, f"telegram-{index + 1}"}
    if total == 1:
        candidates.add("telegram")
    for key in ("id", "username", "name"):
        raw = str(entry.get(key) or "").strip()
        if raw:
            candidates.add(raw)
            candidates.add(raw.lstrip("@"))
    return candidates


def _bot_payload(bot_id: str, source: str, block: dict[str, Any]) -> dict[str, Any]:
    extra = _nested_mapping(block, "extra")
    token = (
        block.get("token")
        or block.get("bot_token")
        or block.get("api_key")
        or extra.get("token")
        or extra.get("bot_token")
        or extra.get("api_key")
    )
    allowed_users = (
        block.get("allowed_users")
        if "allowed_users" in block
        else extra.get("allowed_users", extra.get("allow_from"))
    )
    default_soul = (
        block.get("default_soul")
        if "default_soul" in block
        else extra.get("default_soul", "default")
    )

    return {
        "id": bot_id,
        "name": block.get("name") or block.get("label") or bot_id,
        "username": str(block.get("username")).lstrip("@") if block.get("username") else None,
        "default_soul": str(default_soul or "default"),
        "allowed_users": _coerce_string_list(allowed_users),
        "token_masked": _mask_token(token),
        "enabled": _coerce_bool(block.get("enabled"), True),
        "source": source,
    }


def _collect_gateway_bots(data: dict[str, Any]) -> list[dict[str, Any]]:
    bots: list[dict[str, Any]] = []
    seen: set[str] = set()

    telegrams = data.get("telegrams")
    if isinstance(telegrams, list):
        entries = [entry for entry in telegrams if isinstance(entry, dict)]
        total = len(entries)
        for index, entry in enumerate(entries):
            bot_id = _bot_id_from_entry(entry, index, total)
            if bot_id in seen:
                continue
            seen.add(bot_id)
            bots.append(_bot_payload(bot_id, "api", entry))

    telegram = data.get("telegram")
    if isinstance(telegram, dict) and "telegram" not in seen:
        seen.add("telegram")
        bots.append(_bot_payload("telegram", "api", telegram))

    raw_bots = data.get("bots")
    if isinstance(raw_bots, dict):
        for bot_id, block in raw_bots.items():
            if not isinstance(block, dict):
                continue
            bot_id = str(block.get("id") or bot_id)
            if bot_id in seen:
                continue
            seen.add(bot_id)
            bots.append(_bot_payload(bot_id, "api", block))
    elif isinstance(raw_bots, list):
        for index, block in enumerate(raw_bots):
            if not isinstance(block, dict):
                continue
            bot_id = str(block.get("id") or block.get("username") or block.get("name") or f"bot-{index + 1}")
            if bot_id in seen:
                continue
            seen.add(bot_id)
            bots.append(_bot_payload(bot_id, "api", block))

    platforms = data.get("platforms")
    if isinstance(platforms, dict):
        for platform_id, block in platforms.items():
            if not isinstance(block, dict):
                continue
            bot_id = str(platform_id)
            if bot_id in seen:
                continue
            seen.add(bot_id)
            bots.append(_bot_payload(bot_id, "platform", block))

    if not any(bot["id"] == "telegram" for bot in bots):
        token = os.environ.get("TELEGRAM_BOT_TOKEN")
        if token:
            bots.append(
                _bot_payload(
                    "telegram",
                    "platform",
                    {
                        "name": "Telegram",
                        "token": token,
                        "default_soul": os.environ.get("TELEGRAM_DEFAULT_SOUL", "default"),
                        "allowed_users": os.environ.get("TELEGRAM_ALLOWED_USERS", ""),
                        "enabled": True,
                    },
                )
            )

    return bots


def _requested_changes(body: GatewayBotUpdate) -> dict[str, Any]:
    changes = body.dict(exclude_unset=True)
    if "default_soul" in changes:
        soul = str(changes["default_soul"] or "").strip()
        if not soul:
            raise HTTPException(status_code=400, detail="default_soul cannot be empty")
        changes["default_soul"] = soul
    if "allowed_users" in changes:
        changes["allowed_users"] = _coerce_string_list(changes["allowed_users"])
    return changes


def _apply_changes(block: dict[str, Any], changes: dict[str, Any]) -> None:
    for key, value in changes.items():
        block[key] = value


def _update_telegram_bot(data: dict[str, Any], bot_id: str, changes: dict[str, Any]) -> bool:
    telegrams = data.get("telegrams")
    if not isinstance(telegrams, list):
        return False

    entries = [entry for entry in telegrams if isinstance(entry, dict)]
    total = len(entries)
    for index, entry in enumerate(entries):
        if bot_id in _bot_candidates(entry, index, total):
            _apply_changes(entry, changes)
            return True
    return False


def _update_bots_section(data: dict[str, Any], bot_id: str, changes: dict[str, Any]) -> bool:
    raw_bots = data.get("bots")
    if isinstance(raw_bots, dict):
        for key, block in raw_bots.items():
            if not isinstance(block, dict):
                continue
            candidates = {str(key), str(block.get("id") or ""), str(block.get("username") or "")}
            if bot_id in candidates or bot_id.lstrip("@") in {item.lstrip("@") for item in candidates}:
                _apply_changes(block, changes)
                return True
    elif isinstance(raw_bots, list):
        for index, block in enumerate(raw_bots):
            if not isinstance(block, dict):
                continue
            candidates = {
                str(block.get("id") or f"bot-{index + 1}"),
                str(block.get("username") or ""),
                str(block.get("name") or ""),
            }
            if bot_id in candidates or bot_id.lstrip("@") in {item.lstrip("@") for item in candidates}:
                _apply_changes(block, changes)
                return True
    return False


def _update_platform_section(data: dict[str, Any], bot_id: str, changes: dict[str, Any]) -> bool:
    platforms = data.get("platforms")
    if not isinstance(platforms, dict):
        return False
    block = platforms.get(bot_id)
    if not isinstance(block, dict):
        return False
    extra = block.setdefault("extra", {})
    if not isinstance(extra, dict):
        extra = {}
        block["extra"] = extra
    _apply_changes(extra, changes)
    return True


def _create_bot(data: dict[str, Any], bot_id: str, changes: dict[str, Any]) -> None:
    if bot_id == "telegram" or bot_id.startswith("telegram-"):
        telegrams = data.setdefault("telegrams", [])
        if not isinstance(telegrams, list):
            telegrams = []
            data["telegrams"] = telegrams
        bot = {"id": bot_id, "enabled": True}
        _apply_changes(bot, changes)
        telegrams.append(bot)
        return

    bots = data.setdefault("bots", {})
    if not isinstance(bots, dict):
        bots = {}
        data["bots"] = bots
    bot = {"id": bot_id, "enabled": True}
    _apply_changes(bot, changes)
    bots[bot_id] = bot


@router.get("/bots")
async def list_gateway_bots() -> dict[str, Any]:
    data = _load_gateway_yaml()
    return {"bots": _collect_gateway_bots(data), "path": str(_gateway_yaml_path())}


@router.put("/bots/{bot_id}")
async def update_gateway_bot(bot_id: str, body: GatewayBotUpdate) -> dict[str, Any]:
    bot_id = _validate_bot_id(bot_id)
    changes = _requested_changes(body)
    data = _load_gateway_yaml()

    updated = (
        _update_telegram_bot(data, bot_id, changes)
        or _update_bots_section(data, bot_id, changes)
        or _update_platform_section(data, bot_id, changes)
    )
    if not updated:
        _create_bot(data, bot_id, changes)

    _write_gateway_yaml(data)
    return {"ok": True, "bot": bot_id}
