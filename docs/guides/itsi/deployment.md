# ITSI MCP Server — Deployment Guide

Two ways to deploy the ITSI MCP server, both shipping the same 70 tools, 9 resources, and 3 prompts.

| Mode | Where it runs | Best for |
|---|---|---|
| **Plugin** | Inside the existing `mcp-for-splunk` process | Single deployment unit; one URL and one credential set across both servers; lowest operational footprint. |
| **Standalone** | Its own FastMCP HTTP/stdio process (Docker, or `mcp-itsi-server` CLI) | Independent scaling, separate network policies, multi-tenant routing, distinct restart cadence. |

Pick what matches your operational model. Switching between modes later is non-destructive — both consume the same `X-Splunk-*` auth headers.

## Choosing a mode

| Situation | Recommended | Why |
|---|---|---|
| You're already deploying `mcp-for-splunk` | Plugin | Adds ITSI to the existing process — zero new infrastructure. |
| ITSI lives behind tighter network policies than core Splunk | Standalone | Lets you route ITSI traffic separately and apply distinct firewall rules. |
| You need different scaling or restart cadence for ITSI | Standalone | Isolated container can be scaled / restarted independently. |
| You want one URL for the AI agent | Plugin | Single endpoint, single auth config in the client. |
| Multi-tenant routing where ITSI traffic needs to be observable separately | Standalone | Traefik path prefix `/itsi/mcp` makes ITSI traffic distinct in metrics/logs. |
| You're running the parent server on stdio for a desktop AI client | Plugin | Both surfaces become available on the same stdio session. |

## Mode 1 — plugin of `mcp-for-splunk`

The plugin is registered through the `mcp_splunk.plugins` Python entry point in [`pyproject.toml`](../../../pyproject.toml):

```toml
[project.entry-points."mcp_splunk.plugins"]
itsi = "mcp_itsi.plugin:setup"
```

When the parent server boots, it walks `mcp_splunk.plugins` and calls each `setup(mcp, root_app=...)`. Our `setup` registers the ITSI tools, resources, and prompts on the same `FastMCP` instance.

### Install + run

```bash
uv sync                                   # installs both packages
uv run mcp-server --local --detached      # local FastMCP
# or
docker compose up -d mcp-server           # full stack behind Traefik
```

You should see in the parent logs:

```text
Loading ITSI plugin into parent MCP server
Registered 70 ITSI tools
ITSI plugin loaded
```

### Disable the plugin

Without uninstalling the package:

```bash
MCP_DISABLE_PLUGINS=true uv run mcp-server --local
```

This is also how CI runs the parent's unit tests in isolation.

### Endpoints

| Transport | URL |
|---|---|
| Direct (local FastMCP) | `http://localhost:8001/mcp/` |
| Via Traefik (Docker stack) | `http://localhost:${MCP_SERVER_PORT}/mcp/` (default `8003`) |
| stdio | spawn `uv run mcp-server` and pipe over stdio |

The agent talks to the same URL it would use without the plugin; the new `itsi_*` tools just appear alongside the parent's.

### Auth in plugin mode

ITSI uses **the same** `X-Splunk-*` headers and env defaults as the parent server. There’s nothing extra to configure for auth. The optional `X-ITSI-*` overrides (app/user namespace, API version) are honored only by the ITSI tools — the parent's tools ignore them.

## Mode 2 — standalone

### 2a. Docker Compose (recommended)

The repo's [`docker-compose.yml`](../../../docker-compose.yml) ships an `mcp-itsi` service:

- Builds [`mcp_itsi/Dockerfile`](../../../mcp_itsi/Dockerfile) (Python 3.12-slim, non-root `mcp` user, `HEALTHCHECK`).
- Listens on `:8001` inside the container.
- Sits behind Traefik on the `mcp` entrypoint with `PathPrefix(\`/itsi/mcp\`)` and a `stripprefix` middleware.
- CORS is opened for the `X-Splunk-*` / `X-ITSI-*` headers we accept.

```bash
cp env.example .env
docker compose up -d mcp-itsi

# MCP endpoint:
#   http://localhost:8003/itsi/mcp/
```

Useful overrides (in `.env` or shell):

| Variable | Effect |
|---|---|
| `MCP_SERVER_PORT` (default `8003`) | Public Traefik port for **both** servers. |
| `MCP_ITSI_TRANSPORT` (default `http`) | Switch to `stdio` if you bind a stdio MCP client. |
| `MCP_STATELESS_HTTP` / `MCP_JSON_RESPONSE` | Match the parent server's HTTP behaviour. |
| `MCP_ITSI_LOG_LEVEL` | Independent log level for the ITSI container. |
| `SPLUNK_*` / `ITSI_*` | Default Splunk endpoint and ITSI namespace. |

Health-check the container:

```bash
docker exec mcp-itsi curl --fail --silent http://127.0.0.1:8001/mcp/ -H 'Accept: application/json' >/dev/null && echo OK
```

### 2b. Local Python

Useful for developers and stdio clients.

```bash
uv sync
uv run mcp-itsi-server --host 127.0.0.1 --port 8004
```

CLI flags map to the same settings the standalone container uses:

```text
--host        MCP_ITSI_SERVER_HOST       (default 0.0.0.0)
--port        MCP_ITSI_SERVER_PORT       (default 8004)
--transport   {http, streamable-http, stdio}  (default http)
--version     prints mcp_itsi version
```

stdio mode for desktop AI clients:

```bash
MCP_ITSI_TRANSPORT=stdio uv run mcp-itsi-server
```

### 2c. Container outside compose

If you orchestrate elsewhere, the image is self-contained:

```bash
docker build -t mcp-itsi -f mcp_itsi/Dockerfile .

docker run --rm -p 8004:8001 \
  -e SPLUNK_HOST=splunk.example.com \
  -e SPLUNK_TOKEN=<token> \
  -e SPLUNK_VERIFY_SSL=true \
  mcp-itsi
```

Endpoint: `http://localhost:8004/mcp/`.

## Networking & Traefik

The repo's Traefik config exposes:

- `--entrypoints.web.address=:80`
- `--entrypoints.mcp.address=:${MCP_SERVER_PORT:-8003}` — both `mcp-server` and `mcp-itsi` register here.
- `--entrypoints.inspector.address=:6274` — MCP Inspector UI.

Routing rules:

| Service | Rule | Strip prefix? | Backend port |
|---|---|---|---|
| `mcp-server` | `PathPrefix(\`/mcp\`)` | no | `8001` |
| `mcp-itsi` | `PathPrefix(\`/itsi/mcp\`)` | yes (`/itsi`) | `8001` |
| `mcp-inspector` | `Host(\`inspector.localhost\`)` or `PathPrefix(\`/inspector/\`)` | — | `6274` |

If you front the stack with another reverse proxy (NGINX, ALB, ingress), preserve the same path prefixes — the ITSI tools assume the FastMCP endpoint is reachable at `/mcp/` once any prefix is stripped.

## Configuration reference

### Server settings

