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

## 🔧 **Configuration Methods**

### 1. MCP Client Configuration (Recommended)

Configure Splunk settings at the **MCP client level** instead of per-tool call.

#### **For Cursor IDE / Claude Desktop**

Add one or both of these to your `mcp.json` or settings, depending on transport:

##### StdIO (env-based, single-tenant)

```json
{
  "mcpServers": {
    "splunk": {
      "command": "fastmcp",
      "args": ["run", "/path/to/src/server.py"],
      "env": {
        "MCP_SPLUNK_HOST": "your-splunk.com",
        "MCP_SPLUNK_USERNAME": "your-user",
        "MCP_SPLUNK_PASSWORD": "your-password",
        "MCP_SPLUNK_SCHEME": "https",
        "MCP_SPLUNK_VERIFY_SSL": "true"
      }
    }
  }
}
```

##### HTTP (/mcp/ URL with headers, multi-tenant)

```json
{
  "mcpServers": {
    "splunk-in-docker": {
      "url": "http://localhost:8002/mcp/",
      "headers": {
        "X-Splunk-Host": "so1",
        "X-Splunk-Port": "8089",
        "X-Splunk-Username": "admin",
        "X-Splunk-Password": "Chang3d!",
        "X-Splunk-Scheme": "http",
        "X-Splunk-Verify-SSL": "false",
        "X-Session-ID": "splunk-in-docker-session"
      }
    },
    "splunk-cloud-instance": {
      "url": "http://localhost:8002/mcp/",
      "headers": {
        "X-Splunk-Host": "myorg.splunkcloud.com",
        "X-Splunk-Port": "8089",
        "X-Splunk-Username": "admin@myorg.com",
        "X-Splunk-Password": "Chang3d!Cloud",
        "X-Splunk-Scheme": "https",
        "X-Splunk-Verify-SSL": "true",
        "X-Session-ID": "splunk-cloud-session"
      }
    }
  }
}
```

#### **For Google ADK Integration**

```python
from google.adk.tools.mcp_tool.mcp_toolset import MCPToolset
from google.adk.core.agent import LlmAgent
from google.adk.tools.mcp_tool.params import StdioServerParameters

splunk_agent = LlmAgent(
    model="gemini-2.0-flash",
    tools=[
        MCPToolset(
            connection_params=StdioServerParameters(
                command="fastmcp",
                args=["run", "/path/to/src/server.py"],
                env={
                    "MCP_SPLUNK_HOST": "customer-a.splunk.com",
                    "MCP_SPLUNK_USERNAME": "api_user",
                    "MCP_SPLUNK_PASSWORD": "***"
                }
            )
        )
    ],
)
```

#### **For HTTP Transport**

When using HTTP transport, pass configuration via headers:

```python
from fastmcp.client.transports import StreamableHttpTransport

transport = StreamableHttpTransport(
    url="https://your-mcp-server.com/mcp/",
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

Or initialize the client directly with an HTTP(S) URL (transport inferred):

```python
from fastmcp import Client
import asyncio

client = Client("https://your-mcp-server.com/mcp/")

async def main():
    async with client:
        tools = await client.list_tools()
        print(tools)

asyncio.run(main())
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

# Or, instead of username/password, use a Splunk bearer / access token
# (created in Splunk Web at Settings -> Tokens or via the
# /services/authorization/tokens REST endpoint).
MCP_SPLUNK_TOKEN=eyJraWQiOiJzcGx1bmsuc2VjcmV0...
```

#### **Server Variables** (Fallback - Lower Priority)
```bash
SPLUNK_HOST=splunk.company.com
SPLUNK_PORT=8089
SPLUNK_USERNAME=default_user
SPLUNK_PASSWORD=default_password
SPLUNK_SCHEME=https
SPLUNK_VERIFY_SSL=true

# Or use a bearer / access token at the server level.
SPLUNK_TOKEN=eyJraWQiOiJzcGx1bmsuc2VjcmV0...
```

### 3. HTTP Headers (for HTTP Transport)

When using HTTP transport, you can pass Splunk configuration via request headers.
Each MCP client / tool call can authenticate to Splunk independently.

#### **Username + password**

```
X-Splunk-Host: splunk.company.com
X-Splunk-Port: 8089
X-Splunk-Username: your_username
X-Splunk-Password: your_password
X-Splunk-Scheme: https
X-Splunk-Verify-SSL: true
```

#### **Bearer / access token (recommended for per-user auth)**

Authenticate per request using a Splunk access token. The token maps to
the `splunkToken` argument of `splunklib.client.connect`, so no `login()`
round-trip is performed.

```
X-Splunk-Host: splunk.company.com
X-Splunk-Port: 8089
X-Splunk-Token: eyJraWQiOiJzcGx1bmsuc2VjcmV0...
X-Splunk-Scheme: https
X-Splunk-Verify-SSL: true
```

If MCP server-level auth is disabled (`MCP_AUTH_DISABLED=true`), the
standard `Authorization: Bearer <token>` header is also accepted as a
fallback so existing clients that already inject bearer tokens through
their HTTP middleware can authenticate to Splunk without additional
header plumbing.

> **Tip**: Create a token in Splunk Web under **Settings → Tokens**, or via the
> `/services/authorization/tokens` REST endpoint. See the
> [Splunk docs on creating authentication tokens](https://docs.splunk.com/Documentation/Splunk/latest/Security/CreateAuthTokens).

## 🧩 **Selecting toolsets (`X-MCP-Toolsets`)**

`mcp-server-for-splunk` can host the core Splunk tools alongside one or more
plugin toolsets (e.g. ITSI) in the **same** server. Each client picks which
toolsets it wants on a per-request basis through an HTTP header — no separate
deployment per persona.

For the contract a plugin author needs to satisfy, see
[Per-client toolset filtering in `docs/guides/plugins.md`](../plugins.md#per-client-toolset-filtering-x-mcp-toolsets).
The rest of this section is for **client operators** picking what to connect to.

### Two ways to deploy (`docker-compose.yml`)

| Endpoint                          | Service     | Tools served                        |
|-----------------------------------|-------------|-------------------------------------|
| `http(s)://HOST:PORT/mcp`         | `mcp-server`| Splunk core + every loaded plugin (filtered per-request via `X-MCP-Toolsets`) |
| `http(s)://HOST:PORT/itsi/mcp`    | `mcp-itsi`  | ITSI only (standalone server, no filter) |

