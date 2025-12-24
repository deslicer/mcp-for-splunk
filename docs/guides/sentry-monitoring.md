# Sentry Monitoring for MCP Server

This guide explains how to set up and use Sentry monitoring for the MCP Server for Splunk. Sentry provides comprehensive error tracking, performance monitoring, and distributed tracing specifically optimized for MCP operations.

> **🔧 Sentry is Optional**: The MCP server works perfectly without Sentry. When `SENTRY_DSN` is not set or sentry-sdk is not installed, the server runs normally without any monitoring overhead.

## 🚀 Quick Start

### 1. Install Sentry SDK (Optional)

Sentry is an optional dependency. Install it with:

```bash
# If using pip
pip install mcp-server-for-splunk[sentry]

# Or install sentry-sdk directly
pip install sentry-sdk[starlette,httpx,asyncio]
```

> **Note**: The Docker image includes Sentry by default. For local development, you need to install it explicitly.

### 2. Get Your Sentry DSN

1. Create a Sentry account at [sentry.io](https://sentry.io)
2. Create a new Python project (select **ASGI** template for best results)
3. Copy your DSN from **Settings → Projects → [Your Project] → Client Keys (DSN)**

### 3. Configure Environment

Add to your `.env` file:

```bash
# Required: Your Sentry DSN
SENTRY_DSN=https://your-key@o123.ingest.sentry.io/project-id

# Recommended settings
SENTRY_ENVIRONMENT=development
SENTRY_RELEASE=mcp-server-splunk@0.4.0
SENTRY_TRACES_SAMPLE_RATE=1.0
```

### 4. Start the Server

```bash
# Docker (Sentry included automatically)
./scripts/build_and_run.sh --docker

# Local development (requires step 1)
uv run python src/server.py
```

You'll see in the logs:

```
INFO - Sentry initialized successfully (env=development, release=mcp-server-splunk@0.4.0, traces=100.0%)
INFO - Sentry MCP middleware added for request tracing
INFO - Sentry HTTP middleware added for request tracing
```

If Sentry is **not configured**, you'll see:

```
INFO - SENTRY_DSN not set, Sentry monitoring disabled
```

Or if the SDK is **not installed**:

```
INFO - sentry-sdk not installed - Sentry monitoring disabled
```

## 📊 What Gets Monitored

### Official Sentry MCP Integration

This server uses Sentry's official `MCPIntegration` which automatically captures:

- **Tool executions**: Tool name, arguments, results, and execution errors
- **Prompt requests**: Prompt name, arguments, message counts
- **Resource access**: Resource URI, protocol, access patterns
- **Request context**: Request IDs, session IDs, transport types (stdio/HTTP)
- **Execution spans**: Timing information for all handler invocations

### Automatic Instrumentation

The integration automatically monitors:

| Operation | Span Type | Attributes |
|-----------|-----------|------------|
| HTTP requests | `http.server` | method, path, status code, duration |
| Tool calls | `mcp.tool` | tool name, arguments, result status |
| Resource reads | `mcp.resource` | URI, content size |
| Prompt gets | `mcp.prompt` | name, arguments |
| Splunk API calls | `splunk.api` | operation, query preview, result count |

### MCP-Specific Attributes

Every span includes MCP context:

```python
{
    "mcp.session.id": "session_xyz789",
    "mcp.request.id": "req_abc123",
    "mcp.method.name": "tools/call",
    "mcp.tool.name": "splunk_search",
    "mcp.transport": "http"
}
```

## 🛠 Configuration Options

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `SENTRY_DSN` | Sentry project DSN (required to enable) | - |
| `SENTRY_ENVIRONMENT` | Environment name | `development` |
| `SENTRY_RELEASE` | Release/version identifier | `mcp-server-splunk@0.4.0` |
| `SENTRY_TRACES_SAMPLE_RATE` | Traces sampling rate (0.0-1.0) | `1.0` |
| `SENTRY_PROFILES_SAMPLE_RATE` | Profiling sampling rate (0.0-1.0) | `0.1` |
| `SENTRY_DEBUG` | Enable debug mode | `false` |
| `SENTRY_ENABLE_LOGS` | Enable Sentry Logs feature | `true` |
| `SENTRY_SEND_PII` | Include tool inputs/outputs in traces | `true` |

### Smart Sampling

The integration uses intelligent sampling:

- **MCP operations**: Always traced (100%)
- **Tool executions**: Always traced (100%)
- **Splunk operations**: Higher sampling rate (1.5x base rate)
- **Health checks**: Very low sampling (1%)

## 📝 Sentry Logs

The MCP server captures Python logs to Sentry's Logs feature, enabling centralized log search and analysis.

### How It Works

```python
import logging

# All your existing Python logging is captured automatically
logger = logging.getLogger(__name__)

# INFO+ logs → Sent to Sentry Logs (searchable/filterable)
logger.info("Tool executed", extra={"tool_name": "splunk_search", "duration_ms": 150})

# ERROR+ logs → Create error events AND sent to Sentry Logs
logger.error("Tool failed", extra={"tool_name": "splunk_search", "error": "timeout"})
```

### Log Levels

| Log Level | Sentry Logs | Error Events | Breadcrumbs |
|-----------|-------------|--------------|-------------|
| `DEBUG` | ❌ | ❌ | ❌ |
| `INFO` | ✅ | ❌ | ✅ |
| `WARNING` | ✅ | ❌ | ✅ |
| `ERROR` | ✅ | ✅ | ✅ |
| `CRITICAL` | ✅ | ✅ | ✅ |

### Searchable Attributes

Extra fields become searchable attributes in Sentry:

```python
logger.info("MCP tool call", extra={
    "mcp.tool.name": "splunk_search",
    "mcp.session.id": "session_123",
    "duration_ms": 250,
    "result_count": 100
})
```

Search in Sentry: `mcp.tool.name:splunk_search duration_ms:>200`

### Disable Logs

```bash
SENTRY_ENABLE_LOGS=false
```

## 📊 Session Tracking & Release Health

The MCP server automatically tracks sessions for Release Health monitoring.

### What's Tracked

- **Session per request**: Each MCP request creates a session
- **Session status**: `ok`, `crashed` (unhandled error), `errored` (captured exception)
- **Release association**: Sessions linked to `SENTRY_RELEASE` version

### Release Health Dashboard

View in Sentry at **Releases → [Your Release]**:

| Metric | Description |
|--------|-------------|
| **Crash Free Sessions** | Percentage of sessions without crashes |
| **Crash Free Users** | Percentage of users without crashes |
| **Adoption** | Rollout percentage of this release |
| **Sessions** | Total session count for this release |

### Example

```bash
# Set release version for tracking
SENTRY_RELEASE=mcp-server-splunk@0.4.1
```

Then in Sentry, you'll see:
- How many sessions for `v0.4.1`
- Crash rate comparison vs previous release
- Error trends per release

## 🔧 Custom Instrumentation

### Decorating Tool Functions

Use the `@trace_mcp_tool` decorator for automatic tool tracing:

```python
from src.core.sentry_integration import trace_mcp_tool

@trace_mcp_tool("my_custom_tool")
async def my_custom_tool(ctx: Context, param: str) -> dict:
    """This tool is automatically traced with Sentry spans."""
    result = await do_something(param)
    return {"status": "success", "data": result}
```

### Tracing Splunk Operations

Use `@trace_splunk_operation` for Splunk-specific operations:

```python
from src.core.sentry_integration import trace_splunk_operation

@trace_splunk_operation("search")
async def execute_search(query: str) -> dict:
    """Splunk search operations get specialized tracking."""
    results = await splunk_service.search(query)
    return results
```

### Manual Spans

Create custom spans for specific operations:

```python
from src.core.sentry_integration import mcp_span

async def complex_operation():
    with mcp_span(
        op="custom.operation",
        name="Process Data",
        step="validation",
        item_count=100
    ) as span:
        # Your operation here
        result = await process_data()
        
        # Add more context
        span.set_data("processed_count", len(result))
```

### Adding Breadcrumbs

Track the sequence of operations:

```python
from src.core.sentry_integration import add_breadcrumb

add_breadcrumb(
    message="User requested search",
    category="user.action",
    level="info",
    data={"query_type": "realtime", "index": "main"}
)
```

### Capturing Errors with Context

Manually capture exceptions with MCP context:

```python
from src.core.sentry_integration import capture_mcp_error

try:
    result = await risky_operation()
except Exception as e:
    capture_mcp_error(
        error=e,
        tool_name="risky_operation",
        extra={"retry_count": 3, "input_size": len(data)}
    )
    raise
```

## 📈 Viewing Data in Sentry

### Performance Dashboard

Navigate to **Performance** in Sentry to see:

- Transaction throughput
- Average response times
- Slowest operations
- Error rates by endpoint

### Trace View

Click any transaction to see:

- Full distributed trace
- Span waterfall with timing
- MCP-specific attributes
- Related errors

### Filtering by MCP Context

Use these search filters in Sentry:

```
# Find all tool calls
op:mcp.tool

# Find specific tool errors
mcp.tool.name:splunk_search mcp.tool.status:error

# Find session-specific issues
mcp.session.id:session_xyz789

# Find slow Splunk queries
op:splunk.api splunk.duration:>5000
```

## 🏗 Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        HTTP Request                              │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│  SentryHTTPMiddleware                                           │
│  • Creates transaction for HTTP request                         │
│  • Extracts session/request IDs                                 │
│  • Sets MCP context                                             │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│  SentryMCPMiddleware                                            │
│  • Creates spans for MCP methods                                │
│  • Captures tool/resource-specific data                         │
│  • Records method results                                       │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│  Tool Execution (with @trace_mcp_tool)                          │
│  • Individual tool spans                                        │
│  • Argument sanitization                                        │
│  • Result tracking                                              │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│  Splunk Operations (with @trace_splunk_operation)               │
│  • Query tracking                                               │
│  • Result count                                                 │
│  • Performance metrics                                          │
└─────────────────────────────────────────────────────────────────┘
```

## 🔒 Security Considerations

### Automatic Data Sanitization

The integration automatically:

- **Masks sensitive parameters**: Passwords, tokens, API keys
- **Truncates large values**: Queries > 200 chars shown as previews
- **Excludes content**: Only metadata tracked, not actual data

### PII Protection

By default:

```python
send_default_pii=False  # No automatic PII collection
```

Custom data you add should also be sanitized:

```python
from src.core.sentry_integration import _sanitize_kwargs

# Before logging parameters
safe_params = _sanitize_kwargs({"password": "secret", "query": "search *"})
# Result: {"password": "***REDACTED***", "query": "search *"}
```

## 🚨 Alerting

### Recommended Alerts

Set up alerts in Sentry for:

1. **Error spike**: More than 10 errors in 5 minutes
2. **Slow tools**: Tool execution > 10 seconds
3. **Splunk failures**: `splunk.status:error` rate > 5%
4. **Session issues**: Frequent session timeouts

### Example Alert Query

```
# Alert when Splunk searches are slow
transaction:splunk/* splunk.duration:>30000
```

## 🔍 Troubleshooting

### Sentry Not Initializing

Check logs for:

```
INFO - SENTRY_DSN not set, Sentry monitoring disabled
```

**Solution**: Ensure `SENTRY_DSN` is properly set in your environment.

### Traces Not Appearing

1. Check `SENTRY_TRACES_SAMPLE_RATE` is > 0
2. Verify network connectivity to Sentry
3. Enable debug mode: `SENTRY_DEBUG=true`

### Missing MCP Context

If session/request IDs are missing:

1. Ensure middleware order is correct (HeaderCapture before Sentry)
2. Check that clients send `MCP-Session-ID` or `X-Session-ID` headers

## 📚 Related Resources

- [Sentry Python SDK Docs](https://docs.sentry.io/platforms/python/)
- [Sentry MCP Instrumentation Guide](https://docs.sentry.io/platforms/python/tracing/instrumentation/custom-instrumentation/mcp-module/)
- [OpenTelemetry Support](https://docs.sentry.io/platforms/python/tracing/instrumentation/opentelemetry/)
- [MCP Protocol Specification](https://modelcontextprotocol.io/specification)

