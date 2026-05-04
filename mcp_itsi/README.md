<div align="center">
  <h1>🛡️ MCP Server for Splunk IT Service Intelligence</h1>

  [![FastMCP](https://img.shields.io/badge/FastMCP-2.13%2B-blue)](https://gofastmcp.com/)
  [![Python](https://img.shields.io/badge/Python-3.10%2B-green)](https://python.org)
  [![ITSI](https://img.shields.io/badge/ITSI-4.21-purple)](https://help.splunk.com/en/splunk-it-service-intelligence/splunk-it-service-intelligence/leverage-rest-apis/4.21/itsi-rest-api-reference/itsi-rest-api-reference)
  [![Tools](https://img.shields.io/badge/tools-70-orange)](#capabilities-at-a-glance)
  [![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](../LICENSE)

  *Model Context Protocol server purpose-built for Splunk IT Service Intelligence — runs standalone or as a plugin of [`mcp-server-for-splunk`](../README.md).*
</div>

> **Need the high-level pitch instead?** See [`docs/guides/itsi/`](../docs/guides/itsi/README.md).

## What you get

- **70 tools** covering full CRUD on every mutable ITSI object (services, service templates, entities, entity types, KPI base searches, KPI threshold templates, glass tables, deep dives, home views, teams, notable events, aggregation policies, correlation searches) plus discovery, doc-search, and event triage shortcuts.
- **9 documentation resources** distilled from the official ITSI 4.21 docs — accessible as MCP resources (`itsi://docs/<slug>`) and as `itsi_list_docs` / `itsi_read_doc` / `itsi_search_docs` tools.
- **3 workflow prompts** — `itsi_service_onboarding`, `itsi_kpi_design`, `itsi_episode_triage`.
- **Two deployment modes** with identical capabilities: a dedicated FastMCP process or a plugin of the parent `mcp-server-for-splunk` server.
- **The same auth contract as `mcp-for-splunk`**: per-request `X-Splunk-*` headers (basic, bearer, or session token) plus optional `X-ITSI-*` namespace overrides.

## Choose your path

| You want to… | Go to |
|---|---|
| Run a server in 5 minutes against a real ITSI host | [Getting Started](../docs/guides/itsi/getting-started.md) |
| Decide between standalone and plugin mode | [Deployment Guide](../docs/guides/itsi/deployment.md) |
| Configure auth headers for your MCP client | [Authentication](#authentication) below |
| Browse the tool catalog and resource list | [Capabilities at a glance](#capabilities-at-a-glance) below |
| Understand the package layout | [Architecture](#architecture) below |

## Quick start

### 1. As a plugin of `mcp-for-splunk` (recommended)

Installing this package in the same environment as `mcp-server-for-splunk` is enough — the parent server loads ITSI through the `mcp_splunk.plugins` Python entry point on startup.

```bash
uv sync                       # installs the plugin alongside the parent server
uv run mcp-server --local --detached
# Look for: "Loading ITSI plugin into parent MCP server" in the logs.
```

Connect any MCP client to the **parent** server URL — `http://localhost:8001/mcp/` directly, or `http://localhost:${MCP_SERVER_PORT}/mcp/` (default `8003`) when running behind Traefik — and you'll see the parent's tools plus 70 `itsi_*` tools.

To **disable** the plugin without uninstalling it:

```bash
MCP_DISABLE_PLUGINS=true uv run mcp-server --local
```

### 2. Standalone via Docker Compose

A dedicated `mcp-itsi` container is wired into [`docker-compose.yml`](../docker-compose.yml) behind Traefik:

```bash
cp env.example .env           # tune SPLUNK_* and ITSI_* values
docker compose up -d mcp-itsi

# MCP endpoint:
#   http://localhost:8003/itsi/mcp/   (Traefik strips /itsi → mcp-itsi:8001)
```

### 3. Standalone via local Python

```bash
uv sync
uv run mcp-itsi-server --host 127.0.0.1 --port 8004
# Endpoint: http://127.0.0.1:8004/mcp/
```

`stdio` transport works too:

```bash
MCP_ITSI_TRANSPORT=stdio uv run mcp-itsi-server
```

> **More detail:** see the [Deployment Guide](../docs/guides/itsi/deployment.md) for matrix, networking, and operational considerations.

## Authentication

Send the same `X-Splunk-*` headers the parent project accepts. Optional `X-ITSI-*` headers tweak the ITSI namespace per request.

### Header reference

| Header | Purpose |
|---|---|
| `X-Splunk-Host` | splunkd host (or set `SPLUNK_HOST` in env). |
| `X-Splunk-Port` | splunkd management port, default `8089`. |
| `X-Splunk-Scheme` | `https` (default) or `http`. |
| `X-Splunk-Verify-SSL` | `true` / `false`, default `false`. |
| `X-Splunk-Username` + `X-Splunk-Password` | Basic auth pair. |
| `X-Splunk-Token` | Splunk bearer / access token (preferred). |
| `auth_token` / `X-Auth-Token` / `X-Splunk-Auth-Token` | Aliases for the bearer header (some clients send these names). |
| `X-Splunk-Session-Token` | Existing splunkd session token (sends `Authorization: Splunk …`). |
| `X-ITSI-App` | App namespace, default `SA-ITOA`. |
| `X-ITSI-User-NS` | User namespace, default `nobody`. |
| `X-ITSI-API-Version` | ITSI API version, default `vLatest`. |
| `X-Session-ID` | Optional client-defined session id (logging only). |
| `Authorization: Bearer <token>` | Accepted **only** when `MCP_AUTH_DISABLED=true`. |

Auth precedence is `bearer → session → username/password`. Env defaults (`SPLUNK_TOKEN`, `MCP_SPLUNK_TOKEN`, `SPLUNK_SESSION_TOKEN`, `MCP_SPLUNK_SESSION_TOKEN`, `SPLUNK_USERNAME` / `SPLUNK_PASSWORD`) are used when a header is missing.

### Example — Cursor / Claude Desktop with two ITSI tenants

```jsonc
{
  "mcpServers": {
    "splunk-itsi-prod": {
      "url": "http://localhost:8003/itsi/mcp/",
      "headers": {
        "X-Splunk-Host": "prod-splunk.company.com",
        "X-Splunk-Port": "8089",
        "X-Splunk-Token": "<production-bearer-token>",
        "X-Splunk-Scheme": "https",
        "X-Splunk-Verify-SSL": "true",
        "X-ITSI-App": "SA-ITOA",
        "X-Session-ID": "itsi-prod"
      }
    },
    "splunk-itsi-lab": {
      "url": "http://localhost:8003/itsi/mcp/",
      "headers": {
        "X-Splunk-Host": "so1",
        "X-Splunk-Username": "admin",
        "X-Splunk-Password": "Chang3d!",
        "X-Splunk-Verify-SSL": "false",
        "X-Session-ID": "itsi-lab"
      }
    }
  }
}
```

Token-auth recipes (creating tokens, rotating, scope) live in `itsi://docs/cookbook/header-auth` (also browsable as [`mcp_itsi/knowledge/content/cookbook/header_auth.md`](knowledge/content/cookbook/header_auth.md)).

## Environment variables

All variables have safe defaults; everything below is optional.

| Variable | Default | Purpose |
|---|---|---|
| `MCP_ITSI_SERVER_HOST` | `0.0.0.0` | Bind address for the standalone HTTP server. |
| `MCP_ITSI_SERVER_PORT` | `8004` | Bind port (overridden to `8001` in the Docker image). |
| `MCP_ITSI_TRANSPORT` | `http` | `http`, `streamable-http`, or `stdio`. |
| `MCP_ITSI_LOG_LEVEL` | `INFO` | Falls back to `MCP_LOG_LEVEL`. |
| `MCP_STATELESS_HTTP` | `true` | Disables sticky sessions for FastMCP HTTP. |
| `MCP_JSON_RESPONSE` | `true` | Forces JSON over SSE-style streams (better client compatibility). |
| `ITSI_APP` | `SA-ITOA` | Default app namespace. |
| `ITSI_USER_NS` | `nobody` | Default user namespace. |
| `ITSI_API_VERSION` | `vLatest` | ITSI REST API version. |
| `ITSI_REQUEST_TIMEOUT` | `30` | Per-request timeout in seconds. |
| `MCP_AUTH_DISABLED` | `false` | Enables `Authorization: Bearer` fallback for the Splunk credential. |
| `SPLUNK_HOST` / `SPLUNK_PORT` / `SPLUNK_SCHEME` | — | Default Splunk endpoint when the client omits the headers. |
| `SPLUNK_USERNAME` / `SPLUNK_PASSWORD` | — | Default basic-auth credentials. |
| `SPLUNK_TOKEN` / `MCP_SPLUNK_TOKEN` | — | Default bearer token. |
| `SPLUNK_SESSION_TOKEN` / `MCP_SPLUNK_SESSION_TOKEN` | — | Default splunkd session token. |
| `SPLUNK_VERIFY_SSL` | `false` | Default TLS verification. |

## Capabilities at a glance

### Service Insights (14 tools)

| Tool | Purpose |
|---|---|
| `itsi_list_services` | List services with filter / sort / paging. |
| `itsi_get_service` | Read one service by `_key`. |
| `itsi_create_service` | Create a service. |
| `itsi_update_service` | Partial / full update of a service. |
| `itsi_delete_service` | Delete a service. |
| `itsi_count_services` | Count services by filter. |
| `itsi_list_service_templates` | List `base_service_template` objects. |
| `itsi_get_service_template` | Read one template. |
| `itsi_create_service_template` | Create a template (requires a seed `service_id`). |
| `itsi_update_service_template` | Update a template. |
| `itsi_delete_service_template` | Delete a template. |
| `itsi_templatize_service` | Generate a template payload from a service. |

### Entity integration (10 tools)

| Tool | Purpose |
|---|---|
| `itsi_list_entities` / `itsi_get_entity` | Browse / read entities. |
| `itsi_create_entity` / `itsi_update_entity` / `itsi_delete_entity` | Mutations (note: every alias field listed in `identifier.fields` must be present at the document root, e.g. `"host": ["my-host"]`). |
| `itsi_list_entity_types` / `itsi_get_entity_type` | Browse / read entity types. |
| `itsi_create_entity_type` / `itsi_update_entity_type` / `itsi_delete_entity_type` | Mutations. |
| `itsi_get_alias_list` | Identifier + informational alias inventory across all entities. |

### KPI configuration (10 tools)

| Tool | Purpose |
|---|---|
| `itsi_list_kpi_base_searches` / `itsi_get_kpi_base_search` | Browse / read reusable KPI base searches. |
| `itsi_create_kpi_base_search` / `itsi_update_kpi_base_search` / `itsi_delete_kpi_base_search` | Mutations. |
| `itsi_list_kpi_threshold_templates` / `itsi_get_kpi_threshold_template` | Browse / read threshold templates. |
| `itsi_create_kpi_threshold_template` / `itsi_update_kpi_threshold_template` / `itsi_delete_kpi_threshold_template` | Mutations. |

### Visualisation & investigation (15 tools)

`itsi_list_glass_tables`, `itsi_get_glass_table`, `itsi_create_glass_table`, `itsi_update_glass_table`, `itsi_delete_glass_table`, `itsi_list_home_views`, `itsi_get_home_view`, `itsi_create_home_view`, `itsi_update_home_view`, `itsi_delete_home_view`, `itsi_list_deep_dives`, `itsi_get_deep_dive`, `itsi_create_deep_dive`, `itsi_update_deep_dive`, `itsi_delete_deep_dive`.

### Event Analytics (15 tools)

| Tool | Purpose |
|---|---|
| `itsi_list_notable_events` | Filterable list of notable events. |
| `itsi_get_notable_event` | Read one notable event by `event_id`. |
| `itsi_acknowledge_notable_event` | Set status=2 (in progress). |
| `itsi_close_notable_event` | Set status=5 + optional comment. |
| `itsi_list_aggregation_policies` / `itsi_get_aggregation_policy` | Browse / read aggregation policies. |
| `itsi_create_aggregation_policy` / `itsi_update_aggregation_policy` / `itsi_delete_aggregation_policy` | Mutations (update merges into the full document — see [`docs/guides/itsi_service_creation_review.md`](../docs/guides/itsi_service_creation_review.md)). |
| `itsi_list_correlation_searches` / `itsi_get_correlation_search` | Browse / read correlation searches. |
| `itsi_create_correlation_search` / `itsi_update_correlation_search` / `itsi_delete_correlation_search` | Mutations (update payload must echo `name`). |

### Maintenance, RBAC, meta, docs (8 tools)

`itsi_list_maintenance_windows`, `itsi_get_maintenance_window`, `itsi_list_teams`, `itsi_get_team`, `itsi_get_supported_object_types`, `itsi_list_docs`, `itsi_read_doc`, `itsi_search_docs`.

### Resources

```text
itsi://docs/overview
itsi://docs/api/reference
itsi://docs/api/schema
itsi://docs/service-insights
itsi://docs/entity-integrations
itsi://docs/event-analytics
itsi://docs/modules
itsi://docs/best-practices
itsi://docs/cookbook/header-auth
```

### Prompts

| Prompt | Purpose |
|---|---|
| `itsi_service_onboarding` | End-to-end service onboarding playbook. |
| `itsi_kpi_design` | KPI design plan with thresholds and urgency. |
| `itsi_episode_triage` | Notable event / episode triage runbook. |

## Architecture

```text
mcp_itsi/
├─ __init__.py / __main__.py / cli.py / server.py   # entry points
├─ plugin.py                  # mcp_splunk.plugins entry point (parent server)
├─ Dockerfile                 # standalone container image
├─ config/                    # settings + per-request header parsing
├─ client/                    # async HTTP client + endpoint constants
├─ core/                      # base classes + registration glue
├─ tools/                     # one file per ITSI object type (≤200 lines)
├─ resources/                 # bundled docs as MCP resources
├─ prompts/                   # workflow prompt definitions
└─ knowledge/                 # markdown corpus + lightweight catalog
```

Every file targets ≤200 lines (well under the project's 500-line guard rail) and follows single responsibility: each tool talks to one ITSI object type.

## Verifying the integration

Live integration scripts exercise the full surface against any ITSI cluster:

| Script | Coverage |
|---|---|
| `scripts/test_itsi_mcp.py` | Smoke test — every tool, resource, prompt. |
| `scripts/test_itsi_mcp_deep.py` | Real `_key` round-trips through every `itsi_get_*`. |
| `scripts/test_itsi_mcp_crud.py` | Full Create → Update → Delete for every mutable object, with auto-cleanup. |
| `scripts/test_itsi_plugin_isolation.py` | Plugin mode only: confirms ITSI tools coexist with parent tools. |
| `scripts/test_itsi_mcp_both_modes.py` | Boots both servers in turn and runs all of the above against each. |

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

- **[Getting Started](../docs/guides/itsi/getting-started.md)** — first 15 minutes against a real ITSI cluster.
- **[Deployment Guide](../docs/guides/itsi/deployment.md)** — standalone vs plugin, networking, scaling.
- **[ITSI MCP overview](../docs/guides/itsi_mcp.md)** — short hub page in the project docs.
- **[Service-creation walk-through and critical review](../docs/guides/itsi_service_creation_review.md)** — what works, what's still rough, and the workarounds we've documented.
- **[Parent project README](../README.md)** — the broader MCP Server for Splunk.
