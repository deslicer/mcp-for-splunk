# ITSI MCP Server

A dedicated Model Context Protocol server for **Splunk IT Service Intelligence (ITSI)** ships in this repository under [`mcp_itsi/`](../../mcp_itsi/README.md). It targets ITSI 4.21 and exposes **70 tools, 9 documentation resources, and 3 prompts**.

The server runs in either of two modes — **standalone** (its own FastMCP process) or **plugin** of [`mcp-for-splunk`](../../README.md) — with identical capabilities and the same `X-Splunk-*` per-request auth headers as the parent server.

## Pick a guide

| You want to… | Go to | Time |
|---|---|---|
| Get a working server end-to-end | **[Getting Started](itsi/getting-started.md)** | 10–15 min |
| Decide standalone vs plugin and roll out properly | **[Deployment Guide](itsi/deployment.md)** | 20 min |
| Browse every tool / resource / prompt | **[Package README](../../mcp_itsi/README.md)** | reference |
| Configure auth headers in your MCP client | [Authentication](../../mcp_itsi/README.md#authentication) | 5 min |
| See what works and what doesn't (with workarounds) | [Service-creation review](itsi_service_creation_review.md) | 10 min |
| Browse the ITSI hub page | [ITSI Documentation Hub](itsi/README.md) | 2 min |

## At a glance

- **Service Insights** — services, service templates, KPIs, glass tables, deep dives, home views, count helpers.
- **Entity Integration** — entities, entity types, alias inventory.
- **Event Analytics** — notable events, aggregation policies, correlation searches; ack/close shortcuts for episode triage.
- **Maintenance & RBAC** — maintenance windows, teams.
- **Docs as data** — `itsi_list_docs`, `itsi_read_doc`, `itsi_search_docs`, plus `itsi://docs/<slug>` resources.

## Auth, in one paragraph

Both modes share the same `X-Splunk-*` headers used elsewhere in this project, including bearer tokens (`X-Splunk-Token` / `auth_token` / `X-Auth-Token` / `X-Splunk-Auth-Token`) and splunkd session tokens (`X-Splunk-Session-Token`). When `MCP_AUTH_DISABLED=true`, `Authorization: Bearer <splunk-token>` is accepted as a fallback (same rule as the core MCP server). See the [Client Configuration guide](configuration/client_configuration.md) for the full credential matrix.
