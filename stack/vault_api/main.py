import json
import os
import re
import sqlite3
from datetime import datetime, timezone
from fnmatch import fnmatch
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Query
from filelock import FileLock
from pydantic import BaseModel, Field


app = FastAPI(title="Hermes Vault API", version="0.1.0")

WIKILINK_RE = re.compile(r"\[\[([^\]|#]+)(?:#[^\]|]+)?(?:\|[^\]]+)?\]\]")


def _vault_root() -> Path:
    root = os.environ.get("HERMES_VAULT_PATH", "~/HermesVault")
    return Path(root).expanduser().resolve()


def _safe_path(path: str) -> Path:
    if not path or not str(path).strip():
        raise HTTPException(status_code=400, detail="path is required")
    raw = Path(str(path).replace("\\", "/"))
    if raw.is_absolute() or ".." in raw.parts:
        raise HTTPException(status_code=400, detail="path must stay inside vault")
    root = _vault_root()
    target = (root / raw).resolve()
    try:
        target.relative_to(root)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="path escapes vault") from exc
    return target


def _relative(path: Path) -> str:
    return path.resolve().relative_to(_vault_root()).as_posix()


def _iter_markdown_files(folder: str = "", glob: str = "**/*.md"):
    root = _vault_root()
    base = _safe_path(folder) if folder else root
    if not base.exists():
        return []
    if base.is_file():
        return [base] if fnmatch(base.name, glob) else []
    return sorted(p for p in base.rglob("*.md") if p.is_file() and fnmatch(_relative(p), glob))


def _log_access(action: str, path: str, **extra: Any) -> None:
    root = _vault_root()
    meta = root / ".meta"
    meta.mkdir(parents=True, exist_ok=True)
    row = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "action": action,
        "path": path,
        **extra,
    }
    log_path = meta / "access.log"
    lock = FileLock(str(log_path) + ".lock")
    with lock:
        with log_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


class AppendRequest(BaseModel):
    path: str
    content: str


class SearchRequest(BaseModel):
    query: str
    top_k: int = Field(default=5, ge=1, le=50)


@app.get("/health")
def health():
    return {"ok": True, "vault": str(_vault_root())}


@app.post("/append")
def append_file(request: AppendRequest):
    target = _safe_path(request.path)
    target.parent.mkdir(parents=True, exist_ok=True)
    lock = FileLock(str(target) + ".lock")
    with lock:
        with target.open("a", encoding="utf-8") as handle:
            handle.write(request.content)
    rel = _relative(target)
    _log_access("append", rel, bytes=len(request.content.encode("utf-8")))
    return {"ok": True, "path": rel, "bytes": len(request.content.encode("utf-8"))}


@app.get("/read")
def read_file(path: str = Query(...)):
    target = _safe_path(path)
    if not target.is_file():
        raise HTTPException(status_code=404, detail="file not found")
    rel = _relative(target)
    content = target.read_text(encoding="utf-8")
    _log_access("read", rel)
    return {"path": rel, "content": content}


@app.post("/search")
def search(request: SearchRequest):
    query = request.query.strip()
    if not query:
        raise HTTPException(status_code=400, detail="query is required")
    files = _iter_markdown_files()
    conn = sqlite3.connect(":memory:")
    try:
        conn.execute("CREATE VIRTUAL TABLE pages USING fts5(path, content)")
        for file_path in files:
            rel = _relative(file_path)
            try:
                content = file_path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                continue
            conn.execute("INSERT INTO pages(path, content) VALUES (?, ?)", (rel, content))
        rows = conn.execute(
            "SELECT path, snippet(pages, 1, '[', ']', '...', 12) AS snippet "
            "FROM pages WHERE pages MATCH ? LIMIT ?",
            (query, request.top_k),
        ).fetchall()
        results = [{"path": path, "snippet": snippet} for path, snippet in rows]
    except sqlite3.OperationalError:
        needle = query.lower()
        results = []
        for file_path in files:
            rel = _relative(file_path)
            content = file_path.read_text(encoding="utf-8", errors="ignore")
            idx = content.lower().find(needle)
            if idx >= 0:
                start = max(0, idx - 80)
                end = min(len(content), idx + len(query) + 80)
                results.append({"path": rel, "snippet": content[start:end].replace("\n", " ")})
            if len(results) >= request.top_k:
                break
    finally:
        conn.close()
    _log_access("search", "", query=query, top_k=request.top_k, results=len(results))
    return {"query": query, "results": results}


@app.get("/list")
def list_files(folder: str = "", glob: str = "*"):
    root = _vault_root()
    base = _safe_path(folder) if folder else root
    if not base.exists():
        return {"folder": folder, "entries": []}
    entries = []
    for item in sorted(base.iterdir() if base.is_dir() else [base]):
        rel = _relative(item)
        if fnmatch(item.name, glob) or fnmatch(rel, glob):
            entries.append({"path": rel, "type": "dir" if item.is_dir() else "file"})
    _log_access("list", folder or ".", glob=glob, count=len(entries))
    return {"folder": folder, "entries": entries}


@app.get("/related")
def related(path: str = Query(...)):
    target = _safe_path(path)
    if not target.is_file():
        raise HTTPException(status_code=404, detail="file not found")
    rel = _relative(target)
    content = target.read_text(encoding="utf-8")
    outgoing = sorted(set(WIKILINK_RE.findall(content)))
    aliases = {target.stem, rel, rel.removesuffix(".md")}
    backlinks = []
    for file_path in _iter_markdown_files():
        candidate_rel = _relative(file_path)
        if candidate_rel == rel:
            continue
        linked = set(WIKILINK_RE.findall(file_path.read_text(encoding="utf-8", errors="ignore")))
        if aliases & linked:
            backlinks.append(candidate_rel)
    _log_access("related", rel, links=len(outgoing), backlinks=len(backlinks))
    return {"path": rel, "links": outgoing, "backlinks": sorted(backlinks)}
