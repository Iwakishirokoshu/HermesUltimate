import json
from typing import Any

from ._cdp_client import evaluate


async def cloak_fill(selector: str, text: str) -> dict[str, Any]:
    """Fill an input-like element in the active Cloak browser page."""
    expression = f"""
(() => {{
  const selector = {json.dumps(selector)};
  const text = {json.dumps(text)};
  const el = document.querySelector(selector);
  if (!el) throw new Error(`No element matches ${{selector}}`);
  el.scrollIntoView({{block: 'center', inline: 'center'}});
  el.focus();
  el.value = text;
  el.dispatchEvent(new Event('input', {{bubbles: true}}));
  el.dispatchEvent(new Event('change', {{bubbles: true}}));
  return {{
    selector,
    tagName: el.tagName,
    valueLength: String(el.value || '').length
  }};
}})()
"""
    try:
        result = await evaluate(expression)
        if result.get("exceptionDetails"):
            return {"ok": False, "selector": selector, "error": str(result["exceptionDetails"])}
        value = (result.get("result") or {}).get("value")
        return {"ok": True, "selector": selector, "result": value}
    except Exception as exc:
        return {"ok": False, "selector": selector, "error": str(exc)}
