from __future__ import annotations

import asyncio
import json
import logging
import os
import re
from datetime import datetime, timezone
from typing import Any
from urllib import error, request

try:
    from langchain.agents.middleware import AgentMiddleware
except Exception:  # pragma: no cover - keeps overlay importable outside Decepticon.
    class AgentMiddleware:  # type: ignore[no-redef]
        pass


log = logging.getLogger(__name__)

KG_WRITE_TOOLS = frozenset({"kg_add_node", "kg_add_edge"})
DEFAULT_VAULT_API_URL = "http://vault-api:8090"


class VaultSyncMiddleware(AgentMiddleware):
    """Append Decepticon KG writes to HermesVault findings pages."""

    def __init__(
        self,
        *,
        vault_api_url: str | None = None,
        timeout: float = 5.0,
        enabled: bool | None = None,
    ) -> None:
        super().__init__()
        self.vault_api_url = (
            vault_api_url
            or os.getenv("HERMES_VAULT_API_URL")
            or DEFAULT_VAULT_API_URL
        ).rstrip("/")
        self.timeout = timeout
        self.enabled = (
            _truthy(os.getenv("HERMES_DECEPTICON_VAULT_SYNC", "1"))
            if enabled is None
            else enabled
        )

    def before_node_call(self, node_name: str, state: Any = None, **kwargs: Any) -> None:
        """Compatibility hook for graph wrappers that expose before_node_call."""
        del state
        tool_name = str(kwargs.get("tool_name") or kwargs.get("name") or node_name)
        args = kwargs.get("args") or kwargs.get("tool_args") or kwargs
        self._sync_if_kg_write(tool_name, _coerce_mapping(args), result=None)

    def wrap_tool_call(self, request_obj: Any, handler: Any) -> Any:
        result = handler(request_obj)
        tool_name, args = _request_tool_call(request_obj)
        self._sync_if_kg_write(tool_name, args, result=result)
        return result

    async def awrap_tool_call(self, request_obj: Any, handler: Any) -> Any:
        result = await handler(request_obj)
        tool_name, args = _request_tool_call(request_obj)
        await asyncio.to_thread(self._sync_if_kg_write, tool_name, args, result)
        return result

    def _sync_if_kg_write(
        self,
        tool_name: str,
        args: dict[str, Any],
        result: Any,
    ) -> None:
        if not self.enabled or tool_name not in KG_WRITE_TOOLS:
            return

        event = _kg_event(tool_name, args, result)
        path = f"Wiki/Findings/{_safe_host_slug(event['host'])}.md"
        content = _format_markdown(event)
        payload = json.dumps({"path": path, "content": content}).encode("utf-8")
        req = request.Request(
            f"{self.vault_api_url}/append",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with request.urlopen(req, timeout=self.timeout) as response:
                response.read()
        except (OSError, error.URLError, error.HTTPError) as exc:
            log.warning("vault-sync append failed for %s: %s", path, exc)


def get_middleware(**kwargs: Any) -> list[VaultSyncMiddleware]:
    """Factory shape accepted by Decepticon plugin middleware loading."""
    return [VaultSyncMiddleware(**_factory_kwargs(kwargs))]


def before_node_call(node_name: str, state: Any = None, **kwargs: Any) -> None:
    """Module-level hook for graph configs that import a plain callable."""
    VaultSyncMiddleware().before_node_call(node_name, state, **kwargs)


def _factory_kwargs(kwargs: dict[str, Any]) -> dict[str, Any]:
    allowed = {"vault_api_url", "timeout", "enabled"}
    return {key: value for key, value in kwargs.items() if key in allowed}


def _truthy(value: str) -> bool:
    return value.strip().lower() not in {"", "0", "false", "no", "off"}


def _request_tool_call(request_obj: Any) -> tuple[str, dict[str, Any]]:
    tool = getattr(request_obj, "tool", None)
    tool_name = str(
        getattr(tool, "name", "")
        or getattr(request_obj, "tool_name", "")
        or ""
    )

    tool_call = getattr(request_obj, "tool_call", None)
    if isinstance(tool_call, dict):
        tool_name = tool_name or str(tool_call.get("name") or "")
        args = _coerce_mapping(tool_call.get("args") or tool_call.get("arguments"))
        return tool_name, args

    args = (
        getattr(request_obj, "args", None)
        or getattr(request_obj, "tool_args", None)
        or getattr(request_obj, "input", None)
    )
    return tool_name, _coerce_mapping(args)


def _coerce_mapping(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return dict(value)
    if isinstance(value, str) and value.strip():
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError:
            return {"value": value}
        if isinstance(parsed, dict):
            return parsed
        return {"value": parsed}
    return {}


def _kg_event(tool_name: str, args: dict[str, Any], result: Any) -> dict[str, Any]:
    props = _coerce_mapping(args.get("props"))
    merged = {**props, **args}
    return {
        "tool": tool_name,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "host": _pick_host(merged),
        "kind": str(args.get("kind") or props.get("kind") or ""),
        "label": str(args.get("label") or props.get("label") or ""),
        "src": str(args.get("src") or ""),
        "dst": str(args.get("dst") or ""),
        "weight": args.get("weight"),
        "props": props,
        "result": _result_text(result),
    }


def _pick_host(values: dict[str, Any]) -> str:
    for key in (
        "host",
        "hostname",
        "ip",
        "target",
        "target_host",
        "domain",
        "fqdn",
        "url",
        "service",
        "key",
    ):
        value = values.get(key)
        if value:
            return str(value)
    return "general"


def _safe_host_slug(host: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9_.-]+", "_", host.strip()).strip("._-")
    return slug[:120] or "general"


def _result_text(result: Any) -> str:
    content = getattr(result, "content", None)
    if content is not None:
        return str(content)
    if result is None:
        return ""
    return str(result)


def _format_markdown(event: dict[str, Any]) -> str:
    title = event["label"] or event["kind"] or event["tool"]
    lines = [
        "",
        f"## {title}",
        "",
        f"- time: {event['timestamp']}",
        f"- source: {event['tool']}",
    ]
    if event["kind"]:
        lines.append(f"- kind: {event['kind']}")
    if event["src"] or event["dst"]:
        lines.append(f"- edge: {event['src']} -> {event['dst']}")
    if event["weight"] is not None:
        lines.append(f"- weight: {event['weight']}")
    if event["props"]:
        lines.extend(["", "```json", json.dumps(event["props"], indent=2, sort_keys=True), "```"])
    if event["result"]:
        lines.extend(["", "Result:", "", "```json", event["result"], "```"])
    return "\n".join(lines) + "\n"


__all__ = [
    "DEFAULT_VAULT_API_URL",
    "KG_WRITE_TOOLS",
    "VaultSyncMiddleware",
    "before_node_call",
    "get_middleware",
]
