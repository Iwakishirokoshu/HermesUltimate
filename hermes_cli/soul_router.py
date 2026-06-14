from __future__ import annotations

import os
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True)
class SoulConfig:
    name: str
    backend: str
    soul_md: str
    allowed_toolsets: list[str]
    vault_load: dict[str, Any] | None = None
    langgraph_url: str | None = None

    @classmethod
    def from_mapping(cls, data: dict[str, Any]) -> "SoulConfig":
        return cls(
            name=str(data["name"]),
            backend=str(data.get("backend", "hermes")),
            soul_md=str(data["soul_md"]),
            allowed_toolsets=[str(item) for item in data.get("allowed_toolsets", [])],
            vault_load=data.get("vault_load") if isinstance(data.get("vault_load"), dict) else None,
            langgraph_url=(
                str(data["langgraph_url"])
                if data.get("langgraph_url") is not None
                else None
            ),
        )


class SoulRouter:
    def __init__(
        self,
        souls_dir: str | Path | None = None,
        db_path: str | Path | None = None,
    ) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        hermes_home = Path(os.environ.get("HERMES_HOME") or (Path.home() / ".hermes")).expanduser()
        self.souls_dir = Path(souls_dir) if souls_dir is not None else repo_root / "souls"
        self.db_path = Path(db_path) if db_path is not None else hermes_home / "soul_state.db"
        self._configs_cache: dict[str, SoulConfig] | None = None
        self._mtime_cache: dict[Path, float] = {}

    def list_souls(self) -> list[str]:
        return sorted(self._load_configs())

    def get_active_soul(self, chat_id: str | int) -> SoulConfig:
        self._ensure_db()
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute(
                "SELECT soul_name FROM chat_soul WHERE chat_id = ?",
                (str(chat_id),),
            ).fetchone()

        configs = self._load_configs()
        soul_name = row[0] if row else "default"
        if soul_name not in configs:
            soul_name = "default"
        return configs[soul_name]

    def set_active_soul(self, chat_id: str | int, name: str) -> SoulConfig:
        configs = self._load_configs()
        if name not in configs:
            raise ValueError(f"Unknown soul: {name}")

        self._ensure_db()
        updated_at = datetime.now(timezone.utc).isoformat()
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT INTO chat_soul (chat_id, soul_name, updated_at)
                VALUES (?, ?, ?)
                ON CONFLICT(chat_id) DO UPDATE SET
                    soul_name = excluded.soul_name,
                    updated_at = excluded.updated_at
                """,
                (str(chat_id), name, updated_at),
            )
            conn.commit()
        return configs[name]

    def _ensure_db(self) -> None:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS chat_soul (
                    chat_id TEXT PRIMARY KEY,
                    soul_name TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            conn.commit()

    def _load_configs(self) -> dict[str, SoulConfig]:
        mtimes = {
            path: path.stat().st_mtime
            for path in sorted(self.souls_dir.glob("*.yaml"))
            if path.is_file()
        }
        if self._configs_cache is not None and mtimes == self._mtime_cache:
            return self._configs_cache

        configs: dict[str, SoulConfig] = {}
        for path in mtimes:
            raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
            config = SoulConfig.from_mapping(raw)
            configs[config.name] = config

        self._mtime_cache = mtimes
        self._configs_cache = configs
        return configs
