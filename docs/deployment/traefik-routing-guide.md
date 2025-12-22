# ✅ Traefik Routing - Working Configuration

## Summary

Your MCP server is now accessible through **both** Traefik (recommended) and direct access:

| Method | URL | Status | Use Case |
|--------|-----|--------|----------|
| **Traefik** | `http://localhost:8003/mcp` | ✅ Working | Production, load balancing |
| **Direct** | `http://localhost:8004/mcp` | ✅ Working | Development, debugging |

## Current Configuration

### Architecture

```
┌────────────────────────────────────────────────────────────────┐
│                     Docker Network                              │
│                   (mcp-for-splunk_splunk-network)              │
│                                                                 │
│  ┌──────────────┐        ┌──────────────┐      ┌────────────┐│
│  │   Traefik    │───────▶│ MCP Server   │◀─────│ Inspector  ││
│  │ 172.19.0.2   │        │ 172.19.0.3   │      │172.19.0.4  ││
│  │              │        │ Port: 8003   │      │            ││
│  └──────────────┘        └──────────────┘      └────────────┘│
│         │                        │                             │
└─────────┼────────────────────────┼─────────────────────────────┘
          │                        │
          │                        │
    Port 8003                 Port 8004
    (Traefik)                 (Direct)
          │                        │
          ▼                        ▼
     Your Client             Your Client
```

### Port Mapping

```yaml
# Traefik
ports:
  - "8003:8003"  # External:Internal

# MCP Server
ports:
  - "8004:8003"  # Direct access (Host:8004 -> Container:8003)
```

### Traefik Configuration

The Traefik routing is configured via Docker labels:

```yaml
labels:
  # Router configuration
  - "traefik.http.routers.mcp-server.rule=PathPrefix(`/mcp`)"
  - "traefik.http.routers.mcp-server.entrypoints=mcp"
  
  # Backend service pointing to container port 8003
  - "traefik.http.services.mcp-server.loadbalancer.server.port=8003"
  
  # CORS middleware
  - "traefik.http.middlewares.mcp-cors.headers.accesscontrolalloworiginlist=*"
  - "traefik.http.routers.mcp-server.middlewares=mcp-cors"
```

## Verification

### Check Traefik Backend Status

```bash
# Via Traefik API
curl -s "http://localhost:8081/api/http/services/mcp-server@docker" | jq
```

**Expected output:**
```json
{
  "loadBalancer": {
    "servers": [
      {
        "url": "http://172.19.0.3:8003"
      }
    ]
  },
  "serverStatus": {
    "http://172.19.0.3:8003": "UP"
  }
}
```

### Test MCP Endpoint (via Traefik)

```bash
# The MCP endpoint requires proper headers
curl -X POST \
  -H "Content-Type: application/json" \
  -H "Accept: text/event-stream" \
  http://localhost:8003/mcp

# Should return MCP protocol response (not an error)
```

### Test Direct Health Check

```bash
# Direct access (bypasses Traefik path prefix)
curl http://localhost:8004/health

# Via Traefik (must include /mcp prefix due to PathPrefix rule)
# Note: Health endpoint doesn't require MCP headers
curl http://localhost:8004/health  # Direct works
```

### Check Traefik Logs

```bash
# View routing activity
docker logs traefik-dev --tail 20

# Should show successful routing:
# 172.19.0.1 - "POST /mcp HTTP/1.1" 200 ... "mcp-server@docker" "http://172.19.0.3:8003"
```

## MCP Client Configuration

### Option 1: Via Traefik (Recommended for Production)

```json
{
  "mcpServers": {
    "splunk": {
      "url": "http://localhost:8003/mcp",
      "transport": "streamable-http"
    }
  }
}
```

**Benefits:**
- ✅ Production-ready
- ✅ Load balancing support
- ✅ CORS handling via middleware
- ✅ Easy to add multiple backends
- ✅ Monitoring via Traefik dashboard

### Option 2: Direct Access (For Development)

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

**Benefits:**
- ✅ Lower latency (no proxy)
- ✅ Simpler debugging
- ✅ Direct server logs
- ✅ Isolated testing

## MCP Inspector Configuration

The Inspector is now configured to use **internal Docker network** with Traefik's backend:

```yaml
# Inspector connects internally to:
http://mcp-server-dev:8003/mcp

# Not through Traefik, but directly to container port 8003
```

This is optimal because:
- Inspector is in the same Docker network
- No need to go through Traefik for internal communication
- Faster communication (no proxy overhead)
- Simpler configuration

## Traefik Dashboard

