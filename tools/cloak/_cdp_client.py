import asyncio
import json
import os
from dataclasses import dataclass
from typing import Any
from urllib import error, parse, request


DEFAULT_CDP_HTTP_URL = "http://localhost:9222"


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
    if raw.startswith("ws://"):
        return "http://" + raw[len("ws://"):].split("/devtools/", 1)[0]
    if raw.startswith("wss://"):
        return "https://" + raw[len("wss://"):].split("/devtools/", 1)[0]
    return raw


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


def ensure_page(url: str = "about:blank") -> dict[str, Any]:
    for target in list_targets():
        if target.get("type") == "page" and target.get("webSocketDebuggerUrl"):
            return target
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


async def cdp_call(method: str, params: dict[str, Any] | None = None, ws_url: str | None = None) -> dict[str, Any]:
    try:
        import websockets
    except ImportError as exc:
        raise CDPError("websockets is required for direct CDP calls") from exc

    target = ensure_page()
    websocket_url = ws_url or target["webSocketDebuggerUrl"]
    message_id = 1
    async with websockets.connect(websocket_url, max_size=50 * 1024 * 1024) as ws:
        await ws.send(json.dumps({"id": message_id, "method": method, "params": params or {}}))
        while True:
            raw = await ws.recv()
            data = json.loads(raw)
            if data.get("id") != message_id:
                continue
            if "error" in data:
                raise CDPError(json.dumps(data["error"], ensure_ascii=False))
            return data.get("result", {})


async def evaluate(expression: str, await_promise: bool = True) -> dict[str, Any]:
    return await cdp_call(
        "Runtime.evaluate",
        {
            "expression": expression,
            "awaitPromise": await_promise,
            "returnByValue": True,
        },
    )


def run_async(coro):
    return asyncio.run(coro)
