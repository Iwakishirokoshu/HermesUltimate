import base64
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ._cdp_client import cdp_call
from ._files import ensure_private_dir, write_private_bytes


def screenshot_dir() -> Path:
    root = Path(os.environ.get("HERMES_VAULT_PATH", "~/HermesVault")).expanduser()
    return root / "Sessions" / "screenshots"


async def cloak_screenshot(include_data: bool = False) -> dict[str, Any]:
    """Capture the active Cloak browser page and save it into HermesVault."""
    try:
        result = await cdp_call("Page.captureScreenshot", {"format": "png", "fromSurface": True})
        data = result.get("data")
        if not data:
            return {"ok": False, "error": "CDP did not return screenshot data"}
        out_dir = screenshot_dir()
        ensure_private_dir(out_dir)
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        path = out_dir / f"{stamp}.png"
        raw = base64.b64decode(data)
        write_private_bytes(path, raw)
        response = {"ok": True, "path": str(path), "bytes": len(raw)}
        if include_data:
            response["data"] = data
        return response
    except Exception as exc:
        return {"ok": False, "error": str(exc)}
