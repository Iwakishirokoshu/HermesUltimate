import json
import os
from urllib import error, parse, request


DEFAULT_BASE_URL = "http://localhost:8090"


def vault_api_url() -> str:
    return os.environ.get("HERMES_VAULT_API_URL", DEFAULT_BASE_URL).rstrip("/")


def call_json(method: str, endpoint: str, payload: dict | None = None, params: dict | None = None) -> dict:
    url = vault_api_url() + endpoint
    if params:
        query = parse.urlencode({k: v for k, v in params.items() if v is not None})
        if query:
            url = f"{url}?{query}"
    body = None
    headers = {"Accept": "application/json"}
    if payload is not None:
        body = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = request.Request(url, data=body, headers=headers, method=method.upper())
    try:
        with request.urlopen(req, timeout=20) as response:
            text = response.read().decode("utf-8")
    except error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        return {"success": False, "error": f"vault-api HTTP {exc.code}: {detail}"}
    except error.URLError as exc:
        return {"success": False, "error": f"vault-api unavailable at {vault_api_url()}: {exc.reason}"}
    if not text:
        return {"success": True}
    data = json.loads(text)
    if isinstance(data, dict) and "success" not in data:
        data = {"success": True, **data}
    return data


def dumps(data: dict) -> str:
    return json.dumps(data, ensure_ascii=False, indent=2)