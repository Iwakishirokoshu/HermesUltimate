from ._client import call_json, dumps


def append(path: str, content: str) -> str:
    """Atomically append markdown content through vault-api."""
    return dumps(call_json("POST", "/append", {"path": path, "content": content}))