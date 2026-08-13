# HTTP Client Connection Modes

Connect an MCP client to Streamable HTTP (`/mcp`) in either **sessionless**
(default) or **session-scoped** mode. Both modes send Splunk credentials on
each request via `X-Splunk-*` headers. The difference is whether you pin a
stable session key for config caching and sticky routing.

## Choose a mode

| Mode | Server defaults | Client session headers | Best for |
|------|-----------------|------------------------|----------|
| **Sessionless** | `MCP_STATELESS_HTTP=true`, `MCP_JSON_RESPONSE=true` | Omit `X-Session-ID` / `MCP-Session-ID` | Official MCP clients, load-balanced replicas, bearer-token multi-tenant |
| **Session-scoped** | Works with defaults; sticky LB optional when `MCP_STATELESS_HTTP=false` | Send a stable `X-Session-ID` (or honor `MCP-Session-ID`) | Long-lived IDE sessions, password auth that needs a cache key, sticky Traefik |

Use a real MCP client library (FastMCP Client, Cursor, Claude Desktop, MCP
Inspector). Prefer bearer tokens (`X-Splunk-Token`) over passwords for HTTP.

## Discover session mode (Deslicer AI and other clients)

Do **not** infer sessionless from package version alone. Published **0.6.8** is
handshake-era; unreleased main also reported 0.6.8 after FastMCP 4.

Probe `GET /health` on the same origin as `/mcp` (strip a trailing `/mcp`).
Read the explicit flag, then fall back to session-scoped if anything is missing.

```http
GET /health HTTP/1.1
```

```json
{
  "status": "healthy",
  "server": {
    "name": "MCP Server for Splunk",
    "version": "0.6.9",
    "session_mode": "sessionless"
  },
  "http": {
    "stateless": true,
    "json_response": true,
    "session_mode": "sessionless",
    "client_api": 1
  }
}
```

Response headers (also present on `/mcp`):

```http
X-MCP-Server-Version: 0.6.9
X-MCP-Session-Mode: sessionless
```

Client rule:

1. If `http.session_mode` or `X-MCP-Session-Mode` is `sessionless`, omit session ids.
2. If the value is `session` (operator set `MCP_STATELESS_HTTP=false`), send a stable `X-Session-ID`.
3. If `/health` has no `http` block (older images), send a session id.
4. If `/health` is unreachable, try sessionless first; on `Missing session ID`, retry with a session id.

The MCP resource `info://server` carries the same `version` and `session_mode`
after the client has already connected. Use `/health` to choose the mode
**before** `initialize`.

## Sessionless mode (default)

Local and Docker runs enable sessionless HTTP by default. The server does not
require sticky sessions. Send Splunk headers on every request; omit session ids.

### Server

```bash
export MCP_STATELESS_HTTP=true
export MCP_JSON_RESPONSE=true
export MCP_AUTH_DISABLED=true   # only for local/dev without MCP auth
```

Endpoint: `http://localhost:8003/mcp` (or your Traefik URL).

### Client headers (bearer token)

```http
X-Splunk-Host: splunk.example.com
X-Splunk-Port: 8089
X-Splunk-Scheme: https
X-Splunk-Verify-SSL: true
X-Splunk-Token: <splunk-access-token>
```

Do **not** send `X-Session-ID` or `MCP-Session-ID` unless you want session-scoped
caching. Password-only callers without a session id are not identity-cached;
send a token or an `X-Session-ID` if you need cross-request config reuse.

### FastMCP Client (Python)

```python
from fastmcp import Client
from fastmcp.client.transports import StreamableHttpTransport

headers = {
    "X-Splunk-Host": "splunk.example.com",
    "X-Splunk-Port": "8089",
    "X-Splunk-Scheme": "https",
    "X-Splunk-Verify-SSL": "true",
    "X-Splunk-Token": "<splunk-access-token>",
}

transport = StreamableHttpTransport("http://localhost:8003/mcp", headers=headers)
async with Client(transport) as client:
    tools = await client.list_tools()
    health = await client.call_tool("get_splunk_health", {})
```

### Cursor / Claude Desktop

