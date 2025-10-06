# MCP Server Header Configuration Issue - Troubleshooting Guide

## Problem Summary

Clients were passing Splunk configuration via HTTP headers (e.g., `X-Splunk-Host`, `X-Splunk-Username`, etc.), but these headers were not being properly applied when tools executed. The configuration was being captured by middleware but not accessible to the tools.

## Root Cause Analysis

### Issue 1: Incorrect FastMCP Context Access Pattern

**Problem**: The code was trying to access HTTP request data through `ctx.request_context.request.state`, which is not the recommended FastMCP pattern.

**FastMCP Best Practice**: According to the [FastMCP documentation](https://gofastmcp.com/servers/context#http-requests), you should use **runtime dependency functions** to access HTTP request data:

```python
from fastmcp.server.dependencies import get_http_request, get_http_headers

# Get the HTTP request
request = get_http_request()

# Get headers (safer, returns empty dict if no request context)
headers = get_http_headers(include_all=True)
```

**Why This Matters**: These dependency functions work anywhere within a request's execution flow, not just within your MCP function. They handle the context properly and provide safe fallbacks.

### Issue 2: Session ID Not Being Captured

**Problem**: Logs showed `session_id=None` in the middleware, indicating the context state wasn't being properly associated with sessions.

**Impact**: Without a proper session ID, the middleware couldn't cache configurations per-session, and the context state wasn't being set correctly.

## The Fix

### Changes to `src/core/base.py`

Updated `get_client_config_from_context()` method to use FastMCP runtime dependencies:

```python
# Priority 2: HTTP headers (using FastMCP runtime dependencies)
try:
    from fastmcp.server.dependencies import get_http_headers
    
    headers = get_http_headers(include_all=True)
    if headers:
        self.logger.debug("Attempting to extract config from HTTP headers (available: %s)", list(headers.keys()))
        
        # Extract Splunk configuration from headers
        from src.server import extract_client_config_from_headers
        client_config = extract_client_config_from_headers(headers)
        
        if client_config:
            self.logger.info("Using client config from HTTP headers (keys=%s)", list(client_config.keys()))
            return client_config
except Exception as e:
    self.logger.debug("Failed to get client config from HTTP headers: %s", e)
```

**Key Improvements**:

1. Uses `get_http_headers()` runtime dependency function
2. Includes all headers with `include_all=True`
3. Better error logging with debug messages
4. Shows which config keys were extracted

### Changes to `src/server.py`

Enhanced logging in `ClientConfigMiddleware` to help debug header extraction:

```python
# Better logging when headers are captured
logger.debug("ClientConfigMiddleware: http_headers_context contains %d headers", len(headers))

# Better logging when config is written to context state
logger.info(
    "ClientConfigMiddleware: wrote client_config to context state (keys=%s, session=%s, config=%s)",
    list(client_config.keys()),
    effective_session,
    {k: v if k not in ["splunk_password"] else "***" for k, v in client_config.items()},
)

# Warning when context is not available
elif client_config:
    logger.warning(
        "ClientConfigMiddleware: client_config extracted but context.fastmcp_context not available"
    )
```

## How Configuration Priority Works

The system checks for Splunk configuration in this order:

1. **Context State** (highest priority) - Set by middleware per request
2. **HTTP Headers** - Using FastMCP runtime dependencies
3. **Lifespan Context** - Server environment variables

## Expected Header Format

Clients should send headers with the `X-Splunk-` prefix:

```
X-Splunk-Host: splunk.example.com
X-Splunk-Port: 8089
X-Splunk-Username: admin
X-Splunk-Password: changeme
X-Splunk-Scheme: https
X-Splunk-Verify-SSL: true
X-Session-ID: unique-session-identifier
```

## Debugging Tips

### Enable Debug Logging

Set the log level to DEBUG to see detailed header extraction:

```bash
export MCP_LOG_LEVEL=DEBUG
```

### Check Logs for These Messages

**When headers are captured correctly**:

```
ClientConfigMiddleware: http_headers_context contains 7 headers
ClientConfigMiddleware: extracted client_config from headers (keys=['splunk_host', 'splunk_port', ...])
ClientConfigMiddleware: wrote client_config to context state (keys=['splunk_host', ...], session=abc123)
```

**In tools when config is used**:

```
Using client config from context state (keys=['splunk_host', 'splunk_port', ...])
```

**Or as fallback**:

```
Using client config from HTTP headers (keys=['splunk_host', 'splunk_port', ...])
```

### Verify Headers Are Being Sent

Check the `HeaderCaptureMiddleware` logs:

```
HeaderCaptureMiddleware: Processing request to /mcp
Captured headers: ['x-splunk-host', 'x-splunk-port', ...]
Captured Splunk headers: ['x-splunk-host', 'x-splunk-port', ...]
```

## Testing the Fix

### Test with curl

```bash
curl -X POST http://localhost:8001/mcp \
  -H "Content-Type: application/json" \
  -H "X-Splunk-Host: localhost" \
  -H "X-Splunk-Port: 8089" \
  -H "X-Splunk-Username: admin" \
  -H "X-Splunk-Password: changeme" \
  -H "X-Session-ID: test-session-123" \
  -d '{
    "jsonrpc": "2.0",
    "method": "tools/call",
    "params": {
      "name": "get_splunk_health"
    },
    "id": 1
  }'
```

### Expected Behavior

1. Headers should be captured by `HeaderCaptureMiddleware`
2. Middleware should extract Splunk config and store in context state
3. Tools should retrieve config from context state (Priority 1)
4. If context state fails, tools should fall back to HTTP headers using `get_http_headers()` (Priority 2)
5. Logs should show which configuration source was used

## References

- [FastMCP Context Documentation](https://gofastmcp.com/servers/context)
- [FastMCP HTTP Requests](https://gofastmcp.com/servers/context#http-requests)
- [FastMCP Runtime Dependencies](https://gofastmcp.com/servers/context#runtime-dependencies)

## Files Modified

1. `src/core/base.py` - Updated `get_client_config_from_context()` to use FastMCP runtime dependencies
2. `src/server.py` - Enhanced logging in `ClientConfigMiddleware` for better debugging

## Additional Issue: 400 Bad Request Error

### Problem

Getting `400 Bad Request` errors when clients try to connect to the MCP server.

### Root Cause

The server was incorrectly mounting the MCP app. The original code was:

```python
mcp_app = mcp.http_app(path="/", transport="http")
root_app.mount("/mcp", mcp_app)
```

This created a path conflict where the MCP protocol endpoint wasn't properly accessible.

### Fix

According to the [FastMCP server documentation](https://gofastmcp.com/servers/server), when using `http_app()` with a custom Starlette setup, you should specify the path in the `http_app()` call and mount at root:

```python
# Build the MCP Starlette app with the /mcp path
mcp_app = mcp.http_app(path="/mcp", transport="http")

# Mount at root since the app already includes /mcp in its path
root_app.mount("/", mcp_app)
```

### Alternative: Use FastMCP's Built-in Server

For simpler setups without custom middleware, you can use FastMCP's built-in server:

```python
# In your __main__ block
mcp.run(transport="http", host="0.0.0.0", port=8001)
```

However, since you need the `HeaderCaptureMiddleware` for extracting Splunk headers, the custom uvicorn setup is necessary.

## Additional Issue: Missing job_search.py File

### Problem

After reverting changes, the `src/tools/search/job_search.py` file was accidentally deleted, causing all tools to fail loading. The server would start but no tools would be available except those defined directly in `server.py`.

### Root Cause

During the `git reset --hard HEAD` command, the `job_search.py` file was deleted but not restored from the repository. This caused an import error when the discovery system tried to load tools from `src.tools.search`.

### Fix

Restored the missing file from the main branch:
```bash
git checkout main -- src/tools/search/job_search.py
```

### Symptoms

- MCP server starts successfully
- Only tools defined in `server.py` (like `user_agent_info`) are available
- No tools from `src/tools/` directories are loaded
- No error messages in logs about tool loading failures

## Next Steps

1. Restart the MCP server to apply changes
2. Test with a client that sends Splunk headers
3. Monitor logs to verify headers are being captured and applied
4. Verify all tools are loaded correctly (should see ~40+ tools)
5. If issues persist, check that `X-Session-ID` header is being sent for proper session tracking
5. Verify the client is connecting to the correct endpoint: `http://localhost:8001/mcp`
