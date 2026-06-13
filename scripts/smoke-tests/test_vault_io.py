import json
import os
import socket
import subprocess
import sys
import time
from pathlib import Path
from urllib import error, request


def free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def call_json(method: str, url: str, payload: dict | None = None) -> dict:
    body = json.dumps(payload).encode("utf-8") if payload is not None else None
    headers = {"Accept": "application/json"}
    if payload is not None:
        headers["Content-Type"] = "application/json"
    req = request.Request(url, data=body, headers=headers, method=method)
    with request.urlopen(req, timeout=5) as response:
        return json.loads(response.read().decode("utf-8"))


def wait_for_health(base_url: str, proc: subprocess.Popen, timeout: float = 10.0) -> None:
    deadline = time.time() + timeout
    last_error: Exception | None = None
    while time.time() < deadline:
        if proc.poll() is not None:
            raise AssertionError(f"vault-api exited early with code {proc.returncode}")
        try:
            data = call_json("GET", f"{base_url}/health")
            if data.get("ok") is True:
                return
        except (OSError, error.URLError, TimeoutError) as exc:
            last_error = exc
        time.sleep(0.2)
    raise AssertionError(f"vault-api did not become healthy: {last_error}")


def test_vault_api_append_read_search(tmp_path: Path):
    port = free_port()
    base_url = f"http://127.0.0.1:{port}"
    env = os.environ.copy()
    env["HERMES_VAULT_PATH"] = str(tmp_path)
    env["PYTHONPATH"] = os.getcwd()
    proc = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "stack.vault_api.main:app",
            "--host",
            "127.0.0.1",
            "--port",
            str(port),
            "--log-level",
            "warning",
        ],
        cwd=os.getcwd(),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    try:
        wait_for_health(base_url, proc)
        page = "Wiki/Hot/smoke.md"
        content = "# Smoke Page\n\nfreshneedle content written by smoke test.\n"

        appended = call_json("POST", f"{base_url}/append", {"path": page, "content": content})
        assert appended["ok"] is True
        assert (tmp_path / page).read_text(encoding="utf-8") == content

        read_back = call_json("GET", f"{base_url}/read?path={page}")
        assert read_back["path"] == page
        assert "freshneedle content" in read_back["content"]

        results = call_json("POST", f"{base_url}/search", {"query": "freshneedle", "top_k": 5})
        assert any(item["path"] == page for item in results["results"])
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait(timeout=5)
