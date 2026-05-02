# ITSI MCP Server

Model Context Protocol server for **Splunk IT Service Intelligence (ITSI)**.

It can be deployed two ways:

- **Standalone** — its own FastMCP HTTP/stdio process (runnable via Docker
  Compose, `python -m mcp_itsi`, or the `mcp-itsi-server` console script).
- **Plugin** — mounted on the existing `mcp-for-splunk` server through the
  `mcp_splunk.plugins` Python entry point.

Both modes share the exact same Splunk credential headers as the parent
project, so AI clients only need to configure auth once.

## Quick start (standalone via Docker Compose)

```bash
cp env.example .env
# Edit .env; the same SPLUNK_* settings power both servers.

docker compose up -d mcp-itsi

# Connect any MCP client to:
#   http://localhost:8003/itsi/mcp/
# (the Traefik entrypoint strips /itsi and routes to mcp-itsi:8001)
```

## Quick start (local Python)

```bash
uv sync
uv run mcp-itsi-server --host 127.0.0.1 --port 8004
```

## Quick start (as plugin of mcp-for-splunk)

The plugin entry point is registered automatically when this package is
installed alongside `mcp-server-for-splunk`. Start the parent server as
usual and confirm the load message:

```text
Loading ITSI plugin into parent MCP server
Registered N ITSI tools
```

To **disable** the plugin temporarily, set `MCP_DISABLE_PLUGINS=true`.

## Authentication

Send the same `X-Splunk-*` headers the parent project accepts. Optional
`X-ITSI-*` headers tweak the ITSI namespace per request.

```jsonc
{
  "mcpServers": {
    "splunk-itsi": {
      "url": "http://localhost:8003/itsi/mcp/",
      "headers": {
        "X-Splunk-Host": "so1",
        "X-Splunk-Port": "8089",
        "X-Splunk-Username": "admin",
        "X-Splunk-Password": "Chang3d!",
        "X-Splunk-Scheme": "https",
        "X-Splunk-Verify-SSL": "false",
        "X-ITSI-App": "SA-ITOA",
        "X-ITSI-User-NS": "nobody",
        "X-Session-ID": "itsi-dev-session"
      }
    }
  }
}
```

See `itsi://docs/cookbook/header-auth` for token-based auth and other recipes.

## Capabilities at a glance

### Service Insights tools

| Tool                              | Purpose                                  |
|-----------------------------------|------------------------------------------|
| `itsi_list_services`              | List services with filter / sort / paging|
| `itsi_get_service`                | Read one service.                        |
| `itsi_create_service`             | Create a service.                        |
| `itsi_update_service`             | Partial / full update of a service.      |
| `itsi_delete_service`             | Delete a service by `_key`.              |
| `itsi_count_services`             | Count services by filter.                |
| `itsi_list_service_templates`     | List `base_service_template` objects.    |
| `itsi_get_service_template`       | Read one template.                       |
| `itsi_templatize_service`         | Generate a template payload from service.|

### Entity Integration tools

| Tool                           | Purpose                                |
|--------------------------------|----------------------------------------|
| `itsi_list_entities`           | List entities.                         |
| `itsi_get_entity`              | Read one entity.                       |
| `itsi_create_entity`           | Create an entity.                      |
| `itsi_update_entity`           | Update an entity (partial by default). |
| `itsi_delete_entity`           | Delete an entity.                      |
| `itsi_list_entity_types`       | List entity types.                     |
| `itsi_get_entity_type`         | Read an entity type.                   |
| `itsi_get_alias_list`          | All identifier / informational aliases.|

### KPI tooling

| Tool                                    | Purpose                          |
|-----------------------------------------|----------------------------------|
| `itsi_list_kpi_base_searches`           | Reusable KPI base searches.      |
| `itsi_get_kpi_base_search`              | Read a base search.              |
| `itsi_list_kpi_threshold_templates`     | Threshold templates.             |
| `itsi_get_kpi_threshold_template`       | Read a threshold template.       |

### Visualisation & investigation

| Tool                       | Purpose                          |
|----------------------------|----------------------------------|
| `itsi_list_glass_tables`   | List glass tables.               |
| `itsi_get_glass_table`     | Read a glass table.              |
| `itsi_list_home_views`     | Service Analyzer home views.     |
| `itsi_get_home_view`       | Read a home view.                |
| `itsi_list_deep_dives`     | List deep dives.                 |
| `itsi_get_deep_dive`       | Read a deep dive.                |

### Event Analytics

| Tool                                    | Purpose                                          |
|-----------------------------------------|--------------------------------------------------|
| `itsi_list_notable_events`              | Filterable list of notable events.               |
| `itsi_get_notable_event`                | Read one notable event by `event_id`.            |
| `itsi_acknowledge_notable_event`        | Set status=2 (in progress).                      |
| `itsi_close_notable_event`              | Set status=5 + optional comment.                 |
| `itsi_list_aggregation_policies`        | Aggregation policy catalog.                      |
| `itsi_list_correlation_searches`        | Correlation searches that emit notable events.   |

### Maintenance, RBAC, meta, docs

`itsi_list_maintenance_windows`, `itsi_get_maintenance_window`,
`itsi_list_teams`, `itsi_get_team`, `itsi_get_supported_object_types`,
`itsi_list_docs`, `itsi_read_doc`, `itsi_search_docs`.

### Resources (browse via your MCP client)

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

| Prompt                       | Purpose                                       |
|------------------------------|-----------------------------------------------|
| `itsi_service_onboarding`    | End-to-end service onboarding playbook.       |
| `itsi_kpi_design`            | KPI design plan with thresholds & urgency.    |
| `itsi_episode_triage`        | Notable event / episode triage runbook.       |

## Architecture

```text
mcp_itsi/
├─ __init__.py / __main__.py / cli.py / server.py
├─ plugin.py                  # entry point for parent mcp-for-splunk
├─ Dockerfile                 # standalone container image
├─ config/                    # settings + per-request header parsing
├─ client/                    # async HTTP client + endpoint constants
├─ core/                      # base classes + registration glue
├─ tools/                     # one tool per file (≤200 lines)
├─ resources/                 # bundled docs as MCP resources
├─ prompts/                   # prompt definitions
└─ knowledge/                 # markdown corpus + lightweight catalog
```

Every file targets ≤200 lines (well under the project's 500-line limit) and
respects single-responsibility: each tool talks to one ITSI object type.
