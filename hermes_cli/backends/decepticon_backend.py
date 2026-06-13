from __future__ import annotations

import asyncio
import inspect
import json
import logging
import os
import re
from collections.abc import AsyncIterator, Callable
from typing import Any

import httpx

from hermes_cli.backends.base import AgentBackend, StreamEvent

logger = logging.getLogger(__name__)

_DONE = object()
_APPROVE_CHOICES = {"once", "session", "always", "approve", "approved", "yes", "true"}
_OPS_KIND_RE = re.compile(r"^[A-Za-z0-9_.-]+$")


async def start_ops(
    kind: str,
    *,
    base_url: str | None = None,
    timeout: float = 30.0,
    client_factory: Callable[[], Any] | None = None,
) -> dict[str, Any]:
    """Ask the Decepticon LangGraph backend to start an ops workload."""

    ops_kind = str(kind or "").strip()
    if not ops_kind or not _OPS_KIND_RE.fullmatch(ops_kind):
        raise ValueError("Invalid ops kind")

    target = (
        base_url
        or os.getenv("DECEPTICON_LANGGRAPH_URL")
        or "http://localhost:2024"
    ).rstrip("/")
    payload = {
        "input": {
            "messages": [
                {
                    "role": "user",
                    "content": f"Start Decepticon ops workload: {ops_kind}",
                }
            ],
            "ops_kind": ops_kind,
        },
        "metadata": {
            "source": "hermes-dashboard",
            "ops_kind": ops_kind,
        },
    }

    client = client_factory() if client_factory is not None else httpx.AsyncClient(timeout=timeout)
    try:
        response = await client.post(f"{target}/runs", json=payload)
        response.raise_for_status()
        try:
            data = response.json()
        except ValueError:
            data = {"raw": response.text}
        if not isinstance(data, dict):
            data = {"data": data}

        run_id = data.get("run_id") or data.get("id") or data.get("runId")
        return {
            "ok": True,
            "kind": ops_kind,
            "status": str(data.get("status") or "submitted"),
            "run_id": str(run_id) if run_id else None,
            "message": f"{ops_kind} ops submitted to LangGraph",
            "response": data,
        }
    except httpx.HTTPStatusError as exc:
        body = exc.response.text[:1000]
        return {
            "ok": False,
            "kind": ops_kind,
            "status": "error",
            "message": f"LangGraph returned HTTP {exc.response.status_code}: {body}",
        }
    except httpx.RequestError as exc:
        return {
            "ok": False,
            "kind": ops_kind,
            "status": "unavailable",
            "message": f"LangGraph unavailable at {target}: {exc}",
        }
    finally:
        close = getattr(client, "aclose", None)
        if callable(close):
            maybe_awaitable = close()
            if inspect.isawaitable(maybe_awaitable):
                await maybe_awaitable


