# ITSI Plugin Toolset Filtering — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add per-client toolset selection (`X-MCP-Toolsets` header) on top of the already-shipped `mcp-itsi-server` plugin, so a single deployed `mcp-for-splunk` server can serve clients that want only the `splunk` toolset, only the `itsi` toolset, or both.

**Architecture:** The plugin loader already mounts `mcp_itsi` via the `mcp_splunk.plugins` entry-point group. We add (1) tags on every tool — `{"splunk"}` for host tools and forwarding the existing `("itsi", ...)` metadata for ITSI tools, (2) a `ToolsetFilterMiddleware` in the host that filters `on_list_*`/`on_call_tool` based on a header (default configurable via env), and (3) a `_loaded_plugins` registry surfaced through `/health` and used by the middleware to know the toolset universe.

**Tech Stack:** Python 3.10+, FastMCP 3, pytest, uv.

---

## File map

**Modify:**
- `src/core/loader.py` — line 217 area: add `tags={"splunk"}` (merged with per-tool metadata tags) when registering host tools.
- `mcp_itsi/core/registration.py` — `register_tools()`: forward `tags=set(metadata.tags)` to `mcp.tool(...)`.
- `src/server.py` — `load_plugins()`: track each loaded plugin on `mcp._loaded_plugins`. Install `ToolsetFilterMiddleware` once after plugins load.
- `src/routes/health.py` — `health_api`: include `loaded_plugins` and `available_toolsets`.
- `docs/guides/plugins.md` — document tagging contract and `X-MCP-Toolsets` header.

**Create:**
- `src/core/toolset_filter.py` — `ToolsetFilterMiddleware` class.
- `tests/test_toolset_filter.py` — unit tests for the middleware logic.
- `tests/test_toolset_integration.py` — end-to-end FastMCP in-memory client tests.

**Test (extend):**
- `tests/test_plugin_loader.py` — add a test asserting `mcp._loaded_plugins` is populated.

---

## Convention

The entry-point name in `[project.entry-points."mcp_splunk.plugins"]` IS the toolset tag. ITSI ships under `itsi = "mcp_itsi.plugin:setup"`, and every ITSI tool's `ToolMetadata.tags` contains `"itsi"`. Host (`mcp-for-splunk`) tools are tagged `{"splunk"}`. Future plugins follow the same rule.

Header values match these tag names. `X-MCP-Toolsets: splunk,itsi` enables both. `all` is shorthand for the full known set. Unknown values are dropped.

---

## Task 1: Forward `tags=` from ITSI ToolMetadata to FastMCP

The `mcp_itsi` plugin already declares `tags=("itsi", ...)` on every tool, but `register_tools()` in `mcp_itsi/core/registration.py` calls `mcp.tool(name=..., description=...)` without forwarding tags. FastMCP therefore never sees those tags. Fix it.

**Files:**
- Modify: `mcp_itsi/core/registration.py` (the `register_tools` function around line 30)
- Test: `tests/test_itsi_registration.py` (new)

- [ ] **Step 1: Write the failing test**

Create `tests/test_itsi_registration.py`:

```python
"""Tests for mcp_itsi.core.registration tag forwarding."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from mcp_itsi.core.base import BaseITSITool, ToolMetadata
from mcp_itsi.core.registration import register_tools


class _FakeTool(BaseITSITool):
    """Minimal ITSI tool fixture."""

    METADATA = ToolMetadata(
        name="itsi_test_tool",
        description="A fake tool used in tests.",
        category="testing",
        tags=("itsi", "test"),
    )

    async def execute(self, ctx, *args, **kwargs):  # pragma: no cover - not called
        return {"status": "success"}


def test_register_tools_forwards_tags_to_fastmcp():
    fake_mcp = MagicMock()
    fake_mcp.tool = MagicMock(return_value=lambda fn: fn)

    count = register_tools(fake_mcp, [_FakeTool])

    assert count == 1
    call_args = fake_mcp.tool.call_args
    assert call_args.kwargs["name"] == "itsi_test_tool"
    assert "tags" in call_args.kwargs, "tags must be forwarded to mcp.tool"
    assert call_args.kwargs["tags"] == {"itsi", "test"}
```

- [ ] **Step 2: Run test to verify it fails**

```bash
uv run pytest tests/test_itsi_registration.py::test_register_tools_forwards_tags_to_fastmcp -v
```

Expected: FAIL with `assert "tags" in call_args.kwargs` (tags currently not forwarded).

- [ ] **Step 3: Modify `mcp_itsi/core/registration.py`**

