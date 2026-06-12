# FastMCP Modernization Analysis — Splunk & ITSI MCP Servers

**Date:** 2026-05-07
**Status:** Design / discussion (no implementation in this branch)
**Skills applied:** `brainstorming`, `mcp-builder`, `performance`
**Audience:** Maintainers of `mcp-server-for-splunk` and `mcp-itsi-server`

---

## 1. Executive summary

The repository is **already on the current latest FastMCP release** (`fastmcp == 3.2.4`, pinned via `fastmcp>=3.2.4,<4` in `pyproject.toml`). PyPI confirms `3.2.4` is the most recent published version, released April 2026. There is **no version drift** between this codebase and upstream FastMCP.

What *has* drifted is **feature adoption**. FastMCP 3.0 (Feb 2026), 3.1 (Code Mode), and 3.2.x shipped a large set of capabilities — providers, transforms, granular auth, OpenTelemetry tracing, response limiting, ping keepalive, session-scoped visibility, structured outputs, tool timeouts, and more — that this repository does not yet use. Both servers were ported to FastMCP 3.x but continue to operate as if running on the late-2.x feature surface (raw `@mcp.tool` registration, custom middleware doing work the framework now handles natively, no transforms or providers).

The result is two MCP servers that *work* but leave a meaningful amount of reliability, security, observability, and agent-experience improvement on the table — and that carry significant home-grown infrastructure (large `server.py`, large `loader.py`, hand-rolled middleware, manual `inspect.signature` wrappers) that FastMCP 3.x would now do for them.

The biggest existing risk is structural, not version-related: `src/server.py` is 1,228 lines, `src/core/loader.py` is 1,303 lines, and several adjacent modules cross 400+ lines. The user's own workspace rules treat 1,000-line files as *unacceptable*. Modernizing onto FastMCP 3.x features is the natural lever to fix both problems at once.

---

## 2. Current state (evidence)

### 2.1 Versions

```text
fastmcp                    3.2.4   (latest stable)
mcp[cli]                   1.27.0  (recent)
splunk-sdk                 2.1.1
openinference-instrumentation-mcp >=2.0.0
opentelemetry-exporter-otlp-proto-http >=1.41.1
```

`fastmcp` is at the head of the 3.x line. The only modest dependency hygiene note: `mcp` could move to `>=1.24.0` to match what FastMCP 3.2.4 declares, but the current pin is fine.

### 2.2 File-size hot spots (vs. workspace rule: 500 line max, 1,000 line "unacceptable")

| File | Lines | Status vs. rule |
|---|---|---|
| `src/core/loader.py` | 1,303 | **exceeds 1,000** |
| `src/server.py` | 1,228 | **exceeds 1,000** |
| `src/core/enhanced_config_extractor.py` | 576 | over 500 |
| `src/core/security_monitoring.py` | 439 | over 400 warning |
| `src/core/client_identity.py` | 403 | over 400 warning |
| `src/core/base.py` | 378 | approaching 400 |
| `mcp_itsi/server.py` | 88 | clean |
| `mcp_itsi/core/*.py` | ≤ 136 | clean |
| `mcp_itsi/tools/*.py` | ≤ 196 | clean |

ITSI is structurally healthy. The Splunk core is not.

### 2.3 FastMCP 3.x features already in use

* Streamable HTTP transport with `stateless_http` and `json_response` knobs
* `@mcp.tool` / `@mcp.resource` / `@mcp.prompt` decorators
* `Context.set_state` / `Context.get_state` (per-request session state)
* `lifespan=` for service initialization (Splunk only)
* `auth=` parameter with dynamic verifier loading
* Custom MCP middleware (`Middleware`, `MiddlewareContext`)
* `fastmcp.server.dependencies` (`get_http_headers`, `get_http_request`, `get_context`)
* `mcp.custom_route` for `/health` and `/sentry-test`
* OpenInference / OpenTelemetry instrumentation via `openinference-instrumentation-mcp`

### 2.4 FastMCP 3.x features **not** in use (verified via `rg`)

Confirmed absent in `src/` and `mcp_itsi/`:

