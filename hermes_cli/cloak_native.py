"""Native CloakBrowser profile manager for the Hermes dashboard.

This module keeps profile metadata in a local SQLite database and launches
one CloakBrowser + VNC desktop process per running profile. It intentionally
does not require Docker; Docker-based vnc-cloak remains a fallback through the
legacy ``CLOAK_CDP_URL=http://localhost:9222`` path.
"""

from __future__ import annotations

import datetime as _dt
import json
import os
import signal
import secrets
import shutil
import socket
import sqlite3
import subprocess
import sys
import time
import urllib.request
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any

PROFILE_COLUMNS = (
    "id",
    "name",
    "fingerprint_seed",
    "proxy",
    "timezone",
    "locale",
    "platform",
    "user_agent",
    "screen_width",
    "screen_height",
    "gpu_vendor",
    "gpu_renderer",
    "hardware_concurrency",
    "humanize",
    "human_preset",
    "headless",
    "geoip",
    "color_scheme",
    "launch_args",
    "notes",
    "assigned_to",
    "auto_launch",
    "user_data_dir",
    "created_at",
    "updated_at",
)


@dataclass
class RunningProfile:
    profile_id: str
    process: subprocess.Popen
    display: int
    vnc_port: int
    novnc_port: int
    cdp_port: int
    started_at: str

    @property
    def cdp_url(self) -> str:
        return f"http://127.0.0.1:{self.cdp_port}"


class AdoptedProcess:
    """Small Popen-like wrapper for launcher processes started before restart."""

    def __init__(self, pid: int) -> None:
        self.pid = int(pid)

    def _alive(self) -> bool:
        if self.pid <= 0:
            return False
        proc_stat = Path(f"/proc/{self.pid}/stat")
        if proc_stat.exists():
            try:
                parts = proc_stat.read_text(encoding="utf-8", errors="replace").split()
                if len(parts) > 2 and parts[2] == "Z":
                    return False
            except OSError:
                return False
        try:
            os.kill(self.pid, 0)
            return True
        except OSError:
            return False

    def poll(self) -> int | None:
        return None if self._alive() else 0

    def terminate(self) -> None:
        if self._alive():
            os.kill(self.pid, signal.SIGTERM)

    def kill(self) -> None:
        if self._alive():
            os.kill(self.pid, signal.SIGKILL)

    def wait(self, timeout: float | None = None) -> int:
        deadline = time.time() + timeout if timeout is not None else None
        while self._alive():
            if deadline is not None and time.time() >= deadline:
                raise subprocess.TimeoutExpired(str(self.pid), timeout)
            time.sleep(0.1)
        return 0


def _home() -> Path:
    return Path(os.environ.get("HERMES_HOME", "~/.hermes")).expanduser().resolve()


def manager_root() -> Path:
    return Path(os.environ.get("HERMES_CLOAK_MANAGER_PATH", _home() / "cloak")).expanduser().resolve()


def browser_profiles_root() -> Path:
    return Path(os.environ.get("HERMES_BROWSER_PROFILES", _home() / "browser-profiles")).expanduser().resolve()


def db_path() -> Path:
    return manager_root() / "profiles.db"


def active_profile_path() -> Path:
    return manager_root() / "active_profile.json"


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _now() -> str:
    return _dt.datetime.now(_dt.timezone.utc).isoformat()


def _json_loads(value: Any, default: Any) -> Any:
    if value is None or value == "":
        return default
    try:
        return json.loads(value)
    except Exception:
        return default


def _json_dumps(value: Any) -> str:
    return json.dumps(value if value is not None else [], ensure_ascii=False)


def _bool(value: Any) -> bool:
    return bool(int(value)) if isinstance(value, int) else bool(value)


@contextmanager
def _connect():
    root = manager_root()
    root.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path()))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    try:
        yield conn
    finally:
        conn.close()


