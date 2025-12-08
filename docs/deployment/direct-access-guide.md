# Direct Access to MCP Server (Bypassing Traefik)

## Overview

This guide explains how to access the MCP server directly without going through the Traefik reverse proxy.

## Configuration

### Port Mapping

The MCP server is now accessible on **two ports**:

| Access Method | URL | Port | Description |
|--------------|-----|------|-------------|
| **Direct** | `http://localhost:8004/mcp` | 8004 | Direct container access (bypasses Traefik) |
| **Via Traefik** | `http://localhost:8003/mcp` | 8003 | Through Traefik reverse proxy |

### Docker Compose Configuration

In `docker-compose-dev.yml`, the MCP server exposes port 8004:

```yaml
mcp-server-dev:
  ports:
    # Direct access to MCP server (bypasses Traefik)
    - "8004:8003"       # Host:8004 -> Container:8003
```

**How it works:**
- Container runs on port `8003` internally (set by `MCP_SERVER_PORT`)
- Port `8004` on host maps to container port `8003`
- Port `8003` on host is used by Traefik

## Usage

### Health Check

```bash
# Direct access
curl http://localhost:8004/health

# Via Traefik
curl http://localhost:8003/health
```

**Response:**
```json
{
  "status": "healthy",
  "server": {
    "name": "MCP Server for Splunk",
    "version": "0.3.1",
    "transport": "http"
  },
  "splunk_connection": "connected",
  "splunk_info": {
    "version": "9.3.2",
    "serverName": "splunk-aws-demo-itsi-prod-shm-1201"
  }
}
```

### MCP Endpoint

The MCP endpoint requires proper headers for Streamable HTTP transport:

```bash
# Direct access
curl -X POST \
  -H "Content-Type: application/json" \
  -H "Accept: text/event-stream" \
  http://localhost:8004/mcp

# Via Traefik
curl -X POST \
  -H "Content-Type: application/json" \
  -H "Accept: text/event-stream" \
  http://localhost:8003/mcp
```

## MCP Client Configuration

### Claude Desktop (Direct Access)

Update your `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "splunk": {
      "url": "http://localhost:8004/mcp",
      "transport": "streamable-http"
    }
  }
}
```

### MCP Inspector (Direct Access)

Update the Inspector to use direct access:

```bash
npx @modelcontextprotocol/inspector \
  --transport streamable-http \
  --server-url http://localhost:8004/mcp
```

## Benefits of Direct Access

### ✅ Advantages

1. **Lower Latency**: No reverse proxy overhead
2. **Simpler Debugging**: Direct connection to server
3. **Fewer Dependencies**: Doesn't require Traefik
4. **Clearer Logs**: Server logs show real client IPs

### ⚠️ Disadvantages

1. **No Load Balancing**: Can't distribute across multiple instances
2. **No HTTPS**: Direct connection is HTTP only
3. **No Middleware**: Missing Traefik's CORS and rate limiting
4. **Less Production-Ready**: Traefik provides enterprise features

## When to Use Each Method

| Scenario | Recommended | Reason |
|----------|-------------|--------|
| **Local Development** | Direct (8004) | Faster, simpler debugging |
| **Testing** | Direct (8004) | Isolated testing |
| **Production** | Traefik (8003) | Load balancing, HTTPS, security |
| **Multiple Clients** | Traefik (8003) | Better traffic management |
| **Debugging** | Direct (8004) | Clearer connection issues |

## Troubleshooting

### Connection Refused

```bash
# Check if port is exposed
docker ps --filter "name=mcp-server" --format "table {{.Names}}\t{{.Ports}}"

# Should show:
# mcp-server-dev   0.0.0.0:8004->8003/tcp
```

### Empty Reply from Server

**Cause:** Server is still starting up

**Solution:**
```bash
# Wait for server to be ready
docker logs mcp-server-dev -f

# Look for:
# INFO: Uvicorn running on http://0.0.0.0:8003
```

### Wrong Port

If you see errors connecting to port 8003 directly:

```bash
# Direct access uses port 8004
curl http://localhost:8004/health  # ✅ Correct

# Port 8003 goes through Traefik
curl http://localhost:8003/health  # ✅ Also works (via Traefik)
```

## Network Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        Your Machine                          │
│                                                               │
│  ┌──────────────────┐           ┌─────────────────────────┐ │
│  │   Your Client    │           │    Docker Container     │ │
│  │  (Browser/CLI)   │           │                         │ │
│  └──────────────────┘           │  ┌──────────────────┐   │ │
│           │                      │  │  MCP Server      │   │ │
│           │                      │  │  Port: 8003      │   │ │
│           │                      │  └──────────────────┘   │ │
│           │                      │                         │ │
│           │                      └─────────────────────────┘ │
│           │                                   │               │
│           │                                   │               │
│           ├───────────────────────────────────┤               │
│           │                                   │               │
│      Port 8004                           Port 8003            │
│     (Direct Access)                   (Via Traefik)           │
│                                                               │
└───────────────────────────────────────────────────────────────┘

Direct Access (8004):
  localhost:8004 → Docker Port 8003 → MCP Server

Traefik Access (8003):
  localhost:8003 → Traefik → Docker Port 8003 → MCP Server
```

## Security Considerations

### Development Mode

Current configuration is suitable for **local development only**:

```yaml
environment:
  - MCP_AUTH_DISABLED=true
  - DANGEROUSLY_OMIT_AUTH=true
```

### Production Deployment

For production, you should:

1. **Use Traefik** (port 8003) instead of direct access
2. **Enable authentication**
3. **Use HTTPS** with valid certificates
4. **Remove direct port exposure** (comment out port 8004)
5. **Configure firewall rules**
6. **Enable rate limiting** in Traefik

## Testing Both Endpoints

### Automated Test Script

```bash
#!/bin/bash
echo "Testing Direct Access (port 8004)..."
curl -s http://localhost:8004/health | jq '.status'

echo ""
echo "Testing Traefik Access (port 8003)..."
curl -s http://localhost:8003/health | jq '.status'

echo ""
echo "Both should return: healthy"
```

### Response Time Comparison

```bash
# Direct access timing
time curl -s http://localhost:8004/health > /dev/null

# Traefik access timing
time curl -s http://localhost:8003/health > /dev/null
```

**Expected results:**
- Direct access: ~5-10ms faster (no proxy overhead)
- Both should work reliably

## Summary

You now have **two ways** to access your MCP server:

1. **Direct Access** (`localhost:8004`): Best for development and debugging
2. **Traefik Access** (`localhost:8003`): Best for production and scaling

Choose based on your needs, and remember that **both can run simultaneously** for maximum flexibility! 🚀




