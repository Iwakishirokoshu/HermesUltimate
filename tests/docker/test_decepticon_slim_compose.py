from __future__ import annotations

import json
import tomllib
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[2]


def _env_map(value: object) -> dict[str, str]:
    if isinstance(value, dict):
        return {str(k): str(v) for k, v in value.items()}
    if isinstance(value, list):
        result: dict[str, str] = {}
        for item in value:
            key, _, raw = str(item).partition("=")
            result[key] = raw
        return result
    return {}


def test_decepticon_slim_uses_http_sandbox_daemon() -> None:
    compose = yaml.safe_load(
        (ROOT / "stack" / "docker-compose.decepticon-slim.yml").read_text(
            encoding="utf-8"
        ),
    )

    services = compose["services"]
    sandbox = services["sandbox"]
    assert sandbox["build"] == {
        "context": "./decepticon-slim/upstream",
        "dockerfile": "containers/sandbox.Dockerfile",
    }
    assert not (ROOT / "stack" / "decepticon-slim" / "Dockerfile.sandbox").exists()

    env = _env_map(sandbox.get("environment"))
    assert env["SANDBOX_DAEMON"] == "1"
    assert env["SANDBOX_ROOT_DIR"] == "/workspace"
    assert "${HERMES_VAULT_PATH:-~/HermesVault}/Engagements:/workspace:rw" in sandbox["volumes"]
    assert "http://localhost:9999/healthz" in " ".join(sandbox["healthcheck"]["test"])

    langgraph = services["langgraph"]
    assert langgraph["environment"]["SAAS_SANDBOX_URL"] == "http://sandbox:9999"
    assert langgraph["depends_on"]["sandbox"]["condition"] == "service_healthy"


def test_decepticon_standard_subagents_are_preserved() -> None:
    pyproject = tomllib.loads(
        (
            ROOT
            / "stack"
            / "decepticon-slim"
            / "upstream"
            / "packages"
            / "decepticon"
            / "pyproject.toml"
        )
        .read_text(encoding="utf-8")
    )
    subagents = pyproject["project"]["entry-points"]["decepticon.subagents"]
    standard = {
        name: target
        for name, target in subagents.items()
        if ".agents.standard." in target
    }
    assert len(standard) >= 16

    langgraph = json.loads(
        (ROOT / "stack" / "decepticon-slim" / "upstream" / "langgraph.json").read_text(
            encoding="utf-8"
        )
    )
    graph_names = set(langgraph["graphs"])
    assert {"decepticon", "soundwave", *standard} <= graph_names
