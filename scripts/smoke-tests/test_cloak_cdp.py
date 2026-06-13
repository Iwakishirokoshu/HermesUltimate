import asyncio
from pathlib import Path

import pytest

from tools.cloak._cdp_client import CDPError, cdp_version
from tools.cloak.navigate import cloak_navigate
from tools.cloak.screenshot import cloak_screenshot


def test_cloak_cdp_navigate_and_screenshot(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("HERMES_VAULT_PATH", str(tmp_path))

    try:
        version = cdp_version()
    except CDPError as exc:
        pytest.fail(f"Cloak CDP is not reachable at http://localhost:9222/json/version: {exc}")

    assert version.get("Browser") or version.get("webSocketDebuggerUrl")

    navigation = asyncio.run(cloak_navigate("about:blank"))
    assert navigation["ok"] is True, navigation

    screenshot = asyncio.run(cloak_screenshot())
    assert screenshot["ok"] is True, screenshot

    path = Path(screenshot["path"])
    assert path.exists()
    assert path.is_file()
    assert path.read_bytes().startswith(b"\x89PNG\r\n\x1a\n")
