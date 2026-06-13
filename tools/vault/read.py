from ._client import call_json, dumps


def read(path: str) -> str:
    """Read one markdown file from the Hermes vault."""
    return dumps(call_json("GET", "/read", params={"path": path}))