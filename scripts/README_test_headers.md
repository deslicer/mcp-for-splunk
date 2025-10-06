# MCP Server HTTP Header Authentication Testing

This directory contains a comprehensive test script for validating the MCP server's HTTP header-based authentication system.

## Test Script: `test_mcp_with_headers.py`

Tests the MCP server's ability to accept Splunk connection parameters via HTTP headers instead of environment variables, enabling multiple clients to connect to different Splunk instances simultaneously.

## Quick Start

**Prerequisites:**

```bash
pip install httpx fastmcp
```

**Set Splunk credentials** (or defaults will be used):

```bash
export SPLUNK_HOST=localhost
export SPLUNK_PORT=8089
export SPLUNK_USERNAME=admin
export SPLUNK_PASSWORD=your_password
export SPLUNK_VERIFY_SSL=false
```

**Run tests:**

```bash
python scripts/test_mcp_with_headers.py
```

## What Gets Tested

### Test 1: Basic Connection (Environment Variables)

- Starts MCP server on port 8005
- Connects using FastMCP client
- Lists available tools
- Executes `user_agent_info` tool
- **Validates:** Server starts correctly and basic tools work

### Test 2: Connection with Splunk Headers

- Sends Splunk configuration via HTTP headers:
  - `X-Splunk-Host`
  - `X-Splunk-Port`
  - `X-Splunk-Username`
  - `X-Splunk-Password`
  - `X-Splunk-Scheme`
  - `X-Splunk-Verify-SSL`
  - `X-Session-ID`
- Initializes MCP session
- Lists available tools
- **Validates:** Headers are accepted and processed

### Test 3: Tool Execution with Headers

- Executes `get_splunk_health` tool using header credentials
- Verifies tool receives correct Splunk configuration
- Checks connection source in response
- **Validates:** Tools use header-provided credentials

### Test 4: List Indexes with Headers

- Executes `list_indexes` tool
- Verifies Splunk connection works with headers
- Lists available indexes
- **Validates:** Complex tools work with header auth

### Test 5: Multiple Concurrent Sessions

- Creates two simultaneous sessions with different session IDs
- Executes tools from both sessions
- Verifies session isolation
- **Validates:** Multiple clients can connect independently

## Expected Output

```
============================================================
  MCP Server for Splunk - HTTP Header Authentication Tests
============================================================

Checking Prerequisites
============================================================
✅ httpx library available
✅ fastmcp library available
✅ SPLUNK_HOST set to: localhost

Test 1: Basic Connection (Environment Variables)
============================================================
ℹ️  Starting MCP server on port 8005...
✅ MCP server started on http://localhost:8005/mcp/
✅ Connected successfully! Found 43 tools
ℹ️  Testing user_agent_info tool...
✅ user_agent_info tool works!

Test 2: Connection with Splunk Headers
============================================================
ℹ️  Using Splunk configuration:
  X-Splunk-Host: localhost
  X-Splunk-Port: 8089
  X-Splunk-Username: admin
  X-Splunk-Password: ********
ℹ️  Sending initialize request with headers...
✅ Initialize request successful!
ℹ️  Listing available tools...
✅ Found 43 tools!

[... additional tests ...]

Test Results Summary
============================================================
Basic Connection........................ ✅ PASSED
Connection with Headers................. ✅ PASSED
Tool Execution.......................... ✅ PASSED
List Indexes............................ ✅ PASSED
Multiple Sessions....................... ✅ PASSED

Total: 5/5 tests passed

🎉 ALL TESTS PASSED!
```

## HTTP Headers Reference

The MCP server accepts these Splunk configuration headers:

| Header | Description | Example | Required |
|--------|-------------|---------|----------|
| `Accept` | Content types accepted by client | `application/json, text/event-stream` | **Yes** |
| `X-Splunk-Host` | Splunk server hostname/IP | `localhost`, `splunk.example.com` | No |
| `X-Splunk-Port` | Splunk management port | `8089` | No |
| `X-Splunk-Username` | Splunk username | `admin` | No |
| `X-Splunk-Password` | Splunk password | `Chang3d!` | No |
| `X-Splunk-Scheme` | Connection scheme | `https`, `http` | No |
| `X-Splunk-Verify-SSL` | SSL verification | `true`, `false` | No |
| `X-Session-ID` | Client session identifier | `session-123` | No |

**Note:** The `Accept` header is required by the MCP protocol and must include both `application/json` and `text/event-stream` content types.

## Architecture

The test script validates this flow:

1. **Client** sends HTTP request with `X-Splunk-*` headers
2. **ClientConfigMiddleware** (in `server.py`) intercepts request
3. **Headers extracted** and stored in FastMCP context
4. **Tools** call `get_splunk_service(ctx)` to get configured client
5. **SplunkClient** created with header-provided credentials
6. **Tool executes** against the correct Splunk instance

## Troubleshooting

**Test fails with "httpx library not available":**

```bash
pip install httpx
```

**Test fails with "406 Not Acceptable" error:**

The MCP server requires clients to accept both `application/json` and `text/event-stream` content types. Ensure your client includes:
```
Accept: application/json, text/event-stream
```

**Test fails with connection errors:**

- Verify Splunk is running and accessible
- Check credentials are correct
- Ensure port 8005 is available
- Review logs at `logs/mcp_splunk_server.log`

**Test fails with "No tools found":**

- Check that `src/tools/` directory exists
- Verify all tool files are present
- Review server startup logs

**Multiple sessions test fails:**

- Ensure session IDs are unique
- Check that middleware is properly configured
- Verify context state is being maintained

## Integration with Clients

**Claude Desktop:**

```json
{
  "mcpServers": {
    "splunk": {
      "url": "http://localhost:8001/mcp",
      "headers": {
        "X-Splunk-Host": "splunk.example.com",
        "X-Splunk-Port": "8089",
        "X-Splunk-Username": "admin",
        "X-Splunk-Password": "your_password",
        "X-Splunk-Verify-SSL": "false",
        "X-Session-ID": "claude-session-1"
      }
    }
  }
}
```

**Python Client:**

```python
import httpx
import asyncio

async def test_with_headers():
    headers = {
        "Accept": "application/json, text/event-stream",  # Required by MCP protocol
        "X-Splunk-Host": "localhost",
        "X-Splunk-Port": "8089",
        "X-Splunk-Username": "admin",
        "X-Splunk-Password": "Chang3d!",
        "X-Splunk-Scheme": "https",
        "X-Splunk-Verify-SSL": "false",
        "X-Session-ID": "my-session"
    }
    
    async with httpx.AsyncClient(headers=headers) as client:
        response = await client.post(
            "http://localhost:8001/mcp",
            json={
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/call",
                "params": {
                    "name": "get_splunk_health",
                    "arguments": {}
                }
            }
        )
        print(response.json())

asyncio.run(test_with_headers())
```

## Related Files

- `src/server.py` - Contains `ClientConfigMiddleware`
- `src/core/base.py` - Contains `get_client_config_from_context()`
- `src/client/splunk_client.py` - Splunk SDK wrapper
- `bug.md` - Troubleshooting documentation

## Contributing

When adding new tests:

1. Follow the existing test pattern
2. Use descriptive test names
3. Include proper error handling
4. Add documentation to this README
5. Ensure tests clean up resources (server processes)