* `ResponseLimitingMiddleware` (3.0)
* `PingMiddleware` (3.0)
* `@handle_tool_errors` (3.0)
* `Tool.from_tool` / tool transforms (3.0)
* `VersionFilter`, `ResourcesAsTools`, `PromptsAsTools` transforms (3.0)
* `MultiAuth` for composing token verifiers (3.1)
* `CodeMode` / search transforms for tool discovery (3.1)
* `create_proxy` (3.0)
* `FileSystemProvider`, `OpenAPIProvider`, `ProxyProvider`, `SkillsProvider` (3.0)
* `ctx.elicit()` and `ctx.sample()`
* `outputSchema` on tools (only referenced in `docs/`)
* `enable_components` / `disable_components` / session-specific visibility (3.0)
* `http_client=` injection for token verifier connection pooling (3.1)
* In-memory token introspection cache (3.1)
* Tool foreground execution `timeout=` (3.0)
* MCP-compliant pagination (3.0)
* Background tasks scoped to authorization context (3.2.4)

---

## 3. What's new in FastMCP 3.x worth adopting

I'm grouping by impact category instead of release tag, since the user's question is "how do we get more reliable and performant". Each item references the release that introduced it.

### 3.1 Reliability

| Feature | Release | What it does | Why it matters here |
|---|---|---|---|
| `PingMiddleware` | 3.0 | Periodic MCP-level keepalive | Splunk searches and ITSI REST calls can run minutes; some MCP clients drop idle SSE/HTTP streams. Server-side keepalive prevents premature disconnects. |
| `ResponseLimitingMiddleware` | 3.0 (3.2.x fixes) | Caps tool response size before it crosses the wire | `run_oneshot_search` and `run_splunk_search` can return huge SPL result sets that overflow LLM context or crash clients. |
| Tool foreground `timeout=` | 3.0 | Per-tool soft timeout | The Splunk `run_splunk_search` and ITSI long-running ops have no native timeout today; an LLM call can hang indefinitely. |
| Background tasks (auth-scoped, 3.2.4) | 3.0/3.2.4 | Long-running work runs out-of-band, results polled via `ctx.elicit()` | The right home for "search this index for 24h" — currently we just block. |
| `@handle_tool_errors` | 3.0 | Standard tool-error envelope | Replaces hand-rolled `format_error_response` patterns scattered across `BaseTool` and `BaseITSITool`. |
| Composable lifespans | 3.0 | `[lifespan_a, lifespan_b]` | We can compose `splunk_lifespan` with a future ITSI lifespan instead of the current ad-hoc plugin entry-point dance. |
| Sync→threadpool auto-dispatch | 3.0 | Sync tool fns no longer block the loop | Several Splunk tools call blocking `splunklib` directly inside `async def`; auto-dispatch makes the migration safer. |
| Decorators return real callables | 3.0 | Decorated tools stay testable as plain functions | Cuts down on the `_create_tool_wrapper` / `inspect.signature` gymnastics in `loader.py`. |

### 3.2 Performance

| Feature | Release | Estimated impact |
|---|---|---|
| `http_client=` on token verifiers | 3.1 | Reuses one `httpx.AsyncClient` for OAuth introspection / JWKS instead of opening a new connection per request. ~50–150 ms saved per authenticated call when JWKS is hot. |
| Token introspection in-memory cache | 3.1 | Eliminates redundant introspection round-trips for the same token within TTL. Saves a full HTTP call per request when bearer tokens are reused. |
| Lazy imports | 3.1 | Reduces cold-start time for the server. Useful for `fastmcp run` flows and stdio. |
| Parallelized provider operations | 3.0 | When we adopt providers, list/get calls fan out concurrently. |
| MCP-compliant pagination | 3.0 | Pages tool/resource lists; clients no longer load the whole catalog. |
| Sync→threadpool | 3.0 | Frees the event loop while `splunklib` blocks on I/O. Today, one slow Splunk REST call stalls every other in-flight tool. |

### 3.3 Agent experience (what mcp-builder cares about)