Locate the `register_tools` function. Change the `mcp.tool(...)` call from:

```python
mcp.tool(name=metadata.name, description=metadata.description)(wrapper)
```

to:

```python
mcp.tool(
    name=metadata.name,
    description=metadata.description,
    tags=set(metadata.tags) if metadata.tags else set(),
)(wrapper)
```

- [ ] **Step 4: Run test to verify it passes**

```bash
uv run pytest tests/test_itsi_registration.py -v
```

Expected: PASS.

- [ ] **Step 5: Run full ITSI registration tests to confirm no regressions**

```bash
uv run pytest tests/ -k "itsi or registration" -q
```

Expected: All green.

- [ ] **Step 6: Commit**

```bash
git add mcp_itsi/core/registration.py tests/test_itsi_registration.py
git commit -m "fix(itsi): forward ToolMetadata tags to FastMCP

Without this, the ITSI plugin's tools advertised tags=('itsi', ...) in
their metadata but the FastMCP registration omitted them, so any tag-based
filtering or visibility control downstream had nothing to match on.
"
```

---

## Task 2: Tag core `mcp-for-splunk` tools with `{\"splunk\"}`

Inject a default `{"splunk"}` tag on every host-side tool registered by `ToolLoader.load_tools()`. Per-tool `ToolMetadata.tags` (if any) merges in.

**Files:**
- Modify: `src/core/loader.py` (the `mcp_server.tool(...)` call inside `ToolLoader.load_tools`)
- Test: `tests/test_loader_tags.py` (new)

- [ ] **Step 1: Write the failing test**

Create `tests/test_loader_tags.py`:

```python
"""Verify ToolLoader tags every host tool with {'splunk'}."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from src.core.base import BaseTool, ToolMetadata
from src.core.loader import ToolLoader


class _FakeTool(BaseTool):
    """Minimal host tool used as a fixture."""

    async def execute(self, ctx, *args, **kwargs):  # pragma: no cover - not called
        return {"status": "success"}


def _setup_registry_with(monkeypatch, name: str, extra_tags: list[str] | None):
    metadata = ToolMetadata(
        name=name,
        description="fake",
        category="test",
        tags=extra_tags,
    )

    fake_registry = MagicMock()
    fake_registry.list_tools.return_value = [metadata]
    fake_registry._tools = {name: _FakeTool}
    fake_registry.get_metadata.return_value = metadata

    monkeypatch.setattr("src.core.loader.tool_registry", fake_registry)
    monkeypatch.setattr("src.core.loader.discover_tools", lambda: None)


def test_loader_adds_splunk_tag_to_every_tool(monkeypatch):
    fake_mcp = MagicMock()
    fake_mcp.tool = MagicMock(return_value=lambda fn: fn)

    _setup_registry_with(monkeypatch, "fake_tool", extra_tags=None)

    loader = ToolLoader(fake_mcp)
    loaded = loader.load_tools()

    assert loaded == 1
    kwargs = fake_mcp.tool.call_args.kwargs
    assert "tags" in kwargs
    assert "splunk" in kwargs["tags"]


def test_loader_merges_metadata_tags_with_splunk(monkeypatch):
    fake_mcp = MagicMock()
    fake_mcp.tool = MagicMock(return_value=lambda fn: fn)

    _setup_registry_with(monkeypatch, "fake_tool", extra_tags=["search", "metadata"])

    loader = ToolLoader(fake_mcp)
    loader.load_tools()

    kwargs = fake_mcp.tool.call_args.kwargs
    assert kwargs["tags"] == {"splunk", "search", "metadata"}
```

- [ ] **Step 2: Run test to verify it fails**

```bash
uv run pytest tests/test_loader_tags.py -v
```

Expected: FAIL with `KeyError: 'tags'` (loader never passes tags today).

- [ ] **Step 3: Modify `src/core/loader.py`**

Find the registration line inside `ToolLoader.load_tools` (currently around line 217):

```python
self.mcp_server.tool(name=tool_name)(tool_wrapper)
```

Replace with:

```python
extra_tags = set(getattr(tool_metadata, "tags", None) or [])
all_tags = {"splunk"} | extra_tags
self.mcp_server.tool(name=tool_name, tags=all_tags)(tool_wrapper)
```

- [ ] **Step 4: Run test to verify it passes**

```bash
uv run pytest tests/test_loader_tags.py -v
```

Expected: PASS (both cases).

- [ ] **Step 5: Run modular component tests to ensure no regressions**

```bash
uv run pytest tests/test_factories.py tests/test_plugin_loader.py tests/test_loader_tags.py -q
```

