from ._client import call_json, dumps
from ._tiers import scoped_folder


def list(folder: str = "", glob: str = "*", tier: str = "") -> str:
    """List files or folders in the Hermes vault."""
    return dumps(call_json("GET", "/list", params={"folder": scoped_folder(folder, tier), "glob": glob}))