| Feature | Release | Why agents care |
|---|---|---|
| `outputSchema` + `structuredContent` | 3.0 | LLMs that support structured outputs can validate and route on tool results without re-parsing JSON strings. |
| Search transforms / `CodeMode` | 3.1 | With ~80 ITSI tools + ~40 Splunk tools, the catalog is large. `CodeMode` lets agents discover and chain tools without loading every schema into context. |
| `ResourcesAsTools` / `PromptsAsTools` | 3.0 | Tool-only clients (some IDE assistants) currently can't use our `splunk_docs.py` and `dashboard_studio_docs.py` resources. |
| Component versioning + `VersionFilter` | 3.0 | Lets us ship a `v2` of a renamed tool while keeping old agents working. |
| Session-specific visibility | 3.0 | Show admin tools only after authentication; hide write tools for read-only sessions. |
| `ctx.elicit()` improvements (3.2.4) | 3.2.4 | Tools can ask the user for confirmation with typed responses. Useful for destructive ITSI operations (`itsi_delete_service`, etc.). |

### 3.4 Security & auth

| Feature | Release | Why it matters |
|---|---|---|
| `MultiAuth` | 3.1 | Compose multiple token verifiers (Splunk Bearer, Supabase JWT, internal IDP) without writing branchy code in `server.py`. |
| Granular component authorization | 3.0 | Mark `itsi_delete_*` and `itsi_update_*` as scope-restricted at the tool level instead of doing the check inside each tool. |
| `AuthMiddleware` | 3.0 | Replaces our custom `ClientConfigMiddleware` for the auth concern. |
| RFC 8707 audience binding (3.2.4) | 3.2.4 | Closes a token-reuse gap across MCP resources when `AuthKit` is involved. |
| Inbound→downstream header isolation (3.2.4) | 3.2.4 | Prevents MCP client headers from leaking to downstream APIs (relevant once we proxy more services). |

### 3.5 Observability

| Feature | Release | Why it matters |
|---|---|---|
| Native OpenTelemetry tracing with MCP semantic conventions | 3.0 | We already pull `openinference-instrumentation-mcp`, but FastMCP's built-in OTel emits MCP-spec attributes (`mcp.tool.name`, `mcp.session.id`, `mcp.method`) that line up with the conventions Sentry/Phoenix expect. Removes the need to set tags manually in `sentry_test`. |
| OTel + Sentry coexistence | 3.0 | We can keep Sentry for errors and use OTel exporters for traces — both supported simultaneously. |

---

## 4. Where the gaps hurt today (concrete)

These are concrete pain points in the current code that one or more new features would resolve.

### 4.1 `src/server.py` is doing FastMCP's job by hand

The 1,228-line file contains:
* A custom `HeaderCaptureMiddleware` (Starlette) that copies headers into a `ContextVar` because the team wrote this when `fastmcp.server.dependencies.get_http_headers()` either didn't exist or was unreliable. As of 3.x it's reliable, and a proper FastMCP `Middleware` can read headers directly.
* A second `ClientConfigMiddleware` (FastMCP) that re-reads the `ContextVar`, extracts client config, writes to `ctx.set_state`, and on session-termination methods evicts a global cache. This is exactly what `AuthMiddleware` + a small `Middleware` subclass would do.
* A global `HEADER_CLIENT_CONFIG_CACHE` keyed by session ID, with manual eviction logic. FastMCP 3.x ships `key-value` storage abstractions internally; for a feature this small, `ctx.set_state` plus a TTL-keyed dict-of-dict in the lifespan context is all that's needed.
* Duplicated component-loading logic running in three places: module-level (lines ~559–605), `splunk_lifespan` (~360–365), and `ensure_components_loaded` (~383–429). The lifespan is the right home; the other two paths exist because module-import-time vs lifespan-time was unclear pre-3.x.
* A bespoke `_normalize_session_id` for `MCP-Session-ID: id, id` doubling. FastMCP 3.x normalizes session IDs natively.

### 4.2 `src/core/loader.py` is reimplementing decorator binding

The `_create_tool_wrapper` function (lines ~94–191) inspects the `execute` method, builds a new `inspect.Signature` excluding `self`/`ctx`, copies type hints, and wraps the call. This was the right pattern when FastMCP couldn't introspect class-based tools, but FastMCP 3.x's `mcp.tool(fn)` accepts unbound methods and bound instances and figures it out. The same pattern lives in `mcp_itsi/core/registration.py` (smaller — 137 lines — but same shape).

The cleaner replacement is one of:
* Convert `BaseTool.execute` into a function-style tool registered with `@standalone_decorator`-style helpers (3.0 standalone decorators).
* Keep the class but use `mcp.tool(instance.execute, name=..., description=...)` — FastMCP 3.x will pull the right signature.
* Move both servers onto a `Provider` that owns its own discovery (e.g., a custom subclass of `Provider`, or `FileSystemProvider` for hot-reload in dev).