Expected: all pass.

- [ ] **Step 6: Commit**

```bash
git add src/core/loader.py tests/test_loader_tags.py
git commit -m "feat(core): tag every host tool with {'splunk'} on registration

Each tool registered through ToolLoader now carries the 'splunk' toolset
tag (merged with any per-tool metadata tags), so downstream tag-based
filtering can distinguish host tools from plugin tools.
"
```

---

## Task 3: `ToolsetFilterMiddleware`

Add the per-request filter middleware. Lives in `src/core/toolset_filter.py` so the host owns it and any future plugin benefits automatically.

**Files:**
- Create: `src/core/toolset_filter.py`
- Test: `tests/test_toolset_filter.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_toolset_filter.py`:

```python
"""Unit tests for ToolsetFilterMiddleware logic."""

from __future__ import annotations

import os
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.core.toolset_filter import ToolsetFilterMiddleware, _wanted_toolsets


def _tool(name: str, tags: set[str]):
    t = MagicMock()
    t.name = name
    t.tags = set(tags)
    return t


def test_wanted_toolsets_default_all(monkeypatch):
    monkeypatch.delenv("MCP_DEFAULT_TOOLSETS", raising=False)
    known = {"splunk", "itsi"}
    assert _wanted_toolsets(headers=None, known=known) == known


def test_wanted_toolsets_default_env_override(monkeypatch):
    monkeypatch.setenv("MCP_DEFAULT_TOOLSETS", "splunk")
    assert _wanted_toolsets(headers=None, known={"splunk", "itsi"}) == {"splunk"}


def test_wanted_toolsets_header_wins_over_env(monkeypatch):
    monkeypatch.setenv("MCP_DEFAULT_TOOLSETS", "splunk")
    headers = {"x-mcp-toolsets": "itsi"}
    assert _wanted_toolsets(headers=headers, known={"splunk", "itsi"}) == {"itsi"}


def test_wanted_toolsets_drops_unknown(monkeypatch):
    monkeypatch.delenv("MCP_DEFAULT_TOOLSETS", raising=False)
    headers = {"x-mcp-toolsets": "splunk,bogus"}
    assert _wanted_toolsets(headers=headers, known={"splunk", "itsi"}) == {"splunk"}


def test_wanted_toolsets_all_keyword(monkeypatch):
    monkeypatch.delenv("MCP_DEFAULT_TOOLSETS", raising=False)
    headers = {"x-mcp-toolsets": "all"}
    assert _wanted_toolsets(headers=headers, known={"splunk", "itsi"}) == {"splunk", "itsi"}


def test_wanted_toolsets_empty_header_falls_back_to_env(monkeypatch):
    monkeypatch.setenv("MCP_DEFAULT_TOOLSETS", "itsi")
    headers = {"x-mcp-toolsets": ""}
    assert _wanted_toolsets(headers=headers, known={"splunk", "itsi"}) == {"itsi"}


@pytest.mark.asyncio
async def test_on_list_tools_filters_to_wanted(monkeypatch):
    monkeypatch.delenv("MCP_DEFAULT_TOOLSETS", raising=False)
    mw = ToolsetFilterMiddleware(known_toolsets=lambda: {"splunk", "itsi"})

    tools = [
        _tool("oneshot_search", {"splunk"}),
        _tool("itsi_list_entities", {"itsi", "entity"}),
        _tool("internal_health", set()),
    ]

    ctx = MagicMock()
    ctx.http_headers = {"x-mcp-toolsets": "splunk"}

    async def call_next(_ctx):
        return tools

    out = await mw.on_list_tools(ctx, call_next)
    names = {t.name for t in out}

    assert "oneshot_search" in names, "splunk-tagged tool must remain"
    assert "itsi_list_entities" not in names, "itsi-tagged tool must be hidden"
    assert "internal_health" in names, "untagged tool always visible"


@pytest.mark.asyncio
async def test_on_call_tool_blocks_disabled_toolset(monkeypatch):
    monkeypatch.delenv("MCP_DEFAULT_TOOLSETS", raising=False)
    from fastmcp.exceptions import ToolError

    mw = ToolsetFilterMiddleware(known_toolsets=lambda: {"splunk", "itsi"})

    blocked_tool = _tool("itsi_list_entities", {"itsi"})

    ctx = MagicMock()
    ctx.http_headers = {"x-mcp-toolsets": "splunk"}
    ctx.message.name = "itsi_list_entities"
    ctx.fastmcp_context.fastmcp.get_tool = AsyncMock(return_value=blocked_tool)

    async def call_next(_ctx):
        return {"status": "success"}

    with pytest.raises(ToolError):
        await mw.on_call_tool(ctx, call_next)


@pytest.mark.asyncio
async def test_on_call_tool_allows_enabled_toolset(monkeypatch):
    monkeypatch.delenv("MCP_DEFAULT_TOOLSETS", raising=False)
    mw = ToolsetFilterMiddleware(known_toolsets=lambda: {"splunk", "itsi"})

    allowed = _tool("oneshot_search", {"splunk"})

    ctx = MagicMock()
    ctx.http_headers = {"x-mcp-toolsets": "splunk,itsi"}
    ctx.message.name = "oneshot_search"
    ctx.fastmcp_context.fastmcp.get_tool = AsyncMock(return_value=allowed)

    async def call_next(_ctx):
        return {"status": "success"}

    result = await mw.on_call_tool(ctx, call_next)
    assert result == {"status": "success"}


@pytest.mark.asyncio
async def test_install_once_is_idempotent():
    mw_instances_added = []

    class FakeMcp:
        def add_middleware(self, mw):
            mw_instances_added.append(mw)

    fake = FakeMcp()
    ToolsetFilterMiddleware.install_once(fake, known_toolsets=lambda: set())
    ToolsetFilterMiddleware.install_once(fake, known_toolsets=lambda: set())

    assert len(mw_instances_added) == 1
```