All have safe defaults; everything below is optional. Mirror values listed in [`mcp_itsi/README.md`](../../../mcp_itsi/README.md#environment-variables) — the table here is just for quick reference.

| Variable | Default | Where it matters |
|---|---|---|
| `MCP_ITSI_SERVER_HOST` / `MCP_ITSI_SERVER_PORT` | `0.0.0.0` / `8004` | Standalone process bind. |
| `MCP_ITSI_TRANSPORT` | `http` | Standalone process. |
| `MCP_STATELESS_HTTP` | `true` | Both modes — disables sticky sessions. |
| `MCP_JSON_RESPONSE` | `true` | Both modes — JSON over SSE. |
| `MCP_ITSI_LOG_LEVEL` | `INFO` | Standalone process. |
| `MCP_AUTH_DISABLED` | `false` | Allows `Authorization: Bearer` fallback. |
| `MCP_DISABLE_PLUGINS` | `false` | Plugin mode kill-switch (set on the parent server). |

### Splunk credentials (env defaults)

Header values from the AI client always win. The env vars below are used only when the client omits the corresponding header.

```env
SPLUNK_HOST=...
SPLUNK_PORT=8089
SPLUNK_SCHEME=https
SPLUNK_VERIFY_SSL=true
SPLUNK_USERNAME=...
SPLUNK_PASSWORD=...
SPLUNK_TOKEN=...                  # bearer token (preferred)
MCP_SPLUNK_TOKEN=...              # alias, accepted for parity with parent
SPLUNK_SESSION_TOKEN=...          # pre-existing splunkd session token
MCP_SPLUNK_SESSION_TOKEN=...
```

### ITSI namespace (env defaults)

```env
ITSI_APP=SA-ITOA
ITSI_USER_NS=nobody
ITSI_API_VERSION=vLatest
ITSI_REQUEST_TIMEOUT=30
```

Per-request `X-ITSI-App` / `X-ITSI-User-NS` / `X-ITSI-API-Version` headers override these for a single call.

## Operations

### Health check

The container ships a `HEALTHCHECK` (`curl http://127.0.0.1:8001/mcp/`). Compose surfaces it via `docker compose ps`:

```bash
docker compose ps mcp-itsi
# NAME       SERVICE    STATUS               PORTS
# mcp-itsi   mcp-itsi   Up X minutes (healthy)
```

For the local Python process, hit `/mcp/` yourself:

```bash
curl --fail http://127.0.0.1:8004/mcp/ -H 'Accept: application/json'
```

### Logging

Both modes use Python's stdlib logging. In Docker:

```bash
docker logs --follow mcp-itsi
```

Set verbosity per-process via `MCP_ITSI_LOG_LEVEL=DEBUG` (falls back to `MCP_LOG_LEVEL`). The plugin uses the parent server's logger configuration.

### Scaling

- **Plugin**: scales with the parent server. Run multiple `mcp-server` replicas behind Traefik with sticky sessions, or with `MCP_STATELESS_HTTP=true` for round-robin.
- **Standalone**: scale `mcp-itsi` independently. Each instance is stateless once `MCP_STATELESS_HTTP=true`. Per-request credentials make this safe — the server holds no Splunk session state across requests.

### Resource footprint

- **Container**: ~100 MB image, ~80 MB RSS at idle, single httpx async loop. ITSI calls are I/O-bound on splunkd.
- **Local Python**: same RSS minus the slim base image overhead.

### Security

- The standalone container runs as a non-root `mcp` user (uid `1001`).
- TLS termination is delegated to your reverse proxy (Traefik / NGINX / ingress). The image itself listens on plain HTTP.
- Credential precedence is bearer → session → basic; configure your clients to send a token unless you have a strong reason for password auth.
- `MCP_AUTH_DISABLED` should never be `true` in production unless you understand that it allows clients to send Splunk tokens via `Authorization: Bearer` — see [`src/core/utils.py`](../../../src/core/utils.py).
- Tokens are redacted in logs; the server never prints credential headers (the `Clear-text logging of sensitive information` CodeQL findings on the test scripts have been remediated).

## Verification

```bash
ITSI_HOST=<host> ITSI_USERNAME=<user> ITSI_PASSWORD=<pass> \
ITSI_VERIFY_SSL=false \
uv run python scripts/test_itsi_mcp_both_modes.py
```

This script:

1. Boots a standalone `mcp-itsi-server`, runs `test_itsi_mcp.py`, `test_itsi_mcp_deep.py`, `test_itsi_mcp_crud.py` against it, and tears it down.
2. Boots the parent `mcp-server` with the ITSI plugin loaded and re-runs the suites plus `test_itsi_plugin_isolation.py`.
3. Reports total failures across both modes — should be `0`.

## Migration patterns

| Coming from | Recommended path |
|---|---|
| Already running the parent `mcp-for-splunk` | Run `uv sync` to install `mcp_itsi`; the plugin auto-registers. No URL or auth changes. |
| Running ITSI behind its own ALB/ingress | Use the standalone Docker image and route `/itsi/mcp/` (or any path you choose) to it. |
| Plugin → standalone | Set `MCP_DISABLE_PLUGINS=true` on the parent, deploy `mcp-itsi` separately, point any AI client config that needs ITSI at the new URL. |
| Standalone → plugin | Add `mcp_itsi` to the parent's environment (`uv sync`), unset `MCP_DISABLE_PLUGINS`, and decommission the standalone container. AI clients can keep talking to the parent URL. |

## Releases & PyPI

`mcp-itsi-server` ships as its own PyPI distribution, separate from `mcp-server-for-splunk`:

- **Source root**: `packaging/mcp-itsi-server/` (uv workspace member; the actual code is under `mcp_itsi/`).
- **Versioning**: managed by [release-please](https://github.com/googleapis/release-please) with its own changelog (`packaging/mcp-itsi-server/CHANGELOG.md`) and tag prefix `mcp-itsi-server-v*.*.*`. The parent server keeps its own `v*.*.*` tag scheme.
- **GitHub workflow**: [`.github/workflows/release.yml`](../../../.github/workflows/release.yml) builds and publishes either or both packages depending on which tag fires; release-please dispatches per-package builds via `workflow_call`.
- **PyPI auth**: the workflow prefers a project-scoped `PYPI_ITSI_API_TOKEN` secret if set, falls back to the existing `PYPI_API_TOKEN`, and uses [trusted publishing](https://docs.pypi.org/trusted-publishers/) via GitHub OIDC when neither is configured. To switch to trusted publishing for `mcp-itsi-server`, configure a *pending publisher* on PyPI for this repo + workflow file, then unset the token secret.

End-user install paths (PyPI):

```bash
pip install mcp-itsi-server                 # standalone
pip install "mcp-server-for-splunk[itsi]"   # parent + ITSI plugin
```

## Related

- [Getting Started](getting-started.md) — first 15 minutes against a real cluster.
- [Package README](../../../mcp_itsi/README.md) — tool catalog and architecture.
- [ITSI MCP overview](../itsi_mcp.md) — short hub page in the wider docs.
- [Service-creation review](../itsi_service_creation_review.md) — what works, what doesn’t, and the documented workarounds.
- [Parent deployment guide](../deployment/) — Docker, production, and security patterns shared with `mcp-for-splunk`.
