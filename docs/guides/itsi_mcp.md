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
project.

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
| `X-Splunk-Token`      | Splunk auth token (alternative to username/password).  |
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

## See also

- [`mcp_itsi/README.md`](../../mcp_itsi/README.md) — full reference.
- ITSI knowledge bundle: every doc is also accessible as an MCP resource
  at `itsi://docs/<slug>` and via the `itsi_read_doc` tool.
