import asyncio
import json
import sys
from types import SimpleNamespace

import pytest

from tools.cloak import _cdp_client
from tools.cloak.cookies import cloak_cookies_export
from tools.cloak.screenshot import cloak_screenshot
from hermes_cli import cloak_native
from hermes_cli.dashboard_auth.middleware import _path_is_public
from hermes_cli.web_api.cloak import _cloak_ws_auth_ok


def test_novnc_static_is_public_but_profile_ws_stays_gated():
    assert _path_is_public("/api/cloak/novnc/vnc.html")
    assert _path_is_public("/api/cloak/novnc/app/ui.js")
    assert not _path_is_public("/api/cloak/profiles/profile-1/vnc-ws")


def test_cdp_http_url_uses_active_native_manager_when_auto(monkeypatch):
    monkeypatch.setenv("CLOAK_CDP_URL", "auto")
    monkeypatch.setattr(cloak_native, "read_active_cdp_url", lambda: "http://127.0.0.1:5107/")

    assert _cdp_client.cdp_http_url() == "http://127.0.0.1:5107"


def test_cdp_http_url_keeps_explicit_override(monkeypatch):
    monkeypatch.setenv("CLOAK_CDP_URL", "http://127.0.0.1:9555")
    monkeypatch.setattr(cloak_native, "read_active_cdp_url", lambda: "http://127.0.0.1:5107")

    assert _cdp_client.cdp_http_url() == "http://127.0.0.1:9555"


def test_native_cloak_profiles_persist_humanize_settings(monkeypatch, tmp_path):
    monkeypatch.setenv("HERMES_CLOAK_MANAGER_PATH", str(tmp_path / "manager"))
    monkeypatch.setenv("HERMES_BROWSER_PROFILES", str(tmp_path / "profiles"))
    cloak_native.NATIVE_MANAGER.running.clear()

    profile = cloak_native.create_profile(
        {
            "name": "agent-login",
            "assigned_to": "registration-skill",
            "humanize": True,
            "human_preset": "careful",
            "geoip": True,
            "screen_width": 1440,
            "screen_height": 900,
            "launch_args": ["--fingerprint-storage-quota=5000"],
        }
    )
    cloak_native.write_active_profile(profile, "http://127.0.0.1:5101")
    reloaded = cloak_native.get_profile("agent-login")

    assert reloaded is not None
    assert reloaded["humanize"] is True
    assert reloaded["human_preset"] == "careful"
    assert reloaded["geoip"] is True
    assert reloaded["launch_args"] == ["--fingerprint-storage-quota=5000"]
    assert cloak_native.read_active_cdp_url() == "http://127.0.0.1:5101"


def test_ensure_page_honors_target_hint(monkeypatch):
    monkeypatch.setattr(
        _cdp_client,
        "list_targets",
        lambda: [
            {"id": "1", "type": "page", "url": "https://first.example", "webSocketDebuggerUrl": "ws://first"},
            {"id": "2", "type": "page", "title": "Second tab", "webSocketDebuggerUrl": "ws://second"},
        ],
    )

    assert _cdp_client.ensure_page(target_hint="second")["id"] == "2"


def test_cdp_call_receive_timeout(monkeypatch):
    class FakeWebSocket:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return None

        async def send(self, payload):
            self.payload = payload

        async def recv(self):
            await asyncio.sleep(10)

    monkeypatch.setitem(sys.modules, "websockets", SimpleNamespace(connect=lambda *a, **kw: FakeWebSocket()))
    monkeypatch.setattr(_cdp_client, "ensure_page", lambda: {"webSocketDebuggerUrl": "ws://cloak"})

    with pytest.raises(_cdp_client.CDPError, match="timed out"):
        asyncio.run(_cdp_client.cdp_call("Runtime.evaluate", timeout=0.01))


def test_cookies_export_writes_file_without_inline_cookies(monkeypatch, tmp_path):
    async def fake_cdp_call(method, params=None, **kwargs):
        assert method == "Network.getAllCookies"
        return {"cookies": [{"name": "sid", "value": "secret", "domain": ".example.com"}]}

    monkeypatch.setenv("HERMES_VAULT_PATH", str(tmp_path))
    monkeypatch.setattr("tools.cloak.cookies.cdp_call", fake_cdp_call)

    result = asyncio.run(cloak_cookies_export("example.com"))

    assert result["ok"] is True
    assert result["count"] == 1
    assert "cookies" not in result
    payload = json.loads((tmp_path / "Sessions" / "cookies").glob("*.json").__next__().read_text())
    assert payload["cookies"][0]["value"] == "secret"


def test_screenshot_writes_file_without_inline_data(monkeypatch, tmp_path):
    async def fake_cdp_call(method, params=None, **kwargs):
        assert method == "Page.captureScreenshot"
        return {"data": "iVBORw0KGgo="}

    monkeypatch.setenv("HERMES_VAULT_PATH", str(tmp_path))
    monkeypatch.setattr("tools.cloak.screenshot.cdp_call", fake_cdp_call)

    result = asyncio.run(cloak_screenshot())

    assert result["ok"] is True
    assert result["bytes"] == 8
    assert "data" not in result
    assert (tmp_path / "Sessions" / "screenshots").glob("*.png").__next__().read_bytes().startswith(b"\x89PNG")


def test_cloak_activity_ws_requires_loopback_token():
    state = SimpleNamespace(auth_required=False, session_token="secret-token")
    app = SimpleNamespace(state=state)

    assert not _cloak_ws_auth_ok(SimpleNamespace(app=app, query_params={}))
    assert not _cloak_ws_auth_ok(SimpleNamespace(app=app, query_params={"token": "wrong"}))
    assert _cloak_ws_auth_ok(SimpleNamespace(app=app, query_params={"token": "secret-token"}))
