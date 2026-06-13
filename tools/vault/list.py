from ._client import call_json, dumps


def list(folder: str = "", glob: str = "*") -> str:
    """List files or folders in the Hermes vault."""
    return dumps(call_json("GET", "/list", params={"folder": folder, "glob": glob}))