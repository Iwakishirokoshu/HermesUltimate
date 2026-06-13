import importlib.util
from pathlib import Path

_impl_path = Path(__file__).resolve().parents[1] / "vault-api" / "main.py"
_spec = importlib.util.spec_from_file_location("stack_vault_api_impl", _impl_path)
if _spec is None or _spec.loader is None:
    raise ImportError(f"Cannot load vault-api implementation from {_impl_path}")
_module = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_module)

app = _module.app
AppendRequest = _module.AppendRequest
SearchRequest = _module.SearchRequest