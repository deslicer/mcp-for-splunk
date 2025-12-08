# MCP Inspector Internal Communication Architecture

## Overview

This document explains how the MCP Inspector communicates with the MCP Server internally within the Docker network.

## Network Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                    Docker Network: splunk-network                    │
│                         (172.19.0.0/16)                              │
│                                                                       │
│  ┌──────────────────┐      ┌──────────────────┐      ┌───────────┐ │
│  │  Traefik Proxy   │      │   MCP Server     │      │  Inspector │ │
│  │  172.19.0.2      │      │   172.19.0.3     │      │ 172.19.0.4 │ │
│  │  (traefik-dev)   │      │ (mcp-server-dev) │      │(inspector) │ │
│  └──────────────────┘      └──────────────────┘      └───────────┘ │
│          │                          │                       │         │
│          │                          │                       │         │
│   Port 8090,8003                Port 8001             Port 6274,6277 │
│   Port 8081                         │                       │         │
└─────────────────────────────────────────────────────────────────────┘
          │                          │                       │
          │                          │                       │
          ▼                          ▼                       ▼
   Host: 8090,8003              (internal)           Host: 6274,6277
   Host: 8081                                         
```

## Internal Communication Flow

### 1. **Inspector → MCP Server (Internal Docker Network)**

The Inspector container connects to the MCP server using the **internal Docker DNS name**:

```bash
# Inspector connects to:
http://mcp-server-dev:8001/mcp

# NOT localhost or external IP!
```

**Configuration in docker-compose-dev.yml:**

```yaml
mcp-inspector:
  command: >
    npx @modelcontextprotocol/inspector \
      --transport streamable-http \
      --server-url http://mcp-server-dev:8001/mcp
```

**Key Points:**
- Uses container name `mcp-server-dev` as hostname (Docker DNS)
- Connects to internal port `8001` (not exposed to host)
- Uses `/mcp` endpoint path
- Communication stays within Docker network (fast & secure)

### 2. **Browser → Inspector (External Access)**

Your browser connects to the Inspector UI via exposed ports:

```bash
# Inspector UI (web interface)
http://localhost:6274

# Inspector Proxy (WebSocket server)
http://localhost:6277
```

### 3. **External → MCP Server (via Traefik)**

External clients can access the MCP server through Traefik:

```bash
# Through Traefik reverse proxy
http://localhost:8003/mcp

# Traefik forwards to: http://mcp-server-dev:8001/mcp
```

## Port Mapping Reference

| Service | Internal Port | External Port | Purpose |
|---------|--------------|---------------|---------|
| **MCP Server** | 8001 | 8003 (via Traefik) | MCP API endpoint |
| **Inspector UI** | 6274 | 6274 | Web interface |
| **Inspector Proxy** | 6277 | 6277 | WebSocket server |
| **Traefik Dashboard** | 8080 | 8081 | Monitoring UI |
| **Traefik HTTP** | 80 | 8090 | HTTP entrypoint |

## Network Configuration

### Docker Network: `splunk-network`

```yaml
networks:
  splunk-network:
    name: mcp-for-splunk_splunk-network
    driver: bridge
    attachable: true
```

**Features:**
- All containers share the same network
- Docker provides built-in DNS resolution
- Containers can communicate using service names
- Network isolation from other Docker containers

### Service Dependencies

```yaml
mcp-inspector:
  depends_on:
    - traefik
    - mcp-server-dev
  networks:
    - splunk-network
```

This ensures:
1. MCP Server starts before Inspector
2. Traefik is ready for routing
3. All services are on the same network

## Testing Internal Communication

### 1. Test from Host to Inspector

```bash
# Check Inspector UI is accessible
curl http://localhost:6274

# Check Inspector Proxy
curl http://localhost:6277
```

### 2. Test Internal DNS Resolution

```bash
# From inside Inspector container
docker exec mcp-inspector-dev ping mcp-server-dev

# From inside MCP Server container
docker exec mcp-server-dev ping mcp-inspector-dev
```

### 3. Test MCP Server Endpoint (Internal)

```bash
# From inside Inspector container
docker exec mcp-inspector-dev curl http://mcp-server-dev:8001/health

