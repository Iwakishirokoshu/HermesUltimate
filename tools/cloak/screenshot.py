import base64
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ._cdp_client import cdp_call


def screenshot_dir() -> Path:
    root = Path(os.environ.get("HERMES_VAULT_PATH", "~/HermesVault")).expanduser()
    return root / "Sessions" / "screenshots"


async def cloak_screenshot() -> dict[str, Any]:
    """Capture the active Cloak browser page and save it into HermesVault."""
    try:
        result = await cdp_call("Page.captureScreenshot", {"format": "png", "fromSurface": True})
        data = result.get("data")
        if not data:
            return {"ok": False, "error": "CDP did not return screenshot data"}
        out_dir = screenshot_dir()
        out_dir.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        path = out_dir / f"{stamp}.png"
        path.write_bytes(base64.b64decode(data))
        return {"ok": True, "path": str(path), "data": data}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}
