import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ._cdp_client import cdp_call
from ._files import ensure_private_dir, write_private_text


def cookies_dir() -> Path:
    root = Path(os.environ.get("HERMES_VAULT_PATH", "~/HermesVault")).expanduser()
    return root / "Sessions" / "cookies"


def _cookie_matches(cookie: dict[str, Any], domain: str | None) -> bool:
    if not domain:
        return True
    wanted = domain.lstrip(".").lower()
    actual = str(cookie.get("domain") or "").lstrip(".").lower()
    return actual == wanted or actual.endswith("." + wanted)


async def cloak_cookies_export(domain: str | None = None, include_cookies: bool = False) -> dict[str, Any]:
    """Export Cloak browser cookies to a HermesVault JSON file."""
    try:
        result = await cdp_call("Network.getAllCookies")
        cookies = [cookie for cookie in result.get("cookies", []) if _cookie_matches(cookie, domain)]
        out_dir = cookies_dir()
        ensure_private_dir(out_dir)
        label = (domain or "all").replace("/", "_").replace("\\", "_").replace(":", "_")
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        path = out_dir / f"{label}-{stamp}.json"
        payload = {"domain": domain, "exported_at": stamp, "cookies": cookies}
        write_private_text(path, json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
        response = {"ok": True, "path": str(path), "count": len(cookies)}
        if include_cookies:
            response["cookies"] = cookies
        return response
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


async def cloak_cookies_import(json_path: str) -> dict[str, Any]:
    """Import cookies from a JSON file into the Cloak browser."""
    try:
        path = Path(json_path).expanduser()
        payload = json.loads(path.read_text(encoding="utf-8"))
        cookies = payload.get("cookies", payload) if isinstance(payload, dict) else payload
        if not isinstance(cookies, list):
            return {"ok": False, "error": "cookie JSON must be a list or an object with cookies"}
        result = await cdp_call("Network.setCookies", {"cookies": cookies})
        return {"ok": True, "path": str(path), "count": len(cookies), "result": result}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}
