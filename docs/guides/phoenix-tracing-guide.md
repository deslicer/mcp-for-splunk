# Phoenix OpenTelemetry Tracing Guide

This guide explains how to enable and use Phoenix observability for the MCP Server for Splunk.

## Overview

Phoenix tracing provides comprehensive observability for your MCP server, capturing:

- **MCP Tool Calls**: All tool invocations, parameters, and responses
- **Splunk API Interactions**: Connection attempts, searches, dashboard operations
- **LLM Calls**: If using OpenAI or other LLM providers (via OpenInference)
- **Custom Operations**: Any instrumented application code

Traces are sent to a Phoenix instance via OpenTelemetry Protocol (OTLP) in protobuf format.

## Prerequisites

1. **Phoenix Instance Running**: Either locally or deployed
   - Local: Use `docker-compose.phoenix.dev.yml` from deslicer-ai project
   - Deployed: Phoenix on Coolify or other hosting

2. **Python Dependencies**: Installed via `uv sync`
   ```bash
   # Already included in pyproject.toml
   arize-phoenix-otel>=1.7.0
   openinference-instrumentation-mcp>=0.1.6
   opentelemetry-exporter-otlp-proto-http>=1.27.0
   ```

## Configuration

### 1. Environment Variables

Add to your `.env` file:

```bash
# Enable/disable Phoenix tracing
PHOENIX_ENABLED=true

# Phoenix OTLP collector endpoint (protobuf format)
PHOENIX_COLLECTOR_ENDPOINT=http://localhost:6006/v1/traces

# Phoenix project name (organizes traces in Phoenix UI)
PHOENIX_PROJECT_NAME=mcp-server-for-splunk

# Service identification
MCP_SERVICE_NAME=mcp-server-for-splunk
MCP_SERVICE_VERSION=0.4.0
```

### 2. For Docker Deployment

Update `docker-compose.yml` to include Phoenix environment variables:

```yaml
services:
  mcp-server:
    # ... existing config ...
    environment:
      # ... existing env vars ...
      - PHOENIX_ENABLED=true
      - PHOENIX_COLLECTOR_ENDPOINT=http://phoenix:6006/v1/traces
      - PHOENIX_PROJECT_NAME=mcp-server-for-splunk
```

### 3. Connecting to deslicer-ai Phoenix Instance

If running locally alongside deslicer-ai:

```bash
# In mcp-for-splunk/.env
PHOENIX_COLLECTOR_ENDPOINT=http://localhost:6006/v1/traces
PHOENIX_PROJECT_NAME=mcp-server-for-splunk
```

Phoenix will show traces from both projects, organized by project name.

## What Gets Traced

### Automatic Instrumentation

The `MCPInstrumentor` automatically traces:

1. **MCP Tool Calls**:
   - Tool name and arguments
   - Execution duration
   - Success/failure status
   - Response content

2. **MCP Resources**:
   - Resource requests
   - Resource content delivery

3. **MCP Prompts**:
   - Prompt template usage
   - Prompt argument filling

### Custom Tracing

#### Add Attributes to Current Span

```python
from src.core.phoenix_instrumentation import add_trace_attributes

add_trace_attributes(
    user_id="user123",
    session_id="session456",
    splunk_instance="production",
    search_index="main"
)
```

#### Trace Custom Operations

```python
from src.core.phoenix_instrumentation import trace_operation

# Automatic span creation and closure
with trace_operation("splunk.search", query="index=main error", user="admin"):
    results = service.jobs.oneshot(query)
    # Results are automatically captured in span
```

#### Example: Tracing Splunk Search

```python
from src.core.phoenix_instrumentation import trace_operation, add_trace_attributes

@mcp.tool()
async def search_splunk(query: str, earliest_time: str = "-24h"):
    """Search Splunk with Phoenix tracing"""
    
    with trace_operation(
        "splunk.search",
        query=query,
        earliest_time=earliest_time,
        tool_name="search_splunk"
    ):
        try:
            # Execute search
            job = service.jobs.create(query, earliest_time=earliest_time)
            
            # Add job details to trace
            add_trace_attributes(
                search_job_id=job.sid,
                search_status=job["dispatchState"]
            )
            
            # Wait for results
            while not job.is_done():
                await asyncio.sleep(0.1)
            
            results = job.results()
            
            # Add result metrics
            add_trace_attributes(
                result_count=job["resultCount"],
                scan_count=job["scanCount"],
                duration_sec=job["runDuration"]
            )
            
            return results
            
        except Exception as e:
            add_trace_attributes(error=str(e), error_type=type(e).__name__)
            raise
```

## Viewing Traces in Phoenix

