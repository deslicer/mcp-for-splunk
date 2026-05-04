# ITSI MCP Server — Documentation Hub

A dedicated Model Context Protocol server for **Splunk IT Service Intelligence (ITSI)**. Ships in this repository under [`mcp_itsi/`](../../../mcp_itsi/README.md) and runs in either of two modes with identical capabilities:

- **Plugin** of [`mcp-for-splunk`](../../../README.md) — one process, one URL, one set of credentials.
- **Standalone** FastMCP server — its own container or local Python process, separately routed.

Both modes ship **70 tools**, **9 documentation resources**, and **3 workflow prompts**, target ITSI 4.21, and accept the same `X-Splunk-*` per-request auth headers as the parent server.

## Pick a guide

| You want to… | Go to | Time |
|---|---|---|
| Get a working server in under 15 minutes | **[Getting Started](getting-started.md)** | 10–15 min |
| Decide standalone vs plugin and roll out properly | **[Deployment Guide](deployment.md)** | 20 min |
| Browse every tool, resource, and prompt | **[Package README](../../../mcp_itsi/README.md)** | reference |
| Configure auth headers for an MCP client | [Authentication](../../../mcp_itsi/README.md#authentication) | 5 min |
| Read the documented service-creation walk-through (what works, what doesn't) | [Service-creation review](../itsi_service_creation_review.md) | 10 min |
| See the wider project's MCP capabilities | [Parent README](../../../README.md) | 5 min |

## High-level coverage

- **Service Insights** — services, service templates, KPIs, glass tables, deep dives, home views, count helpers.
- **Entity Integration** — entities, entity types, alias inventory.
- **Event Analytics** — notable events, aggregation policies, correlation searches; ack/close shortcuts for episode triage.
- **Maintenance & RBAC** — maintenance windows, teams.
- **Docs as data** — `itsi_list_docs`, `itsi_read_doc`, `itsi_search_docs`, plus `itsi://docs/<slug>` resources.

## Auth, in one paragraph

The ITSI MCP server reuses the parent project's per-request header convention. Every request can carry its own `X-Splunk-*` headers (basic auth, bearer token, or splunkd session token) plus optional `X-ITSI-*` namespace overrides — see the [parent client configuration guide](../configuration/client_configuration.md) for the full credential matrix and the [package README](../../../mcp_itsi/README.md#authentication) for ITSI-specific headers.

## Verifying

A unified driver runs both modes against any live ITSI cluster:

```bash
ITSI_HOST=<splunk-host> ITSI_USERNAME=<user> ITSI_PASSWORD=<pass> \
ITSI_VERIFY_SSL=false \
uv run python scripts/test_itsi_mcp_both_modes.py
```

It boots the standalone server, runs smoke + deep + CRUD suites, then boots the parent server with the ITSI plugin loaded and re-runs the suites plus a plugin-isolation check. Expected: `TOTAL FAILURES: 0`.
