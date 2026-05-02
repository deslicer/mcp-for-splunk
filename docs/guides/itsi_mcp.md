# ITSI MCP Server

A dedicated Model Context Protocol server for Splunk **IT Service
Intelligence (ITSI)** ships in this repository under
[`mcp_itsi/`](../../mcp_itsi/README.md). It targets ITSI 4.21 and exposes
41 tools, 9 documentation resources, and 3 prompts.

## Deployment options

You have two ways to run it. Pick whichever matches your operating
preference:

1. **Standalone** — its own FastMCP HTTP/stdio process, started via
   `docker compose up mcp-itsi`, `python -m mcp_itsi`, or the
   `mcp-itsi-server` console script.
2. **Plugin** — automatically mounted on the existing `mcp-for-splunk`
   server via the Python entry point `mcp_splunk.plugins.itsi`. No
   additional configuration required when both packages are installed
   in the same environment.

Both modes share the same `X-Splunk-*` headers used elsewhere in this
project, including bearer tokens and session tokens as on
[`client_configuration.md`](configuration/client_configuration.md).

When `MCP_AUTH_DISABLED=true`, `Authorization: Bearer <splunk-token>` is
accepted as a fallback (same rule as the core MCP server).

## Quick start

```bash
cp env.example .env
# Default ITSI port is 8004; standalone container exposes 8001 internally.
docker compose up -d mcp-itsi

# Connect via Traefik:
#   http://localhost:8003/itsi/mcp/
```

## Authentication

The server reuses the same per-request header convention as
`mcp-for-splunk`:

| Header                | Purpose                                                |
|-----------------------|--------------------------------------------------------|
| `X-Splunk-Host`       | splunkd host.                                          |
| `X-Splunk-Port`       | splunkd port (default `8089`).                         |
| `X-Splunk-Username`   | Username (when not using a token).                     |
| `X-Splunk-Password`   | Password.                                              |
| `X-Splunk-Token`      | Splunk bearer / access token (same as parent server).  |
| `X-Splunk-Session-Token` | Existing splunkd session token (`Splunk …` in `Authorization`). |
| `auth_token`          | Alias for the bearer token (some clients send this name). |
| `X-Splunk-Scheme`     | `http` or `https`.                                     |
| `X-Splunk-Verify-SSL` | `true` / `false`.                                      |
| `X-ITSI-App`          | App namespace (default `SA-ITOA`).                     |
| `X-ITSI-User-NS`      | User namespace (default `nobody`).                     |
| `X-ITSI-API-Version`  | API version (default `vLatest`).                       |
| `X-Session-ID`        | Optional client-defined session id.                    |

## Capabilities

See the [package README](../../mcp_itsi/README.md) for the full tool
catalog. High-level coverage:

- **Service Insights**: services, service templates, KPIs, glass tables,
  deep dives, home views.
- **Entity Integrations**: entities, entity types, alias inventory.
- **Event Analytics**: notable events, aggregation policies, correlation
  searches; ack/close shortcuts.
- **Maintenance**: maintenance window inventory.
- **RBAC**: teams.
- **Docs**: `itsi_list_docs`, `itsi_read_doc`, `itsi_search_docs` plus
  `itsi://docs/...` resources for browsing.

## Choosing standalone vs. plugin

| Situation                                                        | Recommended mode |
|------------------------------------------------------------------|------------------|
| Single deployment unit, fewer moving pieces                      | Plugin           |
| ITSI lives behind different network policies than core Splunk    | Standalone       |
| Want different scaling / restart cadence for ITSI                | Standalone       |
| Multi-tenant routing where ITSI traffic is separately observable | Standalone       |

## Verifying the integration

Three live test scripts cover both deployment modes:

| Script | Coverage |
|--------|----------|
| `scripts/test_itsi_mcp.py` | Smoke test — every tool, resource, prompt. |
| `scripts/test_itsi_mcp_deep.py` | Real `_key` round-trips through every `itsi_get_*`. |
| `scripts/test_itsi_mcp_crud.py` | Full Create → Update → Delete for every mutable object. |
| `scripts/test_itsi_plugin_isolation.py` | Plugin mode only: confirms ITSI tools coexist with parent tools. |

The driver `scripts/test_itsi_mcp_both_modes.py` boots both servers in
turn and runs the suites against each. To verify against your own
ITSI cluster:

```bash
ITSI_HOST=<splunk-host> \
ITSI_USERNAME=<user> \
ITSI_PASSWORD=<pass> \
ITSI_VERIFY_SSL=false \
uv run python scripts/test_itsi_mcp_both_modes.py
```

Expected output:

```text
========== STANDALONE MODE ==========
- tools: 70   resources: 9   prompts: 3
... failures: 0 (smoke + deep + CRUD)

========== PLUGIN MODE (mcp-for-splunk + itsi plugin) ==========
- tools: 123   resources: 28   prompts: 6
... failures: 0 (smoke + deep + CRUD + plugin isolation)

--- TOTAL FAILURES: 0 ---
```

## See also

- [`mcp_itsi/README.md`](../../mcp_itsi/README.md) — full reference.
- ITSI knowledge bundle: every doc is also accessible as an MCP resource
  at `itsi://docs/<slug>` and via the `itsi_read_doc` tool.
