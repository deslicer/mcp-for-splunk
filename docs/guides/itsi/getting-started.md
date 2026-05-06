# Getting Started — ITSI MCP Server

This guide takes you from zero to a working ITSI MCP server in **about 15 minutes**. By the end you'll have:

- A running ITSI MCP server (your choice of plugin or standalone).
- An AI client (Cursor / Claude Desktop / curl) calling ITSI tools end-to-end.
- A pass on the live integration smoke test.

> **Already running `mcp-for-splunk`?** Jump straight to [Path A — plugin mode](#path-a--plugin-of-mcp-for-splunk-recommended). The plugin loads automatically when both packages are installed.

## What you'll need

| Requirement | Why | How to check |
|---|---|---|
| Python 3.10+ and [`uv`](https://github.com/astral-sh/uv) | Server runtime + dependency management | `uv --version` |
| Git | Clone this repository | `git --version` |
| Docker (optional) | Standalone container deployment | `docker --version` |
| Splunk ITSI 4.18+ instance, reachable on port `8089` | The server talks to the ITSI REST API | Try `curl -k https://<host>:8089/services/server/info` |
| ITSI credentials | Username/password, an access token, or a session token | See [Authentication](#authentication) |

> **No ITSI of your own?** Spin up a Splunk Cloud ITSI lab or use the docker compose stack’s `so1` Splunk container with the ITSI app installed.

## Step 1 — Install

The repo ships **two PyPI distributions** as a uv workspace:

- `mcp-server-for-splunk` — the parent server (root `pyproject.toml`).
- `mcp-itsi-server` — the ITSI server (this guide; `packaging/mcp-itsi-server/`).

You can install them straight from PyPI:

```bash
# Standalone ITSI server only
pip install mcp-itsi-server

# Together with the parent mcp-server-for-splunk
pip install "mcp-server-for-splunk[itsi]"
```

Or work from a clone (recommended if you'll iterate on tools or run the integration tests):

```bash
git clone https://github.com/[REDACTED]/mcp-for-splunk.git
cd mcp-for-splunk
uv sync                           # installs both packages from local source
cp env.example .env               # tune SPLUNK_*, ITSI_*, MCP_* values
```

The same `.env` powers both servers. The relevant defaults are listed below — adjust to match your environment.

```env
SPLUNK_HOST=<splunk-host>
SPLUNK_PORT=8089
SPLUNK_USERNAME=<user>
SPLUNK_PASSWORD=<pass>
SPLUNK_VERIFY_SSL=false           # set to true in production with a valid cert

# Optional ITSI namespace overrides (defaults shown)
ITSI_APP=SA-ITOA
ITSI_USER_NS=nobody
ITSI_API_VERSION=vLatest

# Optional: prefer a token over basic auth (recommended)
# SPLUNK_TOKEN=eyJraWQiOi…
```

## Step 2 — Start a server

Pick the path that matches how you want to run things. **All paths expose identical tools.** See the [Deployment Guide](deployment.md) for the trade-offs.

### Path A — plugin of `mcp-for-splunk` (recommended)

The ITSI plugin is registered through the `mcp_splunk.plugins` Python entry point and loads automatically when both packages are installed in the same environment.

```bash
uv run mcp-server --local --detached
# → http://localhost:8001/mcp/                     (direct local)
# → http://localhost:${MCP_SERVER_PORT}/mcp/       (Traefik in docker-compose; default 8003)
```

Look for these lines in the logs to confirm the plugin loaded:

```text
Loading ITSI plugin into parent MCP server
Registered 70 ITSI tools
ITSI plugin loaded
```

To temporarily turn the plugin off without uninstalling:

```bash
MCP_DISABLE_PLUGINS=true uv run mcp-server --local
```

### Path B — standalone via Docker Compose

A dedicated `mcp-itsi` service ships in [`docker-compose.yml`](../../../docker-compose.yml) on its own Traefik path prefix.

```bash
docker compose up -d mcp-itsi
# → http://localhost:8003/itsi/mcp/
```

Traefik strips `/itsi` and forwards to `mcp-itsi:8001`. The container runs as a non-root `mcp` user with a built-in HEALTHCHECK.

### Path C — standalone via local Python

Useful for development, stdio-based clients, or one-off CLI testing.

```bash
uv run mcp-itsi-server --host 127.0.0.1 --port 8004
# → http://127.0.0.1:8004/mcp/

# stdio transport instead:
MCP_ITSI_TRANSPORT=stdio uv run mcp-itsi-server
```

## Step 3 — Connect a client

### Cursor / Claude Desktop / any MCP-compatible client

Add a server entry pointing at the URL from Step 2 with the right auth headers. The example below uses the Traefik plugin URL with a Splunk access token (preferred) — replace fields as needed.

```jsonc
{
  "mcpServers": {
    "splunk-itsi": {
      // Replace ${MCP_SERVER_PORT} with the port from your .env (default 8003).
      "url": "http://localhost:8003/mcp/", // pragma: allowlist secret
      "headers": {
        "X-Splunk-Host": "splunk.example.com",
        "X-Splunk-Port": "8089",
        "X-Splunk-Token": "<splunk-access-token>",
        "X-Splunk-Scheme": "https",
        "X-Splunk-Verify-SSL": "true",
        "X-ITSI-App": "SA-ITOA",
        "X-Session-ID": "itsi-dev-session"
      }
    }
  }
}
```

If you’re running the **standalone** server, change `url` to `http://localhost:8003/itsi/mcp/` (Compose) or `http://127.0.0.1:8004/mcp/` (local Python).

### Quick curl sanity check

```bash
curl -s http://localhost:8003/itsi/mcp/ \
  -H 'Accept: application/json, text/event-stream' \
  -H 'Content-Type: application/json' \
  -H "X-Splunk-Host: splunk.example.com" \
  -H "X-Splunk-Token: <splunk-access-token>" \
  -H "X-Splunk-Verify-SSL: true" \
  -d '{"jsonrpc":"2.0","id":"1","method":"tools/list"}' | jq '.result.tools[0:5][].name'
```

You should see ITSI tools such as `itsi_list_services`, `itsi_get_service`, `itsi_list_notable_events`.

## Step 4 — Run the live integration tests

These talk to your real ITSI instance and clean up after themselves.

```bash
ITSI_HOST=<host> \
ITSI_USERNAME=<user> \
ITSI_PASSWORD=<pass> \
ITSI_VERIFY_SSL=false \
uv run python scripts/test_itsi_mcp_both_modes.py
```

Expected:

```text
========== STANDALONE MODE ==========
- tools: 70   resources: 9   prompts: 3
... failures: 0 (smoke + deep + CRUD)

========== PLUGIN MODE (mcp-for-splunk + itsi plugin) ==========
- tools: 123   resources: 28   prompts: 6
... failures: 0 (smoke + deep + CRUD + plugin isolation)

--- TOTAL FAILURES: 0 ---
```

Targeted scripts you can also run directly:

| Script | What it does |
|---|---|
| `scripts/test_itsi_mcp.py` | Read-only smoke test — every tool, resource, prompt. |
| `scripts/test_itsi_mcp_deep.py` | `_key` round-trips through every `itsi_get_*`. |
| `scripts/test_itsi_mcp_crud.py` | Create → Update → Delete on every mutable object. |
| `scripts/test_itsi_plugin_isolation.py` | Confirms parent + plugin coexist (plugin mode only). |

## Step 5 — Try a real workflow

Ask your AI client something like:

- **Service onboarding** — *"Onboard a new service called Web Store with a database and an app tier, attached entities `web-1`, `web-2`, and KPIs for HTTP error rate and CPU."* The agent will call `itsi_create_service`, `itsi_create_entity`, KPI base searches, and aggregation policies in turn.
- **Episode triage** — *"Show me open episodes for tier-1 services from the last 4 hours and acknowledge anything assigned to me."* This pulls from `itsi_list_notable_events`, then `itsi_acknowledge_notable_event`.
- **Knowledge lookup** — *"What are the ITSI best practices for KPI urgency?"* This pulls from the bundled docs via `itsi_search_docs` / `itsi://docs/best-practices`.

## Authentication

The ITSI server accepts the **same** auth headers as `mcp-for-splunk`. Precedence on each request is bearer token → session token → username/password.

- **Recommended**: Splunk access token via `X-Splunk-Token` (or alias `auth_token` / `X-Auth-Token` / `X-Splunk-Auth-Token`). Tokens are scoped, revocable, and have an explicit expiry.
- **Per-user session**: pre-existing splunkd session token via `X-Splunk-Session-Token` (sends `Authorization: Splunk …`).
- **Username/password**: `X-Splunk-Username` + `X-Splunk-Password`. Acceptable for development.
- **Authorization: Bearer**: works **only** when the parent server has `MCP_AUTH_DISABLED=true`. This avoids confusing a Splunk token with an MCP-server JWT.

Env defaults (`SPLUNK_TOKEN`, `MCP_SPLUNK_TOKEN`, `SPLUNK_SESSION_TOKEN`, `MCP_SPLUNK_SESSION_TOKEN`, `SPLUNK_USERNAME`/`SPLUNK_PASSWORD`) fill in any header the client omits.

The full credential matrix and per-mode notes live in the [Client Configuration guide](../configuration/client_configuration.md).

## Troubleshooting

| Symptom | Likely cause / fix |
|---|---|
| `No Splunk credentials provided` on every call | Client isn't sending any of `X-Splunk-Token`, `X-Splunk-Session-Token`, or `X-Splunk-Username`+`X-Splunk-Password`; and no env defaults are set. |
| `401 Unauthorized` from ITSI | Token expired, password mismatch, or basic auth pair sent against an SSO-only Splunk instance. |
| `404 ITSI API` from a tool | Wrong namespace — pass `X-ITSI-App: SA-ITOA` and `X-ITSI-User-NS: nobody` (the defaults), or your custom values. |
| Plugin doesn't appear in `tools/list` | `MCP_DISABLE_PLUGINS=true` is set, or `mcp_itsi` isn’t installed in the same env as `mcp-for-splunk`. Confirm with `uv run python -c "from mcp_itsi.tools import all_tools; print(len(all_tools()))"`. |
| Container exits immediately | Check `docker logs mcp-itsi` — most often `.env` is missing or `SPLUNK_HOST` is unset. |
| Tool returns ITSI 5xx | Some ITSI endpoints validate the **full** schema even with `is_partial=true`. The pattern is GET → merge → PUT-back-with-`is_partial=False`. See the [service-creation review](../itsi_service_creation_review.md). |

For wider-project troubleshooting (Splunk auth, transport, sessions) see [`docs/getting-started/troubleshooting.md`](../../getting-started/troubleshooting.md).

## Where next

- **[Deployment Guide](deployment.md)** — choose between standalone and plugin, configure Traefik, run behind a reverse proxy, scale.
- **[Package README](../../../mcp_itsi/README.md)** — full tool catalog, resources, prompts.
- **[Service-creation review](../itsi_service_creation_review.md)** — documented walk-through against the official ITSI guides.
- **[Parent README](../../../README.md)** — broader MCP Server for Splunk capabilities.
