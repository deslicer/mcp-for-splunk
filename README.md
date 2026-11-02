<!-- mcp-name: io.github.deslicer/mcp-for-splunk -->
<div align="center">
  <img src="media/deslicer_white.svg" alt="Deslicer" width="180">
</div>

# MCP for Splunk: open-source Splunk MCP server

**An open-source Splunk MCP server (Model Context Protocol) that lets AI assistants and agents search, explore and manage Splunk Enterprise and Splunk Cloud Platform.**

[![PyPI](https://img.shields.io/pypi/v/mcp-server-for-splunk)](https://pypi.org/project/mcp-server-for-splunk/)
[![Python](https://img.shields.io/badge/Python-3.11%2B-green)](https://python.org)
[![FastMCP](https://img.shields.io/badge/FastMCP-4.1-blue)](https://gofastmcp.com/)
[![MCP](https://img.shields.io/badge/MCP-Compatible-purple)](https://modelcontextprotocol.io/)
[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)

Python integrations: see the [package namespace migration guide](docs/guides/package-namespace-migration.md).

`mcp-for-splunk` exposes Splunk's REST API as MCP tools, resources and prompts. Any MCP-compatible client, such as Cursor, Claude Desktop, VS Code or your own agent, can run SPL, discover indexes and sourcetypes, read configuration, manage saved searches, alerts, dashboards and KV Store, and look up Splunk and CIM documentation. It runs over **stdio** or **Streamable HTTP**. In HTTP mode, each request can carry its own Splunk credentials in headers, so one server can serve several users or Splunk environments.

- 📖 Setup guide and tools reference: **[deslicer.ai/docs/integrations/splunk-mcp](https://deslicer.ai/docs/integrations/splunk-mcp)**
- ⚖️ How it compares with Splunk's own MCP Server app: **[deslicer.ai/compare/splunk-mcp-server](https://deslicer.ai/compare/splunk-mcp-server)**
- 📦 PyPI: [`mcp-server-for-splunk`](https://pypi.org/project/mcp-server-for-splunk/) · ITSI companion: [`mcp-itsi-server`](https://pypi.org/project/mcp-itsi-server/)

> Looking for Splunk's vendor-supported MCP server? That's the **Splunk MCP Server** app on [Splunkbase (app 7931)](https://splunkbase.splunk.com/app/7931), which runs inside Splunk at `/services/mcp`. This project is a separate, community-maintained server that runs outside Splunk and talks to the management port (8089).

## Contents
- [Quickstart](#quickstart)
- [Configuration](#configuration)
- [Connect a client](#connect-a-client)
- [Tools](#tools)
- [Resources and prompts](#resources-and-prompts)
- [ITSI MCP server](#itsi-mcp-server)
- [Run with Docker](#run-with-docker)
- [Optional: Sentry and OpenTelemetry](#optional-sentry-and-opentelemetry)
- [Contributing](#contributing)
- [License](#license)

## Quickstart

**Requirements:** Python 3.11+ (Python 3.10 is no longer supported), [uv](https://docs.astral.sh/uv/) or pip, and a Splunk Enterprise or Splunk Cloud Platform instance with REST API (port 8089) access. Docker is optional.

### Option A: install from PyPI

```bash
pip install mcp-server-for-splunk          # or: uv tool install mcp-server-for-splunk

export SPLUNK_HOST=your-splunk.example.com
export SPLUNK_PORT=8089
export SPLUNK_TOKEN=<splunk-bearer-token>  # or SPLUNK_USERNAME + SPLUNK_PASSWORD

mcp-server --transport stdio               # for desktop clients that spawn the server
mcp-server                                 # Streamable HTTP on http://localhost:8001/mcp/
```

The installed `mcp-server` command accepts `--transport {http,stdio}`, `--host` and `--port`. The HTTP port defaults to `MCP_SERVER_PORT` or `8001`.

### Option B: run from a source checkout

```bash
git clone https://github.com/deslicer/mcp-for-splunk.git
cd mcp-for-splunk
cp env.example .env                        # then edit the Splunk settings

./scripts/smart-install.sh --dry-run       # macOS/Linux: preview missing prerequisites
./scripts/smart-install.sh                 # install them (Python, uv, Git, Node)

uv run mcp-server --local --detached       # start the server (checkout default port 8003)
uv run mcp-server --test                   # verify; add --detailed for tools/resources
uv run mcp-server --stop                   # stop this project's services
```

On Windows, use the same `uv run mcp-server …` commands from PowerShell (see `scripts/build_and_run.ps1` and the [Windows guide](docs/WINDOWS_GUIDE.md)). In a checkout, `mcp-server` asks whether to run the full Docker stack or a local process. The local endpoint is `http://localhost:8003/mcp/`.

## Configuration

Copy [`env.example`](env.example) to `.env`. The main variables:

| Variable | Purpose | Default |
|---|---|---|
| `SPLUNK_HOST`, `SPLUNK_PORT` | Splunk management endpoint | `8089` port |
| `SPLUNK_SCHEME` | `https` or `http` | |
| `SPLUNK_TOKEN` | Bearer token; takes precedence over username/password | |
| `SPLUNK_USERNAME`, `SPLUNK_PASSWORD` | Basic credentials | |
| `SPLUNK_SESSION_TOKEN` | Existing splunkd session token (advanced) | |
| `SPLUNK_VERIFY_SSL` | TLS verification. The client defaults to `true` when this is unset. `env.example` sets `false` for local labs with self-signed certs | `true` when unset |
| `SPLUNK_WEB_URL` / `SPLUNK_WEB_PORT` / `SPLUNK_WEB_LOCALE` | Used to build links to dashboards and jobs | |
| `MCP_SERVER_HOST`, `MCP_SERVER_PORT` | HTTP bind address | `0.0.0.0`, `8001` (installed) / `8003` (checkout) |
| `MCP_STATELESS_HTTP`, `MCP_JSON_RESPONSE` | Stateless HTTP and JSON responses for wider client compatibility | `true` in `env.example` |
| `MCP_DEFAULT_TOOLSETS` | Toolsets for clients that send no `X-MCP-Toolsets` header (`splunk`, `splunk,itsi`, `all`) | `splunk` |
| `MCP_SEARCH_WAIT_SECONDS` | How long `run_splunk_search` / `run_oneshot_search` wait before returning | `15` |
| `MCP_AUTH_DISABLED`, `MCP_AUTH_PROVIDER` | Inbound MCP authentication | |
| `MCP_LOG_LEVEL` | Log level | `INFO` |

For stdio clients, you can also pass `MCP_SPLUNK_HOST`, `MCP_SPLUNK_PORT`, `MCP_SPLUNK_USERNAME`, `MCP_SPLUNK_PASSWORD`, `MCP_SPLUNK_TOKEN`, `MCP_SPLUNK_SCHEME` and `MCP_SPLUNK_VERIFY_SSL` in the client's `env` block.

## Connect a client

### stdio (Cursor, Claude Desktop, VS Code and similar)

```json
{
  "mcpServers": {
    "splunk": {
      "command": "mcp-server",
      "args": ["--transport", "stdio"],
      "env": {
        "MCP_SPLUNK_HOST": "your-splunk.example.com",
        "MCP_SPLUNK_PORT": "8089",
        "MCP_SPLUNK_TOKEN": "<splunk-bearer-token>",
        "MCP_SPLUNK_VERIFY_SSL": "true"
      }
    }
  }
}
```

### Streamable HTTP with per-request credentials

Start the server once, then let each client send its own Splunk target in headers:

```json
{
  "mcpServers": {
    "splunk-http": {
      "url": "http://localhost:8001/mcp/",
      "headers": {
        "X-Splunk-Host": "your-splunk.example.com",
        "X-Splunk-Port": "8089",
        "X-Splunk-Scheme": "https",
        "X-Splunk-Token": "<splunk-bearer-token>",
        "X-Splunk-Verify-SSL": "true"
      }
    }
  }
}
```

Supported headers: `X-Splunk-Host`, `X-Splunk-Port`, `X-Splunk-Scheme`, `X-Splunk-Token`, `X-Splunk-Username`, `X-Splunk-Password`, `X-Splunk-Session-Token`, `X-Splunk-Verify-SSL`, `X-Splunk-Web-Url`, `X-Splunk-Web-Port`, `X-Splunk-Web-Locale`, `X-MCP-Toolsets`. Sessionless mode is the default. Send a stable `X-Session-ID` if you want config cached across requests. See [HTTP client connection modes](docs/guides/configuration/http-client-modes.md). If you run from a checkout, use port `8003`.

## Tools

The core server registers these tools (source: `src/mcp_server_for_splunk/tools/`). Tools that write to Splunk are marked ✏️. Your Splunk role's permissions still apply.

| Area | Tool | What it does |
|---|---|---|
| Search | `run_oneshot_search` | Run SPL and wait up to `MCP_SEARCH_WAIT_SECONDS` for results |
| | `run_splunk_search` | Run SPL as a tracked job with progress and stats |
| | `get_search_job_info` | Status, properties and messages for a job (sid) |
| | `get_search_job_results` | One page of results from a completed job |
| Saved searches | `list_saved_searches` | Saved searches with owner, schedule and permissions |
| | `get_saved_search_details` | Full configuration of one saved search |
| | `execute_saved_search` | Run a saved search by name |
| | `create_saved_search` ✏️ | Create a saved search, optionally scheduled |
| | `update_saved_search` ✏️ | Update query, schedule or sharing |
| | `delete_saved_search` ✏️ | Delete a saved search (with confirmation) |
| Alerts | `list_triggered_alerts` | Fired alerts and details |
| | `list_alert_actions` | Installed alert actions, including custom ones |
| | `create_alert` ✏️ / `update_alert` ✏️ / `delete_alert` ✏️ | Manage alerts (scheduled saved searches with triggers) |
| Metadata | `list_indexes` | Accessible indexes |
| | `list_sourcetypes` | Sourcetypes via `metadata` (paged) |
| | `list_sources` | Sources via `metadata` (paged) |
| | `get_metadata` | Distinct metadata values for an index |
| Dashboards | `list_dashboards` | Simple XML and Dashboard Studio dashboards |
| | `get_dashboard_definition` | Raw definition of a dashboard |
| | `create_dashboard` ✏️ | Create a Simple XML or Dashboard Studio dashboard |
| KV Store | `list_kvstore_collections` | Collections and schema |
| | `get_kvstore_data` | Query documents with filters |
| | `create_kvstore_collection` ✏️ | Create a collection |
| Lookups | `list_lookup_files` | CSV lookup files |
| | `list_lookup_definitions` | Lookup definitions (transforms) |
| Admin | `list_apps` | Installed apps |
| | `manage_apps` ✏️ | Enable, disable or restart apps |
| | `list_users` | Users and roles |
| | `me` | The authenticated user |
| | `get_configurations` | Read settings from `.conf` files |
| | `create_config` ✏️ | Create or update a stanza in a `.conf` file at app level |
| | `get_splunk_health` | Connectivity and health status |
| | `enhance_tool_description` | Developer helper that improves tool descriptions |
| Docs and CIM | `list_cim_data_models` / `get_cim_reference` | CIM data models and field specifications |
| | `get_spl_reference` / `list_spl_commands` / `get_splunk_cheat_sheet` | SPL reference |
| | `list_config_files` / `get_config_spec` | `.conf` file specs |
| | `list_admin_topics` / `get_admin_guide` | Admin documentation |
| | `list_troubleshooting_topics` / `get_troubleshooting_guide` | Troubleshooting documentation |
| | `list_dashboard_studio_topics` / `get_studio_topic` | Dashboard Studio documentation |
| | `list_available_topics` / `discover_splunk_docs` / `get_splunk_documentation` | Discover and fetch Splunk docs by URI |
| Workflows | `list_workflows` / `workflow_builder` / `workflow_requirements` / `get_executed_workflows` | Discover, author and validate troubleshooting workflow JSON |

Workflow JSON definitions are for discovery, validation and external orchestration. The built-in `workflow_runner` was removed with the move to FastMCP 4 / MCP SDK v2. See the [workflows guide](docs/guides/workflows/README.md) and the [tools reference](docs/reference/tools.md).

## Resources and prompts

- **Resources:** Splunk documentation (`splunk-docs://…`, including SPL reference, troubleshooting and admin topics), configuration specs (`splunk-spec://{config}`), CIM data models, Dashboard Studio docs and embedded docs. See [docs/reference/resources.md](docs/reference/resources.md).
- **Prompts:** `mcp_overview`, `workflow_creation_guide`, `tool_usage_guide`.
- **[llms.txt](llms.txt):** a guide for LLMs on using this server.

## ITSI MCP server

A server for **Splunk IT Service Intelligence** lives in [`mcp_itsi/`](mcp_itsi/README.md) and is published as [`mcp-itsi-server`](https://pypi.org/project/mcp-itsi-server/). Run it as a plugin of this server (`pip install "mcp-server-for-splunk[itsi]"`, enabled per client with `X-MCP-Toolsets: splunk,itsi` or `MCP_DEFAULT_TOOLSETS`) or standalone (`pip install mcp-itsi-server`). It uses the same `X-Splunk-*` headers. See the [ITSI getting started guide](docs/guides/itsi/getting-started.md).

## Run with Docker

`docker-compose.yml` runs the MCP server behind Traefik on `http://localhost:8003/mcp`, together with the MCP Inspector. `docker-compose-splunk.yml` adds a Splunk container (`so1`) for local testing; bring your own Splunk license if you need one. See the [deployment guide](docs/guides/deployment/README.md).

## Optional: Sentry and OpenTelemetry

- `pip install "mcp-server-for-splunk[sentry]"` and set `SENTRY_DSN`. See [Sentry monitoring](docs/guides/sentry-monitoring.md).
- `pip install "mcp-server-for-splunk[otel]"` and set `OTEL_EXPORTER_OTLP_ENDPOINT`. See [OpenTelemetry tracing](docs/guides/otel-tracing.md).

## Contributing

```bash
uv run generate-tool     # scaffold a new tool
uv run validate-tools    # validate tool implementations
```

See [CONTRIBUTING.md](CONTRIBUTING.md), [contrib/README.md](contrib/README.md), [AGENTS.md](AGENTS.md), the [Code of Conduct](CODE_OF_CONDUCT.md), the [Security policy](SECURITY.md) and [Governance](GOVERNANCE.md). Questions and bugs go to [GitHub Issues](https://github.com/deslicer/mcp-for-splunk/issues).

## About

Maintained by [Deslicer](https://deslicer.ai). Deslicer uses this server in its product, where it's documented at [deslicer.ai/docs/integrations/splunk-mcp](https://deslicer.ai/docs/integrations/splunk-mcp). Splunk is a trademark of Splunk LLC; this project is not affiliated with or endorsed by Splunk.

## License

[Apache 2.0](LICENSE)
