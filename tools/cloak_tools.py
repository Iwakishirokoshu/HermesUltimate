from tools.cloak.click import cloak_click
from tools.cloak.cookies import cloak_cookies_export, cloak_cookies_import
from tools.cloak.fill import cloak_fill
from tools.cloak.navigate import cloak_navigate
from tools.cloak.screenshot import cloak_screenshot
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

CLOAK_FILL_SCHEMA = {
    "name": "cloak.fill",
    "description": "Fill an input-like element in the active Cloak browser page using a CSS selector.",
    "parameters": {
        "type": "object",
        "properties": {
            "selector": {"type": "string", "description": "CSS selector for the element to fill."},
            "text": {"type": "string", "description": "Text to place in the element."},
        },
        "required": ["selector", "text"],
    },
}

CLOAK_SCREENSHOT_SCHEMA = {
    "name": "cloak.screenshot",
    "description": "Capture a PNG screenshot from the active Cloak browser page and save it into HermesVault.",
    "parameters": {
        "type": "object",
        "properties": {},
        "required": [],
    },
}

CLOAK_COOKIES_EXPORT_SCHEMA = {
    "name": "cloak.cookies_export",
    "description": "Export cookies from the active Cloak browser, optionally filtered by domain.",
    "parameters": {
        "type": "object",
        "properties": {
            "domain": {"type": "string", "description": "Optional domain filter.", "default": None},
        },
        "required": [],
    },
}

CLOAK_COOKIES_IMPORT_SCHEMA = {
    "name": "cloak.cookies_import",
    "description": "Import cookies into the active Cloak browser from a JSON file.",
    "parameters": {
        "type": "object",
        "properties": {
            "json_path": {"type": "string", "description": "Path to a cookie JSON file."},
        },
        "required": ["json_path"],
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

registry.register(
    name="cloak.fill",
    toolset="cloak",
    schema=CLOAK_FILL_SCHEMA,
    handler=lambda args, **kw: cloak_fill(args.get("selector") or "", args.get("text") or ""),
    check_fn=check_cloak_requirements,
    is_async=True,
    emoji="C",
)

registry.register(
    name="cloak.screenshot",
    toolset="cloak",
    schema=CLOAK_SCREENSHOT_SCHEMA,
    handler=lambda args, **kw: cloak_screenshot(),
    check_fn=check_cloak_requirements,
    is_async=True,
    emoji="C",
)

registry.register(
    name="cloak.cookies_export",
    toolset="cloak",
    schema=CLOAK_COOKIES_EXPORT_SCHEMA,
    handler=lambda args, **kw: cloak_cookies_export(args.get("domain")),
    check_fn=check_cloak_requirements,
    is_async=True,
    emoji="C",
)

registry.register(
    name="cloak.cookies_import",
    toolset="cloak",
    schema=CLOAK_COOKIES_IMPORT_SCHEMA,
    handler=lambda args, **kw: cloak_cookies_import(args.get("json_path") or ""),
    check_fn=check_cloak_requirements,
    is_async=True,
    emoji="C",
)