- [ ] **Step 2: Run the test — it must fail because the module doesn't exist**

```bash
uv run pytest tests/test_toolset_filter.py -v
```

Expected: collection error / `ModuleNotFoundError: No module named 'src.core.toolset_filter'`.

- [ ] **Step 3: Implement `src/core/toolset_filter.py`**

```python
"""Per-client toolset filtering middleware.

Plugins (and the host itself) tag their tools with a "toolset tag" — by
convention the same name used as the entry-point key under
``mcp_splunk.plugins``. Clients pick which toolsets they want for a given
session by sending the ``X-MCP-Toolsets`` header (comma-separated). When the
header is absent the middleware falls back to the ``MCP_DEFAULT_TOOLSETS``
environment variable (``all`` by default).

Untagged components — components whose ``tags`` set has no overlap with the
known toolset universe — are always visible. This protects framework-level
items (health probes, internal helpers) from accidental hiding.
"""

from __future__ import annotations

import logging
import os
from collections.abc import Callable, Iterable

from fastmcp.exceptions import ToolError
from fastmcp.server.middleware import Middleware, MiddlewareContext

logger = logging.getLogger(__name__)

HEADER_NAME = "x-mcp-toolsets"
DEFAULT_ENV_VAR = "MCP_DEFAULT_TOOLSETS"
ALL_KEYWORD = "all"


def _wanted_toolsets(headers: dict | None, known: set[str]) -> set[str]:
    """Return the set of toolset tags the current request wants to see."""
    raw: str | None = None
    if headers:
        raw = headers.get(HEADER_NAME) or headers.get(HEADER_NAME.upper())
    if not raw or not raw.strip():
        raw = os.getenv(DEFAULT_ENV_VAR, ALL_KEYWORD)

    raw = raw.strip().lower()
    if raw == ALL_KEYWORD:
        return set(known)

    requested = {p.strip() for p in raw.split(",") if p.strip()}
    return requested & known


class ToolsetFilterMiddleware(Middleware):
    """Filter tools, resources, and prompts by client-requested toolsets.

    Args:
        known_toolsets: zero-arg callable returning the current set of known
            toolset tags. Called per request so newly-loaded plugins are
            picked up without restarting.
    """

    def __init__(self, known_toolsets: Callable[[], Iterable[str]]):
        self._known_toolsets_fn = known_toolsets

    def _known(self) -> set[str]:
        return set(self._known_toolsets_fn())

    def _is_toolset_member(self, tags: Iterable[str], known: set[str]) -> bool:
        return bool(set(tags) & known)

    def _wanted(self, ctx: MiddlewareContext, known: set[str]) -> set[str]:
        headers = getattr(ctx, "http_headers", None)
        return _wanted_toolsets(headers, known)

    async def on_list_tools(self, context: MiddlewareContext, call_next):
        tools = await call_next(context)
        known = self._known()
        wanted = self._wanted(context, known)
        return [
            t
            for t in tools
            if not self._is_toolset_member(t.tags, known) or (set(t.tags) & wanted)
        ]

    async def on_call_tool(self, context: MiddlewareContext, call_next):
        known = self._known()
        wanted = self._wanted(context, known)
        tool = await context.fastmcp_context.fastmcp.get_tool(context.message.name)
        if self._is_toolset_member(tool.tags, known) and not (set(tool.tags) & wanted):
            raise ToolError(
                f"Tool '{context.message.name}' is not in an enabled toolset for this client"
            )
        return await call_next(context)

    async def on_list_resources(self, context: MiddlewareContext, call_next):
        resources = await call_next(context)
        known = self._known()
        wanted = self._wanted(context, known)
        return [
            r
            for r in resources
            if not self._is_toolset_member(getattr(r, "tags", set()), known)
            or (set(getattr(r, "tags", set())) & wanted)
        ]

    async def on_list_prompts(self, context: MiddlewareContext, call_next):
        prompts = await call_next(context)
        known = self._known()
        wanted = self._wanted(context, known)
        return [
            p
            for p in prompts
            if not self._is_toolset_member(getattr(p, "tags", set()), known)
            or (set(getattr(p, "tags", set())) & wanted)
        ]

    @classmethod
    def install_once(cls, mcp, known_toolsets: Callable[[], Iterable[str]]) -> bool:
        """Install the middleware on ``mcp`` exactly once.

        Returns True the first time, False on subsequent calls (idempotent).
        """
        if getattr(mcp, "_toolset_filter_installed", False):
            return False
        mcp.add_middleware(cls(known_toolsets=known_toolsets))
        mcp._toolset_filter_installed = True
        logger.info("ToolsetFilterMiddleware installed on %s", getattr(mcp, "name", mcp))
        return True
```

