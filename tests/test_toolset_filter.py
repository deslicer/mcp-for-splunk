"""Unit tests for the per-client ToolsetFilterMiddleware.

The middleware filters MCP components on `list_*` and guards `call_tool`
based on the `X-MCP-Toolsets` header (or `MCP_DEFAULT_TOOLSETS` env
variable when the header is absent).

These tests exercise the pure logic in isolation; the full FastMCP
in-memory client integration lives in `tests/test_toolset_integration.py`.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from fastmcp.exceptions import ToolError

from src.core.toolset_filter import ToolsetFilterMiddleware, _wanted_toolsets


def _component(name: str, tags: set[str]):
    """Build a MagicMock that mimics a FastMCP Tool/Resource/Prompt object."""
    obj = MagicMock()
    obj.name = name
    obj.tags = set(tags)
    return obj


def _patch_headers(monkeypatch, headers: dict[str, str] | None):
    """Replace fastmcp's get_http_headers in the toolset_filter module.

    The middleware reads request headers via ``get_http_headers()`` from
    fastmcp.server.dependencies. In unit tests we have no real HTTP request,
    so we patch the symbol where the middleware imports it.
    """
    monkeypatch.setattr(
        "src.core.toolset_filter.get_http_headers",
        lambda: dict(headers or {}),
    )


# --- _wanted_toolsets pure-logic tests --------------------------------------


def test_wanted_defaults_to_splunk_when_no_env_no_header(monkeypatch):
    """Implicit fallback is the host's own toolset, NOT every loaded plugin.

    Plugins (e.g. ITSI) must be opt-in via X-MCP-Toolsets or
    MCP_DEFAULT_TOOLSETS so a fresh deployment looks like a stock
    Splunk MCP server. Regression guard against silently re-enabling
    plugins for header-less clients.
    """
    monkeypatch.delenv("MCP_DEFAULT_TOOLSETS", raising=False)
    known = {"splunk", "itsi"}
    assert _wanted_toolsets(headers=None, known=known) == {"splunk"}


def test_wanted_explicit_default_overrides_splunk_fallback(monkeypatch):
    """Hosts that ship a different default toolset can pass it explicitly."""
    monkeypatch.delenv("MCP_DEFAULT_TOOLSETS", raising=False)
    known = {"splunk", "itsi", "secops"}
    assert _wanted_toolsets(headers=None, known=known, default="secops") == {"secops"}


def test_wanted_explicit_default_can_request_all(monkeypatch):
    """An explicit default of 'all' restores the previous global behaviour."""
    monkeypatch.delenv("MCP_DEFAULT_TOOLSETS", raising=False)
    known = {"splunk", "itsi"}
    assert _wanted_toolsets(headers=None, known=known, default="all") == known


def test_wanted_default_env_override(monkeypatch):
    monkeypatch.setenv("MCP_DEFAULT_TOOLSETS", "splunk")
    assert _wanted_toolsets(headers=None, known={"splunk", "itsi"}) == {"splunk"}


def test_wanted_header_wins_over_env(monkeypatch):
    monkeypatch.setenv("MCP_DEFAULT_TOOLSETS", "splunk")
    headers = {"x-mcp-toolsets": "itsi"}
    assert _wanted_toolsets(headers=headers, known={"splunk", "itsi"}) == {"itsi"}


def test_wanted_drops_unknown_values(monkeypatch):
    monkeypatch.delenv("MCP_DEFAULT_TOOLSETS", raising=False)
    headers = {"x-mcp-toolsets": "splunk,bogus"}
    assert _wanted_toolsets(headers=headers, known={"splunk", "itsi"}) == {"splunk"}


def test_wanted_all_keyword(monkeypatch):
    monkeypatch.delenv("MCP_DEFAULT_TOOLSETS", raising=False)
    headers = {"x-mcp-toolsets": "all"}
    assert _wanted_toolsets(headers=headers, known={"splunk", "itsi"}) == {"splunk", "itsi"}


def test_wanted_empty_header_falls_back_to_env(monkeypatch):
    monkeypatch.setenv("MCP_DEFAULT_TOOLSETS", "itsi")
    headers = {"x-mcp-toolsets": ""}
    assert _wanted_toolsets(headers=headers, known={"splunk", "itsi"}) == {"itsi"}


def test_wanted_uppercase_header_name(monkeypatch):
    """FastMCP may not lowercase headers; accept both forms."""
    monkeypatch.delenv("MCP_DEFAULT_TOOLSETS", raising=False)
    headers = {"X-MCP-Toolsets": "splunk"}
    assert _wanted_toolsets(headers=headers, known={"splunk", "itsi"}) == {"splunk"}


def test_wanted_intersection_with_unknown_only_yields_empty_set(monkeypatch):
    monkeypatch.delenv("MCP_DEFAULT_TOOLSETS", raising=False)
    headers = {"x-mcp-toolsets": "bogus,foo"}
    assert _wanted_toolsets(headers=headers, known={"splunk", "itsi"}) == set()


# --- on_list_tools ----------------------------------------------------------


@pytest.mark.asyncio
async def test_on_list_tools_filters_to_wanted(monkeypatch):
    monkeypatch.delenv("MCP_DEFAULT_TOOLSETS", raising=False)
    mw = ToolsetFilterMiddleware(known_toolsets=lambda: {"splunk", "itsi"})

    tools = [
        _component("oneshot_search", {"splunk"}),
        _component("itsi_list_entities", {"itsi", "entity"}),
        _component("internal_health", set()),
    ]

    _patch_headers(monkeypatch, {"x-mcp-toolsets": "splunk"})
    ctx = MagicMock()

    async def call_next(_ctx):
        return tools

    out = await mw.on_list_tools(ctx, call_next)
    names = {t.name for t in out}

    assert "oneshot_search" in names, "splunk-tagged tool must remain"
    assert "itsi_list_entities" not in names, "itsi-tagged tool must be hidden"
    assert "internal_health" in names, "untagged tool always visible"


@pytest.mark.asyncio
async def test_on_list_tools_keeps_untagged_when_no_wanted(monkeypatch):
    """If wanted is empty, only untagged components remain."""
    monkeypatch.delenv("MCP_DEFAULT_TOOLSETS", raising=False)
    mw = ToolsetFilterMiddleware(known_toolsets=lambda: {"splunk", "itsi"})

    tools = [
        _component("oneshot_search", {"splunk"}),
        _component("itsi_list_entities", {"itsi"}),
        _component("internal_health", set()),
    ]

    _patch_headers(monkeypatch, {"x-mcp-toolsets": "bogus"})
    ctx = MagicMock()

    async def call_next(_ctx):
        return tools

    out = await mw.on_list_tools(ctx, call_next)
    names = {t.name for t in out}

    assert names == {"internal_health"}


# --- on_call_tool -----------------------------------------------------------


@pytest.mark.asyncio
async def test_on_call_tool_blocks_disabled_toolset(monkeypatch):
    monkeypatch.delenv("MCP_DEFAULT_TOOLSETS", raising=False)
    mw = ToolsetFilterMiddleware(known_toolsets=lambda: {"splunk", "itsi"})

    blocked = _component("itsi_list_entities", {"itsi"})

    _patch_headers(monkeypatch, {"x-mcp-toolsets": "splunk"})
    ctx = MagicMock()
    ctx.message.name = "itsi_list_entities"
    ctx.fastmcp_context.fastmcp.get_tool = AsyncMock(return_value=blocked)

    async def call_next(_ctx):
        return {"status": "success"}

    with pytest.raises(ToolError):
        await mw.on_call_tool(ctx, call_next)


@pytest.mark.asyncio
async def test_on_call_tool_allows_enabled_toolset(monkeypatch):
    monkeypatch.delenv("MCP_DEFAULT_TOOLSETS", raising=False)
    mw = ToolsetFilterMiddleware(known_toolsets=lambda: {"splunk", "itsi"})

    allowed = _component("oneshot_search", {"splunk"})

    _patch_headers(monkeypatch, {"x-mcp-toolsets": "splunk,itsi"})
    ctx = MagicMock()
    ctx.message.name = "oneshot_search"
    ctx.fastmcp_context.fastmcp.get_tool = AsyncMock(return_value=allowed)

    async def call_next(_ctx):
        return {"status": "success"}

    result = await mw.on_call_tool(ctx, call_next)
    assert result == {"status": "success"}


@pytest.mark.asyncio
async def test_on_call_tool_allows_untagged_tool_under_any_header(monkeypatch):
    """Untagged tools must remain callable regardless of header value."""
    monkeypatch.delenv("MCP_DEFAULT_TOOLSETS", raising=False)
    mw = ToolsetFilterMiddleware(known_toolsets=lambda: {"splunk", "itsi"})

    untagged = _component("internal_health", set())

    _patch_headers(monkeypatch, {"x-mcp-toolsets": "bogus"})
    ctx = MagicMock()
    ctx.message.name = "internal_health"
    ctx.fastmcp_context.fastmcp.get_tool = AsyncMock(return_value=untagged)

    async def call_next(_ctx):
        return {"status": "ok"}

    result = await mw.on_call_tool(ctx, call_next)
    assert result == {"status": "ok"}


# --- regression guards ------------------------------------------------------


def test_middleware_reads_headers_via_fastmcp_dependency():
    """Regression guard.

    The middleware must read HTTP headers via
    ``fastmcp.server.dependencies.get_http_headers``. ``MiddlewareContext``
    does *not* expose an ``http_headers`` attribute, so any attempt to
    reach for ``ctx.http_headers`` silently returns ``None`` over real
    HTTP and the filter becomes a no-op.

    If this assertion fails it almost certainly means the import was
    removed or renamed; revisit ``_wanted`` before adjusting the test.
    """
    from fastmcp.server.dependencies import get_http_headers as upstream

    import src.core.toolset_filter as tf

    assert tf.get_http_headers is upstream


# --- install_once -----------------------------------------------------------


def test_install_once_is_idempotent():
    added: list = []

    class FakeMcp:
        def add_middleware(self, mw):
            added.append(mw)

    fake = FakeMcp()
    first = ToolsetFilterMiddleware.install_once(fake, known_toolsets=lambda: set())
    second = ToolsetFilterMiddleware.install_once(fake, known_toolsets=lambda: set())

    assert first is True
    assert second is False
    assert len(added) == 1