```json
{
  "mcpServers": {
    "splunk-sessionless": {
      "url": "http://localhost:8003/mcp/",
      "headers": {
        "X-Splunk-Host": "splunk.example.com",
        "X-Splunk-Port": "8089",
        "X-Splunk-Scheme": "https",
        "X-Splunk-Verify-SSL": "true",
        "X-Splunk-Token": "<splunk-access-token>"
      }
    }
  }
}
```

### Live probe

```bash
export MCP_URL=http://127.0.0.1:8014/mcp
export SPLUNK_HOST=splunk.example.com
export SPLUNK_TOKEN=<splunk-access-token>
uv run python scripts/test_sessionless_http.py
```

## Session-scoped mode

Send a stable client session key so the server can cache per-client Splunk
config across requests. Prefer `X-Session-ID`. Legacy handshake-era clients may
send `MCP-Session-ID`; the server honors it when `X-Session-ID` is absent.

### When to use a session id

- Username/password auth over HTTP (identity cache skips password-only keys)
- IDE sessions that should keep one Splunk config for the whole conversation
- Deployments that set `MCP_STATELESS_HTTP=false` and rely on sticky sessions

### Client headers (session + basic auth)

```http
X-Session-ID: ide-session-abc123
X-Splunk-Host: splunk.example.com
X-Splunk-Port: 8089
X-Splunk-Username: analyst
X-Splunk-Password: <password>
X-Splunk-Scheme: https
X-Splunk-Verify-SSL: true
```

### Client headers (session + bearer token)

```http
X-Session-ID: ide-session-abc123
X-Splunk-Host: splunk.example.com
X-Splunk-Port: 8089
X-Splunk-Token: <splunk-access-token>
X-Splunk-Scheme: https
X-Splunk-Verify-SSL: true
```

### FastMCP Client (Python)

```python
from fastmcp import Client
from fastmcp.client.transports import StreamableHttpTransport

headers = {
    "X-Session-ID": "ide-session-abc123",
    "X-Splunk-Host": "splunk.example.com",
    "X-Splunk-Port": "8089",
    "X-Splunk-Username": "analyst",
    "X-Splunk-Password": "<password>",
    "X-Splunk-Scheme": "https",
    "X-Splunk-Verify-SSL": "true",
}

transport = StreamableHttpTransport("http://localhost:8003/mcp", headers=headers)
async with Client(transport) as client:
    await client.call_tool("list_indexes", {})
```

### Cursor / Claude Desktop

```json
{
  "mcpServers": {
    "splunk-session": {
      "url": "http://localhost:8003/mcp/",
      "headers": {
        "X-Session-ID": "cursor-session-1",
        "X-Splunk-Host": "splunk.example.com",
        "X-Splunk-Port": "8089",
        "X-Splunk-Username": "analyst",
        "X-Splunk-Password": "<password>",
        "X-Splunk-Scheme": "https",
        "X-Splunk-Verify-SSL": "true"
      }
    }
  }
}
```

## How the server picks a cache key

Priority for client-config caching:

1. `X-Session-ID`
2. `MCP-Session-ID` (header or protocol session)
3. Identity fingerprint from host + bearer/session token (not password)
4. No cache — each request must carry full Splunk headers

Logs show keys like `cfg_<hash>` for token fingerprints, or your
`X-Session-ID` value when present.

## Required Accept header

Streamable HTTP clients must accept both JSON and SSE:

```http
Accept: application/json, text/event-stream
```

FastMCP Client sets this for you. Raw `curl` must include it.

## Troubleshooting

| Symptom | Likely cause | Fix |
|---------|--------------|-----|
| `Missing session ID` | Stateful transport / raw HTTP without protocol handshake | Use FastMCP Client; or enable `MCP_STATELESS_HTTP=true` |
| Splunk disconnected / wrong host | Headers missing or overridden by server `.env` | Send `X-Splunk-Host` + token/password on every request |
| Password auth flaky without session | Password-only identity is not cached | Add `X-Session-ID` or switch to `X-Splunk-Token` |
| Tools differ per client | `X-MCP-Toolsets` or `MCP_DEFAULT_TOOLSETS` | See [Client Configuration](client_configuration.md#selecting-toolsets-x-mcp-toolsets) |

## Related

- [Client Configuration](client_configuration.md) — full header and env matrix
- [Session Management notes](../../SESSION_MANAGEMENT.md) — protocol handshake tips
- [ITSI Getting Started](../itsi/getting-started.md) — same header conventions for ITSI
