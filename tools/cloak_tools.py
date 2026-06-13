from tools.cloak.click import cloak_click
from tools.cloak.navigate import cloak_navigate
from tools.registry import registry


def check_cloak_requirements() -> bool:
    return True


CLOAK_NAVIGATE_SCHEMA = {
    "name": "cloak.navigate",
    "description": "Navigate the always-on Cloak browser to a URL through Chrome DevTools Protocol.",
    "parameters": {
        "type": "object",
        "properties": {
            "url": {"type": "string", "description": "URL to open in the Cloak browser."},
            "timeout": {"type": "integer", "description": "Light wait after navigation, in seconds.", "default": 30},
        },
        "required": ["url"],
    },
}

CLOAK_CLICK_SCHEMA = {
    "name": "cloak.click",
    "description": "Click an element in the active Cloak browser page using a CSS selector.",
    "parameters": {
        "type": "object",
        "properties": {
            "selector": {"type": "string", "description": "CSS selector for the element to click."},
        },
        "required": ["selector"],
    },
}


registry.register(
    name="cloak.navigate",
    toolset="cloak",
    schema=CLOAK_NAVIGATE_SCHEMA,
    handler=lambda args, **kw: cloak_navigate(args.get("url") or "about:blank", args.get("timeout", 30)),
    check_fn=check_cloak_requirements,
    is_async=True,
    emoji="C",
)

registry.register(
    name="cloak.click",
    toolset="cloak",
    schema=CLOAK_CLICK_SCHEMA,
    handler=lambda args, **kw: cloak_click(args.get("selector") or ""),
    check_fn=check_cloak_requirements,
    is_async=True,
    emoji="C",
)