def init_db() -> None:
    manager_root().mkdir(parents=True, exist_ok=True)
    browser_profiles_root().mkdir(parents=True, exist_ok=True)
    with _connect() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS cloak_profiles (
              id TEXT PRIMARY KEY,
              name TEXT NOT NULL UNIQUE,
              fingerprint_seed INTEGER NOT NULL,
              proxy TEXT,
              timezone TEXT,
              locale TEXT,
              platform TEXT DEFAULT 'windows',
              user_agent TEXT,
              screen_width INTEGER DEFAULT 1920,
              screen_height INTEGER DEFAULT 1080,
              gpu_vendor TEXT,
              gpu_renderer TEXT,
              hardware_concurrency INTEGER,
              humanize INTEGER DEFAULT 1,
              human_preset TEXT DEFAULT 'default',
              headless INTEGER DEFAULT 0,
              geoip INTEGER DEFAULT 0,
              color_scheme TEXT,
              launch_args TEXT DEFAULT '[]',
              notes TEXT,
              assigned_to TEXT DEFAULT 'manual',
              auto_launch INTEGER DEFAULT 0,
              user_data_dir TEXT NOT NULL,
              created_at TEXT NOT NULL,
              updated_at TEXT NOT NULL
            );
            """
        )
        cols = {row[1] for row in conn.execute("PRAGMA table_info(cloak_profiles)").fetchall()}
        migrations = {
            "assigned_to": "ALTER TABLE cloak_profiles ADD COLUMN assigned_to TEXT DEFAULT 'manual'",
            "auto_launch": "ALTER TABLE cloak_profiles ADD COLUMN auto_launch INTEGER DEFAULT 0",
            "launch_args": "ALTER TABLE cloak_profiles ADD COLUMN launch_args TEXT DEFAULT '[]'",
            "color_scheme": "ALTER TABLE cloak_profiles ADD COLUMN color_scheme TEXT",
        }
        for column, statement in migrations.items():
            if column not in cols:
                conn.execute(statement)
        conn.commit()


def _row_to_profile(row: sqlite3.Row | dict[str, Any], running: RunningProfile | None = None) -> dict[str, Any]:
    raw = dict(row)
    launch_args = _json_loads(raw.get("launch_args"), [])
    profile = {
        **raw,
        "humanize": _bool(raw.get("humanize", 1)),
        "headless": _bool(raw.get("headless", 0)),
        "geoip": _bool(raw.get("geoip", 0)),
        "auto_launch": _bool(raw.get("auto_launch", 0)),
        "launch_args": launch_args if isinstance(launch_args, list) else [],
        "status": "running" if running and running.process.poll() is None else "stopped",
        "display": f":{running.display}" if running else None,
        "vnc_port": running.vnc_port if running else None,
        "novnc_port": running.novnc_port if running else None,
        "cdp_port": running.cdp_port if running else None,
        "cdp_url": running.cdp_url if running else None,
        "novnc_url": "/api/cloak/novnc/vnc.html" if running else None,
        "active": read_active_profile_id() == raw.get("id"),
        "path": raw.get("user_data_dir"),
    }
    return profile


def create_profile(data: dict[str, Any]) -> dict[str, Any]:
    init_db()
    name = str(data.get("name") or "").strip()
    if not name:
        raise ValueError("Profile name is required")
    profile_id = str(data.get("id") or secrets.token_hex(8))
    seed = int(data.get("fingerprint_seed") or secrets.randbelow(90000) + 10000)
    user_data_dir = str(browser_profiles_root() / profile_id)
    now = _now()
    fields = {
        "id": profile_id,
        "name": name,
        "fingerprint_seed": seed,
        "proxy": data.get("proxy") or None,
        "timezone": data.get("timezone") or None,
        "locale": data.get("locale") or None,
        "platform": data.get("platform") or "windows",
        "user_agent": data.get("user_agent") or None,
        "screen_width": int(data.get("screen_width") or 1920),
        "screen_height": int(data.get("screen_height") or 1080),
        "gpu_vendor": data.get("gpu_vendor") or None,
        "gpu_renderer": data.get("gpu_renderer") or None,
        "hardware_concurrency": data.get("hardware_concurrency"),
        "humanize": 1 if data.get("humanize", True) else 0,
        "human_preset": data.get("human_preset") or "default",
        "headless": 1 if data.get("headless", False) else 0,
        "geoip": 1 if data.get("geoip", False) else 0,
        "color_scheme": data.get("color_scheme") or None,
        "launch_args": _json_dumps(data.get("launch_args") or []),
        "notes": data.get("notes") or None,
        "assigned_to": data.get("assigned_to") or "manual",
        "auto_launch": 1 if data.get("auto_launch", False) else 0,
        "user_data_dir": user_data_dir,
        "created_at": now,
        "updated_at": now,
    }
    with _connect() as conn:
        conn.execute(
            f"INSERT INTO cloak_profiles ({', '.join(PROFILE_COLUMNS)}) "
            f"VALUES ({', '.join(['?'] * len(PROFILE_COLUMNS))})",
            [fields[column] for column in PROFILE_COLUMNS],
        )
        conn.commit()
    Path(user_data_dir).mkdir(parents=True, exist_ok=True)
    return get_profile(profile_id)  # type: ignore[return-value]


def ensure_default_profile() -> dict[str, Any]:
    init_db()
    profiles = list_profiles()
    if profiles:
        return profiles[0]
    return create_profile(
        {
            "name": "default",
            "assigned_to": "hermes",
            "humanize": True,
            "screen_width": 1920,
            "screen_height": 1080,
        }
    )


def get_profile(profile_id_or_name: str) -> dict[str, Any] | None:
    init_db()
    NATIVE_MANAGER._cleanup_dead()
    with _connect() as conn:
        row = conn.execute(
            "SELECT * FROM cloak_profiles WHERE id = ? OR name = ?",
            (profile_id_or_name, profile_id_or_name),
        ).fetchone()
    if not row:
        return None
    running = NATIVE_MANAGER.running.get(row["id"])
    return _row_to_profile(row, running)


def list_profiles() -> list[dict[str, Any]]:
    init_db()
    NATIVE_MANAGER._cleanup_dead()
    with _connect() as conn:
        rows = conn.execute("SELECT * FROM cloak_profiles ORDER BY lower(name)").fetchall()
    return [_row_to_profile(row, NATIVE_MANAGER.running.get(row["id"])) for row in rows]


def update_profile(profile_id: str, fields: dict[str, Any]) -> dict[str, Any] | None:
    init_db()
    allowed = {
        "name",
        "fingerprint_seed",
        "proxy",
        "timezone",
        "locale",
        "platform",
        "user_agent",
        "screen_width",
        "screen_height",
        "gpu_vendor",
        "gpu_renderer",
        "hardware_concurrency",
        "humanize",
        "human_preset",
        "headless",
        "geoip",
        "color_scheme",
        "launch_args",
        "notes",
        "assigned_to",
        "auto_launch",
    }
    updates: list[str] = []
    values: list[Any] = []
    for key, value in fields.items():
        if key not in allowed:
            continue
        if key in {"humanize", "headless", "geoip", "auto_launch"}:
            value = 1 if value else 0
        if key == "launch_args":
            value = _json_dumps(value or [])
        updates.append(f"{key} = ?")
        values.append(value)
    if not updates:
        return get_profile(profile_id)
    updates.append("updated_at = ?")
    values.append(_now())
    values.append(profile_id)
    with _connect() as conn:
        conn.execute(f"UPDATE cloak_profiles SET {', '.join(updates)} WHERE id = ?", values)
        conn.commit()
    return get_profile(profile_id)


def delete_profile(profile_id: str) -> bool:
    init_db()
    profile = get_profile(profile_id)
    if not profile:
        return False
    NATIVE_MANAGER.stop(profile_id)
    with _connect() as conn:
        cur = conn.execute("DELETE FROM cloak_profiles WHERE id = ?", (profile["id"],))
        conn.commit()
    if cur.rowcount:
        shutil.rmtree(profile["user_data_dir"], ignore_errors=True)
    return bool(cur.rowcount)


def read_active_profile() -> dict[str, Any] | None:
    path = active_profile_path()
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None
    return data if isinstance(data, dict) else None


def read_active_profile_id() -> str | None:
    active = read_active_profile()
    if not active:
        return None
    return str(active.get("id") or "") or None


def read_active_cdp_url() -> str | None:
    active = read_active_profile()
    if not active:
        return None
    url = str(active.get("cdp_url") or "").strip().rstrip("/")
    return url or None


def write_active_profile(profile: dict[str, Any], cdp_url: str | None = None) -> None:
    manager_root().mkdir(parents=True, exist_ok=True)
    payload = {
        "id": profile["id"],
        "name": profile["name"],
        "user_data_dir": profile["user_data_dir"],
        "cdp_url": cdp_url or profile.get("cdp_url"),
        "updated_at": _now(),
    }
    active_profile_path().write_text(json.dumps(payload, indent=2), encoding="utf-8")
    try:
        active_profile_path().chmod(0o600)
    except OSError:
        pass


def dependency_status() -> dict[str, Any]:
    commands = {
        "Xvfb": shutil.which("Xvfb"),
        "openbox": shutil.which("openbox"),
        "x11vnc": shutil.which("x11vnc"),
        "websockify": shutil.which("websockify"),
        "xclip": shutil.which("xclip"),
    }
    novnc_root = find_novnc_root()
    try:
        import cloakbrowser  # noqa: F401

        cloakbrowser_ok = True
    except Exception:
        cloakbrowser_ok = False
    missing = [name for name, path in commands.items() if not path]
    if not novnc_root:
        missing.append("noVNC")
    if not cloakbrowser_ok:
        missing.append("cloakbrowser[geoip]")
    return {
        "ok": not missing,
        "missing": missing,
        "commands": commands,
        "novnc_root": str(novnc_root) if novnc_root else None,
        "cloakbrowser": cloakbrowser_ok,
    }


def find_novnc_root() -> Path | None:
    candidates = [
        os.environ.get("NOVNC_WEB_ROOT"),
        "/usr/share/novnc",
        "/usr/local/share/novnc",
        "/opt/novnc",
    ]
    for raw in candidates:
        if not raw:
            continue
        root = Path(raw).expanduser().resolve()
        if (root / "vnc.html").is_file():
            return root
    return None


def novnc_asset_path(asset_path: str) -> Path:
    root = find_novnc_root()
    if not root:
        raise FileNotFoundError("noVNC web root was not found")
    clean = asset_path.strip("/") or "vnc.html"
    target = (root / clean).resolve()
    target.relative_to(root)
    if not target.is_file():
        raise FileNotFoundError(clean)
    return target


def _free_port(start: int, stop: int) -> int:
    for port in range(start, stop + 1):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                sock.bind(("127.0.0.1", port))
            except OSError:
                continue
            return port
    raise RuntimeError(f"No free port in {start}-{stop}")


def _http_ready(url: str, timeout: float) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=2) as response:
                if response.status < 500:
                    return True
        except Exception:
            time.sleep(0.25)
    return False


def _tcp_ready(port: int, timeout: float) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(1)
            try:
                sock.connect(("127.0.0.1", int(port)))
                return True
            except OSError:
                time.sleep(0.25)
    return False


def _launcher_pids_by_config() -> dict[str, int]:
    if os.name == "nt":
        return {}
    proc_root = Path("/proc")
    result: dict[str, int] = {}
    for entry in proc_root.iterdir():
        if not entry.name.isdigit():
            continue
        cmdline = entry / "cmdline"
        try:
            raw = cmdline.read_bytes()
        except OSError:
            continue
        if not raw:
            continue
        parts = [part.decode("utf-8", errors="replace") for part in raw.split(b"\0") if part]
        joined = " ".join(parts)
        if "cloak-native-launcher.py" not in joined:
            continue
        for index, part in enumerate(parts):
            if part == "--config" and index + 1 < len(parts):
                result[str(Path(parts[index + 1]).expanduser().resolve())] = int(entry.name)
                break
    return result


class NativeCloakManager:
    def __init__(self) -> None:
        self.running: dict[str, RunningProfile] = {}

    def _cleanup_dead(self) -> None:
        self._adopt_existing()
        for profile_id, running in list(self.running.items()):
            if running.process.poll() is not None:
                self.running.pop(profile_id, None)

    def _adopt_existing(self) -> None:
        run_dir = manager_root() / "run"
        if not run_dir.is_dir():
            return
        pids = _launcher_pids_by_config()
        for config_path in sorted(run_dir.glob("*.json")):
            key = str(config_path.resolve())
            pid = pids.get(key)
            if not pid:
                continue
            try:
                config = json.loads(config_path.read_text(encoding="utf-8"))
                profile = config.get("profile") or {}
                profile_id = str(profile.get("id") or config_path.stem)
                display = int(config["display"])
                vnc_port = int(config["vnc_port"])
                novnc_port = int(config["novnc_port"])
                cdp_port = int(config["cdp_port"])
            except Exception:
                continue
            if profile_id in self.running and self.running[profile_id].process.poll() is None:
                continue
            self.running[profile_id] = RunningProfile(
                profile_id=profile_id,
                process=AdoptedProcess(pid),  # type: ignore[arg-type]
                display=display,
                vnc_port=vnc_port,
                novnc_port=novnc_port,
                cdp_port=cdp_port,
                started_at=_now(),
            )

    def launch(self, profile_id: str) -> dict[str, Any]:
        init_db()
        self._cleanup_dead()
        profile = get_profile(profile_id)
        if not profile:
            raise KeyError(profile_id)
        if profile["id"] in self.running:
            running = self.running[profile["id"]]
            write_active_profile(profile, running.cdp_url)
            return _row_to_profile(profile, running)

        deps = dependency_status()
        if not deps["ok"]:
            raise RuntimeError("Missing native Cloak dependencies: " + ", ".join(deps["missing"]))

        display = int(os.environ.get("CLOAK_DISPLAY_BASE", "100"))
        used_displays = {running.display for running in self.running.values()}
        while display in used_displays or Path(f"/tmp/.X{display}-lock").exists():
            display += 1
        vnc_port = _free_port(5901, 5999)
        novnc_port = _free_port(6100, 6199)
        cdp_port = _free_port(5100, 5199)

        run_dir = manager_root() / "run"
        run_dir.mkdir(parents=True, exist_ok=True)
        config_path = run_dir / f"{profile['id']}.json"
        config = {
            "profile": profile,
            "display": display,
            "vnc_port": vnc_port,
            "novnc_port": novnc_port,
            "cdp_port": cdp_port,
            "novnc_root": deps["novnc_root"],
        }
        config_path.write_text(json.dumps(config, indent=2), encoding="utf-8")
        try:
            config_path.chmod(0o600)
        except OSError:
            pass

        script = _repo_root() / "scripts" / "cloak-native-launcher.py"
        env = os.environ.copy()
        env["PYTHONUNBUFFERED"] = "1"
        creationflags = 0
        start_new_session = False
        if os.name == "nt":
            creationflags = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
        else:
            start_new_session = True
        proc = subprocess.Popen(
            [sys.executable, str(script), "--config", str(config_path)],
            cwd=str(_repo_root()),
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=start_new_session,
            creationflags=creationflags,
        )

        running = RunningProfile(
            profile_id=profile["id"],
            process=proc,
            display=display,
            vnc_port=vnc_port,
            novnc_port=novnc_port,
            cdp_port=cdp_port,
            started_at=_now(),
        )
        self.running[profile["id"]] = running
        if not _http_ready(f"http://127.0.0.1:{cdp_port}/json/version", 45):
            self.stop(profile["id"])
            raise RuntimeError("CloakBrowser did not expose CDP before timeout")
        if not _tcp_ready(novnc_port, 10):
            self.stop(profile["id"])
            raise RuntimeError("Cloak noVNC websocket bridge did not start before timeout")
        write_active_profile(profile, running.cdp_url)
        return _row_to_profile(profile, running)

    def stop(self, profile_id: str) -> bool:
        self._cleanup_dead()
        running = self.running.pop(profile_id, None)
        if not running:
            return False
        if running.process.poll() is None:
            if os.name == "nt":
                running.process.terminate()
            else:
                try:
                    os.killpg(running.process.pid, 15)
                except OSError:
                    running.process.terminate()
            try:
                running.process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                if os.name == "nt":
                    running.process.kill()
                else:
                    try:
                        os.killpg(running.process.pid, 9)
                    except OSError:
                        running.process.kill()
        return True

    def status(self, profile_id: str) -> dict[str, Any]:
        self._cleanup_dead()
        profile = get_profile(profile_id)
        if not profile:
            raise KeyError(profile_id)
        return _row_to_profile(profile, self.running.get(profile["id"]))


NATIVE_MANAGER = NativeCloakManager()
