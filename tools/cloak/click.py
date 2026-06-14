import json
from typing import Any

from ._cdp_client import evaluate


async def cloak_click(selector: str) -> dict[str, Any]:
    """Click a DOM element in the active Cloak browser page."""
    expression = f"""
(() => {{
  const selector = {json.dumps(selector)};
  const el = document.querySelector(selector);
  if (!el) throw new Error(`No element matches ${{selector}}`);
  el.scrollIntoView({{block: 'center', inline: 'center'}});
  const rect = el.getBoundingClientRect();
  const clientX = rect.left + rect.width / 2;
  const clientY = rect.top + rect.height / 2;
  for (const type of ['pointerdown', 'mousedown', 'pointerup', 'mouseup', 'click']) {{
    const event = type.startsWith('pointer') && typeof PointerEvent !== 'undefined'
      ? new PointerEvent(type, {{bubbles: true, cancelable: true, view: window, clientX, clientY, pointerId: 1, pointerType: 'mouse', isPrimary: true}})
      : new MouseEvent(type, {{bubbles: true, cancelable: true, view: window, clientX, clientY, button: 0}});
    el.dispatchEvent(event);
  }}
  return {{
    selector,
    tagName: el.tagName,
    text: (el.innerText || el.value || el.getAttribute('aria-label') || '').slice(0, 200)
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