- [ ] **Step 4: Run the test to verify all pass**

```bash
uv run pytest tests/test_toolset_filter.py -v
```

Expected: PASS for all 9 tests.

- [ ] **Step 5: Commit**

```bash
git add src/core/toolset_filter.py tests/test_toolset_filter.py
git commit -m "feat(core): add ToolsetFilterMiddleware for per-client toolset selection

Adds a FastMCP middleware that filters tools/resources/prompts on
list_* and call_tool based on the X-MCP-Toolsets header (with
MCP_DEFAULT_TOOLSETS env fallback). Untagged components are always
visible so framework internals stay reachable.
"
```

---

## Task 4: Track loaded plugins on the FastMCP instance

`load_plugins()` currently logs each loaded plugin but keeps no record. We need a structured registry on the server instance so the middleware (Task 5) and `/health` (Task 6) can query it.

**Files:**
- Modify: `src/server.py` (`load_plugins` function)
- Test: `tests/test_plugin_loader.py` (extend)

- [ ] **Step 1: Write the failing test**

Append to `tests/test_plugin_loader.py`:

```python
def test_load_plugins_records_each_loaded_plugin_on_server(monkeypatch):
    monkeypatch.delenv("MCP_DISABLE_PLUGINS", raising=False)
    monkeypatch.delenv("MCP_PLUGIN_GROUP", raising=False)

    def setup_fn(*, mcp=None, root_app=None):
        return None

    class FakeEntryPoint:
        name = "itsi"

        @staticmethod
        def load():
            return setup_fn

    class FakeEntryPoints:
        def select(self, group):
            if group == "mcp_splunk.plugins":
                return [FakeEntryPoint()]
            return []

    server = importlib.import_module("src.server")
    monkeypatch.setattr(server, "entry_points", lambda: FakeEntryPoints(), raising=True)

    if hasattr(server.mcp, "_loaded_plugins"):
        delattr(server.mcp, "_loaded_plugins")

    server.load_plugins(server.mcp)

    assert hasattr(server.mcp, "_loaded_plugins")
    names = [p["name"] for p in server.mcp._loaded_plugins]
    assert "itsi" in names
```

- [ ] **Step 2: Run the new test — must fail**

```bash
uv run pytest tests/test_plugin_loader.py::test_load_plugins_records_each_loaded_plugin_on_server -v
```

Expected: FAIL because `_loaded_plugins` is never set today.

- [ ] **Step 3: Modify `src/server.py::load_plugins`**

Inside `load_plugins`, change the success branch of the per-entry-point loop to track the plugin. Find:

```python
for ep in eps:
    try:
        setup = ep.load()
        setup(mcp=mcp, root_app=root_app)
        loaded += 1
        logger.info("Loaded plugin: %s", getattr(ep, "name", str(ep)))
    except Exception as e:
        logger.warning("Plugin %s failed during setup: %s", getattr(ep, "name", str(ep)), e)
```

