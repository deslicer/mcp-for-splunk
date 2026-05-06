# mcp-itsi-server

Model Context Protocol server for **Splunk IT Service Intelligence (ITSI)** — runs standalone or as a plugin of [`mcp-server-for-splunk`](https://pypi.org/project/mcp-server-for-splunk/).

[![Tools](https://img.shields.io/badge/tools-70-orange)](https://github.com/[REDACTED]/mcp-for-splunk/blob/main/mcp_itsi/README.md#capabilities-at-a-glance)
[![FastMCP](https://img.shields.io/badge/FastMCP-2.13%2B-blue)](https://gofastmcp.com/)
[![ITSI](https://img.shields.io/badge/ITSI-4.21-purple)](https://help.splunk.com/en/splunk-it-service-intelligence/splunk-it-service-intelligence/leverage-rest-apis/4.21/itsi-rest-api-reference/itsi-rest-api-reference)

## What you get

- **70 tools** covering full CRUD on every mutable ITSI object (services, service templates, entities, entity types, KPI base searches, KPI threshold templates, glass tables, deep dives, home views, teams, notable events, aggregation policies, correlation searches), plus discovery, doc-search, and event triage shortcuts.
- **9 documentation resources** distilled from the official ITSI 4.21 docs (`itsi://docs/<slug>`).
- **3 workflow prompts**: `itsi_service_onboarding`, `itsi_kpi_design`, `itsi_episode_triage`.

## Install

```bash
# Standalone server (only ITSI tools)
pip install mcp-itsi-server

# Together with the parent mcp-server-for-splunk
pip install "mcp-server-for-splunk[itsi]"
```

## Run

```bash
# HTTP, default port 8004
mcp-itsi-server

# stdio (e.g. for desktop AI clients)
MCP_ITSI_TRANSPORT=stdio mcp-itsi-server

# Override host/port
mcp-itsi-server --host 127.0.0.1 --port 8004
```

When installed alongside `mcp-server-for-splunk`, the ITSI tools auto-register on the parent server through the `mcp_splunk.plugins` entry point — no extra configuration needed. Set `MCP_DISABLE_PLUGINS=true` to opt out.

## Auth (in one paragraph)

Per-request `X-Splunk-*` headers (basic, bearer token, or splunkd session token), plus optional `X-ITSI-App` / `X-ITSI-User-NS` / `X-ITSI-API-Version` namespace overrides. Env defaults (`SPLUNK_HOST`, `SPLUNK_TOKEN`, `SPLUNK_USERNAME` / `SPLUNK_PASSWORD`, etc.) fill in any header the client omits. Same contract as the parent server — see the [client configuration guide](https://github.com/[REDACTED]/mcp-for-splunk/blob/main/docs/guides/configuration/client_configuration.md).

## Documentation

- **[Package README](https://github.com/[REDACTED]/mcp-for-splunk/blob/main/mcp_itsi/README.md)** — full tool catalog, env vars, architecture.
- **[Getting Started](https://github.com/[REDACTED]/mcp-for-splunk/blob/main/docs/guides/itsi/getting-started.md)** — first 15 minutes against a real ITSI cluster.
- **[Deployment Guide](https://github.com/[REDACTED]/mcp-for-splunk/blob/main/docs/guides/itsi/deployment.md)** — standalone vs plugin, Docker, scaling, security.

## Source

This package is built from [`mcp-for-splunk`](https://github.com/[REDACTED]/mcp-for-splunk) under [`mcp_itsi/`](https://github.com/[REDACTED]/mcp-for-splunk/tree/main/mcp_itsi). Releases are managed by [release-please](https://github.com/googleapis/release-please) — see [`packaging/mcp-itsi-server/CHANGELOG.md`](https://github.com/[REDACTED]/mcp-for-splunk/blob/main/packaging/mcp-itsi-server/CHANGELOG.md).

Apache 2.0 licensed.
