import asyncio
from typing import Any

from ._cdp_client import cdp_call


async def cloak_navigate(url: str, timeout: int = 30) -> dict[str, Any]:
    """Navigate the active Cloak browser page through CDP."""
    try:
        await cdp_call("Page.enable")
        result = await cdp_call("Page.navigate", {"url": url})
        if timeout > 0:
            await asyncio.sleep(min(float(timeout), 1.0))
        return {"ok": True, "url": url, "result": result}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}
