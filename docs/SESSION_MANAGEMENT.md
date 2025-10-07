# MCP Session Management in HTTP Mode

## The Problem: "Missing session ID"

When using raw HTTP requests (like `httpx`) to test the MCP server, you may encounter:

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

## Root Cause

FastMCP's **Streamable HTTP transport** creates a **new session for every HTTP POST request**. This is by design - Streamable HTTP expects clients to maintain session continuity through:

1. **Server-Sent Events (SSE)** for server-to-client messages
2. **Session ID tracking** across requests
3. **Proper MCP protocol handshake**

### What's Happening

Looking at the server logs:

```
2025-10-07 08:30:16,562 - mcp.server.streamable_http_manager - INFO - Created new transport with session ID: 6a858eb454824565a92e84389decfe21
2025-10-07 08:30:16,567 - mcp.server.streamable_http_manager - INFO - Created new transport with session ID: 25b4fdbe7f754f5aa1c48019796571ea
2025-10-07 08:30:16,570 - mcp.server.streamable_http_manager - INFO - Created new transport with session ID: 561320c6862f4f1e9ffdf43fc24790b5
```

Each request creates a **new session**, so:
- Request 1: `initialize` → Session A
- Request 2: `notifications/initialized` → Session B ❌ (new session!)
- Request 3: `tools/call` → Session C ❌ (new session!)

The tool call in Session C fails because it was never initialized.

## Why `user_agent_info` Works but `list_indexes` Doesn't

### `user_agent_info` (Simple Function Tool)
```python
@mcp.tool
async def user_agent_info(ctx: Context) -> dict:
    """Simple tool defined directly in server.py"""
    # Doesn't require session state
    # Works even without proper initialization
```

**Works because**: It's a simple function tool that doesn't depend on session-specific state.

### `list_indexes` (Class-Based Tool)
```python
class ListIndexes(BaseTool):
    async def execute(self, ctx: Context) -> dict[str, Any]:
        # Requires proper MCP context initialization
        # Needs session state for client config
        service = await self.get_splunk_service(ctx)
```

**Fails because**: It's a class-based tool loaded via the component loader that requires:
- Proper session initialization
- Access to session-specific client configuration
- Full MCP context with state management

## Solutions

### ✅ Solution 1: Use FastMCP Client (Recommended)

The **FastMCP Client** properly handles session management:

```python
from fastmcp import Client

headers = {
    "X-Splunk-Host": "localhost",
    "X-Splunk-Port": "8089",
    "X-Splunk-Username": "admin",
    "X-Splunk-Password": "changeme",
    "X-Session-ID": "my-session-123",
}

async with Client(
    transport="http://localhost:8003/mcp",
    headers=headers
) as client:
    # Client handles session initialization automatically
    tools = await client.list_tools()
    result = await client.call_tool("list_indexes", {})
```

**Advantages**:
- Automatic session management
- Proper MCP protocol handshake
- SSE connection handling
- Session ID tracking

**Example**: See `scripts/test_mcp_simple.py`

### ❌ Solution 2: Raw HTTP (Not Recommended)

If you must use raw HTTP requests, you need to:

1. **Extract session ID from `initialize` response**
2. **Include it in subsequent requests** (implementation-specific)
3. **Maintain SSE connection** for server messages

This is **complex and error-prone**. The MCP protocol is designed to work with proper clients, not raw HTTP.

## Best Practices

### For Testing

✅ **DO**: Use the FastMCP Client
```bash
python scripts/test_mcp_simple.py
```

❌ **DON'T**: Use raw HTTP requests for MCP testing
```bash
# This approach has session management issues
python scripts/test_mcp_with_headers.py
```

### For Production Clients

1. **Use official MCP client libraries**:
   - Python: `fastmcp`
   - TypeScript: `@modelcontextprotocol/sdk`
   - Other languages: Check MCP documentation

2. **Let the client handle**:
   - Session initialization
   - Session ID tracking
   - SSE connection management
   - Protocol handshake

3. **Focus on your logic**:
   - Provide configuration via headers
   - Call tools with proper parameters
   - Handle tool responses

## Architecture

### HTTP Header-Based Configuration

Our server supports **per-client configuration** via HTTP headers:

```
X-Splunk-Host: splunk.example.com
X-Splunk-Port: 8089
X-Splunk-Username: user123
X-Splunk-Password: secret
X-Splunk-Scheme: https
X-Splunk-Verify-SSL: false
X-Session-ID: client-session-abc
```

### How It Works

1. **HeaderCaptureMiddleware** (ASGI layer):
   - Captures HTTP headers from incoming requests
   - Stores them in `http_headers_context` (ContextVar)
   - Caches config per `X-Session-ID`

2. **ClientConfigMiddleware** (MCP layer):
   - Extracts Splunk config from headers
   - Writes to MCP context state
   - Makes config available to tools

3. **BaseTool.get_splunk_service()**:
   - Retrieves client config from context
   - Creates Splunk connection with client credentials
   - Falls back to server default if no client config

### Session Management Flow

```
Client Request (with headers)
    ↓
HeaderCaptureMiddleware
    ↓ (stores headers in ContextVar)
ClientConfigMiddleware
    ↓ (extracts config, caches by session ID)
MCP Context State
    ↓ (config available to tools)
Tool Execution
    ↓ (uses client-specific Splunk connection)
Response
```

## Troubleshooting

### Error: "Missing session ID"

**Cause**: Tool called without proper session initialization

**Fix**: Use FastMCP Client instead of raw HTTP requests

### Error: "Splunk connection not available"

**Cause**: No Splunk credentials provided (headers or env vars)

**Fix**: 
1. Set `X-Splunk-*` headers in your client
2. Or set `SPLUNK_*` environment variables on the server

### Tools work in Test 1 but fail in Test 4

**Cause**: Test 1 uses `user_agent_info` (simple tool), Test 4 uses `list_indexes` (requires session)

**Fix**: Use FastMCP Client for all tests

## References

- FastMCP Documentation: https://gofastmcp.com
- MCP Protocol Specification: https://modelcontextprotocol.io
- Streamable HTTP Transport: https://gofastmcp.com/servers/transports#http

## Examples

### Working Example (FastMCP Client)
```python
# scripts/test_mcp_simple.py
async with Client(
    transport="http://localhost:8003/mcp",
    headers={"X-Splunk-Host": "localhost", ...}
) as client:
    result = await client.call_tool("list_indexes", {})
    # ✅ Works perfectly!
```

### Broken Example (Raw HTTP)
```python
# scripts/test_mcp_with_headers.py (has session issues)
async with httpx.AsyncClient(headers={...}) as http_client:
    # Request 1: initialize
    await http_client.post(url, json=init_request)
    # Request 2: notifications/initialized (NEW SESSION!)
    await http_client.post(url, json=initialized_notification)
    # Request 3: tools/call (ANOTHER NEW SESSION!)
    await http_client.post(url, json=tool_call_request)
    # ❌ Fails with "Missing session ID"
```

## Conclusion

The **"Missing session ID"** error is **not a bug in our code** - it's a **protocol requirement** of FastMCP's Streamable HTTP transport.

**Solution**: Use the **FastMCP Client** which properly handles session management, or implement full Streamable HTTP protocol support in your custom client.

For testing MCP servers, **always use official MCP client libraries** rather than raw HTTP requests.
