"""Hermes wrapper for Agent-Reach."""

from __future__ import annotations

import asyncio
import concurrent.futures
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

from tools.registry import registry


REACH_SCHEMA = {
    "name": "reach",
    "description": (
        "Run Agent-Reach commands through its CLI, or call the Agent-Reach MCP "
        "stdio server for status/doctor checks."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "channel": {
                "type": "string",
                "description": (
                    "Agent-Reach channel or 'agent-reach' for root CLI commands."
                ),
            },
            "action": {
                "type": "string",
                "description": "Action or root Agent-Reach CLI command to run.",
            },
            "args": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Extra positional CLI arguments.",
                "default": [],
            },
            "mcp": {
                "type": "boolean",
                "description": "Use Agent-Reach MCP stdio mode instead of CLI mode.",
                "default": False,
            },
            "timeout": {
                "type": "integer",
                "description": "Command timeout in seconds.",
                "default": 60,
            },
        },
        "required": ["channel", "action"],
        "additionalProperties": True,
    },
}

_ROOT_CLI_ALIASES = {"agent-reach", "reach", "cli"}
_MCP_STATUS_ACTIONS = {"doctor", "get_status", "status"}


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


def check_reach_requirements() -> bool:
    return _agent_reach_bin() is not None


def _coerce_timeout(value: Any) -> int:
    try:
        timeout = int(value)
    except (TypeError, ValueError):
        timeout = 60
    return max(1, timeout)


def _append_cli_value(command: list[str], key: str, value: Any) -> None:
    if value is None or value is False:
        return
    flag = "--" + key.replace("_", "-")
    if value is True:
        command.append(flag)
        return
    if isinstance(value, (list, tuple)):
        for item in value:
            command.extend([flag, str(item)])
        return
    if isinstance(value, dict):
        command.extend([flag, json.dumps(value, ensure_ascii=False)])
        return
    command.extend([flag, str(value)])


def _build_cli_command(
    agent_reach: str,
    channel: str,
    action: str,
    extra_args: list[str],
    extra_kwargs: dict[str, Any],
) -> list[str]:
    command = [agent_reach]
    if channel in _ROOT_CLI_ALIASES:
        command.append(action)
    else:
        command.extend([channel, action])

    command.extend(str(item) for item in extra_args)
    for key in sorted(extra_kwargs):
        _append_cli_value(command, key, extra_kwargs[key])
    return command


def _run_cli(channel: str, action: str, kwargs: dict[str, Any]) -> dict[str, Any]:
    agent_reach = _agent_reach_bin()
    if not agent_reach:
        return {
            "ok": False,
            "mode": "cli",
            "error": "agent-reach executable not found",
        }

    timeout = _coerce_timeout(kwargs.pop("timeout", 60))
    extra_args = kwargs.pop("args", []) or []
    if not isinstance(extra_args, list):
        extra_args = [str(extra_args)]

    command = _build_cli_command(agent_reach, channel, action, extra_args, kwargs)
    creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    try:
        completed = subprocess.run(
            command,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            creationflags=creationflags,
        )
    except subprocess.TimeoutExpired as exc:
        return {
            "ok": False,
            "mode": "cli",
            "command": command,
            "error": f"agent-reach timed out after {timeout}s",
            "stdout": exc.stdout or "",
            "stderr": exc.stderr or "",
        }
    except OSError as exc:
        return {
            "ok": False,
            "mode": "cli",
            "command": command,
            "error": str(exc),
        }

    return {
        "ok": completed.returncode == 0,
        "mode": "cli",
        "command": command,
        "returncode": completed.returncode,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
    }


def _mcp_tool_name(channel: str, action: str) -> str:
    if action in _MCP_STATUS_ACTIONS:
        return "get_status"
    if channel in _ROOT_CLI_ALIASES:
        return action
    return action


def _normalise_mcp_result(result: Any) -> Any:
    content = getattr(result, "content", None)
    if not content:
        return result
    items: list[Any] = []
    for item in content:
        text = getattr(item, "text", None)
        if text is None:
            items.append(str(item))
            continue
        try:
            items.append(json.loads(text))
        except json.JSONDecodeError:
            items.append(text)
    return items[0] if len(items) == 1 else items


async def _call_mcp(channel: str, action: str, kwargs: dict[str, Any]) -> dict[str, Any]:
    timeout = _coerce_timeout(kwargs.pop("timeout", 60))
    arguments = kwargs.pop("arguments", None)
    if arguments is None:
        arguments = dict(kwargs)
    if not isinstance(arguments, dict):
        arguments = {"value": arguments}

    try:
        from mcp import ClientSession, StdioServerParameters
        from mcp.client.stdio import stdio_client
    except Exception as exc:
        return {
            "ok": False,
            "mode": "mcp",
            "error": f"mcp client unavailable: {exc}",
        }

    tool_name = _mcp_tool_name(channel, action)
    params = StdioServerParameters(
        command=sys.executable,
        args=["-m", "agent_reach.integrations.mcp_server"],
    )

    try:
        async with stdio_client(params) as (read_stream, write_stream):
            async with ClientSession(read_stream, write_stream) as session:
                await asyncio.wait_for(session.initialize(), timeout=timeout)
                result = await asyncio.wait_for(
                    session.call_tool(tool_name, arguments),
                    timeout=timeout,
                )
    except Exception as exc:
        return {
            "ok": False,
            "mode": "mcp",
            "tool": tool_name,
            "error": str(exc),
        }

    return {
        "ok": True,
        "mode": "mcp",
        "tool": tool_name,
        "result": _normalise_mcp_result(result),
    }


def _run_coro(coro):
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)

    if not loop.is_running():
        return loop.run_until_complete(coro)

    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
        return pool.submit(lambda: asyncio.run(coro)).result()


def reach(channel: str, action: str, **kwargs: Any) -> dict[str, Any]:
    channel = (channel or "").strip()
    action = (action or "").strip()
    if not channel or not action:
        return {
            "ok": False,
            "error": "channel and action are required",
        }

    call_kwargs = dict(kwargs)
    use_mcp = bool(call_kwargs.pop("mcp", False)) or channel == "--mcp"
    if use_mcp:
        return _run_coro(_call_mcp(channel, action, call_kwargs))
    return _run_cli(channel, action, call_kwargs)


def _handle_reach(args: dict[str, Any], **_: Any) -> str:
    args = dict(args or {})
    channel = args.pop("channel", "")
    action = args.pop("action", "")
    return json.dumps(reach(channel, action, **args), ensure_ascii=False)


registry.register(
    name="reach",
    toolset="reach",
    schema=REACH_SCHEMA,
    handler=_handle_reach,
    check_fn=check_reach_requirements,
    description=REACH_SCHEMA["description"],
    emoji="R",
)
