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
_SERVICE_RE = re.compile(r"^[A-Za-z0-9_.-]+$")
_ACTIONS = {"start", "stop", "restart"}


def _compose_file() -> Path | None:
    raw = os.environ.get("HERMES_STACK_COMPOSE_FILE") or os.environ.get(
        "HERMES_DOCKER_COMPOSE_FILE"
    )
    if raw:
        path = Path(raw).expanduser()
        return path if path.is_absolute() else (_PROJECT_ROOT / path).resolve()

    windows_file = _PROJECT_ROOT / "docker-compose.windows.yml"
    if os.name == "nt" and windows_file.exists():
        return windows_file

    default_file = _PROJECT_ROOT / "docker-compose.yml"
    return default_file if default_file.exists() else None


def _compose_command(*args: str) -> list[str]:
    command = ["docker", "compose"]
    compose_file = _compose_file()
    if compose_file is not None:
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
    return service


def _validate_service(service: str) -> str:
    if not _SERVICE_RE.fullmatch(service):
        raise HTTPException(status_code=400, detail="Invalid service name")
    return service


@router.get("/services")
async def get_stack_services() -> list[dict[str, Any]]:
    completed = _run_compose("ps", "--format", "json", timeout=30)
    return [_normalise_service(item) for item in _parse_compose_json(completed.stdout)]


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
