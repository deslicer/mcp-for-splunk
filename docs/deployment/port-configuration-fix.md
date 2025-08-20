# Port Configuration Fix Documentation

## Overview

This document explains the fixes applied to resolve port mismatch and dependency issues in the MCP Server for Splunk Docker Compose configurations.

## Issues Fixed

### 1. Port Mismatch in Development Mode

**Problem**: The MCP server container was defaulting to port 8000, but Traefik's load balancer and MCP Inspector were configured to connect to port 8003, causing connection failures.

**Solution**: Standardized development mode to use port 8003 consistently across all services.

### 2. Unconditional Dependency on Splunk Container

**Problem**: The `mcp-server-dev` service unconditionally depended on `so1`, which is only available when the `splunk` profile is active, potentially causing startup issues.

**Solution**: Added the `splunk` profile to `mcp-server-dev` to make the dependency conditional.

## Configuration Summary

### Development Mode (`docker-compose-dev.yml`)

| Service | Container Port | External Port | Profile | Notes |
|---------|----------------|---------------|---------|-------|
| Traefik MCP Entrypoint | - | `${MCP_SERVER_PORT:-8003}` | - | Load balancer entry point |
| MCP Server | 8003 | - | `splunk` | No direct port mapping, Traefik handles access |
| MCP Inspector | 6274 | 6274 | - | Connects to MCP server on port 8003 |
| Splunk (so1) | 8000 | 9000 | `splunk` | Optional, only when profile is active |

**Key Features**:
- Hot reload enabled
- Port 8003 used consistently
- Splunk container optional (profile-based)
- MCP Inspector pre-configured for port 8003

### Production Mode (`docker-compose.yml`)

| Service | Container Port | External Port | Profile | Notes |
|---------|----------------|---------------|---------|-------|
| Traefik MCP Entrypoint | - | 8001 | - | Fixed port for production |
| MCP Server | 8000 | - | - | No direct port mapping |
| MCP Inspector | 6274 | 6274 | - | Connects to MCP server on port 8000 |
| Splunk (so1) | 8000 | 9000 | `splunk` | Optional, only when profile is active |

**Key Features**:
- Hot reload disabled for performance
- Port 8001 for external access (Traefik)
- Port 8000 for internal MCP server
- Fixed, predictable port configuration

## Environment Variables

### Default Ports

| Mode | MCP_SERVER_PORT | Traefik Entrypoint | MCP Server Container |
|------|------------------|-------------------|---------------------|
| Development | 8003 | 8003 | 8003 |
| Production | 8001 | 8001 | 8000 |

### Configuration Files

- **`.env`**: Set `MCP_SERVER_PORT` to override defaults
- **`env.example`**: Updated to use port 8003 as default
- **Scripts**: Updated to use port 8003 as default for consistency

## Usage Examples

### Start Development Environment

```bash
# Start with Splunk container
docker compose -f docker-compose-dev.yml --profile splunk up -d

# Start without Splunk container
docker compose -f docker-compose-dev.yml up -d
```

### Start Production Environment

```bash
# Start with Splunk container
docker compose --profile splunk up -d

# Start without Splunk container
docker compose up -d
```

### Custom Port Configuration

```bash
# Override default port
MCP_SERVER_PORT=8005 docker compose -f docker-compose-dev.yml up -d
```

## Script Updates

The following scripts have been updated to use port 8003 as the default:

- `scripts/build_and_run.sh`
- `scripts/build_and_run.ps1`
- `scripts/build_and_run.bat`

## Verification

### Check Service Status

```bash
# Check if services are running
docker compose -f docker-compose-dev.yml ps

# Check MCP server logs
docker compose -f docker-compose-dev.yml logs mcp-server-dev
```

### Test MCP Inspector Connection

1. Open `http://localhost:6274`
2. Set server URL to `http://localhost:8003/mcp/` (dev) or `http://localhost:8001/mcp/` (prod)
3. Click Connect to verify successful connection

### Test Traefik Routing

```bash
# Test MCP server through Traefik
curl http://localhost:8003/mcp/  # Development
curl http://localhost:8001/mcp/  # Production
```

## Troubleshooting

### Port Already in Use

If port 8003 is already in use:

```bash
# Check what's using the port
lsof -i :8003

# Use a different port
MCP_SERVER_PORT=8005 docker compose -f docker-compose-dev.yml up -d
```

### Connection Refused

If MCP Inspector can't connect:

1. Verify MCP server is running: `docker compose -f docker-compose-dev.yml ps`
2. Check MCP server logs: `docker compose -f docker-compose-dev.yml logs mcp-server-dev`
3. Verify Traefik is routing correctly: `curl http://localhost:8003/mcp/`

### Splunk Container Issues

If using the `splunk` profile:

1. Ensure Docker has sufficient resources (4GB+ RAM recommended)
2. Check Splunk license requirements
3. Verify health check: `docker compose -f docker-compose-dev.yml exec so1 curl -s -k https://localhost:8089/services/server/info`

## Migration Notes

### From Previous Versions

- **Port 8001 → 8003**: Development mode now uses port 8003 by default
- **Profile-based dependencies**: MCP server now respects the `splunk` profile
- **Consistent configuration**: All services now use the same port configuration

### Environment File Updates

If you have an existing `.env` file:

```bash
# Update your .env file
MCP_SERVER_PORT=8003  # For development mode
# or
MCP_SERVER_PORT=8001  # For production mode
```

## Best Practices

1. **Use profiles**: Always specify the `splunk` profile when you need Splunk functionality
2. **Port consistency**: Stick to the default ports unless you have conflicts
3. **Environment isolation**: Use different `.env` files for different environments
4. **Health checks**: Monitor service health, especially when using profiles

## Support

For issues related to port configuration:

1. Check this documentation
2. Review service logs: `docker compose logs <service-name>`
3. Verify environment variables: `docker compose config`
4. Check GitHub issues for similar problems
