#!/usr/bin/env python3
import hashlib
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


CACHE_VERSION = 1
GROUPS = [
    ("Hot", "Wiki/Hot/"),
    ("Warm", "Wiki/Warm/"),
    ("Cold", "Wiki/Cold/"),
    ("Findings", "Wiki/Findings/"),
    ("Engagements", "Engagements/"),
]


def vault_root() -> Path:
    return Path(os.environ.get("HERMES_VAULT_PATH", "~/HermesVault")).expanduser().resolve()


def rel_path(root: Path, path: Path) -> str:
    return path.resolve().relative_to(root).as_posix()


def load_cache(cache_path: Path) -> dict[str, Any]:
    if not cache_path.exists():
        return {"version": CACHE_VERSION, "pages": {}}
    try:
        cache = json.loads(cache_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {"version": CACHE_VERSION, "pages": {}}
    if cache.get("version") != CACHE_VERSION or not isinstance(cache.get("pages"), dict):
        return {"version": CACHE_VERSION, "pages": {}}
    return cache


def split_frontmatter(text: str) -> tuple[dict[str, list[str]], str]:
    if not text.startswith("---\n"):
        return {}, text
    end = text.find("\n---", 4)
    if end == -1:
        return {}, text
    raw = text[4:end].strip().splitlines()
    body = text[end + len("\n---"):].lstrip("\r\n")
    tags: list[str] = []
    in_tags = False
    for line in raw:
        stripped = line.strip()
        if stripped.startswith("tags:"):
            in_tags = True
            value = stripped.split(":", 1)[1].strip()
            tags.extend(parse_tag_value(value))
            continue
        if in_tags and stripped.startswith("- "):
            tags.extend(parse_tag_value(stripped[2:].strip()))
            continue
        if stripped and not stripped.startswith("- "):
            in_tags = False
    return {"tags": tags}, body


def parse_tag_value(value: str) -> list[str]:
    value = value.strip()
    if not value:
        return []
    if value.startswith("[") and value.endswith("]"):
        value = value[1:-1]
    parts = [part.strip().strip("'\"") for part in value.split(",")]
    return [part.lstrip("#") for part in parts if part.strip().strip("'\"")]


def extract_h1(body: str, fallback: str) -> str:
    for line in body.splitlines():
        stripped = line.strip()
        if stripped.startswith("# "):
            return stripped[2:].strip() or fallback
    return fallback


def strip_markdown(text: str) -> str:
    text = re.sub(r"`([^`]+)`", r"\1", text)
    text = re.sub(r"\[\[([^\]|]+)\|([^\]]+)\]\]", r"\2", text)
    text = re.sub(r"\[\[([^\]]+)\]\]", r"\1", text)
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
    text = re.sub(r"[*_>#-]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def first_paragraph(body: str) -> str:
    cleaned_lines: list[str] = []
    in_code = False
    for line in body.splitlines():
        stripped = line.strip()
        if stripped.startswith("```"):
            in_code = not in_code
            continue
        if in_code or stripped.startswith("# "):
            continue
        if not stripped:
            if cleaned_lines:
                break
            continue
        cleaned_lines.append(stripped)
    return strip_markdown(" ".join(cleaned_lines))[:80]


def group_for_path(path: str) -> str:
    for group, prefix in GROUPS:
        if path.startswith(prefix):
            return group
    return "Other"


def parse_page(root: Path, path: Path) -> dict[str, Any]:
    rel = rel_path(root, path)
    raw = path.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    text = raw.decode("utf-8", errors="replace")
    frontmatter, body = split_frontmatter(text)
    title = extract_h1(body, path.stem)
    tags = sorted(set(frontmatter.get("tags", [])))
    return {
        "path": rel,
        "title": title,
        "tags": tags,
        "summary": first_paragraph(body),
        "group": group_for_path(rel),
        "mtime_ns": path.stat().st_mtime_ns,
        "hash": digest,
    }


def collect_pages(root: Path, cache: dict[str, Any]) -> list[dict[str, Any]]:
    pages_cache = cache.setdefault("pages", {})
    seen: set[str] = set()
    pages: list[dict[str, Any]] = []
    for path in sorted(root.rglob("*.md")):
        rel = rel_path(root, path)
        if rel == "INDEX.md" or rel.startswith(".meta/"):
            continue
        seen.add(rel)
        stat = path.stat()
        cached = pages_cache.get(rel)
        if cached and cached.get("mtime_ns") == stat.st_mtime_ns:
            pages.append(cached)
            continue
        parsed = parse_page(root, path)
        pages_cache[rel] = parsed
        pages.append(parsed)
    for stale in sorted(set(pages_cache) - seen):
        pages_cache.pop(stale, None)
    return pages


def tag_text(tags: list[str]) -> str:
    if not tags:
        return ""
    return " " + " ".join(f"#{tag}" for tag in tags)


def render_index(pages: list[dict[str, Any]]) -> str:
    generated = datetime.now(timezone.utc).isoformat()
    lines = [
        "# HermesVault Index",
        "",
        f"Generated: {generated}",
        "",
    ]
    groups = [group for group, _prefix in GROUPS] + ["Other"]
    for group in groups:
        group_pages = [page for page in pages if page.get("group") == group]
        if not group_pages:
            continue
        lines.append(f"## {group}")
        lines.append("")
        for page in sorted(group_pages, key=lambda item: (str(item.get("title", "")), str(item.get("path", "")))):
            path = str(page.get("path", ""))
            title = str(page.get("title", Path(path).stem))
            summary = str(page.get("summary") or "")
            suffix = f" - {summary}" if summary else ""
            lines.append(f"- [[{path}|{title}]]{tag_text(page.get('tags', []))}{suffix}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def main() -> int:
    root = vault_root()
    root.mkdir(parents=True, exist_ok=True)
    meta = root / ".meta"
    meta.mkdir(parents=True, exist_ok=True)
    cache_path = meta / "index_cache.json"
    cache = load_cache(cache_path)
    pages = collect_pages(root, cache)
    (root / "INDEX.md").write_text(render_index(pages), encoding="utf-8")
    cache_path.write_text(json.dumps(cache, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"Indexed {len(pages)} pages into {root / 'INDEX.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
