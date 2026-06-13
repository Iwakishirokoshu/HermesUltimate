#!/usr/bin/env python3
import argparse
import json
import os
import re
import shutil
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


WIKILINK_RE = re.compile(r"\[\[([^\]|#]+)(#[^\]|]+)?(\|[^\]]+)?\]\]")
TIERS = (
    ("Wiki/Hot", "Wiki/Warm", 7),
    ("Wiki/Warm", "Wiki/Cold", 90),
)


@dataclass(frozen=True)
class MovePlan:
    old_rel: str
    new_rel: str
    age_days: int
    last_read: datetime | None
    reason: str


def vault_root() -> Path:
    return Path(os.environ.get("HERMES_VAULT_PATH", "~/HermesVault")).expanduser().resolve()


def parse_timestamp(value: str) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def rel_path(root: Path, path: Path) -> str:
    return path.resolve().relative_to(root).as_posix()


def load_last_reads(root: Path) -> dict[str, datetime]:
    reads: dict[str, datetime] = {}
    log_path = root / ".meta" / "access.log"
    if not log_path.exists():
        return reads
    with log_path.open("r", encoding="utf-8", errors="replace") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            if row.get("action") != "read":
                continue
            path = str(row.get("path") or "").replace("\\", "/").strip("/")
            timestamp = parse_timestamp(str(row.get("timestamp") or ""))
            if not path or timestamp is None:
                continue
            current = reads.get(path)
            if current is None or timestamp > current:
                reads[path] = timestamp
    return reads


def file_mtime_utc(path: Path) -> datetime:
    return datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)


def collect_move_plan(root: Path, now: datetime) -> list[MovePlan]:
    reads = load_last_reads(root)
    moves: list[MovePlan] = []
    for source_tier, target_tier, threshold_days in TIERS:
        source_root = root / source_tier
        if not source_root.exists():
            continue
        for page in sorted(source_root.rglob("*.md")):
            old_rel = rel_path(root, page)
            last_read = reads.get(old_rel)
            age_base = last_read or file_mtime_utc(page)
            age_days = (now - age_base).days
            if age_days < threshold_days:
                continue
            suffix = page.relative_to(source_root).as_posix()
            new_rel = f"{target_tier}/{suffix}"
            reason = f"no read for {age_days}d (threshold {threshold_days}d)"
            if last_read is None:
                reason = f"no read log; mtime age {age_days}d (threshold {threshold_days}d)"
            moves.append(MovePlan(old_rel, new_rel, age_days, last_read, reason))
    return moves


def build_wikilink_lookup(moves: list[MovePlan]) -> dict[str, str]:
    lookup: dict[str, str] = {}
    stem_counts: dict[str, int] = {}
    for move in moves:
        stem_counts[Path(move.old_rel).stem] = stem_counts.get(Path(move.old_rel).stem, 0) + 1
    for move in moves:
        old_no_ext = move.old_rel.removesuffix(".md")
        new_no_ext = move.new_rel.removesuffix(".md")
        lookup[move.old_rel] = move.new_rel
        lookup[old_no_ext] = new_no_ext
        lookup[Path(move.old_rel).name] = Path(move.new_rel).name
        lookup[Path(move.old_rel).name.removesuffix(".md")] = Path(move.new_rel).name.removesuffix(".md")
        if stem_counts[Path(move.old_rel).stem] == 1:
            lookup[Path(move.old_rel).stem] = new_no_ext
    return lookup


def rewrite_wikilinks(text: str, lookup: dict[str, str]) -> str:
    def replace(match: re.Match[str]) -> str:
        target = match.group(1).replace("\\", "/").strip()
        anchor = match.group(2) or ""
        alias = match.group(3) or ""
        new_target = lookup.get(target)
        if new_target is None:
            return match.group(0)
        return f"[[{new_target}{anchor}{alias}]]"

    return WIKILINK_RE.sub(replace, text)


def impacted_wikilink_files(root: Path, moves: list[MovePlan]) -> list[str]:
    lookup = build_wikilink_lookup(moves)
    impacted: list[str] = []
    for page in sorted(root.rglob("*.md")):
        text = page.read_text(encoding="utf-8", errors="replace")
        if rewrite_wikilinks(text, lookup) != text:
            impacted.append(rel_path(root, page))
    return impacted


def apply_moves(root: Path, moves: list[MovePlan]) -> list[MovePlan]:
    applied: list[MovePlan] = []
    for move in moves:
        source = root / move.old_rel
        target = root / move.new_rel
        if not source.exists() or target.exists():
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(source), str(target))
        applied.append(move)
    return applied


def apply_wikilink_rewrites(root: Path, moves: list[MovePlan]) -> list[str]:
    lookup = build_wikilink_lookup(moves)
    changed: list[str] = []
    for page in sorted(root.rglob("*.md")):
        text = page.read_text(encoding="utf-8", errors="replace")
        updated = rewrite_wikilinks(text, lookup)
        if updated == text:
            continue
        page.write_text(updated, encoding="utf-8")
        changed.append(rel_path(root, page))
    return changed


def print_plan(root: Path, moves: list[MovePlan], impacted: list[str], dry_run: bool) -> None:
    mode = "DRY RUN" if dry_run else "APPLY"
    print(f"{mode} vault-tier-rotate: {root}")
    if not moves:
        print("No tier moves needed.")
    for move in moves:
        last = move.last_read.isoformat() if move.last_read else "never"
        print(f"MOVE {move.old_rel} -> {move.new_rel} | last_read={last} | {move.reason}")
    if impacted:
        print("WIKILINK UPDATES")
        for path in impacted:
            print(f"UPDATE {path}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Rotate HermesVault pages between Hot, Warm, and Cold tiers.")
    parser.add_argument("--dry-run", action="store_true", help="Print the move plan without changing files.")
    args = parser.parse_args()

    root = vault_root()
    if not root.exists():
        print(f"Vault not found: {root}")
        print("No tier moves needed.")
        return 0

    now = datetime.now(timezone.utc)
    moves = collect_move_plan(root, now)
    impacted = impacted_wikilink_files(root, moves) if moves else []
    print_plan(root, moves, impacted, args.dry_run)
    if args.dry_run:
        return 0

    applied = apply_moves(root, moves)
    changed = apply_wikilink_rewrites(root, applied) if applied else []
    print(f"Applied moves: {len(applied)}")
    print(f"Updated wikilink files: {len(changed)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