Replace with:

```python
if not hasattr(mcp, "_loaded_plugins"):
    mcp._loaded_plugins = []  # list of {"name": str}
existing_names = {p["name"] for p in mcp._loaded_plugins}

for ep in eps:
    try:
        setup = ep.load()
        setup(mcp=mcp, root_app=root_app)
        loaded += 1
        ep_name = getattr(ep, "name", str(ep))
        if ep_name not in existing_names:
            mcp._loaded_plugins.append({"name": ep_name})
            existing_names.add(ep_name)
        logger.info("Loaded plugin: %s", ep_name)
    except Exception as e:
        logger.warning("Plugin %s failed during setup: %s", getattr(ep, "name", str(ep)), e)
```

- [ ] **Step 4: Run the new test — must pass**

```bash
uv run pytest tests/test_plugin_loader.py -v
```

Expected: all 3 plugin-loader tests pass.

- [ ] **Step 5: Commit**

```bash
git add src/server.py tests/test_plugin_loader.py
git commit -m "feat(server): record loaded plugins on FastMCP instance

load_plugins() now appends {'name': <entry-point name>} to
mcp._loaded_plugins for each successful setup. The middleware and
health endpoint will use this to know the toolset universe.
"
```

---

## Task 5: Wire `ToolsetFilterMiddleware` into the host server

After `load_plugins()` runs, install the middleware. The `known_toolsets` callable returns `{"splunk"} ∪ {p["name"] for p in mcp._loaded_plugins}`, computed lazily so plugins loaded later are picked up.

**Files:**
- Modify: `src/server.py` (after the `load_plugins` call site at module bottom)
- Test: `tests/test_toolset_integration.py` (new — full in-memory client test)

- [ ] **Step 1: Write the failing integration test**

Create `tests/test_toolset_integration.py`:

```python
"""End-to-end test: header-driven toolset filtering through a FastMCP client."""

from __future__ import annotations

from typing import Any

import pytest
from fastmcp import Client, FastMCP

from src.core.toolset_filter import ToolsetFilterMiddleware


@pytest.fixture
def host() -> FastMCP:
    """Build a host server with two toolsets: splunk and itsi."""
    mcp = FastMCP(name="TestHost")

    @mcp.tool(name="oneshot_search", tags={"splunk"})
    async def oneshot_search(query: str) -> dict:
        return {"status": "success", "query": query, "from": "splunk"}

    @mcp.tool(name="itsi_list_entities", tags={"itsi"})
    async def itsi_list_entities() -> dict:
        return {"status": "success", "from": "itsi"}

    @mcp.tool(name="internal_health")
    async def internal_health() -> dict:
        return {"status": "ok", "from": "internal"}

    ToolsetFilterMiddleware.install_once(mcp, known_toolsets=lambda: {"splunk", "itsi"})
    return mcp


@pytest.mark.asyncio
async def test_header_splunk_only_hides_itsi(host: FastMCP):
    async with Client(host, headers={"X-MCP-Toolsets": "splunk"}) as client:
        names = {t.name for t in await client.list_tools()}
        assert "oneshot_search" in names
        assert "internal_health" in names
        assert "itsi_list_entities" not in names


@pytest.mark.asyncio
async def test_header_itsi_only_hides_splunk(host: FastMCP):
    async with Client(host, headers={"X-MCP-Toolsets": "itsi"}) as client:
        names = {t.name for t in await client.list_tools()}
        assert "itsi_list_entities" in names
        assert "internal_health" in names
        assert "oneshot_search" not in names


@pytest.mark.asyncio
async def test_header_both_shows_both(host: FastMCP):
    async with Client(host, headers={"X-MCP-Toolsets": "splunk,itsi"}) as client:
        names = {t.name for t in await client.list_tools()}
        assert {"oneshot_search", "itsi_list_entities", "internal_health"}.issubset(names)


@pytest.mark.asyncio
async def test_no_header_default_all(monkeypatch, host: FastMCP):
    monkeypatch.delenv("MCP_DEFAULT_TOOLSETS", raising=False)
    async with Client(host) as client:
        names = {t.name for t in await client.list_tools()}
        assert {"oneshot_search", "itsi_list_entities", "internal_health"}.issubset(names)


@pytest.mark.asyncio
async def test_no_header_with_env_default(monkeypatch, host: FastMCP):
    monkeypatch.setenv("MCP_DEFAULT_TOOLSETS", "splunk")
    async with Client(host) as client:
        names = {t.name for t in await client.list_tools()}
        assert "oneshot_search" in names
        assert "itsi_list_entities" not in names


@pytest.mark.asyncio
async def test_call_blocked_tool_raises(host: FastMCP):
    from fastmcp.exceptions import ToolError

    async with Client(host, headers={"X-MCP-Toolsets": "splunk"}) as client:
        with pytest.raises(Exception):  # FastMCP wraps ToolError
            await client.call_tool("itsi_list_entities", {})
```