Pick the **unified** endpoint when you want one URL for everything and let
clients opt into toolsets dynamically. Pick the **standalone** endpoint when
you want strict role separation (e.g. an ITSI-only environment).

### Header reference

```http
X-MCP-Toolsets: splunk            # core Splunk tools only
X-MCP-Toolsets: itsi              # ITSI plugin tools only
X-MCP-Toolsets: splunk,itsi       # both
X-MCP-Toolsets: all               # every known toolset
```

- Unknown values are silently dropped.
- Untagged framework helpers (e.g. `sentry_test`, internal probes) stay
  visible regardless of header.
- When the header is omitted the server falls back to the
  `MCP_DEFAULT_TOOLSETS` env var, which defaults to `splunk`. Plugins
  (e.g. ITSI) must be opted into explicitly — header or env var.

Discover what your server supports via `/health`:

```json
{
  "available_toolsets": ["itsi", "splunk"],
  "loaded_plugins": [{"name": "itsi"}]
}
```

### Cursor IDE / Claude Desktop

Add one entry per persona under `mcpServers`. The header travels with every
request, so calls to `tools/list` and `tools/call` both see the same view.

```json
{
  "mcpServers": {
    "splunk-only": {
      "url": "http://localhost:8003/mcp/",
      "headers": {
        "X-MCP-Toolsets": "splunk",
        "X-Splunk-Host": "splunk.company.com",
        "X-Splunk-Token": "eyJraWQiOiJzcGx1bmsuc2VjcmV0..."
      }
    },
    "itsi-only": {
      "url": "http://localhost:8003/mcp/",
      "headers": {
        "X-MCP-Toolsets": "itsi",
        "X-Splunk-Host": "splunk.company.com",
        "X-Splunk-Token": "eyJraWQiOiJzcGx1bmsuc2VjcmV0..."
      }
    },
    "splunk-and-itsi": {
      "url": "http://localhost:8003/mcp/",
      "headers": {
        "X-MCP-Toolsets": "splunk,itsi",
        "X-Splunk-Host": "splunk.company.com",
        "X-Splunk-Token": "eyJraWQiOiJzcGx1bmsuc2VjcmV0..."
      }
    }
  }
}
```

> Most clients merge `headers` into every outbound MCP request automatically.
> If yours does not, set `MCP_DEFAULT_TOOLSETS` server-side (next section) so
> header-less clients still land on the right view.

### MCP Inspector

In the Inspector UI (the compose stack ships one at <http://localhost:6274>):

1. Set **Transport** to `Streamable HTTP`.
2. Set **Server URL** to `http://localhost:8003/mcp` (or `/itsi/mcp` for the
   standalone server).
3. Open **Custom Headers** and add `X-MCP-Toolsets: splunk` (or `itsi`,
   `splunk,itsi`, `all`).
4. Click **Connect** and **List Tools** — the list reflects your selection
   immediately.

### Python (FastMCP client)

```python
from fastmcp import Client
from fastmcp.client.transports import StreamableHttpTransport

transport = StreamableHttpTransport(
    "http://localhost:8003/mcp",
    headers={
        "X-MCP-Toolsets": "splunk,itsi",
        # plus any X-Splunk-* headers you would normally send
    },
)

async with Client(transport) as client:
    tools = await client.list_tools()
    print(sorted(t.name for t in tools))
```

### Raw HTTP / curl smoke test

```bash
curl -sS -X POST http://localhost:8003/mcp \
  -H 'Content-Type: application/json' \
  -H 'Accept: application/json, text/event-stream' \
  -H 'X-MCP-Toolsets: itsi' \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}' | head
```

### Operator default (`MCP_DEFAULT_TOOLSETS`)

Set it in the compose `.env` (already wired through `docker-compose.yml`) to
choose what header-less clients see:

```bash
MCP_DEFAULT_TOOLSETS=splunk        # default — host tools only, plugins opt-in
MCP_DEFAULT_TOOLSETS=splunk,itsi   # opt clients into ITSI by default
MCP_DEFAULT_TOOLSETS=all           # opt every loaded plugin in
```

A request that includes `X-MCP-Toolsets` always wins over this default.

### Calling a disabled tool

The middleware also guards `tools/call`. A client that asks for a tool whose
toolset is not enabled receives a `ToolError` instead of an unexpected
execution:

```text
Tool 'itsi_list_entities' is not in an enabled toolset for this client
```

This is the canonical signal to surface in your client UI when a toolset
toggle changes.

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
5. **Prefer access tokens over passwords** - Splunk access tokens (`X-Splunk-Token` /
   `SPLUNK_TOKEN`) are scoped, revocable, and have an explicit expiry. They are also
   logged-redacted alongside `password` and `authorization` values throughout the server.

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