class DecepticonBackend(AgentBackend):
    """LangGraph SSE adapter for the Decepticon backend."""

    def __init__(
        self,
        base_url: str | None = None,
        *,
        timeout: float = 300.0,
        approval_handler: Callable[[dict[str, Any]], Any] | None = None,
        client_factory: Callable[[], Any] | None = None,
    ) -> None:
        self.base_url = (
            base_url
            or os.getenv("DECEPTICON_LANGGRAPH_URL")
            or "http://localhost:2024"
        ).rstrip("/")
        self.timeout = timeout
        self.approval_handler = approval_handler
        self._client_factory = client_factory

    async def stream(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
        system_prompt: str,
    ) -> AsyncIterator[StreamEvent]:
        payload = {
            "input": {
                "messages": messages,
                "tools": tools,
                "system_prompt": system_prompt,
            }
        }

        client = self._make_client()
        try:
            async with client.stream(
                "POST",
                self._url("/runs/stream"),
                json=payload,
            ) as response:
                response.raise_for_status()
                async for langgraph_event in self._iter_sse(response):
                    if langgraph_event is _DONE:
                        break
                    async for event in self._map_langgraph_event(client, langgraph_event):
                        yield event
        finally:
            close = getattr(client, "aclose", None)
            if callable(close):
                maybe_awaitable = close()
                if inspect.isawaitable(maybe_awaitable):
                    await maybe_awaitable

    def _make_client(self) -> Any:
        if self._client_factory is not None:
            return self._client_factory()
        return httpx.AsyncClient(timeout=self.timeout)

    def _url(self, path: str) -> str:
        return f"{self.base_url}{path if path.startswith('/') else '/' + path}"

    async def _iter_sse(self, response: Any) -> AsyncIterator[dict[str, Any] | object]:
        event_name: str | None = None
        data_lines: list[str] = []

        async for raw_line in response.aiter_lines():
            line = str(raw_line).rstrip("\r")
            if not line:
                decoded = self._decode_sse_event(event_name, data_lines)
                event_name = None
                data_lines = []
                if decoded is not None:
                    yield decoded
                continue

            if line.startswith(":"):
                continue

            field, separator, value = line.partition(":")
            if not separator:
                continue
            if value.startswith(" "):
                value = value[1:]

            if field == "event":
                event_name = value
            elif field == "data":
                data_lines.append(value)

        decoded = self._decode_sse_event(event_name, data_lines)
        if decoded is not None:
            yield decoded

    def _decode_sse_event(
        self,
        event_name: str | None,
        data_lines: list[str],
    ) -> dict[str, Any] | object | None:
        if not data_lines:
            return None

        raw_data = "\n".join(data_lines).strip()
        if raw_data == "[DONE]":
            return _DONE

        try:
            decoded = json.loads(raw_data)
        except json.JSONDecodeError:
            decoded = {"data": raw_data}

        if isinstance(decoded, dict):
            event = dict(decoded)
        else:
            event = {"data": decoded}

        if event_name and "event" not in event:
            event["event"] = event_name
        return event

    async def _map_langgraph_event(
        self,
        client: Any,
        event: dict[str, Any],
    ) -> AsyncIterator[StreamEvent]:
        hitl_payload = self._extract_hitl_request(event)
        if hitl_payload is not None:
            approval_data = self._to_approval_request(event, hitl_payload)
            yield StreamEvent("hitl_request", approval_data)
            decision = await self._await_approval(approval_data)
            await self._resume_run(client, approval_data, decision)
            return

        token = self._extract_token(event)
        if token:
            yield StreamEvent("token", {"text": token})
            return

        tool_call = self._extract_tool_call(event)
        if tool_call is not None:
            yield StreamEvent("tool_call", tool_call)
            return

        tool_result = self._extract_tool_result(event)
        if tool_result is not None:
            yield StreamEvent("tool_result", tool_result)

    def _event_name(self, event: dict[str, Any]) -> str:
        value = (
            event.get("event")
            or event.get("type")
            or event.get("kind")
            or event.get("name")
            or ""
        )
        return str(value).lower()

    def _event_data(self, event: dict[str, Any]) -> dict[str, Any]:
        data = event.get("data")
        if isinstance(data, dict):
            return data
        return event

    def _extract_token(self, event: dict[str, Any]) -> str:
        event_name = self._event_name(event)
        data = self._event_data(event)

        if not any(
            marker in event_name
            for marker in (
                "chat_model_stream",
                "llm_stream",
                "token",
                "message",
                "messages",
                "text_delta",
            )
        ):
            return ""

        candidates = [
            data.get("token"),
            data.get("text"),
            data.get("content"),
            event.get("token"),
            event.get("text"),
            event.get("content"),
        ]

        chunk = data.get("chunk") or event.get("chunk")
        if isinstance(chunk, dict):
            candidates.extend(
                [
                    chunk.get("content"),
                    chunk.get("text"),
                    chunk.get("token"),
                ]
            )

        message = data.get("message") or event.get("message")
        if isinstance(message, dict):
            candidates.extend([message.get("content"), message.get("text")])

        for candidate in candidates:
            text = self._coerce_text(candidate)
            if text:
                return text
        return ""

    def _extract_tool_call(self, event: dict[str, Any]) -> dict[str, Any] | None:
        event_name = self._event_name(event)
        data = self._event_data(event)
        if not (
            "tool_start" in event_name
            or "tool_call" in event_name
            or data.get("type") == "tool_call"
        ):
            return None

        return {
            "id": data.get("id") or data.get("tool_call_id") or event.get("run_id"),
            "name": data.get("name") or data.get("tool") or event.get("name"),
            "args": data.get("args")
            if data.get("args") is not None
            else data.get("arguments")
            if data.get("arguments") is not None
            else data.get("input"),
            "raw": event,
        }

    def _extract_tool_result(self, event: dict[str, Any]) -> dict[str, Any] | None:
        event_name = self._event_name(event)
        data = self._event_data(event)
        if not (
            "tool_end" in event_name
            or "tool_result" in event_name
            or data.get("type") == "tool_result"
        ):
            return None

        return {
            "id": data.get("id") or data.get("tool_call_id") or event.get("run_id"),
            "name": data.get("name") or data.get("tool") or event.get("name"),
            "output": data.get("output")
            if data.get("output") is not None
            else data.get("result"),
            "raw": event,
        }

    def _extract_hitl_request(self, event: dict[str, Any]) -> dict[str, Any] | None:
        data = self._event_data(event)
        for key in (
            "hitl_request",
            "approval_request",
            "command_approval_request",
            "interrupt",
        ):
            nested = data.get(key) if isinstance(data, dict) else None
            if isinstance(nested, dict):
                return dict(nested)
            nested = event.get(key)
            if isinstance(nested, dict):
                return dict(nested)

        event_name = self._event_name(event)
        if any(
            marker in event_name
            for marker in (
                "hitl",
                "human_input_required",
                "approval_request",
                "command-approval-request",
                "interrupt",
            )
        ):
            return dict(data)

        if data.get("requires_approval") is True:
            return dict(data)

        return None

    def _to_approval_request(
        self,
        event: dict[str, Any],
        hitl_payload: dict[str, Any],
    ) -> dict[str, Any]:
        command = (
            hitl_payload.get("command")
            or hitl_payload.get("cmd")
            or hitl_payload.get("tool_input")
            or hitl_payload.get("input")
            or hitl_payload.get("prompt")
            or "decepticon HITL request"
        )
        description = (
            hitl_payload.get("description")
            or hitl_payload.get("reason")
            or hitl_payload.get("message")
            or "Decepticon requested human approval before continuing."
        )
        run_id = self._extract_run_id(event, hitl_payload)

        return {
            "type": "command-approval-request",
            "command": self._coerce_text(command) or str(command),
            "description": self._coerce_text(description) or str(description),
            "pattern_key": "decepticon_hitl",
            "pattern_keys": ["decepticon_hitl"],
            "run_id": run_id,
            "raw": hitl_payload,
        }

    async def _await_approval(self, approval_data: dict[str, Any]) -> dict[str, Any]:
        if self.approval_handler is not None:
            result = self.approval_handler(approval_data)
            if inspect.isawaitable(result):
                result = await result
            return self._normalize_approval_result(result)

        try:
            from tools import approval as approval_mod

            session_key = approval_mod.get_current_session_key("default")
            with approval_mod._lock:  # type: ignore[attr-defined]
                notify_cb = approval_mod._gateway_notify_cbs.get(session_key)  # type: ignore[attr-defined]

            if notify_cb is None:
                approval_mod.submit_pending(session_key, approval_data)
                return {
                    "approved": False,
                    "choice": "pending_approval",
                    "message": "No gateway approval callback registered.",
                }

            decision = await asyncio.to_thread(
                approval_mod._await_gateway_decision,  # type: ignore[attr-defined]
                session_key,
                notify_cb,
                approval_data,
                surface="decepticon",
            )
            choice = str(decision.get("choice") or "deny").lower()
            return {
                "approved": bool(decision.get("resolved")) and choice in _APPROVE_CHOICES,
                "choice": choice,
                "message": None,
            }
        except Exception as exc:
            logger.warning("Decepticon HITL approval failed closed: %s", exc)
            return {"approved": False, "choice": "error", "message": str(exc)}

    def _normalize_approval_result(self, result: Any) -> dict[str, Any]:
        if isinstance(result, dict):
            approved = bool(result.get("approved"))
            choice = str(result.get("choice") or ("once" if approved else "deny")).lower()
            return {
                "approved": approved or choice in _APPROVE_CHOICES,
                "choice": choice,
                "message": result.get("message"),
            }
        if isinstance(result, bool):
            return {
                "approved": result,
                "choice": "once" if result else "deny",
                "message": None,
            }

        choice = str(result or "deny").lower()
        return {
            "approved": choice in _APPROVE_CHOICES,
            "choice": choice,
            "message": None,
        }

    async def _resume_run(
        self,
        client: Any,
        approval_data: dict[str, Any],
        decision: dict[str, Any],
    ) -> None:
        run_id = approval_data.get("run_id")
        if not run_id:
            logger.warning("Decepticon HITL request did not include run_id; cannot resume")
            return

        payload = {
            "input": {
                "approved": bool(decision.get("approved")),
                "choice": decision.get("choice", "deny"),
                "message": decision.get("message"),
                "approval": approval_data,
            }
        }
        response = await client.post(self._url(f"/runs/{run_id}/resume"), json=payload)
        response.raise_for_status()

    def _extract_run_id(
        self,
        event: dict[str, Any],
        payload: dict[str, Any],
    ) -> str | None:
        for source in (payload, event, self._event_data(event)):
            value = source.get("run_id") or source.get("runId")
            if value:
                return str(value)
            run = source.get("run")
            if isinstance(run, dict) and run.get("id"):
                return str(run["id"])
        return None

    def _coerce_text(self, value: Any) -> str:
        if value is None:
            return ""
        if isinstance(value, str):
            return value
        if isinstance(value, list):
            parts: list[str] = []
            for item in value:
                if isinstance(item, dict):
                    parts.append(
                        self._coerce_text(item.get("text") or item.get("content"))
                    )
                else:
                    parts.append(self._coerce_text(item))
            return "".join(parts)
        if isinstance(value, dict):
            return self._coerce_text(value.get("text") or value.get("content"))
        return str(value)
