# Client-Provided Splunk Configuration

This guide explains how MCP clients can provide Splunk connection configuration directly to tools, allowing different clients to connect to different Splunk instances without modifying server configuration.

## Overview

The MCP Server for Splunk supports **two configuration modes**:

1. **Server Configuration** (Default) - Splunk settings from environment variables
2. **Client Configuration** (New) - Splunk settings provided by the MCP client per request

Client configuration takes precedence when provided, with automatic fallback to server configuration.

## Supported Configuration Parameters

All tools that connect to Splunk accept these optional parameters:

| Parameter | Type | Description | Default |
|-----------|------|-------------|---------|
| `splunk_host` | string | Splunk server hostname | localhost |
| `splunk_port` | integer | Splunk management port | 8089 |
| `splunk_username` | string | Splunk username | (required) |
| `splunk_password` | string | Splunk password | (required) |
| `splunk_scheme` | string | Connection scheme (http/https) | https |
| `splunk_verify_ssl` | boolean | Verify SSL certificates | false |

## Usage Examples

### 1. Cursor IDE Configuration

**Standard Configuration (uses server environment variables):**
```json
{
  "mcpServers": {
    "mcp-server-for-splunk": {
      "command": "uv",
      "args": [
        "--directory", "/path/to/mcp-server-for-splunk/",
        "run", "python", "src/server.py"
      ]
    }
  }
}
```

**Client-Specific Configuration (client provides Splunk settings):**
```json
{
  "mcpServers": {
    "mcp-server-for-splunk-production": {
      "command": "uv",
      "args": [
        "--directory", "/path/to/mcp-server-for-splunk/",
        "run", "python", "src/server.py"
      ]
    }
  }
}
```

When using tools in Cursor, you can now provide Splunk configuration:

```
Please check the health of our production Splunk instance with these parameters:
- splunk_host: splunk-prod.company.com
- splunk_username: monitoring-user
- splunk_password: secure-password
- splunk_verify_ssl: true
```

### 2. MCP Inspector Usage

