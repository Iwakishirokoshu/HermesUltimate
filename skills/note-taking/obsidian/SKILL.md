---
name: obsidian
description: Read, search, create, and edit notes in the Obsidian vault.
platforms: [linux, macos, windows]
---

# Obsidian Vault

Use this skill for HermesVault-backed Obsidian work: reading notes, listing notes, searching note files, creating notes, appending content, and adding wikilinks.

## Vault path

Use a known or resolved vault path before calling file tools.

The documented vault-path convention is the `HERMES_VAULT_PATH` environment variable, for example from `~/.hermes/.env`. If it is unset, use `~/HermesVault`.

File tools do not expand shell variables. Do not pass paths containing `$HERMES_VAULT_PATH` to `read_file`, `write_file`, `patch`, or `search_files`; resolve the vault path first and pass a concrete absolute path. Vault paths may contain spaces, which is another reason to prefer file tools over shell commands.

If the vault path is unknown, `terminal` is acceptable for resolving `HERMES_VAULT_PATH` or checking whether the fallback path exists. Once the path is known, switch back to file tools.

Use the HermesVault layout: `INDEX.md`, `Wiki/Hot/`, `Wiki/Warm/`, `Wiki/Cold/`, `Wiki/Findings/`, `Wiki/References/SecondBrain/`, `Engagements/`, `Sessions/`, and `.meta/`. Put active working notes in `Wiki/Hot/`, cooler reference material in `Wiki/Warm/` or `Wiki/Cold/`, and operation-specific notes under `Engagements/`.

## Read a note

Use `read_file` with the resolved absolute path to the note. Prefer this over `cat` because it provides line numbers and pagination.

## List notes

Use `search_files` with `target: "files"` and the resolved vault path. Prefer this over `find` or `ls`.

- To list all markdown notes, use `pattern: "*.md"` under the vault path.
- To list a subfolder, search under that subfolder's absolute path.

## Search

Use `search_files` for both filename and content searches. Prefer this over `grep`, `find`, or `ls`.

- For filenames, use `search_files` with `target: "files"` and a filename `pattern`.
- For note contents, use `search_files` with `target: "content"`, the content regex as `pattern`, and `file_glob: "*.md"` when you want to restrict matches to markdown notes.

## Create a note

Use `vault.append` with a vault-relative path such as `Wiki/Hot/<note>.md` or `Engagements/<engagement>/<note>.md` and the full markdown content. Prefer this over direct file writes because it is atomic and records the write in `.meta/access.log`.

## Append to a note

Prefer `vault.append` for all simple appends because it is atomic and records the write in `.meta/access.log`.

Use a native file-tool workflow only when an anchored edit is required:

- Read the target note with `read_file`.
- Use `patch` for an anchored append when there is stable context, such as adding a section after an existing heading or appending before a known trailing block.
- Use `write_file` when rewriting the whole note is clearer than constructing a fragile patch.

For an anchored append with `patch`, replace the anchor with the anchor plus the new content.

For a simple append with no stable context, use `vault.append`.

## Targeted edits

Use `patch` for focused note changes when the current content gives you stable context. Prefer this over shell text rewriting.

## Wikilinks

Obsidian links notes with `[[Note Name]]` syntax. When creating notes, use these to link related content.
