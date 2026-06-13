# Hermes Souls

Souls are named runtime profiles for Hermes Ultimate. A soul selects:

- the backend (`hermes` or `decepticon`)
- the identity file loaded into the system prompt
- the toolsets allowed for that soul
- optional vault files to preload into context

Soul configs live in `souls/*.yaml`. The matching identity files usually live
under `souls/<name>/SOUL.md`.

## Built-In Souls

`default` is the standard Hermes assistant:

```yaml
name: default
backend: hermes
soul_md: souls/default/SOUL.md
allowed_toolsets:
  - all
vault_load:
  include:
    - INDEX.md
    - Wiki/Hot/general/**
    - Wiki/Hot/personal/**
  budget_kb: 5
```

`red` routes to the Decepticon backend and is scoped for RoE-aware security
work:

```yaml
name: red
backend: decepticon
soul_md: souls/red/SOUL.md
allowed_toolsets:
  - cloak
  - reach
  - shell
  - vault
  - kali
langgraph_url: http://localhost:2024
vault_load:
  include:
    - INDEX.md
    - Engagements/${current_slug}/**
    - Wiki/Findings/*.md
  budget_kb: 8
```

## Create A Soul

1. Add a config file at `souls/<name>.yaml`.
2. Add an identity file at `souls/<name>/SOUL.md`.
3. Set `soul_md` in the yaml to that identity file.
4. Pick `backend: hermes` for the native Hermes loop or `backend: decepticon`
   for the Decepticon LangGraph backend.
5. List only the toolsets this soul should use.

Minimal example:

```yaml
name: analyst
backend: hermes
soul_md: souls/analyst/SOUL.md
allowed_toolsets:
  - all
vault_load:
  include:
    - INDEX.md
  budget_kb: 4
```

`SOUL.md` should describe the operator style, boundaries, and mission of the
soul. Keep it direct and operational; it is loaded as identity text, not as a
chat message.

## Switch Souls

Soul selection is stored per chat in `~/.hermes/soul_state.db`.

- `/red` switches the chat to the `red` soul.
- `/blue` switches the chat back to `default`.
- `/soul <name>` switches to any configured soul.
- `/soul` shows the active soul and available names.

After a switch, Hermes evicts the cached agent for that chat so the next turn
rebuilds the system prompt with the selected soul.

## HermesRedBot

Use a second Telegram bot when you want security sessions to start directly in
the `red` soul without typing `/red` first. Configure it in
`~/.hermes/gateway.yaml` under `telegrams:`:

```yaml
telegrams:
  - id: telegram
    name: Hermes Main Bot
    token: "<main bot token>"
    default_soul: default
    allowed_users:
      - "<your Telegram user id>"

  - id: red
    name: HermesRedBot
    token: "<red bot token>"
    default_soul: red
    allowed_users:
      - "<your Telegram user id>"
```

When Hermes starts the gateway, messages received by the `red` bot use
`default_soul: red` for new chats. A manual `/blue`, `/red`, or `/soul <name>`
choice still wins for chats that already have an active soul saved in
`~/.hermes/soul_state.db`.
