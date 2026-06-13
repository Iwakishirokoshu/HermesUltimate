from ._client import call_json, dumps


def related(path: str) -> str:
    """Return wikilinks and backlinks for one vault page."""
    return dumps(call_json("GET", "/related", params={"path": path}))