When testing tools in MCP Inspector (http://localhost:3001):

**Basic Health Check (uses server config):**
```javascript
{
  "tool": "get_splunk_health",
  "arguments": {}
}
```

**Health Check with Client Config:**
```javascript
{
  "tool": "get_splunk_health",
  "arguments": {
    "splunk_host": "dev-splunk.company.com",
    "splunk_port": 8089,
    "splunk_username": "dev-user",
    "splunk_password": "dev-password",
    "splunk_scheme": "https",
    "splunk_verify_ssl": false
  }
}
```

### 3. Google ADK Integration

**Basic Setup (server config):**
```python
from google.adk.tools.mcp_tool.mcp_toolset import MCPToolset, StdioServerParameters

splunk_agent = LlmAgent(
    model='gemini-2.0-flash',
    tools=[
        MCPToolset(
            connection_params=StdioServerParameters(
                command='uv',
                args=['--directory', '/path/to/mcp-server-for-splunk/',
                      'run', 'python', 'src/server.py']
            )
        )
    ]
)
```

**Client-Configured Usage:**
```python
# Tool calls with client configuration
await splunk_agent.execute_tool(
    "get_splunk_health",
    splunk_host="production-splunk.company.com",
    splunk_username="monitoring",
    splunk_password="secure-password",
    splunk_verify_ssl=True
)

await splunk_agent.execute_tool(
    "run_oneshot_search",
    query="index=security | head 10",
    splunk_host="security-splunk.company.com",
    splunk_username="security-analyst",
    splunk_password="analyst-password"
)
```

### 4. Direct HTTP API Calls

**POST to MCP Server with Client Config:**
```bash
curl -X POST http://localhost:8001/mcp/tools/get_splunk_health \
  -H "Content-Type: application/json" \
  -d '{
    "splunk_host": "remote-splunk.example.com",
    "splunk_port": 8089,
    "splunk_username": "api-user",
    "splunk_password": "api-password",
    "splunk_scheme": "https",
    "splunk_verify_ssl": true
  }'
```

## Multi-Environment Scenarios

### Development vs Production

**Development Splunk:**
```python
dev_results = await execute_tool(
    "list_indexes",
    splunk_host="dev-splunk.internal",
    splunk_username="dev-user",
    splunk_password="dev-pass",
    splunk_verify_ssl=False
)
```

**Production Splunk:**
```python
prod_results = await execute_tool(
    "list_indexes", 
    splunk_host="prod-splunk.company.com",
    splunk_username="prod-readonly",
    splunk_password="secure-prod-pass",
    splunk_verify_ssl=True
)
```

### Multi-Tenant Environments

**Customer A's Splunk:**
```python
customer_a_data = await execute_tool(
    "run_oneshot_search",
    query="index=customer_a_logs | head 100",
    splunk_host="customer-a-splunk.saas.company.com",
    splunk_username="customer-a-service",
    splunk_password="customer-a-token"
)
```

**Customer B's Splunk:**
```python
customer_b_data = await execute_tool(
    "run_oneshot_search", 
    query="index=customer_b_logs | head 100",
    splunk_host="customer-b-splunk.saas.company.com",
    splunk_username="customer-b-service",
    splunk_password="customer-b-token"
)
```

## Tool Compatibility

### Tools Supporting Client Configuration

All core tools support client configuration:

- ✅ `get_splunk_health` - Health and version checks
- ✅ `list_indexes` - Index discovery
- ✅ `run_oneshot_search` - Quick searches
- ✅ `run_splunk_search` - Complex searches with progress
- ✅ `list_sourcetypes` - Data type discovery
- ✅ `list_sources` - Data source discovery
- ✅ `list_apps` - Application management
- ✅ `list_users` - User management  
- ✅ `list_kvstore_collections` - KV Store collections
- ✅ `get_kvstore_data` - KV Store data retrieval
- ✅ `create_kvstore_collection` - KV Store creation
- ✅ `get_configurations` - Configuration access

### Configuration Priority

1. **Client-provided parameters** (highest priority)
2. **Server environment variables** (fallback)
3. **Built-in defaults** (last resort)

## Error Handling

### Configuration Validation

The server validates client configuration and provides helpful error messages:

```json
{
  "status": "error",
  "error": "Splunk username and password must be provided via client config or environment variables",
  "connection_source": "client_config"
}
```

### Fallback Behavior

If client configuration fails, tools automatically attempt to use server configuration:

```json
{
  "status": "connected",
  "version": "9.1.0",
  "server_name": "splunk-server",
  "connection_source": "server_config",
  "note": "Client config failed, using server default"
}
```

## Security Considerations

### Password Security

**❌ Avoid:**
```python
# Don't hardcode credentials in code
await execute_tool(
    "get_splunk_health",
    splunk_password="hardcoded-password"  # BAD!
)
```

**✅ Recommended:**
```python
import os

# Use environment variables or secure vaults
await execute_tool(
    "get_splunk_health",
    splunk_host=os.environ["PROD_SPLUNK_HOST"],
    splunk_username=os.environ["PROD_SPLUNK_USER"],
    splunk_password=os.environ["PROD_SPLUNK_PASS"]
)
```

### SSL Verification

**Production environments** should always use SSL verification:
```python
await execute_tool(
    "get_splunk_health",
    splunk_host="production.company.com",
    splunk_verify_ssl=True  # Always verify in production
)
```

**Development environments** may disable SSL verification:
```python
await execute_tool(
    "get_splunk_health", 
    splunk_host="dev-splunk.local",
    splunk_verify_ssl=False  # OK for development
)
```

## Troubleshooting

### Connection Issues

**Test connectivity first:**
```python
health_result = await execute_tool(
    "get_splunk_health",
    splunk_host="your-splunk-host.com",
    splunk_username="your-username",
    splunk_password="your-password"
)

if health_result["status"] == "connected":
    print("Connection successful!")
else:
    print(f"Connection failed: {health_result['error']}")
```

### Common Issues

1. **Wrong Port**: Ensure you're using the management port (default 8089), not the web port (8000)

2. **SSL Issues**: Try setting `splunk_verify_ssl: false` for testing

3. **Authentication**: Verify username/password work with Splunk Web UI

4. **Network**: Ensure the MCP server can reach the Splunk host

### Debug Logging

Enable debug logging to see connection attempts:

```bash
# Set log level in environment
export MCP_LOG_LEVEL=DEBUG

# Run server
python src/server.py
```

## Migration from Server-Only Configuration

### Step 1: Test Current Setup
```python
# Test your current server configuration
health = await execute_tool("get_splunk_health")
print(f"Current server config: {health}")
```

### Step 2: Add Client Configuration Gradually
```python
# Start with optional client config
health = await execute_tool(
    "get_splunk_health",
    splunk_host="new-splunk-server.com"  # Only override what's needed
)
```

### Step 3: Full Client Configuration
```python
# Complete client configuration
health = await execute_tool(
    "get_splunk_health",
    splunk_host="new-splunk-server.com",
    splunk_username="new-user",
    splunk_password="new-password",
    splunk_verify_ssl=True
)
```

This approach allows you to migrate gradually while maintaining backward compatibility with your existing setup. 