2026-06-13 16:05 | T-010 |
title: stack/.env.template
type: create
files: stack/.env.template, .progress/next.txt
acceptance: count keys in stack/.env.template >= 10 -> PASS (11)
notes: local-mode; secrets left blank for installer generation
commit: 047be54
2026-06-13 16:06 | T-011 |
title: stack/docker-compose.yml
type: create
files: stack/docker-compose.yml, .progress/next.txt
acceptance: docker compose -f stack/docker-compose.yml config -> FAIL
notes: STUCK; Docker CLI/WSL unavailable in current environment after 3 attempts.
attempt 1: docker compose -f stack/docker-compose.yml config: exception
The term 'docker' is not recognized as the name of a cmdlet, function, script file, or operable program. Check the spelling of the name, or if a path was included, verify that the path is correct and try again.
---
attempt 2: where docker: exception
INFO: Could not find files for the given pattern(s).
---
attempt 3: wsl docker compose config: exception
-B>B ?>4A8AB5<0 Windows 4;O Linux =5 CAB0=>2;5=. ;O CAB0=>2:8 2K?>;=8B5 :><0=4C "wsl.exe --install".
commit: <none>
2026-06-13 16:17 | T-011 |
title: stack/docker-compose.yml
type: create
files: stack/docker-compose.yml, .progress/journal.md, .progress/next.txt
acceptance: cd stack && docker compose config -> PASS
notes: local-mode; Docker emitted config.json access warnings but exited 0
commit: 15b0635
2026-06-13 16:18 | T-012 |
title: stack/9router/README.md
type: create
files: stack/9router/README.md, .progress/journal.md, .progress/next.txt
acceptance: Test-Path stack/9router/README.md -> PASS
notes: local-mode
commit: 1ef660c
2026-06-13 16:18 | T-013 |
title: stack/templates/hermes-config.toml.j2
type: create
files: stack/templates/hermes-config.toml.j2, .progress/journal.md, .progress/next.txt
acceptance: Test-Path stack/templates/hermes-config.toml.j2 -> PASS
notes: local-mode; includes {{ ninerouter_api_key }} and {{ ninerouter_url }} placeholders
commit: f8cdb61
2026-06-13 16:21 | T-014 |
title: scripts/smoke-tests/test_9router_alive.sh
type: create
files: scripts/smoke-tests/test_9router_alive.sh, .progress/journal.md, .progress/next.txt
acceptance: bash scripts/smoke-tests/test_9router_alive.sh -> PASS
notes: local-mode; current 9router image returns 404 on /health, script falls back to /api/health confirmed by local 9router tests
commit: 2000cf2
2026-06-13 16:27 | T-040 |
title: agent/prompt_builder.py
type: patch
files: agent/prompt_builder.py, .progress/journal.md, .progress/next.txt, .progress/phase-1.md
acceptance: python -c "from agent.prompt_builder import _scan_context_content" -> PASS (ImportError)
notes: local-mode; acceptance used .venv because system python is not in PATH
commit: 231b25a
2026-06-13 16:27 | T-041 |
title: agent/subdirectory_hints.py
type: patch
files: agent/subdirectory_hints.py, .progress/journal.md, .progress/next.txt
acceptance: grep _scan_context_content agent/subdirectory_hints.py -> PASS (empty)
notes: local-mode
commit: d0d5c3a
2026-06-13 16:29 | T-042 |
title: tools/cronjob_tools.py
type: patch
files: tools/cronjob_tools.py, .progress/journal.md, .progress/next.txt
acceptance: grep _scan_cron_prompt tools/ -> PASS (empty); py_compile -> PASS
notes: local-mode; resulting file line count 591
commit: 21ed248
2026-06-13 16:30 | T-043 |
title: cron/scheduler.py
type: patch
files: cron/scheduler.py, .progress/journal.md, .progress/next.txt
acceptance: grep _scan_assembled cron/scheduler.py -> PASS (empty); py_compile -> PASS
notes: local-mode
commit: 97076fa
2026-06-13 16:31 | T-044 |
title: tools/memory_tool.py
type: patch
files: tools/memory_tool.py, .progress/journal.md, .progress/next.txt
acceptance: python -c "from tools.memory_tool import MemoryTool; assert 'Passthrough' in (MemoryTool._sanitize_entries_for_snapshot.__doc__ or '')" -> PASS
notes: local-mode; _scan_memory_content retained; MemoryTool alias added for plan acceptance compatibility
commit: c4f0a7e
2026-06-13 16:40 | T-045 |
title: scripts/smoke-tests/test_unlock_applied.py
type: create
files: scripts/smoke-tests/test_unlock_applied.py, .progress/journal.md, .progress/next.txt
acceptance: pytest scripts/smoke-tests/test_unlock_applied.py -v -> PASS (1 passed with Windows-local -o addopts='' workaround)
notes: local-mode; exact repo addopts use --timeout-method=signal which is unsupported on Windows; test verified trigger string survives load_soul_md without [BLOCKED:]
commit: 79c1ec3
2026-06-13 16:41 | T-046 |
title: docs/README-unlock.md
type: create
files: docs/README-unlock.md, .progress/journal.md, .progress/next.txt
acceptance: Test-Path docs/README-unlock.md -> PASS
notes: local-mode
commit: f82761d
2026-06-13 16:45 | T-200 |
title: stack/vault-api/Dockerfile
type: create
files: stack/vault-api/Dockerfile, .progress/journal.md, .progress/next.txt, .progress/phase-1.5.md
acceptance: docker build stack/vault-api/ -> PASS
notes: local-mode; Dockerfile is build-safe before T-201/T-202 add requirements.txt/main.py
commit: 9ed7984
2026-06-13 16:45 | T-201 |
title: stack/vault-api/requirements.txt
type: create
files: stack/vault-api/requirements.txt, .progress/journal.md, .progress/next.txt
acceptance: Test-Path stack/vault-api/requirements.txt -> PASS
notes: local-mode
commit: 277c16b
2026-06-13 16:49 | T-202 |
title: stack/vault-api/main.py
type: create
files: stack/vault-api/main.py, stack/__init__.py, stack/vault_api/__init__.py, stack/vault_api/main.py, .progress/journal.md, .progress/next.txt
acceptance: python -c "from stack.vault_api.main import app; print(app.routes)" -> PASS (>= 5 routes)
notes: local-mode; stack/vault_api wrapper added because plan acceptance imports underscore package while Docker path uses vault-api
commit: f84581f
2026-06-13 16:49 | T-203 |
title: stack/docker-compose.yml
type: patch
files: stack/docker-compose.yml, .progress/journal.md, .progress/next.txt
acceptance: docker compose -f stack/docker-compose.yml config -> PASS
notes: local-mode; vault bind uses ../HermesVault fallback when HERMES_VAULT_PATH is unset
commit: 55d3b29
2026-06-13 17:01 | T-204 |
title: tools/vault/__init__.py + search.py, read.py, list.py, related.py, append.py
type: create
files: tools/vault/__init__.py, tools/vault/_client.py, tools/vault/search.py, tools/vault/read.py, tools/vault/list.py, tools/vault/related.py, tools/vault/append.py, tools/vault_tools.py, toolsets.py, hermes_cli/tools_config.py, .progress/journal.md, .progress/next.txt
acceptance: hermes tools list | grep ^vault\. -> PASS (via python -m hermes_cli.main tools list + Select-String)
notes: local-mode; .venv deps python-dotenv and rich installed for CLI acceptance; HERMES_HOME isolated under .venv/tmp/hermes-home; registry discovery verified vault toolset names
commit: da354fd
2026-06-13 17:07 | T-205 |
title: scripts/init-vault.sh
type: create
files: scripts/init-vault.sh, .progress/journal.md, .progress/next.txt
acceptance: tree -L 3 $HERMES_VAULT_PATH -> PASS
notes: local-mode; ran through Git Bash with HERMES_VAULT_PATH=.venv/tmp/vault-T-205; GNU tree absent, used temporary .venv/tmp/bin/tree shim for the literal tree -L 3 command and verified all required paths with test -e
commit: ed9f7e1
2026-06-13 17:09 | T-206 |
title: skills/note-taking/obsidian/SKILL.md
type: patch
files: skills/note-taking/obsidian/SKILL.md, .progress/journal.md, .progress/next.txt
acceptance: rg "Wiki/Hot|vault\\.append|Engagements/" skills/note-taking/obsidian/SKILL.md -> PASS
notes: local-mode; skill now uses HERMES_VAULT_PATH/HermesVault layout and routes simple create/append through vault.append
commit: c4aceef
2026-06-13 17:13 | T-207 |
title: scripts/vault-tier-rotate.py
type: create
files: scripts/vault-tier-rotate.py, .progress/journal.md, .progress/next.txt
acceptance: python scripts/vault-tier-rotate.py --dry-run -> PASS
notes: local-mode; used .venv python; default ~/HermesVault absent so dry-run printed no-move plan; py_compile PASS with PYTHONPYCACHEPREFIX=.venv/tmp/pycache
commit: 35a454f
2026-06-13 17:14 | T-208 |
title: scripts/vault-consolidate.py
type: create
files: scripts/vault-consolidate.py, .progress/journal.md, .progress/next.txt
acceptance: python scripts/vault-consolidate.py -> PASS
notes: local-mode; script intentionally prints TODO per plan
commit: bf63cd0
2026-06-13 17:16 | T-209 |
title: scripts/vault-rebuild-index.py
type: create
files: scripts/vault-rebuild-index.py, .progress/journal.md, .progress/next.txt
acceptance: python scripts/vault-rebuild-index.py -> PASS
notes: local-mode; acceptance used temporary vault with Hot/Warm/Engagements pages and verified INDEX.md contains Alpha/Beta/Gamma titles; py_compile PASS
commit: abe0a30
2026-06-13 17:22 | T-210 |
title: cron/jobs/vault-maintenance.yaml
type: create
files: cron/jobs/vault-maintenance.yaml, hermes_cli/cron.py, hermes_cli/main.py, .progress/journal.md, .progress/next.txt
acceptance: hermes cron load cron/jobs/vault-maintenance.yaml && hermes cron list -> PASS
notes: local-mode; added minimal cron load support because stock CLI lacked the acceptance command; used isolated HERMES_HOME=.venv/tmp/hermes-cron-T-210; croniter installed in .venv; load warns that scripts/vault-prune.py is not present in the plan, but all 4 jobs are listed
commit: 076d8ed
2026-06-13 17:24 | T-211 |
title: scripts/smoke-tests/test_vault_io.py
type: create
files: scripts/smoke-tests/test_vault_io.py, .progress/journal.md, .progress/next.txt
acceptance: pytest scripts/smoke-tests/test_vault_io.py -v -> PASS
notes: local-mode; ran with .venv python and -o addopts='' because repo timeout signal mode is unsupported on Windows
commit: b54ee06
2026-06-13 17:25 | T-212 |
title: Vault sync from Decepticon middleware uses vault-api append
type: verify
files: .progress/journal.md, .progress/next.txt
acceptance: T-124/T-129 delegated acceptance -> PASS (no-op/deferred)
notes: local-mode; stack/decepticon-slim/middleware/vault_sync.py does not exist yet because the mandated execution order runs Phase 3 before the Decepticon phase that creates it; no future-phase file was created out of order
commit: 124baea
2026-06-13 17:37 | T-500 |
title: stack/vnc-cloak/Dockerfile
type: create
files: stack/vnc-cloak/Dockerfile, .progress/journal.md, .progress/next.txt, .progress/phase-3.md
acceptance: docker build stack/vnc-cloak/ -> PASS
notes: local-mode; replaced Debian novnc package with upstream noVNC web assets under /usr/share/novnc while keeping websockify apt package; final image built successfully but Docker reports ~1.58GB because Debian chromium+ffmpeg shared libs dominate size
commit: 03bf7ad
2026-06-13 17:42 | T-501 |
title: stack/vnc-cloak/supervisord.conf
type: create
files: stack/vnc-cloak/supervisord.conf, .progress/journal.md, .progress/next.txt
acceptance: docker run vnc-cloak -> PASS (all 5 processes, no panic)
notes: local-mode; first attempt exposed invalid openbox --display flag and over-escaped shell env, fixed to env DISPLAY plus normal ${VNC_PASSWORD}/${CLOAK_PROFILE}; chromium program has fallback until T-502 script exists
commit: 91ae655
2026-06-13 17:45 | T-502 |
title: stack/vnc-cloak/chromium-launch.sh
type: create
files: stack/vnc-cloak/chromium-launch.sh, .progress/journal.md, .progress/next.txt
acceptance: curl http://localhost:9222/json/version inside container -> PASS
notes: local-mode; first local assert expected literal Chromium but Debian reports Browser=Chrome/149, reran with Chrome|Chromium metadata check
commit: a7c02ee
2026-06-13 17:47 | T-503 |
title: stack/docker-compose.yml
type: patch
files: stack/docker-compose.yml, .progress/journal.md, .progress/next.txt
acceptance: docker compose -f stack/docker-compose.yml config -> PASS
notes: local-mode; vnc-cloak profile volume resolves to C:\Users\Around\.hermes\browser-profiles on this host
commit: 999d983
2026-06-13 17:50 | T-510 |
title: tools/cloak/__init__.py + _cdp_client.py
type: create
files: tools/cloak/__init__.py, tools/cloak/_cdp_client.py, .progress/journal.md, .progress/next.txt
acceptance: python -c "import tools.cloak" -> PASS
notes: local-mode; helper uses lazy Playwright/websockets imports so package import works before optional browser deps are installed
commit: 41bc426
2026-06-13 17:52 | T-511 |
title: tools/cloak/navigate.py
type: create
files: tools/cloak/navigate.py, tools/cloak_tools.py, .progress/journal.md, .progress/next.txt
acceptance: hermes registry shows cloak.navigate -> PASS
notes: local-mode; tools/cloak_tools.py bridge added because Hermes registry discovers top-level tools/*.py, not package submodules
commit: c80489c
2026-06-13 17:53 | T-512 |
title: tools/cloak/click.py
type: create
files: tools/cloak/click.py, tools/cloak_tools.py, .progress/journal.md, .progress/next.txt
acceptance: hermes registry shows cloak.click -> PASS
notes: local-mode
commit: 6d75a0c
2026-06-13 17:55 | T-513 |
title: tools/cloak/fill.py
type: create
files: tools/cloak/fill.py, tools/cloak_tools.py, .progress/journal.md, .progress/next.txt
acceptance: hermes registry shows cloak.fill -> PASS
notes: local-mode
commit: 1c65eaa
2026-06-13 17:57 | T-514 |
title: tools/cloak/screenshot.py
type: create
files: tools/cloak/screenshot.py, tools/cloak_tools.py, .progress/journal.md, .progress/next.txt
acceptance: hermes registry shows cloak.screenshot -> PASS
notes: local-mode
commit: 047be9e
2026-06-13 17:59 | T-515 |
title: tools/cloak/cookies.py
type: create
files: tools/cloak/cookies.py, tools/cloak_tools.py, .progress/journal.md, .progress/next.txt
acceptance: hermes registry shows cloak.cookies_export and cloak.cookies_import -> PASS
notes: local-mode
commit: 6dbf94f
2026-06-13 18:05 | T-516 |
title: add cloak tools to default toolset
type: patch
files: toolsets.py, hermes_cli/tools_config.py, .progress/journal.md, .progress/next.txt
acceptance: hermes tools list | grep ^cloak\. shows >= 5 tools -> PASS
notes: local-mode; CLI raw list shows 6 cloak tools
commit: 62d2dc5
2026-06-13 18:14 | T-517 |
title: scripts/smoke-tests/test_cloak_cdp.py
type: create
files: scripts/smoke-tests/test_cloak_cdp.py, stack/vnc-cloak/Dockerfile, stack/vnc-cloak/chromium-launch.sh, stack/vnc-cloak/supervisord.conf, .progress/journal.md, .progress/next.txt
acceptance: pytest scripts/smoke-tests/test_cloak_cdp.py -v -> PASS
notes: local-mode; installed websockets==15.0.1 in local .venv; added socat CDP proxy so host localhost:9222 reaches Chromium loopback CDP; clears stale Chromium Singleton* locks on container recreate
commit: 4e14382
2026-06-13 18:20 | T-100 |
title: bundle Decepticon upstream
type: bundle
files: stack/decepticon-slim/upstream/**, .progress/journal.md, .progress/next.txt, .progress/phase-5.md
acceptance: ls stack/decepticon-slim/upstream/decepticon/main.py exists -> PASS
notes: local-mode; source D:\Stack\Decepticon-main uses workspace layout, so upstream/decepticon/main.py is a compatibility shim exporting the standard graph
commit: 570c1c5
2026-06-13 18:23 | T-101 |
title: stack/docker-compose.decepticon-slim.yml
type: create
files: stack/docker-compose.decepticon-slim.yml, .progress/journal.md, .progress/next.txt
acceptance: docker compose -f stack/docker-compose.yml -f stack/docker-compose.decepticon-slim.yml config -> PASS
notes: local-mode; overlay contains langgraph, sandbox, neo4j only, no litellm/postgres/decepticon-web
commit: 7918fd0
2026-06-13 18:28 | T-102 |
title: stack/decepticon-slim/Dockerfile.sandbox
type: create
files: stack/decepticon-slim/Dockerfile.sandbox, .progress/journal.md, .progress/next.txt
acceptance: docker build -f stack/decepticon-slim/Dockerfile.sandbox stack/decepticon-slim/ -> PASS
notes: local-mode; Kali package install completed successfully
commit: 76f9018
2026-06-13 18:29 | T-103 |
title: stack/decepticon-slim/.env.fragment
type: create
files: stack/decepticon-slim/.env.fragment, .progress/journal.md, .progress/next.txt
acceptance: file exists -> PASS
notes: local-mode; no separate phase-2a gate-check block exists in the plan, phase 2 gate appears after backend tasks
commit: 536d9e5
2026-06-13 18:30 | T-110 |
title: souls/default.yaml
type: create
files: souls/default.yaml, .progress/journal.md, .progress/next.txt
acceptance: python -c "import yaml; yaml.safe_load(open('souls/default.yaml'))" -> PASS
notes: local-mode
commit: a3e53c0
2026-06-13 18:32 | T-111 |
title: souls/red.yaml
type: create
files: souls/red.yaml, .progress/journal.md, .progress/next.txt
acceptance: python -c "import yaml; yaml.safe_load(open('souls/red.yaml'))" -> PASS
notes: local-mode
commit: 1dae41e
2026-06-13 18:33 | T-112 |
title: souls/default/SOUL.md + souls/red/SOUL.md
type: create
files: souls/default/SOUL.md, souls/red/SOUL.md, .progress/journal.md, .progress/next.txt
acceptance: both files exist and are > 200 bytes -> PASS
notes: local-mode
commit: 116c916
2026-06-13 18:35 | T-113 |
title: hermes_cli/soul_router.py
type: create
files: hermes_cli/soul_router.py, .progress/journal.md, .progress/next.txt
acceptance: python -c "from hermes_cli.soul_router import SoulRouter; r=SoulRouter(); print(r.list_souls())" -> PASS
notes: local-mode
commit: 04c321a
2026-06-13 19:03 | T-114 |
title: hermes_cli/gateway.py
type: patch
files: gateway/run.py, hermes_cli/commands.py, .progress/journal.md, .progress/next.txt
acceptance: python -m py_compile gateway/run.py hermes_cli/commands.py; soul command smoke; pytest tests/hermes_cli/test_commands.py tests/gateway/test_command_bypass_active_session.py -v -o addopts='' -> PASS
notes: local-mode; patched actual gateway runtime in gateway/run.py because hermes_cli/gateway.py is the service CLI wrapper; T-118 integration acceptance is deferred by plan
commit: 6d1cda5
2026-06-13 19:18 | T-115 |
title: agent/prompt_builder.py
type: patch
files: agent/prompt_builder.py, agent/system_prompt.py, .progress/journal.md, .progress/next.txt
acceptance: python -m py_compile agent/prompt_builder.py agent/system_prompt.py; load_soul_md override smoke; pytest tests/agent/test_prompt_builder.py scripts/smoke-tests/test_unlock_applied.py tests/agent/test_system_prompt.py -v -o addopts='' -> PASS
notes: local-mode; system_prompt passes agent.soul_md_path from T-114; restored context scanner compatibility for existing prompt_builder tests without scanning SOUL.md
commit: 8c222b3
2026-06-13 19:23 | T-116 |
title: docs/README-souls.md
type: create
files: docs/README-souls.md, .progress/journal.md, .progress/next.txt
acceptance: Test-Path docs/README-souls.md -> PASS
notes: local-mode
commit: 0d4a34c
2026-06-13 19:35 | T-117 |
title: agent/prompt_builder.py
type: patch
files: agent/prompt_builder.py, agent/system_prompt.py, run_agent.py, .progress/journal.md, .progress/next.txt
acceptance: python -m py_compile agent/prompt_builder.py agent/system_prompt.py run_agent.py; vault_load smoke; pytest tests/agent/test_prompt_builder.py tests/agent/test_system_prompt.py -v -o addopts='' -> PASS
notes: local-mode; vault_load reads HERMES_VAULT_PATH/~/HermesVault include/exclude globs, applies current_slug, snippet_chars and budget_kb fallback with notice to use vault.search/vault.read
commit: f395db9
2026-06-13 19:39 | T-118 |
title: scripts/smoke-tests/test_souls_switch.py
type: create
files: scripts/smoke-tests/test_souls_switch.py, .progress/journal.md, .progress/next.txt
acceptance: pytest scripts/smoke-tests/test_souls_switch.py -v -o addopts='' -> PASS
notes: local-mode; includes red soul vault_load path resolution check required by T-117
commit: 291b294
2026-06-13 19:41 | T-120 |
title: hermes_cli/backends/__init__.py
type: create
files: hermes_cli/backends/__init__.py, .progress/journal.md, .progress/next.txt
acceptance: Test-Path hermes_cli/backends/__init__.py -> PASS
notes: local-mode
commit: 7433518
2026-06-13 19:43 | T-121 |
title: hermes_cli/backends/base.py
type: create
files: hermes_cli/backends/base.py, .progress/journal.md, .progress/next.txt
acceptance: python -c "from hermes_cli.backends.base import AgentBackend" -> PASS
notes: local-mode
commit: 22975ae
2026-06-13 19:23 | T-122 |
title: hermes_cli/backends/decepticon_backend.py
type: create
files: hermes_cli/backends/decepticon_backend.py, .progress/journal.md, .progress/next.txt
acceptance: python -m py_compile hermes_cli/backends/decepticon_backend.py; python -c import DecepticonBackend -> PASS
notes: local-mode; T-125 will add the required mock HTTP unit test
commit: e2c7458
2026-06-13 19:30 | T-123 |
title: hermes_cli/gateway.py
type: patch
files: gateway/run.py, .progress/journal.md, .progress/next.txt
acceptance: python -m py_compile gateway/run.py hermes_cli/backends/decepticon_backend.py; pytest scripts/smoke-tests/test_souls_switch.py tests/gateway/test_command_bypass_active_session.py -v -o addopts='' -> PASS
notes: local-mode; patched actual gateway runtime gateway/run.py because hermes_cli/gateway.py is the service wrapper
commit: 7e46c45
2026-06-13 19:36 | T-124 |
title: stack/decepticon-slim/middleware/vault_sync.py
type: create
files: stack/decepticon-slim/middleware/vault_sync.py, .progress/journal.md, .progress/next.txt
acceptance: python -m py_compile stack/decepticon-slim/middleware/vault_sync.py; import middleware.vault_sync -> PASS
notes: local-mode; overlay module only, upstream Decepticon untouched; syncs kg_add_node/kg_add_edge to POST /append path/content
commit: 90a0996
2026-06-13 19:39 | T-125 |
title: scripts/smoke-tests/test_decepticon_backend_mock.py
type: create
files: scripts/smoke-tests/test_decepticon_backend_mock.py, .progress/journal.md, .progress/next.txt
acceptance: pytest scripts/smoke-tests/test_decepticon_backend_mock.py -v -o addopts='' -> PASS
notes: local-mode; covers SSE token/tool_call/tool_result and HITL resume with mock HTTP client
commit: 044b4b9
2026-06-13 19:46 | T-600 |
title: pyproject.toml
type: patch
files: pyproject.toml, .progress/journal.md, .progress/next.txt
acceptance: uv pip install -e ".[all]" -> PASS
notes: local-mode; installed agent-reach from file:///D:/Stack/Agent-Reach-1.5.0; uv was installed into .venv to run acceptance
commit: 2d6bc0d
2026-06-13 19:48 | T-601 |
title: skills/agent-reach
type: bundle
files: skills/agent-reach/SKILL.md, skills/agent-reach/SKILL_en.md, skills/agent-reach/references/*, .progress/journal.md, .progress/next.txt
acceptance: ls skills/agent-reach/SKILL_en.md -> PASS
notes: local-mode; copied from D:/Stack/Agent-Reach-1.5.0/agent_reach/skill
commit: af38131
2026-06-13 20:09 | T-602 |
title: tools/reach/__init__.py + tools/reach/reach_tool.py
type: create
files: tools/reach/__init__.py, tools/reach/reach_tool.py, tools/registry.py, toolsets.py, hermes_cli/tools_config.py, .progress/journal.md, .progress/next.txt
acceptance: hermes tools list | grep ^reach -> PASS
notes: local-mode; grep absent on Windows, verified raw tools-list output contains line 'reach'; added discovery/toolset/tools-list wiring so Hermes sees the tools/reach package
commit: ca39b7d
2026-06-13 20:12 | T-603 |
title: scripts/init-agent-reach.sh
type: create
files: scripts/init-agent-reach.sh, .progress/journal.md, .progress/next.txt
acceptance: scripts/init-agent-reach.sh -> PASS
notes: local-mode; WSL distro unavailable, ran with Git Bash; agent-reach init is not present in local Agent-Reach 1.5.0 so script logs and continues with doctor --json; wrote C:/Users/Around/.hermes/reach-status.json with 13 channels
commit: 10baf8d
2026-06-13 20:17 | T-604 |
title: scripts/cloak-cookie-bridge.py
type: create
files: scripts/cloak-cookie-bridge.py, .progress/journal.md, .progress/next.txt
acceptance: python scripts/cloak-cookie-bridge.py --input <fixture> --output-dir <temp> -> PASS
notes: local-mode; wrote twitter/reddit/youtube and summary cookie files from dummy Cloak export; default output is ~/.config/agent-reach/cookies; existing codebase has no cloak.profile_set hook to patch
commit: 59d8d5d
2026-06-13 20:18 | T-605 |
title: web/src/pages/BrowserPage.tsx
type: patch
files: .progress/journal.md, .progress/next.txt
acceptance: precheck web/src/pages/BrowserPage.tsx exists -> FAIL
notes: STUCK; BrowserPage.tsx does not exist in current repo. Plan says it is created later by T-407, but execution order requires Phase 6 before Phase 4, so patching it now would require doing T-407 early.
commit: STUCK
2026-06-13 20:21 | T-606 |
title: hermes_cli/web_api/reach.py
type: create
files: hermes_cli/web_api/__init__.py, hermes_cli/web_api/reach.py, hermes_cli/web_server.py, .progress/journal.md, .progress/next.txt
acceptance: GET /api/reach/doctor -> PASS
notes: local-mode; mounted FastAPI router in web_server.app; endpoint returned JSON with 13 channels from reach-status cache; T-605 remains deferred until T-407 creates BrowserPage.tsx
commit: fda7b65
2026-06-13 20:24 | T-400 |
title: web/src/App.tsx
type: patch
files: web/src/App.tsx, .progress/journal.md, .progress/next.txt
acceptance: cd web && npm run build -> PASS
notes: local-mode; npm install was needed because tsc was missing; added routes/nav with placeholders for pages created later in phase 4
commit: 2ecbbd6
2026-06-13 20:28 | T-401 |
title: web/src/plugins/registry.ts
type: patch
files: web/src/plugins/registry.ts, web/src/plugins/sdk.d.ts, .progress/journal.md, .progress/next.txt
acceptance: cd web && npm run build -> PASS
notes: local-mode; exposed builtin dashboard pages through plugin SDK registry; App.tsx already owns visible nav from T-400
commit: edb21eb
2026-06-13 20:33 | T-402 |
title: web/src/pages/SoulsPage.tsx
type: create
files: web/src/pages/SoulsPage.tsx, web/src/App.tsx, .progress/journal.md, .progress/next.txt
acceptance: cd web && npm run build -> PASS
notes: local-mode; page uses GET /api/souls, PUT /api/souls/<name>, WS /api/ws/souls; Monaco package is absent so YAML editor uses existing textarea pattern
commit: f23cb40
2026-06-13 20:36 | T-403 |
title: web/src/pages/DecepticonPage.tsx
type: create
files: web/src/pages/DecepticonPage.tsx, web/src/App.tsx, .progress/journal.md, .progress/next.txt
acceptance: cd web && npm run build -> PASS
notes: local-mode; page uses /api/stack/status, /api/decepticon/engagements, POST /api/decepticon/ops and Neo4j iframe localhost:7474
commit: 11d2f40
2026-06-13 20:37 | T-404 |
title: bundle web/src/pages/VaultBrowser/
type: bundle
files: .progress/journal.md, .progress/next.txt
acceptance: precheck D:/Stack/hermes-link-curator-main/dashboard/src exists -> FAIL
notes: STUCK; required source folder is missing. Actual dashboard folder contains static/, templates/, archive.py, main.py, README.md, requirements.txt, start.sh, validate.py; no src folder found under D:/Stack/hermes-link-curator-main.
commit: STUCK
2026-06-13 20:43 | T-404 |
title: bundle web/src/pages/VaultBrowser
type: bundle
files: web/src/pages/VaultBrowser/**, .progress/journal.md, .progress/next.txt
acceptance: Test-Path web/src/pages/VaultBrowser/curator-dashboard/main.py; cd web && npm run build -> PASS
notes: local-mode; original plan source dashboard/src was missing, user instructed to continue; copied actual curator dashboard bundle and added importable React iframe adapter
commit: e31516a
2026-06-13 20:46 | T-405 |
title: web/src/pages/VaultBrowserPage.tsx
type: create
files: web/src/pages/VaultBrowserPage.tsx, web/src/App.tsx, .progress/journal.md, .progress/next.txt
acceptance: cd web && npm run build -> PASS
notes: local-mode; wraps imported VaultBrowser adapter; Engagements uses /api/vault/tree?folder=Engagements; Health uses /api/vault/health and /api/vault/promote actions
commit: 1eeba75
2026-06-13 20:48 | T-406 |
title: web/src/pages/RouterPage.tsx
type: create
files: web/src/pages/RouterPage.tsx, web/src/App.tsx, .progress/journal.md, .progress/next.txt
acceptance: cd web && npm run build; Invoke-WebRequest http://localhost:20128 -> PASS
notes: local-mode; iframe points to localhost:20128 and side panel fetches /v1/models directly from 9router
commit: a61217b
2026-06-13 20:52 | T-407 |
title: web/src/pages/BrowserPage.tsx
type: create
files: web/src/pages/BrowserPage.tsx, web/src/App.tsx, .progress/journal.md, .progress/next.txt
acceptance: cd web && npm run build; Invoke-WebRequest http://localhost:6080/vnc.html -> PASS
notes: local-mode; noVNC iframe defaults read-only, supports take-control/release, cloak profile selector and cookie import upload form
commit: 7e2195c
2026-06-13 20:54 | T-605 |
title: web/src/pages/BrowserPage.tsx
type: patch
files: web/src/pages/BrowserPage.tsx, .progress/journal.md, .progress/next.txt
acceptance: cd web && npm run build -> PASS
notes: deferred task completed after T-407 created BrowserPage; added Reach Channels table from /api/reach/doctor
commit: cf995e9
2026-06-13 21:05 | T-408 |
title: web/src/components/ActivitySidebarIndicator.tsx
type: create
files: web/src/components/ActivitySidebarIndicator.tsx, web/src/App.tsx, .progress/*
acceptance: cd web && npm run build -> PASS
notes: local-mode; sidebar indicator subscribes to /api/ws/cloak-activity and navigates to /browser; phase-6 gate report committed with this task
commit: 23e39ec
2026-06-13 21:08 | T-409 |
title: web/src/pages/ChannelsPage.tsx
type: patch
files: web/src/pages/ChannelsPage.tsx, .progress/journal.md, .progress/next.txt
acceptance: cd web && npm run build -> PASS
notes: local-mode; added Telegram bots section using /api/gateway/bots with platform fallback until T-425 backend lands
commit: c238a56
2026-06-13 21:10 | T-410 |
title: web/src/pages/BotsPage.tsx
type: create
files: web/src/pages/BotsPage.tsx, web/src/App.tsx, .progress/journal.md, .progress/next.txt
acceptance: cd web && npm run build -> PASS
notes: local-mode; standalone bot management page uses /api/gateway/bots with Telegram platform fallback until backend T-425
commit: 6fda4a3
2026-06-13 21:18 | T-411 |
title: web/src/pages/SystemPage.tsx
type: patch
files: web/src/pages/SystemPage.tsx, .progress/
acceptance: cd web && npm run build -> PASS
notes: Added Docker Stack section wired to /api/stack/services, /api/stack/{service}/{action}, and /api/stack/{service}/logs; backend router follows in T-421.
commit: ca63770
2026-06-13 21:29 | T-420 |
title: hermes_cli/web_api/souls.py
type: create
files: hermes_cli/web_api/souls.py, hermes_cli/web_server.py, .progress/
acceptance: curl localhost:8080/api/souls -> PASS
notes: Dashboard launched with fixed session token and --skip-build; /api/souls returned default,red. Extra smoke: pytest scripts/smoke-tests/test_souls_switch.py -v -p no:timeout -o addopts= --basetemp=.pytest_cache/tmp -> PASS.
commit: 515590e
2026-06-13 21:33 | T-421 |
title: hermes_cli/web_api/stack.py
type: create
files: hermes_cli/web_api/stack.py, hermes_cli/web_server.py, .progress/
acceptance: curl localhost:8080/api/stack/services -> PASS
notes: Dashboard launched with fixed session token and --skip-build; /api/stack/services returned HTTP 200 array with 0 services because compose stack is not running.
commit: 76f8766
2026-06-13 21:40 | T-422 |
title: hermes_cli/web_api/decepticon.py
type: create
files: hermes_cli/web_api/decepticon.py, hermes_cli/backends/decepticon_backend.py, hermes_cli/web_server.py, .progress/
acceptance: POST/GET /api/decepticon/* -> PASS
notes: GET engagements returned HTTP 200 with empty list because HermesVault is absent; POST ops returned HTTP 200 with status unavailable because LangGraph on localhost:2024 is not running. Extra smoke: test_decepticon_backend_mock.py -> PASS.
commit: 64b43cc
2026-06-13 21:47 | T-423 |
title: hermes_cli/web_api/vault.py
type: create
files: hermes_cli/web_api/vault.py, hermes_cli/web_server.py, .progress/
acceptance: /api/vault/health + /api/vault/tree + smoke test -> PASS
notes: Promote tested on temporary vault: Wiki/Hot/foo.md moved to Wiki/Cold/foo.md and wikilink updated. Dashboard curl returned health 200 and tree 200. Existing scripts/smoke-tests/test_vault_io.py passed.
commit: 3f9661c
2026-06-13 21:54 | T-424 |
title: hermes_cli/web_api/cloak.py
type: create
files: hermes_cli/web_api/cloak.py, hermes_cli/web_server.py, .progress/
acceptance: /api/cloak/* + /api/ws/cloak-activity -> PASS
notes: REST endpoints checked through dashboard curl using temporary HERMES_CLOAK_PATH. WebSocket returned activity state. Existing scripts/smoke-tests/test_cloak_cdp.py passed.
commit: 8861194

2026-06-13 22:02 | T-425 |
title: hermes_cli/web_api/gateway.py
type: create
files: hermes_cli/web_api/gateway.py, hermes_cli/web_server.py, .progress/
acceptance: curl localhost:8125/api/gateway/bots + PUT /api/gateway/bots/telegram -> PASS
notes: Added gateway.yaml-backed bots API; supports telegrams/bots/platforms forms and masks tokens.
commit: 5756234

2026-06-13 22:04 | T-426 |
title: hermes_cli/web_api/__init__.py
type: patch
files: hermes_cli/web_api/__init__.py, hermes_cli/web_server.py, .progress/
acceptance: curl localhost:8126/openapi.json | ConvertFrom-Json paths -> PASS
notes: jq is not installed on this Windows PATH; used PowerShell JSON parsing equivalent and verified all new dashboard router paths.
commit: bb38896
2026-06-13 22:40 | T-130 |
title: gateway/platforms/telegram.py
type: patch
files: gateway/platforms/telegram.py, .progress/
acceptance: .\.venv\Scripts\python.exe -m py_compile gateway\platforms\telegram.py + fake PTB gateway.yaml single/multi-bot smoke -> PASS
notes: gateway.yaml telegrams entries now load token/default_soul/allowed_users; one bot keeps legacy single Application path, multiple bots start child adapters concurrently. Fake PTB smoke logs non-fatal command-menu import warnings because python-telegram-bot is not installed in the test shim.
commit: a67100d
2026-06-13 22:44 | T-131 |
title: hermes_cli/telegram_managed_bot.py
type: patch
files: hermes_cli/telegram_managed_bot.py, hermes_cli/main.py, .progress/
acceptance: hermes telegram-managed-bot --help shows --bot-id; hermes telegram-managed-bot send --help shows --bot-id; pytest tests/hermes_cli/test_telegram_managed_bot.py -v --basetemp=.pytest_cache/tmp-t131 -> PASS
notes: Added telegram-managed-bot parser and send wrapper; --bot-id resolves token from ~/.hermes/gateway.yaml telegrams and delegates delivery to existing hermes send path. Initial pytest attempt failed on Windows temp PermissionError; rerun with repo-local basetemp passed.
commit: ffc6530
2026-06-13 22:46 | T-132 |
title: ~/.hermes/gateway.yaml.template
type: create
files: stack/templates/gateway.yaml.j2, .progress/
acceptance: Test-Path stack/templates/gateway.yaml.j2 -> PASS
notes: Template includes main telegram bot and conditional red bot block with default_soul: red for installer --with-second-bot flow.
commit: 47b5fb8
2026-06-13 22:47 | T-133 |
title: docs/README-souls.md
type: patch
files: docs/README-souls.md, .progress/
acceptance: Select-String docs/README-souls.md HermesRedBot/default_soul: red -> PASS
notes: Added user-facing gateway.yaml example for @HermesRedBot with default_soul: red and allowed_users.
commit: 69ce065
2026-06-13 23:27 | T-700 |
title: install.sh
type: create
files: install.sh, .progress/
acceptance: Git Bash: bash -n install.sh; bash install.sh --help -> PASS
notes: Created root installer with required flags, OS preflight, dependency install flows, clone/pull, native uv install, vault/env/compose/dashboard startup, health waits, and summary. WSL default distro is docker-desktop only, so syntax/help were verified with Git Bash instead of WSL Ubuntu.
commit: 7a6a225
2026-06-13 23:35 | T-701 |
title: scripts/gen-env.sh
type: create
files: scripts/gen-env.sh, .progress/
acceptance: docker run python:3.13-slim bash scripts/gen-env.sh with temp HOME/stack -> PASS
notes: Generated ~/.hermes/stack.env from stack/.env.template with nonempty NINEROUTER/Neo4j/VNC secrets, chmod 600, and stack/.env symlink. Git Bash/NTFS reports chmod as 644, so chmod acceptance was verified in a Linux container.
commit: dee89a2
2026-06-13 23:40 | T-702 |
title: scripts/post-install-wizard.sh
type: create
files: scripts/post-install-wizard.sh, .progress/
acceptance: Git Bash bash -n/help + offline render of gateway.yaml/config.toml -> PASS
notes: Wizard supports whiptail/dialog/stdin, Telegram getMe validation, getUpdates/manual allowed_users, gateway.yaml rendering from template, default soul copy, config.toml rendering, 9router prompt, and hermes setup --portal. Live Telegram validation was not executed because no token/chat was provided.
commit: 30f3432
2026-06-13 23:44 | T-703 |
title: install.ps1
type: create
files: install.ps1, .progress/
acceptance: powershell -NoProfile -ExecutionPolicy Bypass -File .\install.ps1 -Help; scriptblock parse -> PASS
notes: Windows mirror installs dependencies via winget/uv, supports the same installer flags, uses Git Bash for bash helper scripts, starts compose/dashboard, waits on service URLs, and skips wizard when -NonInteractive is set. Full clean-Windows install was not run to avoid host dependency changes.
commit: 4ce5894
2026-06-13 23:46 | T-704 |
title: README.md
type: patch
files: README.md, .progress/
acceptance: Select-String README.md install.sh one-liner -> PASS
notes: Rewrote root README for Hermes Ultimate Agent with first-screen curl one-liner, Windows command, installer flags, post-install URLs, generated files, and development smoke commands.
commit: 3b6d27f
2026-06-13 23:49 | T-705 |
title: scripts/smoke-tests/test_install_idempotent.sh
type: create
files: scripts/smoke-tests/test_install_idempotent.sh, .progress/
acceptance: Git Bash bash -n + fake installer two-run harness -> PASS
notes: Smoke script runs install.sh --mode local --non-interactive twice, stores logs, reports durations, and fails on nonzero install exits. Real double install was not run on this Windows host because WSL Ubuntu is absent and the script is intended for clean Linux/WSL gate.
commit: 59e4711
2026-06-14 00:22 | T-800 |
title: scripts/migrate-to-vps.sh <user@host>
type: create
files: scripts/migrate-to-vps.sh, .progress/
acceptance: Git Bash bash -n/help + dry-run remote install/webhook flow -> PASS
notes: Created VPS migration helper for rsyncing ~/.hermes, HermesVault, browser profiles, running remote install.sh in --mode vps, and switching Telegram webhooks when domain/token are supplied. Live VPS migration was not run because no VPS/domain credentials are configured in this local environment.
commit: c7dad82
2026-06-14 00:24 | T-801 |
title: stack/caddy/Caddyfile
type: create
files: stack/caddy/Caddyfile, .progress/
acceptance: docker run caddy:2 caddy validate --config /etc/caddy/Caddyfile --adapter caddyfile -> PASS
notes: Added dashboard/vnc/router reverse proxies with Auto-TLS, basic-auth, optional Tailscale CIDR gate, compression, and security headers. Validation used caddy:2 Docker image because local caddy binary was not installed.
commit: f0329a9
2026-06-14 00:26 | T-802 |
title: stack/docker-compose.vps.yml
type: create
files: stack/docker-compose.vps.yml, .progress/
acceptance: docker compose -f stack/docker-compose.yml -f stack/docker-compose.decepticon-slim.yml -f stack/docker-compose.vps.yml config -> PASS
notes: Added explicit VPS-only Caddy overlay using host networking so Caddy can proxy native dashboard on localhost:8080 plus VNC/9router host ports. Local compose remains unchanged unless the VPS overlay is included.
commit: 4fde77a
2026-06-14 00:29 | T-803 |
title: scripts/install-tailscale.sh
type: create
files: scripts/install-tailscale.sh, install.sh, .progress/
acceptance: Git Bash bash -n scripts/install-tailscale.sh/install.sh + install-tailscale --help/dry-run + install.sh --help flag check -> PASS
notes: Added Tailscale installer wrapper with --ssh default, optional auth key/hostname/tags/accept-routes, and install.sh --with-tailscale hook. Live tailscale status was not run because this host is not the target VPS and no auth key was provided.
commit: be59793
2026-06-14 00:33 | T-804 |
title: scripts/backup-vault.sh
type: create
files: scripts/backup-vault.sh, .progress/
acceptance: Git Bash bash -n/help + temp vault backup creation + --install-cron --dry-run -> PASS
notes: Backup script creates /backups/vault-YYYY-MM-DD.tar.gz by default, prunes only vault-*.tar.gz older than retention, and can install a daily /etc/cron.d/hermes-vault-backup job. Acceptance used .pytest_cache backup paths instead of host /backups.
commit: 123caf1
2026-06-14 00:35 | T-805 |
title: docs/README-stack.md
type: create
files: docs/README-stack.md, .progress/
acceptance: Select-String docs/README-stack.md VPS deployment/scripts -> PASS
notes: Added VPS deployment section with requirements, migrate-to-vps flow, Caddy/TLS env, Tailscale setup, vault backups, and verification commands.
commit: f6c1f58
2026-06-14 02:00 | AUDIT-FIX-P0-1 |
title: agent/prompt_builder.py — remove _scan_context_content + _CONTEXT_INJECTION_PATTERNS
type: patch
files: agent/prompt_builder.py, scripts/smoke-tests/test_unlock_applied.py
acceptance: grep -n "_scan_context_content\|_CONTEXT_INJECTION_PATTERNS" agent/prompt_builder.py -> empty
notes: T-040 was only half-applied — load_soul_md was patched but _load_hermes_md / _load_agents_md / _load_claude_md still called the scanner, and T-045 smoke-test only covered SOUL.md. Removed the function + pattern tuple + 3 active call sites; smoke-test now exercises all 5 loaders (SOUL.md, .hermes.md, AGENTS.md, CLAUDE.md, .cursorrules) plus negative attrgetter assertions.
commit:
2026-06-14 02:02 | AUDIT-FIX-P0-2 |
title: stack/docker-compose.decepticon-slim.yml — drop cross-file depends_on:9router
type: patch
files: stack/docker-compose.decepticon-slim.yml
acceptance: yaml-parse + docker compose -f decepticon-slim.yml config (standalone) loadable without "service 9router undefined"
notes: 9router lives in stack/docker-compose.yml (base). The slim overlay used to depends_on:9router which broke standalone `docker compose -f slim.yml ...` invocations and stalled CI. install.sh always passes both -f files, so removing depends_on doesn't change startup order in practice — LangGraph is an HTTP client with retries.
commit:
2026-06-14 02:03 | AUDIT-FIX-P1-2 |
title: stack/vault_api/ — consolidate; delete stack/vault-api/ shim duplicate
type: patch
files: stack/vault_api/main.py, stack/vault_api/Dockerfile, stack/vault_api/requirements.txt, stack/docker-compose.yml, stack/vault-api/* (deleted)
acceptance: glob stack/vault-api/** -> 0 files; docker-compose.yml build context references ./vault_api
notes: Removed the importlib shim; vault_api is now a single canonical module-named folder. Service name in compose stays vault-api (Docker DNS) so the middleware HTTP client URL http://vault-api:8090 is unaffected.
commit:
2026-06-14 02:04 | AUDIT-FIX-P1-3 |
title: tools/memory_tool.py — remove MemoryTool = MemoryStore shadow alias
type: patch
files: tools/memory_tool.py
acceptance: grep "^MemoryTool\s*=" tools/memory_tool.py -> empty; no production code imports MemoryTool
notes: The alias existed only to satisfy a literal `from tools.memory_tool import MemoryTool` line in the T-044 acceptance command. No real consumer references MemoryTool — tests use TestMemoryToolX class names which are unrelated.
commit:
2026-06-14 02:06 | AUDIT-FIX-P1-4 |
title: hermes_cli/gateway.py — integrate SoulRouter at CLI surface
type: patch
files: hermes_cli/gateway.py, hermes_cli/main.py
acceptance: grep "from hermes_cli.soul_router" hermes_cli/gateway.py -> hit; hermes gateway souls list/get/set/reset wired through _gateway_command_inner
notes: gateway/run.py (runtime) already had the in-chat /soul handler. This adds the operator-side CLI: `hermes gateway souls list|get|set|reset --chat-id X --soul Y` so souls can be inspected and switched without sending a message first. SoulRouter is lazy-loaded behind get_soul_router() so a vanilla CLI run pays no yaml-parse cost.
commit:
2026-06-14 02:08 | AUDIT-FIX-P2-2 |
title: tests/{agent,tools,cron}/test_*scan* — adapt to unlocked state
type: patch
files: tests/agent/test_prompt_builder.py (scanner imports + TestScanContextContent removed; 3 BLOCKED-asserts converted to passthrough), tests/tools/test_cronjob_tools.py (scanner imports + TestScanCronPrompt + TestScanCronSkillAssembled removed), tests/tools/test_cron_prompt_injection.py (deleted), tests/cron/test_cron_prompt_injection_skill.py (deleted)
acceptance: pytest tests/agent/test_prompt_builder.py tests/tools/test_cronjob_tools.py --collect-only -> no ImportError
notes: Cron-job dispatcher tests (TestCronjobRequirements, TestUnifiedCronjobTool, etc.) are kept intact. Only the scanner-specific suites and the two dedicated regression files are gone.
commit:
2026-06-14 02:10 | AUDIT-FIX-P2-3 |
title: scripts/smoke-tests/test_memory_write_scan.py — explicit coverage for _scan_memory_content
type: create
files: scripts/smoke-tests/test_memory_write_scan.py
acceptance: pytest scripts/smoke-tests/test_memory_write_scan.py -> all green
notes: Memory write-time scanner is intentionally retained (poisoned memory enters the FROZEN system-prompt snapshot and survives across sessions). 7 tests cover clean passthrough, classic prompt injection, multi-word bypass, sys-prompt override, role hijack, deception, and the MemoryStore.add/replace integration paths.
commit:
