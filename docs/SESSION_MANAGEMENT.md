# MCP Session Management in HTTP Mode

Streamable HTTP supports two client styles with this server:

1. **Sessionless** (default) — `MCP_STATELESS_HTTP=true`; no sticky session
   required; send `X-Splunk-*` on each request.
2. **Session-scoped** — send a stable `X-Session-ID` (or legacy
   `MCP-Session-ID`) so Splunk config can be cached across requests.

For copy-paste client configs, see
**[HTTP Client Connection Modes](guides/configuration/http-client-modes.md)**.

## Prefer a real MCP client

Use FastMCP Client, Cursor, Claude Desktop, or MCP Inspector. They perform the
protocol handshake correctly. Raw `httpx`/`curl` loops that POST `initialize`
and `tools/call` on separate connections often fail with:

```json
{
  "jsonrpc": "2.0",
  "id": "server-error",
  "error": {
    "code": -32600,
    "message": "Bad Request: Missing session ID"
  }
}
```

That error means the transport expected a handshake-era session that your raw
client did not continue. Fixes:

- Use FastMCP Client (recommended)
- Or run the server with `MCP_STATELESS_HTTP=true` (default) and still use a
  proper MCP client for the initialize handshake within one connection

## Sessionless vs session-scoped (quick)

### Sessionless

```python
from fastmcp import Client
from fastmcp.client.transports import StreamableHttpTransport

headers = {
    "X-Splunk-Host": "splunk.example.com",
    "X-Splunk-Port": "8089",
    "X-Splunk-Token": "<token>",
    "X-Splunk-Scheme": "https",
    "X-Splunk-Verify-SSL": "true",
}
# No X-Session-ID / MCP-Session-ID
transport = StreamableHttpTransport("http://localhost:8003/mcp", headers=headers)
async with Client(transport) as client:
    await client.call_tool("get_splunk_health", {})
```

### Session-scoped

```python
headers = {
    "X-Session-ID": "my-session-123",
    "X-Splunk-Host": "splunk.example.com",
    "X-Splunk-Port": "8089",
    "X-Splunk-Username": "admin",
    "X-Splunk-Password": "changeme",
    "X-Splunk-Scheme": "https",
    "X-Splunk-Verify-SSL": "false",
}
transport = StreamableHttpTransport("http://localhost:8003/mcp", headers=headers)
async with Client(transport) as client:
    await client.call_tool("list_indexes", {})
```

## How config caching works

1. **HeaderCaptureMiddleware** captures `X-Splunk-*` headers.
2. **ClientConfigMiddleware** resolves a cache key:
   `X-Session-ID` → `MCP-Session-ID` → bearer/session-token fingerprint → none.
3. Tools read the per-request client config (or cache) and open Splunk.

Password-only requests without a session id are not identity-cached. Use a
token or send `X-Session-ID`.

## Troubleshooting

| Error | Fix |
|-------|-----|
| Missing session ID | Use FastMCP Client; confirm `MCP_STATELESS_HTTP=true` for LB setups |
| Splunk connection not available | Send `X-Splunk-*` headers or set server `SPLUNK_*` defaults |
| Config bleeds across clients | Give each client a unique `X-Session-ID`, or use distinct tokens |

## Examples

- Sessionless token probe: `scripts/test_sessionless_http.py`
- Header smoke tests: `scripts/test_mcp_simple.py`, `scripts/test_mcp_with_headers.py`

## References

- [HTTP Client Connection Modes](guides/configuration/http-client-modes.md)
- [Client Configuration](guides/configuration/client_configuration.md)
- [FastMCP HTTP docs](https://gofastmcp.com)
- [MCP specification](https://modelcontextprotocol.io)