The third option is what the `mcp-builder` skill recommends for servers that already have ≥ 80 tools.

### 4.3 No response size guard on Splunk searches

`run_oneshot_search` reads results into a `list` (lines ~107–116 of `oneshot_search.py`) capped at `max_results` but with no byte budget. A user passing `max_results=10000` against a wide event in `index=main` can return tens of MB. `ResponseLimitingMiddleware` would clamp this server-side regardless of the tool's own logic.

### 4.4 No tool timeouts

`run_splunk_search` (job-based search) hands control to `splunklib` and waits. A search that hangs because of an upstream Splunk issue will hold the MCP request open until the client times out. FastMCP's per-tool `timeout=` would surface a clean error and free the worker.

### 4.5 Destructive ITSI tools have no confirmation step

`itsi_delete_service`, `itsi_delete_entity`, `itsi_delete_kpi_base_search`, etc. just call the API. The tool descriptions say "consumers should confirm intent with the user", but there is no `ctx.elicit()` to actually do that. With 3.2.4's improved `elicit()` (`response_title`, `response_description`), each destructive tool can prompt the calling agent for a typed confirmation before deleting.

### 4.6 No structured outputs

Both servers return `dict` from every tool. Newer MCP clients (Cursor included) prefer `outputSchema` + `structuredContent` because it lets them validate and route the data without parsing the text content. Adding `outputSchema` to the most-used tools (`run_splunk_search`, `itsi_list_services`, `list_indexes`, `get_user_info`) is low-risk and improves agent reliability.

### 4.7 Tool catalog is large and undiscoverable for some clients

ITSI registers ~75 tools (counted from `mcp_itsi/tools/__init__.py::all_tools`). Splunk registers another ~40. Agents that load the entire catalog into the system prompt waste tokens on tools they won't use. `CodeMode` (3.1) and search transforms address this directly.

### 4.8 Auth verifier loaded synchronously without connection reuse

`server.py:441-540` dynamically imports `MCP_AUTH_PROVIDER` and instantiates a verifier, but does not pass an `httpx.AsyncClient`. Every JWKS fetch / introspection call opens a new TCP+TLS connection. FastMCP 3.1 added `http_client=` exactly for this.

---

## 5. Three approaches (pick one)

The goal is reliability + performance + agent experience, but each approach has a different blast radius. Per the workspace rules (no time estimates), I'll describe each by *what changes* and *what risks*.

### Approach A — Drop-in middleware adoption (smallest blast radius)

**Scope:** Add new FastMCP middleware where it slots in cleanly without restructuring.

* Add `ResponseLimitingMiddleware` with a sane default (e.g., 2 MB).
* Add `PingMiddleware` with 30 s interval.
* Pass `http_client=` to whatever auth verifier `MCP_AUTH_PROVIDER` returns (gracefully — only if the verifier accepts it).
* Add `timeout=` to the few tools known to hang (`run_splunk_search`, `run_saved_search`, `itsi_*` long-list ops).
* Convert hand-rolled error formatting in tool wrappers to `@handle_tool_errors`.

**What we don't change:** `BaseTool` / `BaseITSITool` hierarchy, `loader.py` discovery, current `ClientConfigMiddleware`, server file structure.

**Risk:** Low. Each item is independently revertible. Touches both servers.
**What it doesn't fix:** The 1,200-line `server.py` and 1,300-line `loader.py` stay as they are.

### Approach B — Migrate to FastMCP-native registration + transforms (medium)

**Scope:** Approach A + replace the bespoke wrapper machinery with FastMCP 3.x primitives.