- [ ] **Step 2: Run the test — must fail**

```bash
uv run pytest tests/test_toolset_integration.py -v
```

Expected: tests pass for the explicit-fixture case (since the fixture installs the middleware itself). Use this file primarily as documentation of expected behavior; the *real* failure mode is that `src/server.py` doesn't auto-install the middleware. Add a separate test to cover the real server.

Append to the same file:

```python
@pytest.mark.asyncio
async def test_real_server_installs_toolset_filter(monkeypatch):
    """The shipping src.server.mcp must have the middleware installed."""
    import importlib

    monkeypatch.setenv("MCP_DISABLE_PLUGINS", "true")
    server = importlib.reload(importlib.import_module("src.server"))

    server.install_toolset_filter(server.mcp)

    assert getattr(server.mcp, "_toolset_filter_installed", False) is True
```

Run again:

```bash
uv run pytest tests/test_toolset_integration.py::test_real_server_installs_toolset_filter -v
```

Expected: FAIL with `AttributeError: module 'src.server' has no attribute 'install_toolset_filter'`.

- [ ] **Step 3: Add `install_toolset_filter` in `src/server.py`**

After the `load_plugins` definition, add:

```python
def install_toolset_filter(mcp: FastMCP) -> bool:
    """Install ToolsetFilterMiddleware with a dynamic known-toolsets callable.

    Known toolsets are 'splunk' (always present) plus every plugin name
    recorded in ``mcp._loaded_plugins``. The lambda is evaluated per request
    so plugins loaded after install still take effect.
    """
    from src.core.toolset_filter import ToolsetFilterMiddleware

    def _known() -> set[str]:
        plugin_names = {p["name"] for p in getattr(mcp, "_loaded_plugins", [])}
        return {"splunk"} | plugin_names

    return ToolsetFilterMiddleware.install_once(mcp, known_toolsets=_known)
```

Then locate the call site near the bottom of `src/server.py` where `load_plugins(mcp, root_app=...)` is invoked. Add a call to `install_toolset_filter(mcp)` immediately after it. Search for `load_plugins(mcp` and add the install call adjacent. There may be two call sites (MCP stage and HTTP stage); call `install_toolset_filter` after each because it's idempotent.

- [ ] **Step 4: Run the integration tests**

```bash
uv run pytest tests/test_toolset_integration.py -v
```

Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add src/server.py tests/test_toolset_integration.py
git commit -m "feat(server): install ToolsetFilterMiddleware after plugin load

Wires the new middleware into the host server with a dynamic
known-toolsets callable that combines 'splunk' with every loaded
plugin name. Idempotent install_once means the MCP stage and HTTP
stage of plugin loading both call it without harm.
"
```

---

## Task 6: Surface `loaded_plugins` and `available_toolsets` in `/health`

**Files:**
- Modify: `src/routes/health.py` (the JSON returned by `health_api`)
- Test: extend a new health-API test (`tests/test_health_routes.py`, new)

- [ ] **Step 1: Write the failing test**

Create `tests/test_health_routes.py`:

```python
"""Verify /health JSON exposes loaded plugins and toolsets."""

from __future__ import annotations

import json
from unittest.mock import MagicMock

import pytest
from starlette.testclient import TestClient

from fastmcp import FastMCP

from src.routes.health import setup_health_routes


def test_health_api_includes_loaded_plugins_and_toolsets():
    mcp = FastMCP(name="TestHealth")
    mcp._loaded_plugins = [{"name": "itsi"}, {"name": "auth"}]
    setup_health_routes(mcp)

    app = mcp.http_app()
    client = TestClient(app)
    resp = client.get("/health")

    assert resp.status_code == 200
    body = resp.json()
    assert body.get("loaded_plugins") == [{"name": "itsi"}, {"name": "auth"}]
    assert set(body.get("available_toolsets", [])) == {"splunk", "itsi", "auth"}
