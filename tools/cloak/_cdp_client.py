import asyncio
import json
import os
from dataclasses import dataclass
from typing import Any
from urllib import error, parse, request


DEFAULT_CDP_HTTP_URL = "http://localhost:9222"
DEFAULT_CDP_TIMEOUT_SECONDS = 10.0


class CDPError(RuntimeError):
    pass


@dataclass
class PlaywrightCDPConnection:
    playwright: Any
    browser: Any

    async def close(self) -> None:
        await self.browser.close()
        await self.playwright.stop()


def cdp_http_url() -> str:
    raw = os.environ.get("CLOAK_CDP_URL") or os.environ.get("BROWSER_CDP_URL") or DEFAULT_CDP_HTTP_URL
    raw = raw.strip().rstrip("/")
    active = _active_manager_cdp_url()
    if raw.lower() in {"", "auto", "manager", "native"}:
        return active or DEFAULT_CDP_HTTP_URL
    if raw == DEFAULT_CDP_HTTP_URL and active and os.environ.get("CLOAK_CDP_URL_STRICT") != "1":
        return active
    if raw.startswith("ws://"):
        return "http://" + raw[len("ws://"):].split("/devtools/", 1)[0]
    if raw.startswith("wss://"):
        return "https://" + raw[len("wss://"):].split("/devtools/", 1)[0]
    return raw


def _active_manager_cdp_url() -> str | None:
    try:
        from hermes_cli.cloak_native import read_active_cdp_url

        value = read_active_cdp_url()
    except Exception:
        value = None
    if not value:
        return None
    return value.strip().rstrip("/")


def cdp_timeout(default: float = DEFAULT_CDP_TIMEOUT_SECONDS) -> float:
    raw = os.environ.get("CLOAK_CDP_TIMEOUT") or os.environ.get("BROWSER_CDP_TIMEOUT")
    if not raw:
        return default
    try:
        value = float(raw)
    except ValueError:
        return default
    return max(0.1, value)


def _json_http(method: str, path: str, payload: dict[str, Any] | None = None) -> Any:
    url = cdp_http_url() + path
    body = None
    headers = {"Accept": "application/json"}
    if payload is not None:
        body = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = request.Request(url, data=body, headers=headers, method=method)
    try:
        with request.urlopen(req, timeout=10) as response:
            text = response.read().decode("utf-8")
    except error.URLError as exc:
        raise CDPError(f"Cloak CDP is unavailable at {cdp_http_url()}: {exc}") from exc
    return json.loads(text) if text else {}


def cdp_version() -> dict[str, Any]:
    return _json_http("GET", "/json/version")


def list_targets() -> list[dict[str, Any]]:
    data = _json_http("GET", "/json/list")
    return data if isinstance(data, list) else []


def new_target(url: str = "about:blank") -> dict[str, Any]:
    encoded = parse.quote(url, safe=":/?#[]@!$&'()*+,;=%")
    path = f"/json/new?{encoded}"
    try:
        return _json_http("PUT", path)
    except CDPError:
        return _json_http("GET", path)


def _target_matches_hint(target: dict[str, Any], hint: str) -> bool:
    wanted = hint.strip().lower()
    if not wanted:
        return False
    for key in ("id", "targetId", "url", "title"):
        if wanted in str(target.get(key) or "").lower():
            return True
    return False


def ensure_page(url: str = "about:blank", target_hint: str | None = None) -> dict[str, Any]:
    pages = [
        target
        for target in list_targets()
        if target.get("type") == "page" and target.get("webSocketDebuggerUrl")
    ]
    hint = target_hint or os.environ.get("CLOAK_TARGET_HINT") or os.environ.get("BROWSER_TARGET_HINT")
    if hint:
        for target in pages:
            if _target_matches_hint(target, hint):
                return target
    if pages:
        return pages[0]
    target = new_target(url)
    if not target.get("webSocketDebuggerUrl"):
        raise CDPError("Cloak CDP did not return a page websocket URL")
    return target


async def connect_playwright_over_cdp(cdp_url: str | None = None) -> PlaywrightCDPConnection:
    try:
        from playwright.async_api import async_playwright
    except ImportError as exc:
        raise CDPError("playwright is required for connect_playwright_over_cdp") from exc
    playwright = await async_playwright().start()
    try:
        browser = await playwright.chromium.connect_over_cdp(cdp_url or cdp_http_url())
    except Exception:
        await playwright.stop()
        raise
    return PlaywrightCDPConnection(playwright=playwright, browser=browser)


async def cdp_call(
    method: str,
    params: dict[str, Any] | None = None,
    ws_url: str | None = None,
    timeout: float | None = None,
) -> dict[str, Any]:
    try:
        import websockets
    except ImportError as exc:
        raise CDPError("websockets is required for direct CDP calls") from exc

    websocket_url = ws_url or ensure_page()["webSocketDebuggerUrl"]
    message_id = 1
    call_timeout = max(0.1, float(timeout)) if timeout is not None else cdp_timeout()
    try:
        async with websockets.connect(
            websocket_url,
            max_size=50 * 1024 * 1024,
            open_timeout=call_timeout,
            close_timeout=2,
        ) as ws:
            await asyncio.wait_for(
                ws.send(json.dumps({"id": message_id, "method": method, "params": params or {}})),
                timeout=call_timeout,
            )
            deadline = asyncio.get_running_loop().time() + call_timeout
            while True:
                remaining = deadline - asyncio.get_running_loop().time()
                if remaining <= 0:
                    raise asyncio.TimeoutError
                raw = await asyncio.wait_for(ws.recv(), timeout=remaining)
                data = json.loads(raw)
                if data.get("id") != message_id:
                    continue
                if "error" in data:
                    raise CDPError(json.dumps(data["error"], ensure_ascii=False))
                return data.get("result", {})
    except asyncio.TimeoutError as exc:
        raise CDPError(f"CDP call {method} timed out after {call_timeout:.1f}s") from exc


async def evaluate(expression: str, await_promise: bool = True, timeout: float | None = None) -> dict[str, Any]:
    return await cdp_call(
        "Runtime.evaluate",
        {
            "expression": expression,
            "awaitPromise": await_promise,
            "returnByValue": True,
        },
        timeout=timeout,
    )


def run_async(coro):
    return asyncio.run(coro)
