import asyncio
from typing import Any

from ._cdp_client import cdp_call, evaluate


async def _wait_for_ready_state(timeout: float) -> str:
    deadline = asyncio.get_running_loop().time() + max(0.0, timeout)
    last_state = "unknown"
    while True:
        remaining = deadline - asyncio.get_running_loop().time()
        if remaining <= 0:
            return last_state
        result = await evaluate("document.readyState", timeout=min(remaining, 5.0))
        last_state = str((result.get("result") or {}).get("value") or "unknown")
        if last_state == "complete":
            return last_state
        await asyncio.sleep(min(0.2, max(0.0, remaining)))


async def cloak_navigate(url: str, timeout: int = 30) -> dict[str, Any]:
    """Navigate the active Cloak browser page through CDP."""
    try:
        wait_timeout = max(0.0, float(timeout or 0))
        await cdp_call("Page.enable", timeout=min(max(wait_timeout, 1.0), 10.0))
        result = await cdp_call("Page.navigate", {"url": url}, timeout=min(max(wait_timeout, 1.0), 10.0))
        ready_state = "skipped"
        if wait_timeout > 0:
            ready_state = await _wait_for_ready_state(wait_timeout)
        return {"ok": True, "url": url, "ready_state": ready_state, "result": result}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}