### 1. Access Phoenix UI

Navigate to: `http://localhost:6006`

### 2. Select Project

- Use the project dropdown to select "mcp-server-for-splunk"
- Or view all projects together

### 3. Trace Views

**Traces Tab**: 
- See all MCP tool calls
- Filter by tool name, duration, status
- View request/response payloads

**Spans Tab**:
- Detailed span timeline
- Nested spans (MCP tool → Splunk API → network)
- Attributes and metadata

**Sessions Tab**:
- Group traces by session ID
- Track user journeys

## Integration with deslicer-ai Traces

When both MCP server and deslicer-ai Next.js app send to the same Phoenix:

1. **Separate Projects**: Each service has its own project name
2. **Correlated Traces**: Use `session_id` or `request_id` attributes
3. **Full Stack View**: See frontend AI calls → MCP tool → Splunk API

### Correlation Example

In deslicer-ai (Next.js):
```typescript
experimental_telemetry: {
  metadata: {
    requestId: "req-123",
    toolConfigId: "splunk-mcp-1"
  }
}
```

In MCP server:
```python
add_trace_attributes(
    request_id="req-123",  # Same ID!
    tool_config_id="splunk-mcp-1"
)
```

Phoenix will link these traces together.

## Troubleshooting

### Traces Not Appearing

1. **Check Phoenix endpoint**:
   ```bash
   curl -v http://localhost:6006/v1/traces
   # Should return 405 (POST required, but endpoint is reachable)
   ```

2. **Check server logs**:
   ```bash
   tail -f logs/mcp_splunk_server.log | grep Phoenix
   ```
   
   Expected output:
   ```
   ✅ Phoenix tracing initialized for project: mcp-server-for-splunk
      Endpoint: http://localhost:6006/v1/traces
      Service: mcp-server-for-splunk v0.4.0
      MCP instrumentation: enabled
   ```

3. **Verify dependencies**:
   ```bash
   uv pip list | grep -E "(phoenix|openinference|opentelemetry)"
   ```

4. **Check for errors**:
   ```bash
   # Look for OTLP export errors
   grep -i "otlp\|phoenix\|trace" logs/mcp_splunk_server.log
   ```

### Performance Impact

- **Minimal overhead**: <5ms per trace
- **Async export**: Traces sent in background batches
- **No blocking**: Never blocks MCP tool execution
- **Configurable**: Set `PHOENIX_ENABLED=false` to disable

### Disable Tracing

```bash
# In .env
PHOENIX_ENABLED=false
```

Or unset the environment variable:
```bash
unset PHOENIX_COLLECTOR_ENDPOINT
```

## Advanced Configuration

### Custom Span Processors

Edit `src/core/phoenix_instrumentation.py`:

```python
from opentelemetry.sdk.trace.export import SimpleSpanProcessor

# Add a custom processor
tracer_provider.add_span_processor(
    SimpleSpanProcessor(MyCustomExporter())
)
```

### Sampling

Reduce trace volume by sampling:

```python
from opentelemetry.sdk.trace.sampling import TraceIdRatioBased

tracer_provider = TracerProvider(
    sampler=TraceIdRatioBased(0.1),  # Sample 10% of traces
    resource=resource
)
```

### Additional Instrumentations

Auto-instrument HTTP, database, etc.:

```python
from opentelemetry.instrumentation.requests import RequestsInstrumentor
from opentelemetry.instrumentation.logging import LoggingInstrumentor

RequestsInstrumentor().instrument()
LoggingInstrumentor().instrument()
```

## Best Practices

1. **Add Semantic Attributes**: Use OpenTelemetry semantic conventions
   ```python
   add_trace_attributes(
       "http.method": "POST",
       "db.system": "splunk",
       "db.statement": query
   )
   ```

2. **Use Span Status**: Mark success/failure explicitly
   ```python
   from opentelemetry import trace
   span = trace.get_current_span()
   span.set_status(Status(StatusCode.ERROR, "Search failed"))
   ```

3. **Add Events**: Log significant moments
   ```python
   span.add_event("search_started", {"index": "main"})
   span.add_event("results_parsed", {"count": len(results)})
   ```

4. **Avoid PII**: Don't log passwords, tokens, sensitive data
   ```python
   # ❌ Don't do this
   add_trace_attributes(password=password)
   
   # ✅ Do this
   add_trace_attributes(auth_type="password", has_credentials=True)
   ```

## Next Steps

- [Main README](../../README.md)
- [Deployment Guide](../deployment/direct-access-guide.md)
- [Monitoring Guide](./monitoring.md)
- [Phoenix Documentation](https://docs.arize.com/phoenix)


