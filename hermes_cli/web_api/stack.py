"""Docker Compose stack dashboard API."""

from __future__ import annotations

import json
import os
import re
import subprocess
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, Query


router = APIRouter(prefix="/api/stack", tags=["stack"])

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_STACK_ROOT = _PROJECT_ROOT / "stack"
_SERVICE_RE = re.compile(r"^[A-Za-z0-9_.-]+$")
_ACTIONS = {"start", "stop", "restart"}
_STATUS_SERVICE_KEYS = ("langgraph", "sandbox", "neo4j", "9router", "vault-api")
_HTTP_PORTS = {
    "9router": 20128,
    "langgraph": 2024,
    "neo4j": 7474,
    "vault-api": 8090,
}


def _resolve_compose_file(raw: str) -> Path:
    path = Path(raw).expanduser()
    return path if path.is_absolute() else (_PROJECT_ROOT / path).resolve()


def _compose_files() -> list[Path]:
    raw = os.environ.get("HERMES_STACK_COMPOSE_FILE") or os.environ.get(
        "HERMES_DOCKER_COMPOSE_FILE"
    )
    if raw:
        return [_resolve_compose_file(raw)]

    stack_file = _STACK_ROOT / "docker-compose.yml"
    if stack_file.exists():
        files = [stack_file]
        decepticon_file = _STACK_ROOT / "docker-compose.decepticon-slim.yml"
        if decepticon_file.exists():
            files.append(decepticon_file)
        return files

    windows_file = _PROJECT_ROOT / "docker-compose.windows.yml"
    if os.name == "nt" and windows_file.exists():
        return [windows_file]

    default_file = _PROJECT_ROOT / "docker-compose.yml"
    return [default_file] if default_file.exists() else []


def _compose_command(*args: str) -> list[str]:
    command = ["docker", "compose"]
    for compose_file in _compose_files():
        command.extend(["-f", str(compose_file)])
    command.extend(args)
    return command


def _run_compose(*args: str, timeout: int = 30) -> subprocess.CompletedProcess[str]:
    try:
        completed = subprocess.run(
            _compose_command(*args),
            cwd=_PROJECT_ROOT,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=503, detail="docker executable not found") from exc
    except subprocess.TimeoutExpired as exc:
        raise HTTPException(status_code=504, detail="docker compose timed out") from exc
    except OSError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    if completed.returncode != 0:
        detail = completed.stderr.strip() or completed.stdout.strip()
        raise HTTPException(status_code=502, detail=detail[:2000] or "docker compose failed")
    return completed


def _parse_compose_json(stdout: str) -> list[dict[str, Any]]:
    text = stdout.strip()
    if not text:
        return []

    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        rows: list[dict[str, Any]] = []
        for line in text.splitlines():
            if not line.strip():
                continue
            try:
                item = json.loads(line)
            except json.JSONDecodeError as exc:
                raise HTTPException(
                    status_code=502,
                    detail=f"docker compose returned invalid JSON: {exc}",
                ) from exc
            if isinstance(item, dict):
                rows.append(item)
        return rows

    if isinstance(parsed, list):
        return [item for item in parsed if isinstance(item, dict)]
    if isinstance(parsed, dict):
        return [parsed]
    raise HTTPException(status_code=502, detail="docker compose returned unexpected JSON")


def _publisher_ports(publishers: Any) -> list[str]:
    if not isinstance(publishers, list):
        return []

    ports: list[str] = []
    for publisher in publishers:
        if not isinstance(publisher, dict):
            continue
        url = str(publisher.get("URL") or "0.0.0.0")
        published = publisher.get("PublishedPort")
        target = publisher.get("TargetPort")
        protocol = publisher.get("Protocol")
        proto = f"/{protocol}" if protocol else ""
        if published and target:
            ports.append(f"{url}:{published}->{target}{proto}")
        elif published:
            ports.append(f"{url}:{published}{proto}")
        elif target:
            ports.append(f"{target}{proto}")
    return ports


def _publisher_http_url(service_name: str | None, publishers: Any) -> str | None:
    if not isinstance(publishers, list) or not service_name:
        return None

    target_port = _HTTP_PORTS.get(str(service_name))
    if not target_port:
        return None

    for publisher in publishers:
        if not isinstance(publisher, dict):
            continue
        if int(publisher.get("TargetPort") or 0) != target_port:
            continue
        published = int(publisher.get("PublishedPort") or 0)
        if not published:
            continue
        host = str(publisher.get("URL") or "127.0.0.1")
        if host in {"", "0.0.0.0", "::"}:
            host = "127.0.0.1"
        suffix = "/browser/" if service_name == "neo4j" else ""
        return f"http://{host}:{published}{suffix}"
    return None


def _normalise_service(raw: dict[str, Any]) -> dict[str, Any]:
    service = dict(raw)
    service_name = service.get("Service") or service.get("service") or service.get("Name")
    state = service.get("State") or service.get("state") or service.get("Status")
    health = service.get("Health") or service.get("health")
    image = service.get("Image") or service.get("image")
    ports = service.get("Ports") or service.get("ports") or _publisher_ports(
        service.get("Publishers") or service.get("publishers")
    )

    service["service"] = service_name
    service["name"] = service.get("Name") or service_name
    service["state"] = state
    service["status"] = health or state or "unknown"
    service["health"] = health
    service["image"] = image
    service["ports"] = ports
    service["url"] = service.get("url") or _publisher_http_url(
        str(service_name or ""),
        service.get("Publishers") or service.get("publishers"),
    )
    return service


def _validate_service(service: str) -> str:
    if not _SERVICE_RE.fullmatch(service):
        raise HTTPException(status_code=400, detail="Invalid service name")
    return service


def _stack_status_payload(services: list[dict[str, Any]]) -> dict[str, Any]:
    payload: dict[str, Any] = {"services": services}
    for key in _STATUS_SERVICE_KEYS:
        match = next(
            (
                service
                for service in services
                if str(service.get("service") or "").lower() == key
                or str(service.get("name") or "").lower() == key
                or key in str(service.get("name") or "").lower()
            ),
            None,
        )
        if match is not None:
            payload[key.replace("-", "_")] = match
            payload[key] = match
    return payload


@router.get("/services")
async def get_stack_services() -> list[dict[str, Any]]:
    completed = _run_compose("ps", "--format", "json", timeout=30)
    return [_normalise_service(item) for item in _parse_compose_json(completed.stdout)]


@router.get("/status")
async def get_stack_status() -> dict[str, Any]:
    return _stack_status_payload(await get_stack_services())


@router.post("/{service}/{action}")
async def run_stack_action(service: str, action: str) -> dict[str, Any]:
    service = _validate_service(service)
    if action not in _ACTIONS:
        raise HTTPException(status_code=400, detail="Invalid stack action")

    completed = _run_compose(action, service, timeout=60)
    return {
        "ok": True,
        "service": service,
        "action": action,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
    }


@router.get("/{service}/logs")
async def get_stack_logs(
    service: str,
    tail: int = Query(default=200, ge=1, le=2000),
) -> dict[str, Any]:
    service = _validate_service(service)
    completed = _run_compose(
        "logs",
        "--no-color",
        "--tail",
        str(tail),
        service,
        timeout=45,
    )
    logs = completed.stdout or completed.stderr
    return {"service": service, "logs": logs, "lines": logs.splitlines()}