* Replace `_create_tool_wrapper` in `src/core/loader.py` with direct `mcp.tool(instance.execute, name=..., description=...)` registration. Same change in `mcp_itsi/core/registration.py`.
* Add `outputSchema` to the top 10 highest-traffic tools per server.
* Apply `ResourcesAsTools` transform so tool-only clients can access `splunk_docs`, `dashboard_studio_docs`, `splunk_cim`.
* Add `VersionFilter` and `version="..."` annotations on tools that have changed signatures recently (e.g., `create_dashboard` after the Studio theme change in PR #122).
* Replace `HeaderCaptureMiddleware` + `ClientConfigMiddleware` with one `AuthMiddleware`-aligned middleware that reads headers via `get_http_headers`, sets `ctx.set_state`, and evicts on `session/terminate`.
* Split `src/server.py` into:
  * `src/server/app.py` — Starlette factory only
  * `src/server/lifespan.py` — `splunk_lifespan` + `ensure_components_loaded`
  * `src/server/middleware.py` — `ClientConfigMiddleware` (slimmed down)
  * `src/server/diagnostics.py` — `sentry_test`, `user_agent_info`, health resources
  * `src/server/__init__.py` — `mcp = FastMCP(...)`, exports
* Split `src/core/loader.py` similarly into `discovery.py`, `registry.py` (already exists, expand its role), `register_tools.py`, `register_resources.py`, `register_prompts.py`, `hot_reload.py`.

**What we don't change:** Tool implementations, ITSI client/HTTP layer, auth provider machinery, public tool names.

**Risk:** Medium. Touches every tool registration path. Tests must verify each tool still loads and responds. The split of `server.py` and `loader.py` is mechanical but large.
**What it fixes:** Brings file sizes within the workspace rules. Removes 200+ lines of glue code that FastMCP now does for us.

### Approach C — Provider-based architecture with CodeMode (largest)

**Scope:** Approach B + restructure both servers around FastMCP `Provider` and transform chains.

* Implement a `SplunkProvider(Provider)` and `ITSIProvider(Provider)` that own discovery and registration. Replace the entry-point plugin mechanism with composition: `mcp = FastMCP(...); mcp.add_provider(SplunkProvider(...)); mcp.add_provider(ITSIProvider(...))`.
* Add `CodeMode` transform with a tool-search index over the combined catalog. Agents call `search_tools("notable event")` instead of receiving 110 schemas.
* Add `MultiAuth` so we can layer Splunk bearer auth, Supabase JWT, and any future provider without branchy code in `server.py`.
* Add `ctx.elicit()` confirmation to all destructive ITSI tools.
* Adopt `outputSchema` across the board.
* Native FastMCP OpenTelemetry tracing. Move Sentry to error-only sink.

**What we don't change:** Tool *behavior*. Public tool names stay, schemas stay, results stay.

**Risk:** High. Touches discovery, registration, auth, and observability simultaneously. Requires test coverage of provider composition. Some clients may behave differently when schemas come from a transform chain.
**What it fixes:** Future-proofs the project against the next FastMCP minor. Makes premium plugins (current entry-point system) become regular providers. CodeMode transforms tool discovery into a scalable problem.

### Recommendation

**Approach B**, sequenced as **A → B**. The drop-in middleware items in A are low-risk, high-reward, and don't depend on the larger refactor. Once they ship and are observed in production, do the structural work in B.

Approach C is the right *long-term* destination but should not be the next move because (a) the current file-structure debt is the actual operational risk and (b) provider composition is meaningfully different from the current plugin model and deserves a dedicated spec.

The workspace rule about file size and the user's stated goal ("more reliable and performant") line up best with **Approach B**.

---

## 6. Performance recommendations (ordered by estimated impact)

Per the `performance` skill: lead with impact estimate, name the affected metric, before/after.

> Note: There are no Core Web Vitals here (this is a Python server, not a web frontend). I'm using analogous server-side metrics: P50 / P95 tool latency, server cold-start, and bytes-on-the-wire.

### 1. **[P95 latency, ~50–500 ms] Cap tool response size with `ResponseLimitingMiddleware`**

A `run_oneshot_search` over a noisy index can return 10+ MB. Wire-time alone for 10 MB over HTTP/1.1 with TLS adds ~200–400 ms; downstream LLM context costs are worse.

```python
from fastmcp.server.middleware import ResponseLimitingMiddleware

mcp.add_middleware(ResponseLimitingMiddleware(max_bytes=2 * 1024 * 1024))
```

### 2. **[Cold-start, hundreds of ms] Stop preloading components at module import**

Today `src/server.py` loads components at import time (~559–605), in `splunk_lifespan` (~362–365), and in `ensure_components_loaded` (~415–419). Two of those are redundant. Lifespan is the only correct location post-3.x.

```python
mcp = FastMCP(
    name="MCP Server for Splunk",
    auth=auth_verifier,
    lifespan=splunk_lifespan,
)
```

The other two paths can be deleted. This reduces cold-start time and makes `fastmcp run --reload` work cleanly.

### 3. **[P95 latency under auth, ~50–150 ms per request] Reuse one `httpx.AsyncClient` in token verifier**

```python
import httpx

shared_http = httpx.AsyncClient(timeout=10.0, http2=True, limits=httpx.Limits(max_keepalive_connections=20))
auth_verifier = MyJWTVerifier(jwks_url="...", http_client=shared_http)
```

When `MCP_AUTH_PROVIDER` resolves to a 3.1+ verifier, this is a one-line change. For older verifiers, we keep the current path.

### 4. **[Event loop fairness] Run blocking `splunklib` calls in a threadpool**

`splunklib.client.connect`, `service.jobs.oneshot`, and `service.jobs.create` are synchronous and CPU/I/O blocking. Today they run inside `async def execute(...)` and stall the loop. FastMCP 3.0 auto-dispatches sync tool functions to a threadpool, but our tools are declared `async def`, so they don't qualify.

Two options:
* Convert the `splunklib` call sites to `await asyncio.to_thread(...)`.
* Or split tools into sync ones (auto-dispatched) and async ones (genuinely async).

The first is the smaller change.

### 5. **[Tool catalog size, token cost on the LLM side] Add `outputSchema` to high-traffic tools**

Modern clients can short-circuit text parsing when `outputSchema` is set. Lower per-call token cost, faster downstream agent decisions.

### 6. **[Memory growth over long sessions] Bound `HEADER_CLIENT_CONFIG_CACHE`**

The current dict has no eviction. Long-lived servers accumulate entries forever. Either move the cache into the lifespan-scoped object with a TTL, or use FastMCP 3.x `ctx.set_state` per session and rely on FastMCP's session lifecycle to evict.

### 7. **[Tail latency] Add per-tool `timeout=` for known long-runners**

```python
@mcp.tool(timeout=120)
def run_splunk_search(...): ...
```

Prevents indefinite hangs when Splunk REST is slow. Surfaces a deterministic error instead of relying on the client's HTTP timeout.

### 8. **[Logging volume] Demote chatty info logs to debug**

`ClientConfigMiddleware` emits 4–6 INFO log lines per request, including a `"keys=..., session_key=..."` line that effectively repeats the same data. Demoting to DEBUG saves disk I/O and parsing cost on the log-aggregation side.

---

## 7. Agent experience (mcp-builder lens)

The `mcp-builder` skill emphasizes:
* Comprehensive API coverage with workflow conveniences.
* Clear, descriptive tool names with consistent prefixes.
* Concise descriptions, structured outputs, actionable errors.

Where each lands today:

| mcp-builder principle | Splunk server | ITSI server |
|---|---|---|
| Comprehensive API coverage | Good for search, KV-store, indexes; thin on alerting and saved searches | Excellent — all major ITSI object types covered |
| Workflow tools | Has dashboard creation, workflow builder, performance analysis | Has `templatize_service` and event triage prompts |
| Consistent prefixing | Inconsistent (`run_splunk_search`, `run_oneshot_search`, but also `list_indexes`, `get_user_info`) | Consistent (`itsi_*` for all tools) |
| Concise descriptions | Some tool descriptions duplicate the `Args:` section (e.g., `OneshotSearch.METADATA.description` repeats the docstring) | Concise and well-structured |
| Structured outputs | None (returns `dict`) | None (returns `dict`) |
| Actionable errors | Yes for the connection layer; mixed at tool level | Yes — `error_response` is consistent |
| Pagination | Manual `max_results` knob; no MCP pagination | `limit`/`offset` on list tools — good |
| Annotations (`readOnlyHint`, `destructiveHint`, `idempotentHint`) | Not set | Not set |

Quick-win improvements:
1. **Rename Splunk tools to a consistent prefix.** `splunk_search`, `splunk_search_oneshot`, `splunk_list_indexes`, `splunk_get_user`, etc. (Breaking; gate behind a major version. Component versioning lets us keep both for one release.)
2. **Annotate every tool** with `readOnlyHint`/`destructiveHint`/`idempotentHint`. Trivial to add. Helps clients reason about safety.
3. **Add `outputSchema` to the top 10 tools per server** (run-search, list-indexes, list-services, list-entities, etc.).
4. **Trim duplicated tool descriptions.** Some descriptions duplicate the `Args:` section; FastMCP 3.2.4 extracts parameter descriptions from docstrings automatically, so we can let it.

---

## 8. Risks and non-goals

### Risks
* Renaming public tool names is breaking. Anything in section 7 that mentions a rename should ship behind component versioning, not as a hard cut.
* Changing the middleware stack in `server.py` is sensitive: the current cache-and-restore-session-id machinery exists because of real production bugs (header doubling, sticky-session failures behind Traefik). Any replacement must preserve the same behavior under those failure modes.
* Adopting `CodeMode` (Approach C only) changes how clients discover tools. Some clients may not handle search transforms gracefully.
* `ResponseLimitingMiddleware` truncation must be observable — silent truncation is worse than an error.

### Non-goals
* Bumping FastMCP to a non-existent newer version. We're already on the latest.
* Rewriting Splunk SDK integration. `splunk-sdk` 2.1.1 is fine.
* Changing the `mcp-itsi-server` packaging split. The recent `f846b19` made it a separate distribution; that's correct.
* Replacing Sentry. Sentry continues to make sense for error tracking; FastMCP's OTel tracing is complementary, not a replacement.

---

## 9. Open questions for the maintainers

These are the questions whose answers shape which approach we pick. None are blocking the *analysis*; they shape the *implementation* spec.

1. Is anyone in production relying on the global `HEADER_CLIENT_CONFIG_CACHE` semantics (cross-request, in-memory) — or is per-session caching enough?
2. How important is preserving exact tool names? (Determines whether section 7 renames are achievable in a minor.)
3. Do downstream agents rely on the fact that resources are *not* exposed as tools today, or would `ResourcesAsTools` be welcome?
4. Is there appetite for `CodeMode` adoption or is the catalog of ~110 tools manageable as-is for current users?
5. What's the operational story for OpenTelemetry exporters — is there an OTLP collector available today, or only the Sentry path?

---

## 10. Suggested next step

Open a follow-up *implementation* spec for **Approach A** only:
* Title: `fastmcp-3x-quick-wins-implementation.md` (dated when written)
* Scope: items 1, 3, 6, 7 from §6 plus `@handle_tool_errors`
* Test plan: existing pytest suite + a smoke test that issues a tool call larger than the response cap and verifies a clean error
* Rollout: feature-flag each middleware behind an env var (`MCP_RESPONSE_LIMIT_BYTES`, `MCP_PING_INTERVAL_S`) with sensible defaults

Once Approach A lands and is observed for one or two release cycles, write the Approach B spec covering the `server.py` / `loader.py` split and the FastMCP-native registration migration.

---

## Appendix A — Verified data points

* FastMCP latest: **3.2.4** (PyPI, https://pypi.org/pypi/fastmcp/json)
* Project pin: `fastmcp>=3.2.4,<4` (`pyproject.toml` line 21)
* Project resolved version: `3.2.4` (`uv.lock`)
* MCP SDK: `mcp[cli]>=1.27.0` (compatible with FastMCP 3.2.4's `mcp<2.0,>=1.24.0`)
* Splunk server lifespan: `splunk_lifespan` registered (`src/server.py:549`)
* ITSI server lifespan: none — uses `build_server` factory and `mcp.run` directly (`mcp_itsi/server.py:35-78`)
* `src/server.py` line count: 1,228 (`wc -l`)
* `src/core/loader.py` line count: 1,303 (`wc -l`)
* Splunk tool count: ~40 across `src/tools/{admin,alerts,dashboards,docs,health,kvstore,lookups,metadata,resources,search,workflows}/`
* ITSI tool count: 75 in `mcp_itsi/tools/__init__.py::all_tools`

## Appendix B — Sources consulted

* FastMCP changelog (https://gofastmcp.com/changelog), v3.0–v3.2.4 entries
* FastMCP releases (https://github.com/PrefectHQ/fastmcp/releases)
* FastMCP PyPI metadata (https://pypi.org/pypi/fastmcp/json)
* Project source (`/workspace/src`, `/workspace/mcp_itsi`)
* Workspace rules (`.cursorrules` and user rules on file size, single-responsibility, modularity)
* `mcp-builder` skill — design principles for tool selection and naming
* `performance` skill — impact ordering and before/after format
* `brainstorming` skill — design-doc structure
