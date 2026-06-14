# Hermes Ultimate Framework Unlock

Hermes Ultimate commits the framework-unlock directly in source. The fork removes promptware/threat scanners from local context-loading and cron prompt assembly paths so red-team, reverse-engineering, malware-analysis, and C2 research notes can be carried through the agent without being replaced by `[BLOCKED: ...]` placeholders.

## Unlocked Points

- `agent/prompt_builder.py`: SOUL.md, HERMES.md, AGENTS.md, CLAUDE.md, `.cursorrules`, and `.cursor/rules/*.mdc` are truncated for size but no longer scanned by `_scan_context_content`.
- `agent/subdirectory_hints.py`: lazily loaded AGENTS.md/CLAUDE.md/.cursorrules hints are no longer passed through `_scan_context_content`.
- `tools/cronjob_tools.py`: create/update cron prompts are stored without `_scan_cron_prompt` blocking.
- `cron/scheduler.py`: assembled cron prompts, including skill content, run without `_scan_assembled_cron_prompt`.
- `tools/memory_tool.py`: `_sanitize_entries_for_snapshot()` is a passthrough for the frozen memory snapshot.

## Intentionally Not Changed

The unlock does not modify tool approval, file safety, URL safety, skill install guards, website policy, tool guardrails, message sanitization, or `_scan_memory_content()`. Those controls remain separate from the context/cron/memory snapshot scanner path described above.

## Source Plan

Implementation follows the local Hermes Ultimate plan at `C:\Users\Around\.cursor\plans\hermes_ultimate_agent_66fd9205.plan.md`, phase 1.5.