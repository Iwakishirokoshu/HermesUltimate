from ._client import call_json, dumps
from ._tiers import filter_search_results


def search(query: str, top_k: int = 5, tier: str = "") -> str:
    """Search the Hermes vault via vault-api FTS5."""
    requested_top_k = int(top_k or 5)
    search_top_k = min(50, max(requested_top_k, requested_top_k * 3)) if tier else requested_top_k
    data = call_json("POST", "/search", {"query": query, "top_k": search_top_k})
    return dumps(filter_search_results(data, tier, limit=requested_top_k))