Access the Traefik dashboard to monitor routing:

```bash
open http://localhost:8081/dashboard/
```

**Features:**
- View all routers and services
- Check backend health status
- Monitor request metrics
- Debug routing rules

## Troubleshooting

### Issue: 502 Bad Gateway

**Symptoms:**
```bash
curl http://localhost:8003/mcp
# Returns: Bad Gateway
```

**Check:**
1. Container is running: `docker ps | grep mcp-server`
2. Traefik can reach backend: `docker logs traefik-dev | tail`
3. Backend port matches label: Should be `8003`

**Fix:**
```bash
# Recreate container to update labels
docker compose -f docker-compose-dev.yml up -d --force-recreate mcp-server-dev
```

### Issue: 404 Not Found

**Symptoms:**
```bash
curl http://localhost:8003/health
# Returns: 404 page not found
```

**Cause:** Missing `/mcp` path prefix (due to `PathPrefix` rule)

**Fix:** Traefik routes only paths starting with `/mcp`:
```bash
# Direct health check (bypasses Traefik)
curl http://localhost:8004/health  # ✅ Works

# MCP endpoint via Traefik
curl http://localhost:8003/mcp      # ✅ Works
```

### Issue: Connection Refused

**Symptoms:**
```bash
curl http://localhost:8003/mcp
# Returns: Connection refused
```

**Check:**
1. Traefik is running: `docker ps | grep traefik`
2. Port 8003 is exposed: Should show `0.0.0.0:8003->8003/tcp`

**Fix:**
```bash
# Restart Traefik
docker compose -f docker-compose-dev.yml restart traefik
```

## Comparison: Traefik vs Direct

| Feature | Via Traefik (8003) | Direct Access (8004) |
|---------|-------------------|---------------------|
| **Latency** | ~1-2ms overhead | Direct connection |
| **Load Balancing** | ✅ Supported | ❌ Single backend |
| **CORS** | ✅ Handled by middleware | ⚠️ Server config only |
| **Monitoring** | ✅ Traefik dashboard | ❌ Server logs only |
| **SSL/TLS** | ✅ Can terminate | ❌ Server only |
| **Rate Limiting** | ✅ Easy to add | ❌ Server only |
| **Multiple Backends** | ✅ Easy to add | ❌ Not supported |
| **Debugging** | ⚠️ Extra hop | ✅ Direct connection |
| **Production Ready** | ✅ Yes | ⚠️ Development only |

## Best Practices

### Development

Use **direct access** (port 8004) for:
- Local testing
- Debugging connection issues
- Performance testing without proxy
- Isolated development

### Staging/Production

Use **Traefik** (port 8003) for:
- Multi-client environments
- Load balancing across instances
- SSL/TLS termination
- Rate limiting and security
- Monitoring and metrics

## Configuration Summary

### Current docker-compose-dev.yml Settings

```yaml
mcp-server-dev:
  environment:
    - MCP_SERVER_PORT=8003  # Container listens on 8003
  ports:
    - "8004:8003"           # Direct access: host:8004 -> container:8003
  labels:
    # Traefik routes /mcp to container port 8003
    - "traefik.http.services.mcp-server.loadbalancer.server.port=8003"
```

### Traefik Entrypoints

```yaml
traefik:
  command:
    - --entrypoints.mcp.address=:8003
  ports:
    - "8003:8003"  # Traefik listens on 8003, routes to backend
```

## Testing Commands

```bash
# 1. Test Traefik routing
curl -X POST \
  -H "Content-Type: application/json" \
  -H "Accept: text/event-stream" \
  http://localhost:8003/mcp

# 2. Test direct access
curl -X POST \
  -H "Content-Type: application/json" \
  -H "Accept: text/event-stream" \
  http://localhost:8004/mcp

# 3. Check Traefik status
curl http://localhost:8081/api/http/services/mcp-server@docker

# 4. View Traefik logs
docker logs traefik-dev --tail 10

# 5. View MCP server logs
docker logs mcp-server-dev --tail 10
```

## Next Steps

1. ✅ **Traefik routing is working** - Use `http://localhost:8003/mcp`
2. ✅ **Direct access available** - Use `http://localhost:8004/mcp` for debugging
3. ✅ **Inspector configured** - Uses internal network connection
4. 📊 **Monitor via dashboard** - Visit `http://localhost:8081/dashboard/`

Choose the access method based on your use case:
- **Production/Staging**: Use Traefik (port 8003)
- **Development/Debugging**: Use Direct (port 8004)

Both routes are working and can be used simultaneously! 🚀




