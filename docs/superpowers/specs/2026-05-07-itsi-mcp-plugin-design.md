# Design: `itsi-mcp` as a plugin to `mcp-for-splunk`

**Status:** Re-baselined against `origin/main@12edca7` — see "Re-baseline" section
**Author:** Cursor agent (with Young)
**Date:** 2026-05-07
**Related code:**

- `src/server.py` — existing entry-point plugin loader (`load_plugins`, `PLUGIN_GROUP = "mcp_splunk.plugins"`)
- `docs/guides/plugins.md` — current plugin authoring guide
- `src/core/base.py` — `BaseTool`, `SplunkContext`, `get_splunk_service`
- `mcp_itsi/` — **already-shipped ITSI plugin source (in-repo)**
- `packaging/mcp-itsi-server/` — separate PyPI build root for the plugin
- `mcp_itsi/plugin.py` — entry-point target `setup(mcp, root_app=None)`
- `mcp_itsi/core/registration.py` — `register_tools/resources/prompts` glue

## 0. Re-baseline (2026-05-07)

When this design was first written we assumed `itsi-mcp` was greenfield. After
syncing to `origin/main@12edca7` we discovered the plugin and its packaging
already exist upstream:

| Original design item | Upstream status |
|---|---|
| Entry-point plugin loader | Already in `src/server.py::load_plugins` |
| `mcp-itsi-server` PyPI package | Shipped via `packaging/mcp-itsi-server/pyproject.toml` (PR #127) |
| `mcp_itsi/` source | 55+ files; tools, prompts, resources, knowledge base (PR #121) |
| ITSI tool names prefixed `itsi_*` | Done via `ToolMetadata.name="itsi_..."` |
| ITSI tool tags `("itsi", ...)` in metadata | **Defined but not surfaced** — `register_tools()` does not forward `tags=` to `mcp.tool()` |
| Core `mcp-for-splunk` tools tagged `{"splunk"}` | Missing |
| `ToolsetFilterMiddleware` (`X-MCP-Toolsets` header) | Missing |
| `_loaded_plugins` registry + `/health` surface | Missing |
| Docs for `X-MCP-Toolsets` and tagging contract | Missing |

Sections 5 (repo layout), 6 (plugin entry-point), 10 (standalone mode) are
now **descriptive** (already implemented upstream). Sections 8, 11, 13, 14
are **prescriptive** (still to implement). Section 7 is half-and-half: ITSI
tag metadata exists; we still must (a) forward those tags to FastMCP, and
(b) tag core Splunk tools.

The remaining-work plan lives at
`docs/superpowers/plans/2026-05-07-itsi-mcp-plugin-implementation.md`.

### Convention: entry-point name = toolset tag

Locked in by upstream and adopted by this design: the entry-point name in
`[project.entry-points."mcp_splunk.plugins"]` is also the canonical toolset
tag. ITSI ships under `itsi = mcp_itsi.plugin:setup` and tags its tools
with `"itsi"`. The host registers `"splunk"` for its own tools by default.

This convention removes the need for plugins to opt in to filtering through
a custom API — they just have to tag tools with their entry-point name.

## 1. Goal

Allow a single deployed MCP server to expose either the `mcp-for-splunk` core
toolset, the `itsi-mcp` toolset, or both, with the choice made by each
connecting client at runtime via an HTTP header. Ship `itsi-mcp` as an
independently installable Python package that plugs into the existing host.

## 2. Non-goals

- Multi-tenant Splunk authentication isolation (clients still authenticate
  against Splunk through the host's existing per-request `client_config`
  mechanism).
- Stdio-transport runtime selection. This design targets HTTP/SSE transports.
  For stdio, operators control toolsets at startup via env vars
  (`MCP_DISABLE_PLUGINS`, `MCP_DEFAULT_TOOLSETS`).
- Per-tool ACLs beyond toolset granularity. Sub-toolset filtering (e.g.
  `itsi:services`) is left for a future iteration.
- Migration of existing core tools' tags. We will tag core tools `{"splunk"}`
  in the loader as a one-time, low-risk migration (Section 11).

## 3. Decisions (locked from brainstorm)

| # | Decision | Value |
|---|---|---|
| 1 | itsi-mcp state | Greenfield — new package |
| 2 | Selection mechanism | HTTP header `X-MCP-Toolsets` |
| 3 | Tool naming | Mount prefix `itsi_` |
| 4 | Default when header absent | Configurable via `MCP_DEFAULT_TOOLSETS` (fallback `all`) |
| 5 | Splunk connection | Reuse parent's `SplunkContext` |
| 6 | Composition mechanism | `parent_mcp.mount(itsi_mcp, prefix="itsi")` (FastMCP 3 live composition) |
| 7 | Plugin distribution | Python entry-point `mcp_splunk.plugins` |

## 4. High-level architecture

```text
                  ┌────────────────────────────────────────┐
                  │   mcp-for-splunk (FastMCP "host")      │
                  │   /mcp HTTP endpoint                   │
                  │                                        │
   X-MCP-         │   ┌──────────────────────────────┐     │
   Toolsets ────► │   │ ToolsetFilterMiddleware      │     │
   header         │   │  - reads header / env default│     │
                  │   │  - filters on_list_*         │     │
                  │   │  - guards on_call_tool       │     │
                  │   └──────────────────────────────┘     │
                  │                                        │
                  │   ┌──────────────┐  ┌─────────────┐    │
                  │   │ splunk-core  │  │  itsi-mcp   │    │
                  │   │  tools       │  │  (mounted   │    │
                  │   │ tag={splunk} │  │  prefix=itsi│    │
                  │   └──────────────┘  │  tag={itsi})│    │
                  │                     └─────────────┘    │
                  │                                        │
                  │   shared SplunkContext (lifespan)      │
                  └────────────────────────────────────────┘
```

One process. One URL. Per-client toolset selection at runtime. Plugin can be
omitted at deploy time by leaving the package uninstalled or setting
`MCP_DISABLE_PLUGINS=true`.

## 5. Repository / package layout

`itsi-mcp` is a separate sibling repo (or sibling folder under
`~/code/deslicer/itsi-mcp`) that depends on `mcp-server-for-splunk`.

```text
itsi-mcp/
├── pyproject.toml
├── README.md
├── src/itsi_mcp/
│   ├── __init__.py
│   ├── plugin.py              # setup(mcp, root_app) — entry-point target
│   ├── server.py              # build_itsi_server() — single source of truth
│   ├── cli.py                 # standalone runner (`itsi-mcp` console script)
│   ├── middleware.py          # ToolsetFilterMiddleware (lives here so the
│   │                          # plugin owns it; host stays toolset-agnostic)
│   ├── tools/
│   │   ├── __init__.py
│   │   ├── services/
│   │   │   ├── health.py      # subclasses BaseTool from mcp-for-splunk
│   │   │   └── ...
│   │   ├── kpis/
│   │   ├── episodes/          # NEAP / episode review
│   │   └── ...
│   └── resources/
└── tests/
    ├── test_mounted_filtering.py
    ├── test_standalone_mode.py
    └── test_plugin_setup.py
```

`pyproject.toml` essentials:

```toml
[project]
name = "itsi-mcp"
version = "0.1.0"
requires-python = ">=3.10"
dependencies = [
  "mcp-server-for-splunk>=0.5.2",
  "fastmcp>=3.0.0,<4",
]

[project.scripts]
itsi-mcp = "itsi_mcp.cli:main"

[project.entry-points."mcp_splunk.plugins"]
itsi = "itsi_mcp.plugin:setup"
```

## 6. Plugin entry-point — `setup(mcp, root_app)`

```python
# src/itsi_mcp/plugin.py
from fastmcp import FastMCP

from itsi_mcp.middleware import ToolsetFilterMiddleware
from itsi_mcp.server import build_itsi_server

DEFAULT_PREFIX_ENV = "MCP_ITSI_PREFIX"
DEFAULT_PREFIX = "itsi"


def setup(mcp: FastMCP, root_app=None) -> None:
    """Entry-point target invoked by mcp-for-splunk's load_plugins()."""
    import os

    prefix = os.getenv(DEFAULT_PREFIX_ENV, DEFAULT_PREFIX).strip() or DEFAULT_PREFIX
    itsi = build_itsi_server()
    mcp.mount(itsi, prefix=prefix)
    ToolsetFilterMiddleware.install_once(mcp)
```

`build_itsi_server()` returns a fully-formed `FastMCP("ITSI")` whose tools all
carry `tags={"itsi"}`. The same builder powers both mounted and standalone
modes — guaranteed identical tool code.

## 7. Tool tagging and naming

| | mcp-for-splunk core | itsi-mcp |
|---|---|---|
| Tag | `{"splunk"}` | `{"itsi"}` |
| Final name on host | unchanged (e.g. `oneshot_search`) | prefixed (e.g. `itsi_get_service_health`) |

Prefixing comes from `mount(prefix="itsi")` and is automatic.

Tool source files in itsi-mcp register tools with explicit tags:

```python
@itsi_mcp.tool(tags={"itsi"})
async def get_service_health(ctx: Context, service: str) -> dict:
    ...
```

## 8. ToolsetFilterMiddleware

Single middleware enforces per-client toolset selection on every request.
Lives inside `itsi-mcp` so the host package stays toolset-agnostic; the
middleware is installed exactly once via `install_once()` regardless of how
many tagged plugins are loaded.

```python
# src/itsi_mcp/middleware.py
import os

from fastmcp.exceptions import ToolError
from fastmcp.server.middleware import Middleware, MiddlewareContext

KNOWN_TAGS: frozenset[str] = frozenset({"splunk", "itsi"})


def _wanted(headers: dict | None) -> set[str]:
    raw = None
    if headers:
        # FastMCP may lower-case headers; check both forms defensively
        raw = headers.get("x-mcp-toolsets") or headers.get("X-MCP-Toolsets")
    if not raw:
        raw = os.getenv("MCP_DEFAULT_TOOLSETS", "all")
    raw = raw.strip().lower()
    if raw == "all":
        return set(KNOWN_TAGS)
    return {p.strip() for p in raw.split(",") if p.strip()} & KNOWN_TAGS


def _is_toolset_member(tags: set[str]) -> bool:
    return bool(tags & KNOWN_TAGS)


class ToolsetFilterMiddleware(Middleware):
    """Filter tools/resources/prompts by client-requested toolsets.

    Untagged components (no tag in KNOWN_TAGS) are always exposed — this keeps
    framework-internal items (e.g. health probes) visible regardless of
    client preference.
    """

    async def on_list_tools(self, context: MiddlewareContext, call_next):
        tools = await call_next(context)
        wanted = _wanted(getattr(context, "http_headers", None))
        return [t for t in tools if not _is_toolset_member(t.tags) or (t.tags & wanted)]

    async def on_call_tool(self, context: MiddlewareContext, call_next):
        wanted = _wanted(getattr(context, "http_headers", None))
        tool = await context.fastmcp_context.fastmcp.get_tool(context.message.name)
        if _is_toolset_member(tool.tags) and not (tool.tags & wanted):
            raise ToolError(f"Tool '{context.message.name}' is not enabled for this client")
        return await call_next(context)

    async def on_list_resources(self, context: MiddlewareContext, call_next):
        resources = await call_next(context)
        wanted = _wanted(getattr(context, "http_headers", None))
        return [r for r in resources if not _is_toolset_member(r.tags) or (r.tags & wanted)]

    async def on_list_prompts(self, context: MiddlewareContext, call_next):
        prompts = await call_next(context)
        wanted = _wanted(getattr(context, "http_headers", None))
        return [p for p in prompts if not _is_toolset_member(p.tags) or (p.tags & wanted)]

    @classmethod
    def install_once(cls, mcp) -> None:
        if not getattr(mcp, "_toolset_filter_installed", False):
            mcp.add_middleware(cls())
            mcp._toolset_filter_installed = True
```

### Filter semantics

- Untagged components → always visible (avoids accidentally hiding host
  internals such as `get_health` if a future plugin lacks tags).
- Tagged components → visible only if `tags ∩ wanted` is non-empty.
- Unknown tag values in the header are silently dropped (filtered through
  `KNOWN_TAGS`); empty intersection means "no toolset enabled".

## 9. Splunk connection sharing

ITSI tools subclass `BaseTool` from `mcp-server-for-splunk` and call
`await self.get_splunk_service(ctx)`. The existing fallback chain works
unchanged when mounted:

1. `ctx.request_context.lifespan_context` → parent's `SplunkContext` (this is
   what runs because FastMCP `mount()` uses the parent's lifespan).
2. `get_server()._splunk_context` → fallback for module-init paths.
3. Per-request `client_config` from headers → already implemented in
   `BaseTool.get_client_config_from_context`.

No code change required in mcp-for-splunk to support this. ITSI tools get the
same Splunk credentials the host resolved for the request.

## 10. Standalone mode (for ITSI development/testing)

```python
# src/itsi_mcp/cli.py
def main() -> None:
    """Run itsi-mcp as a standalone MCP server (dev/testing only)."""
    import os

    from src.server import splunk_lifespan  # reuse the host's lifespan

    from itsi_mcp.middleware import ToolsetFilterMiddleware
    from itsi_mcp.server import build_itsi_server

    itsi = build_itsi_server(lifespan=splunk_lifespan)
    ToolsetFilterMiddleware.install_once(itsi)
    itsi.run_http(
        host=os.getenv("ITSI_MCP_HOST", "0.0.0.0"),
        port=int(os.getenv("ITSI_MCP_PORT", "8001")),
    )
```

Standalone mode reuses the host's `splunk_lifespan` — same connection logic,
no duplication. Tag filtering still applies in standalone mode for parity.

## 11. Required changes in `mcp-for-splunk`

Small, additive changes only. No behavior change when no plugins are loaded.

1. **Tag core tools as `{"splunk"}`.** In `src/core/loader.py` — the tool
   loader already has registration metadata. Inject `tags={"splunk"}` (merged
   with any existing tags) when calling `mcp.tool(...)`. One-place change.
2. **Track loaded plugin names.** In `src/server.py::load_plugins`, record
   `(name, version, prefix)` in a list attached to the FastMCP instance
   (`mcp._loaded_plugins`).
3. **Health endpoint surface.** Extend `setup_health_routes` to include
   `loaded_plugins` and `available_toolsets` (derived from
   `mcp._loaded_plugins` plus the static `"splunk"`).
4. **Docs update.** Update `docs/guides/plugins.md` to point readers to this
   design and the future itsi-mcp README.

No changes to the existing entry-point loading mechanism, no changes to
`BaseTool`, no changes to lifespan logic.

## 12. Configuration

| Variable | Default | Effect |
|---|---|---|
| `MCP_DISABLE_PLUGINS` | `false` | Skip all plugin loading. Host runs splunk-only. |
| `MCP_PLUGIN_GROUP` | `mcp_splunk.plugins` | Override entry-point group (existing). |
| `MCP_DEFAULT_TOOLSETS` | `all` | Default toolsets when header missing. Values: `all`, `splunk`, `itsi`, or comma-separated combination. |
| `MCP_ITSI_PREFIX` | `itsi` | Override mount prefix (escape hatch for collisions). |

Per-client header: `X-MCP-Toolsets: splunk,itsi`.

## 13. Failure modes and edge cases

| Scenario | Behavior |
|---|---|
| Header absent | Use `MCP_DEFAULT_TOOLSETS` (default `all`). |
| Header value `all` | All known toolsets enabled. |
| Header value empty (`X-MCP-Toolsets:`) | Treated as absent — fall back to default. |
| Header value contains unknown tag (`splunk,foo`) | Unknown tags ignored; valid tags applied. If intersection is empty → tagged tools hidden. |
| `itsi-mcp` not installed | `load_plugins` finds no entry point → host runs splunk-only; no error. |
| `itsi-mcp` `setup()` raises | Existing loader logs a warning and continues; host still serves splunk tools. |
| Two plugins both call `install_once` | Idempotent flag prevents duplicate middleware. |
| Tool name collision after prefix | Mount prefix makes this near-impossible; if it ever happens, the operator can override `MCP_ITSI_PREFIX`. |
| Standalone itsi-mcp without Splunk env | `splunk_lifespan` enters degraded mode (existing behavior); tools surface clear error from `BaseTool.check_splunk_available`. |

## 14. Testing strategy

### Unit tests (`itsi-mcp/tests/`)

- `test_plugin_setup.py` — load fake `mcp_splunk.plugins` entry point, assert
  `mcp.mount` called with prefix `itsi`, middleware installed exactly once
  even if `setup` runs twice.
- Per-tool tests with mocked `SplunkContext`.

### Integration tests (FastMCP in-memory client)

Build a host `FastMCP`, mount a fake itsi-mcp, install
`ToolsetFilterMiddleware`, then via `Client(host_mcp)`:

| Header | Expected `list_tools` | Expected `call_tool` |
|---|---|---|
| `splunk` | core tools only | `itsi_*` → `ToolError` |
| `itsi` | `itsi_*` only | core tools → `ToolError` |
| `splunk,itsi` | both | both succeed |
| _absent_ + `MCP_DEFAULT_TOOLSETS=all` | both | both succeed |
| _absent_ + `MCP_DEFAULT_TOOLSETS=splunk` | core only | `itsi_*` → `ToolError` |
| `unknown` | none of the toolset-tagged components | all toolset-tagged → `ToolError` |

### Existing tests

Extend `tests/test_plugin_loader.py` to cover the `mount`-on-setup pattern
using a fake plugin module that calls `mcp.mount`.

## 15. Out of scope (future work)

- Sub-toolset tags (`itsi:services`, `itsi:kpis`) and hierarchical filtering.
- Per-tool RBAC tied to OAuth scopes (FastMCP `restrict_tag` integration).
- Resource URI namespacing audit (mount prefixes resource URIs too — verify
  no existing client depends on un-prefixed ITSI resource URIs once tools
  exist).
- Stdio transport runtime selection.

## 16. Open questions

None blocking. Items flagged at the end of brainstorming were resolved by
sections 5, 7, 8, and 11 respectively.
