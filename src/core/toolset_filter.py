"""Per-client toolset filtering middleware.

Plugins (and the host itself) tag their tools with a *toolset tag* — by
convention the same name used as the entry-point key under
``mcp_splunk.plugins``. Clients pick which toolsets they want for a
session by sending the ``X-MCP-Toolsets`` HTTP header (comma-separated).
When the header is absent the middleware falls back to the
``MCP_DEFAULT_TOOLSETS`` environment variable, which defaults to
``"splunk"`` — i.e. only the host's own toolset is visible. Plugins
(e.g. ITSI) must be opted into explicitly via header or env var.

Untagged components — components whose ``tags`` set has no overlap with
the known toolset universe — are always visible. This protects
framework-level items (health probes, internal helpers) from being
accidentally hidden when a client sends a strict header value.

The middleware is wired into the host server by
:func:`src.server.install_toolset_filter` after plugin loading. It is
intentionally generic: any future plugin that follows the entry-point
naming convention gets per-client toggling for free.
"""

from __future__ import annotations

import logging
import os
from collections.abc import Callable, Iterable

from fastmcp.exceptions import ToolError
from fastmcp.server.dependencies import get_http_headers
from fastmcp.server.middleware import Middleware, MiddlewareContext

logger = logging.getLogger(__name__)

HEADER_NAME = "x-mcp-toolsets"
DEFAULT_ENV_VAR = "MCP_DEFAULT_TOOLSETS"
ALL_KEYWORD = "all"
# Implicit fallback when neither the X-MCP-Toolsets header nor the
# MCP_DEFAULT_TOOLSETS env var is set. Defaults to the host's own
# toolset so plugins (e.g. ITSI) must be explicitly opted into.
HOST_DEFAULT = "splunk"


def _read_header(headers: dict | None) -> str | None:
    """Return the X-MCP-Toolsets header value, case-insensitive, or None."""
    if not headers:
        return None
    return (
        headers.get(HEADER_NAME)
        or headers.get(HEADER_NAME.upper())
        or headers.get("X-MCP-Toolsets")
    )


def _wanted_toolsets(
    headers: dict | None,
    known: set[str],
    default: str = HOST_DEFAULT,
) -> set[str]:
    """Return the set of toolset tags the current request wants to see.

    Selection rules (highest precedence first):

    1. ``X-MCP-Toolsets`` header value (case-insensitive header name).
    2. ``MCP_DEFAULT_TOOLSETS`` environment variable.
    3. The ``default`` argument (``"splunk"`` for the standard host).

    The literal keyword ``"all"`` (case-insensitive) at any layer
    expands to ``known``. Unknown values are silently dropped.
    """
    raw: str | None = _read_header(headers)
    if not raw or not raw.strip():
        raw = os.getenv(DEFAULT_ENV_VAR, default)

    raw = raw.strip().lower()
    if raw == ALL_KEYWORD:
        return set(known)

    requested = {p.strip() for p in raw.split(",") if p.strip()}
    return requested & known


class ToolsetFilterMiddleware(Middleware):
    """Filter tools, resources, and prompts by client-requested toolsets.

    The ``known_toolsets`` callable is invoked per request so the universe
    of toolsets can change at runtime as plugins are loaded.

    Args:
        known_toolsets: zero-arg callable returning the current set of
            known toolset tags (e.g. ``{"splunk", "itsi"}``).
    """

    def __init__(self, known_toolsets: Callable[[], Iterable[str]]):
        self._known_toolsets_fn = known_toolsets

    # -- helpers -----------------------------------------------------------

    def _known(self) -> set[str]:
        return set(self._known_toolsets_fn())

    @staticmethod
    def _is_toolset_member(tags: Iterable[str], known: set[str]) -> bool:
        """A component is a toolset member iff at least one of its tags is a known toolset tag."""
        return bool(set(tags) & known)

    def _wanted(self, ctx: MiddlewareContext, known: set[str]) -> set[str]:
        # FastMCP exposes the active HTTP request's headers via this dependency.
        # Outside an HTTP request (e.g. in-memory transport, unit tests) it
        # returns an empty dict, in which case we fall back to MCP_DEFAULT_TOOLSETS.
        # The ``ctx`` argument is kept for future per-context overrides.
        del ctx
        headers = get_http_headers()
        return _wanted_toolsets(headers, known)

    def _passes(self, tags: Iterable[str], known: set[str], wanted: set[str]) -> bool:
        """A component is visible iff it's untagged or its tags overlap wanted."""
        return not self._is_toolset_member(tags, known) or bool(set(tags) & wanted)

    # -- middleware hooks --------------------------------------------------

    async def on_list_tools(self, context: MiddlewareContext, call_next):
        tools = await call_next(context)
        known = self._known()
        wanted = self._wanted(context, known)
        return [t for t in tools if self._passes(getattr(t, "tags", set()), known, wanted)]

    async def on_call_tool(self, context: MiddlewareContext, call_next):
        known = self._known()
        wanted = self._wanted(context, known)
        # FastMCP always populates fastmcp_context for tools/call middleware;
        # the explicit None-guard narrows ``Context | None`` to ``Context``
        # for mypy and fails closed (rather than silently skipping the
        # toolset guard) if the upstream invariant ever changes. We raise
        # instead of ``assert`` so the check survives ``python -O``, which
        # strips assertions from compiled byte code (Bandit B101).
        fastmcp_ctx = context.fastmcp_context
        if fastmcp_ctx is None:
            raise RuntimeError(
                "fastmcp_context must be populated during tools/call"
            )
        tool = await fastmcp_ctx.fastmcp.get_tool(context.message.name)
        if self._is_toolset_member(getattr(tool, "tags", set()), known) and not (
            set(getattr(tool, "tags", set())) & wanted
        ):
            raise ToolError(
                f"Tool '{context.message.name}' is not in an enabled toolset for this client"
            )
        return await call_next(context)

    async def on_list_resources(self, context: MiddlewareContext, call_next):
        resources = await call_next(context)
        known = self._known()
        wanted = self._wanted(context, known)
        return [
            r for r in resources if self._passes(getattr(r, "tags", set()), known, wanted)
        ]

    async def on_list_prompts(self, context: MiddlewareContext, call_next):
        prompts = await call_next(context)
        known = self._known()
        wanted = self._wanted(context, known)
        return [
            p for p in prompts if self._passes(getattr(p, "tags", set()), known, wanted)
        ]

    # -- installation ------------------------------------------------------

    @classmethod
    def install_once(
        cls,
        mcp,
        known_toolsets: Callable[[], Iterable[str]],
    ) -> bool:
        """Install the middleware on ``mcp`` exactly once.

        Returns ``True`` the first time the middleware is added and
        ``False`` on subsequent calls. The flag is stored on ``mcp`` so
        repeated calls from different code paths (e.g. MCP-stage and
        HTTP-stage plugin loading) don't double-register.
        """
        if getattr(mcp, "_toolset_filter_installed", False):
            return False
        mcp.add_middleware(cls(known_toolsets=known_toolsets))
        mcp._toolset_filter_installed = True
        logger.info(
            "ToolsetFilterMiddleware installed on %s",
            getattr(mcp, "name", mcp),
        )
        return True
