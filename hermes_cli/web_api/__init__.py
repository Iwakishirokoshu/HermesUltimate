"""Dashboard API routers."""

from __future__ import annotations

from hermes_cli.web_api.cloak import router as cloak_router
from hermes_cli.web_api.decepticon import router as decepticon_router
from hermes_cli.web_api.gateway import router as gateway_router
from hermes_cli.web_api.reach import router as reach_router
from hermes_cli.web_api.souls import router as souls_router
from hermes_cli.web_api.stack import router as stack_router
from hermes_cli.web_api.vault import router as vault_router


DASHBOARD_ROUTERS = (
    reach_router,
    cloak_router,
    decepticon_router,
    gateway_router,
    souls_router,
    stack_router,
    vault_router,
)


__all__ = ["DASHBOARD_ROUTERS"]