# Expected output:
# {"status":"healthy","splunk_connection":"connected",...}
```

### 4. Test MCP Server Endpoint (External via Traefik)

```bash
# From host machine
curl http://localhost:8003/health
```

## Common Issues & Solutions

### ❌ Issue: Inspector can't connect to MCP Server

**Symptoms:**
```
Error: Connection refused to localhost:8001
```

**Cause:** Inspector is trying to use `localhost` instead of Docker service name

**Solution:** Check `docker-compose-dev.yml` line 69:
```yaml
--server-url http://mcp-server-dev:8001/mcp  # ✅ Correct
--server-url http://localhost:8001/mcp       # ❌ Wrong
```

### ❌ Issue: MCP Server not accessible from Inspector

**Symptoms:**
```
Error: getaddrinfo ENOTFOUND mcp-server-dev
```

**Cause:** Containers not on the same Docker network

**Solution:**
```bash
# Check network membership
docker network inspect mcp-for-splunk_splunk-network

# Restart with proper network configuration
docker compose -f docker-compose-dev.yml down
docker compose -f docker-compose-dev.yml up -d
```

### ❌ Issue: Port conflicts

**Symptoms:**
```
Error: Bind for 0.0.0.0:6274 failed: port is already allocated
```

**Solution:**
```bash
# Find process using the port
lsof -i :6274

# Kill the process or change port in docker-compose-dev.yml
```

## Security Considerations

### Internal Network Security

✅ **Secure by default:**
- MCP Server port 8001 is **NOT** exposed to host
- Only accessible within Docker network
- Traefik acts as reverse proxy and firewall

### Authentication

⚠️ **Development Mode:**
```yaml
environment:
  - DANGEROUSLY_OMIT_AUTH=true  # Only for development!
```

🔒 **Production Mode:**
- Remove `DANGEROUSLY_OMIT_AUTH`
- Enable MCP authentication
- Use HTTPS with valid certificates
- Configure Traefik with TLS

## Architecture Benefits

### 1. **Network Isolation**
- MCP Server not directly exposed to host
- All traffic goes through Traefik
- Easy to add authentication/rate limiting

### 2. **Service Discovery**
- No hardcoded IP addresses
- Docker DNS handles name resolution
- Services can move/restart without config changes

### 3. **Scalability**
- Easy to add more MCP server instances
- Traefik can load balance between instances
- Independent scaling of each service

### 4. **Development Experience**
- Inspector and MCP Server on same network
- Fast communication (no external network)
- Easy debugging with Docker logs

## Monitoring & Debugging

### View Real-time Logs

```bash
# All services
docker compose -f docker-compose-dev.yml logs -f

# Specific service
docker logs -f mcp-server-dev
docker logs -f mcp-inspector-dev
docker logs -f traefik-dev
```

### Check Network Connectivity

```bash
# Show all containers on network
docker network inspect mcp-for-splunk_splunk-network \
  --format '{{range .Containers}}{{.Name}}: {{.IPv4Address}}{{"\n"}}{{end}}'

# Test connectivity between containers
docker exec mcp-inspector-dev ping -c 3 mcp-server-dev
```

### Traefik Dashboard

Access Traefik monitoring UI:
```
http://localhost:8081/dashboard/
```

Shows:
- Active routes
- Service health
- Request metrics
- Load balancer status

## Quick Reference Commands

```bash
# Start all services
docker compose -f docker-compose-dev.yml up -d

# Start specific services
docker compose -f docker-compose-dev.yml up -d mcp-server-dev mcp-inspector

# View logs
docker compose -f docker-compose-dev.yml logs -f

# Restart after config changes
docker compose -f docker-compose-dev.yml down
docker compose -f docker-compose-dev.yml up -d

# Check service health
docker compose -f docker-compose-dev.yml ps

# Access Inspector UI
open http://localhost:6274
```

## Summary

The MCP Inspector communicates with the MCP Server using:

1. **Internal Docker network** (`splunk-network`)
2. **Docker service name** as hostname (`mcp-server-dev`)
3. **Internal port** (8001) not exposed to host
4. **Streamable HTTP** transport protocol

This architecture provides:
- ✅ Fast internal communication
- ✅ Network isolation and security
- ✅ Easy service discovery
- ✅ Simple scaling and deployment




