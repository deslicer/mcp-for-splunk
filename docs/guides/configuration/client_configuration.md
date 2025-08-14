# Client Configuration Guide

The MCP Server for Splunk supports **flexible client configuration**, allowing MCP clients to provide their own Splunk connection settings instead of relying solely on server-side environment variables.

## 🎯 **Key Benefits**

- **Multi-environment support** - Different clients can connect to different Splunk instances
- **Enhanced security** - Clients provide their own credentials, server doesn't store them
- **Dynamic configuration** - No server restarts needed when switching Splunk environments
- **Multi-tenant support** - Multiple clients can use different Splunk configurations simultaneously

## 🏗️ **Supported Servers**

Both server implementations support client configuration:

- ✅ **`src/server.py`** - Full support (HTTP headers + environment variables)
- ✅ **`src/server.py`** - Full support (HTTP headers + environment variables)

## 🔧 **Configuration Methods**

### 1. MCP Client Configuration (Recommended)

Configure Splunk settings at the **MCP client level** instead of per-tool call.

#### **For Cursor IDE / Claude Desktop**

Add this to your `mcp.json` or settings:

```json
{
  "mcpServers": {
    "splunk-prod": {
      "command": "python",
      "args": ["path/to/mcp-server-for-splunk/src/server.py"],
      "env": {
        "MCP_SPLUNK_HOST": "splunk-prod.company.com",
        "MCP_SPLUNK_PORT": "8089",
        "MCP_SPLUNK_USERNAME": "prod_user",
        "MCP_SPLUNK_PASSWORD": "prod_password",
        "MCP_SPLUNK_SCHEME": "https",
        "MCP_SPLUNK_VERIFY_SSL": "true"
      }
    },
    "splunk-dev": {
      "command": "python",
      "args": ["path/to/mcp-server-for-splunk/src/server.py"],
      "env": {
        "MCP_SPLUNK_HOST": "splunk-dev.company.com",
        "MCP_SPLUNK_USERNAME": "dev_user",
        "MCP_SPLUNK_PASSWORD": "dev_password",
        "MCP_SPLUNK_VERIFY_SSL": "false"
      }
    }
  }
}
```

#### **For Google ADK Integration**

```python
from mcp import Client

config = {
    "mcpServers": {
        "splunk-customer-a": {
            "command": "python",
            "args": ["./server.py"],
            "env": {
                "MCP_SPLUNK_HOST": "customer-a.splunk.com",
                "MCP_SPLUNK_USERNAME": os.getenv("CUSTOMER_A_USERNAME"),
                "MCP_SPLUNK_PASSWORD": os.getenv("CUSTOMER_A_PASSWORD")
            }
        }
    }
}

client = Client(config)
```

#### **For HTTP Transport**

When using HTTP transport, pass configuration via headers:

```python
from fastmcp.client.transports import StreamableHttpTransport

transport = StreamableHttpTransport(
    url="https://your-mcp-server.com/mcp",
    headers={
        "X-Splunk-Host": "splunk.company.com",
        "X-Splunk-Port": "8089",
        "X-Splunk-Username": "your_username",
        "X-Splunk-Password": "your_password",
        "X-Splunk-Scheme": "https",
        "X-Splunk-Verify-SSL": "true"
    }
)

client = Client(transport)
```

### 2. Environment Variables Reference

#### **MCP Client Variables** (Recommended - Higher Priority)
```bash
MCP_SPLUNK_HOST=splunk.company.com
MCP_SPLUNK_PORT=8089
MCP_SPLUNK_USERNAME=your_username
MCP_SPLUNK_PASSWORD=your_password
MCP_SPLUNK_SCHEME=https
MCP_SPLUNK_VERIFY_SSL=true
```

#### **Server Variables** (Fallback - Lower Priority)
```bash
SPLUNK_HOST=splunk.company.com
SPLUNK_PORT=8089
SPLUNK_USERNAME=default_user
SPLUNK_PASSWORD=default_password
SPLUNK_SCHEME=https
SPLUNK_VERIFY_SSL=true
```

