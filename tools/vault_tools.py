from tools.registry import registry
from tools.vault.append import append as vault_append
from tools.vault.list import list as vault_list
from tools.vault.read import read as vault_read
from tools.vault.related import related as vault_related
from tools.vault.search import search as vault_search


VAULT_SEARCH_SCHEMA = {
    "name": "vault.search",
    "description": "Search the shared HermesVault markdown brain using vault-api FTS5.",
    "parameters": {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Search query."},
            "top_k": {"type": "integer", "description": "Maximum results to return.", "default": 5},
            "tier": {
                "type": "string",
                "description": "Optional vault tier to search: hot, warm, cold, or findings.",
                "enum": ["hot", "warm", "cold", "findings"],
            },
        },
        "required": ["query"],
    },
}

VAULT_READ_SCHEMA = {
    "name": "vault.read",
    "description": "Read a specific markdown file from HermesVault by relative path.",
    "parameters": {
        "type": "object",
        "properties": {"path": {"type": "string", "description": "Vault-relative markdown path."}},
        "required": ["path"],
    },
}

VAULT_LIST_SCHEMA = {
    "name": "vault.list",
    "description": "List files and folders in HermesVault.",
    "parameters": {
        "type": "object",
        "properties": {
            "folder": {"type": "string", "description": "Vault-relative folder.", "default": ""},
            "glob": {"type": "string", "description": "Glob filter for entry names or relative paths.", "default": "*"},
            "tier": {
                "type": "string",
                "description": "Optional vault tier root: hot, warm, cold, or findings.",
                "enum": ["hot", "warm", "cold", "findings"],
            },
        },
        "required": [],
    },
}

VAULT_RELATED_SCHEMA = {
    "name": "vault.related",
    "description": "Return outgoing wikilinks and backlinks for a vault page.",
    "parameters": {
        "type": "object",
        "properties": {"path": {"type": "string", "description": "Vault-relative markdown path."}},
        "required": ["path"],
    },
}

VAULT_APPEND_SCHEMA = {
    "name": "vault.append",
    "description": "Atomically append markdown content to a HermesVault file through vault-api.",
    "parameters": {
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "Vault-relative markdown path."},
            "content": {"type": "string", "description": "Markdown content to append."},
        },
        "required": ["path", "content"],
    },
}


def check_vault_requirements() -> bool:
    return True


registry.register(
    name="vault.search",
    toolset="vault",
    schema=VAULT_SEARCH_SCHEMA,
    handler=lambda args, **kw: vault_search(args.get("query") or "", args.get("top_k", 5), args.get("tier") or ""),
    check_fn=check_vault_requirements,
    emoji="V",
)
registry.register(
    name="vault.read",
    toolset="vault",
    schema=VAULT_READ_SCHEMA,
    handler=lambda args, **kw: vault_read(args.get("path") or ""),
    check_fn=check_vault_requirements,
    emoji="V",
)
registry.register(
    name="vault.list",
    toolset="vault",
    schema=VAULT_LIST_SCHEMA,
    handler=lambda args, **kw: vault_list(args.get("folder") or "", args.get("glob") or "*", args.get("tier") or ""),
    check_fn=check_vault_requirements,
    emoji="V",
)
registry.register(
    name="vault.related",
    toolset="vault",
    schema=VAULT_RELATED_SCHEMA,
    handler=lambda args, **kw: vault_related(args.get("path") or ""),
    check_fn=check_vault_requirements,
    emoji="V",
)
registry.register(
    name="vault.append",
    toolset="vault",
    schema=VAULT_APPEND_SCHEMA,
    handler=lambda args, **kw: vault_append(args.get("path") or "", args.get("content") or ""),
    check_fn=check_vault_requirements,
    emoji="V",
)
