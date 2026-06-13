from ._client import call_json, dumps


def search(query: str, top_k: int = 5) -> str:
    """Search the Hermes vault via vault-api FTS5."""
    return dumps(call_json("POST", "/search", {"query": query, "top_k": top_k}))