### 3. HTTP Headers (for HTTP Transport)

When using HTTP transport, you can pass Splunk configuration via request headers:

```
X-Splunk-Host: splunk.company.com
X-Splunk-Port: 8089
X-Splunk-Username: your_username
X-Splunk-Password: your_password
X-Splunk-Scheme: https
X-Splunk-Verify-SSL: true
```

## 🎯 **Configuration Priority**

The server uses the following priority order (highest to lowest):

1. **Tool-level parameters** - Splunk config passed directly to tool calls
2. **HTTP headers** - X-Splunk-* headers (for HTTP transport)
3. **MCP client environment** - MCP_SPLUNK_* variables (for stdio transport)
4. **Server environment** - SPLUNK_* variables (server defaults)

## 📝 **Usage Examples**

### Example 1: Multi-Environment Setup

```json
{
  "mcpServers": {
    "splunk-production": {
      "command": "python",
      "args": ["./server.py"],
      "env": {
        "MCP_SPLUNK_HOST": "prod-splunk.company.com",
        "MCP_SPLUNK_USERNAME": "prod_analyst"
      }
    },
    "splunk-staging": {
      "command": "python",
      "args": ["./server.py"],
      "env": {
        "MCP_SPLUNK_HOST": "staging-splunk.company.com",
        "MCP_SPLUNK_USERNAME": "staging_user"
      }
    }
  }
}
```

Once configured, all tool calls automatically use the respective environment's settings:

```python
# This automatically uses prod-splunk.company.com
await client.call_tool("splunk-production_run_oneshot_search", {
    "query": "index=main | head 10"
})

# This automatically uses staging-splunk.company.com
await client.call_tool("splunk-staging_run_oneshot_search", {
    "query": "index=test | head 10"
})
```

### Example 2: Customer-Specific Configuration

```python
# Each customer gets their own MCP server instance
customer_configs = {
    "customer_123": {
        "MCP_SPLUNK_HOST": "customer123.splunk.cloud",
        "MCP_SPLUNK_USERNAME": "api_user_123"
    },
    "customer_456": {
        "MCP_SPLUNK_HOST": "customer456.splunk.cloud",
        "MCP_SPLUNK_USERNAME": "api_user_456"
    }
}

for customer_id, config in customer_configs.items():
    client_config = {
        "mcpServers": {
            f"splunk-{customer_id}": {
                "command": "python",
                "args": ["./server.py"],
                "env": config
            }
        }
    }

    # Each client automatically connects to the right Splunk instance
    async with Client(client_config) as client:
        results = await client.call_tool("run_oneshot_search", {
            "query": "index=* | stats count"
        })
```

## 🔒 **Security Considerations**

1. **Environment Variables** - Use MCP_SPLUNK_* variables for client-specific config
2. **HTTP Headers** - X-Splunk-* headers are prefixed for security
3. **Credential Management** - Consider using credential managers for sensitive values
4. **SSL Verification** - Always use `MCP_SPLUNK_VERIFY_SSL=true` in production

## 🚀 **Getting Started**

1. **Set up your MCP client configuration** using the examples above
2. **Start the MCP server** - it will automatically detect and use client config
3. **Call tools normally** - no need to pass Splunk parameters to individual tool calls
4. **Monitor logs** - Server will log which configuration source is being used

## 🔧 **Troubleshooting**

### Issue: "Splunk service is not available"
- Check that your MCP client environment variables are set correctly
- Verify network connectivity to the Splunk host
- Ensure credentials are valid

### Issue: Client config not detected
- Verify the MCP_SPLUNK_* variable naming (not SPLUNK_*)
- Check that the MCP client is passing environment variables correctly
- Look for "Found MCP client configuration" in server logs

### Issue: Wrong Splunk instance
- Check the configuration priority order
- Verify that no tool-level parameters are overriding client config
- Review server logs to see which config source is being used