```

- [ ] **Step 2: Run the test — must fail**

```bash
uv run pytest tests/test_health_routes.py -v
```

Expected: FAIL because `loaded_plugins`/`available_toolsets` aren't in the JSON.

- [ ] **Step 3: Modify `src/routes/health.py`**

Inside `health_api` (the JSON endpoint), before the `return JSONResponse(...)`, compute the values:

```python
loaded_plugins = list(getattr(mcp, "_loaded_plugins", []))
available_toolsets = sorted({"splunk"} | {p["name"] for p in loaded_plugins})
```

Then add to the JSONResponse body:

```python
return JSONResponse(
    {
        "status": "healthy",
        "server": server_info_data,
        "splunk_connection": splunk_status,
        "splunk_info": splunk_info,
        "loaded_plugins": loaded_plugins,
        "available_toolsets": available_toolsets,
        "timestamp": time.time(),
    }
)
```

- [ ] **Step 4: Run the test — must pass**

```bash
uv run pytest tests/test_health_routes.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/routes/health.py tests/test_health_routes.py
git commit -m "feat(health): expose loaded_plugins and available_toolsets in /health

Operators can now see at a glance which plugins are active and which
toolset tag values clients can request via X-MCP-Toolsets.
"
```

---

## Task 7: Documentation update

Document the toolset filter contract for plugin authors and operators.

**Files:**
- Modify: `docs/guides/plugins.md`

- [ ] **Step 1: Append a new section to `docs/guides/plugins.md`**

After the existing example, add:

````markdown
## Toolset filtering and the `X-MCP-Toolsets` header

Once installed, every plugin's tools are filterable per-client via the
`X-MCP-Toolsets` HTTP header. The contract is intentionally minimal:

1. Tag every tool with your plugin's entry-point name.

   ```python
   @mcp.tool(name="my_tool", tags={"my_plugin"})
   async def my_tool(...): ...
   ```

   When using `mcp_itsi`-style class-based tools, set
   `tags=("itsi", ...)` in the `ToolMetadata` and let
   `register_tools()` forward it to FastMCP.

2. Match your entry-point name to the tag.

   ```toml
   [project.entry-points."mcp_splunk.plugins"]
   my_plugin = "my_plugin.plugin:setup"
   ```

3. Clients pick toolsets at runtime:

   ```http
   X-MCP-Toolsets: splunk,itsi
   ```

   Special value `all` enables every known toolset. Unknown toolsets
   in the header are silently dropped.

4. Operators set the default for header-less clients:

   ```bash
   export MCP_DEFAULT_TOOLSETS=splunk      # OSS-only deployment
   export MCP_DEFAULT_TOOLSETS=splunk,itsi # both
   export MCP_DEFAULT_TOOLSETS=all         # default
   ```

5. Untagged components are always visible — health probes and other
   framework internals are not affected.

The list of currently-known toolsets is exposed at `/health`:

```json
{
  "available_toolsets": ["itsi", "splunk"],
  "loaded_plugins": [{"name": "itsi"}]
}
```
````

- [ ] **Step 2: Verify the markdown is well-formed**

```bash
uv run python -c "import pathlib; print(len(pathlib.Path('docs/guides/plugins.md').read_text()))"
```

Expected: prints a positive integer (file readable).

- [ ] **Step 3: Commit**

```bash
git add docs/guides/plugins.md
git commit -m "docs(plugins): document X-MCP-Toolsets header and tagging contract"
```

---

## Final verification

- [ ] Run the full unit test suite (excluding integration/slow tests):

```bash
uv run pytest tests/ -m "not integration" -m "not slow" -q
```

Expected: all pass.

- [ ] Optional smoke test of the running server:

```bash
MCP_DISABLE_PLUGINS=true uv run mcp-server --help
```

Expected: clean exit, no traceback.

- [ ] Update the spec's "Open questions" section to note that the design has been fully implemented for this iteration.

---

## Self-review checklist (run before handing off)

1. **Spec coverage:**
   - Section 7 (tags & naming) → Tasks 1, 2 ✓
   - Section 8 (middleware) → Task 3 ✓
   - Section 9 (Splunk connection sharing) → already implemented upstream
   - Section 11 (host changes) → Tasks 2, 4, 5, 6 ✓
   - Section 12 (configuration) → Task 7 (docs) ✓
   - Section 14 (testing) → Tasks 1, 2, 3, 5, 6 ✓

2. **Placeholder scan:** None.

3. **Type/name consistency:**
   - `_loaded_plugins` (list of dicts with `name` key) used in Tasks 4, 5, 6 — consistent.
   - `ToolsetFilterMiddleware.install_once(mcp, known_toolsets=...)` signature stable across Tasks 3 and 5.
   - `_wanted_toolsets` is module-level so the test imports it directly in Task 3.
