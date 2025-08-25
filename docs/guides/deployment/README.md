# Deployment Guide

This section covers deployment strategies for the MCP Server for Splunk across different environments and use cases.

## 📋 Deployment Options

| Deployment Type | Best For | Complexity | Startup Time |
|----------------|----------|------------|--------------|
| **[Local Development](#local-development)** | Development, testing | Low | ~10 seconds |
| **[Docker Compose](#docker-compose)** | Local testing, demos | Medium | ~2 minutes |
| **[Production Docker](production.md)** | Production environments | Medium | ~5 minutes |
| Kubernetes (coming soon) | Enterprise, scale | High | ~10 minutes |
| Cloud Platforms (coming soon) | Cloud-native deployments | Medium-High | ~5-15 minutes |

## 🚀 Quick Deployment

### Local Development

Perfect for development and AI client integration:

```bash
# Clone and setup
git clone https://github.com/your-org/mcp-for-splunk.git
cd mcp-for-splunk

# One-command setup
./scripts/build_and_run.sh    # macOS/Linux
.\scripts\build_and_run.ps1   # Windows
```

**What you get:**
- MCP server on `http://localhost:8000+` (auto-detected port)
- MCP Inspector on `http://localhost:6274` (if Node.js available)
- Ready for stdio-based AI clients (Claude, Cursor)

### Docker Compose

Full stack with monitoring and testing tools:

```bash
# Basic stack
docker-compose up -d

# Development stack with hot reload
docker-compose -f docker-compose-dev.yml up -d
```

**What you get:**
- MCP server behind Traefik: `http://localhost:8001/mcp/`
- MCP Inspector: `http://localhost:3001`
- Traefik dashboard: `http://localhost:8080`
- Optional Splunk Enterprise: `http://localhost:9000`

## 🏗️ Architecture Patterns

### Single-Tenant (Dedicated Instance)

Each deployment serves one Splunk environment:

```yaml
# docker-compose.yml
services:
  mcp-server:
    image: mcp-server-for-splunk:latest
    environment:
      - SPLUNK_HOST=your-splunk.company.com
      - SPLUNK_USERNAME=service-account
      - SPLUNK_PASSWORD=${SPLUNK_PASSWORD}
    ports:
      - "8001:8000"
```

### Multi-Tenant (Shared Instance)

One deployment serves multiple Splunk environments:

```yaml
# docker-compose.yml
services:
  mcp-server:
    image: mcp-server-for-splunk:latest
    # No default Splunk config - clients provide via headers
    ports:
      - "8001:8000"
```

Clients connect with environment-specific headers:
```bash
curl -H "X-Splunk-Host: tenant1.splunk.com" \
     -H "X-Splunk-Username: tenant1-user" \
     http://localhost:8001/mcp/
```

### High Availability

Load-balanced deployment with redundancy:

```yaml
# docker-compose.yml
services:
  traefik:
    image: traefik:v2.10
    # Load balancer configuration

  mcp-server-1:
    image: mcp-server-for-splunk:latest
    labels:
      - "traefik.enable=true"
      - "traefik.http.services.mcp.loadbalancer.server.port=8000"

  mcp-server-2:
    image: mcp-server-for-splunk:latest
    labels:
      - "traefik.enable=true"
      - "traefik.http.services.mcp.loadbalancer.server.port=8000"
```

## 🔧 Configuration Management

### Environment Variables

**Development:**
```env
SPLUNK_HOST=localhost
SPLUNK_USERNAME=admin
SPLUNK_PASSWORD=Chang3d!
SPLUNK_VERIFY_SSL=false
DEBUG=true
LOG_LEVEL=DEBUG
```

**Production:**
```env
SPLUNK_HOST=prod-splunk.company.com
SPLUNK_USERNAME=mcp-service-account
SPLUNK_VERIFY_SSL=true
LOG_LEVEL=INFO
ENABLE_METRICS=true
```

### Configuration Files

**docker-compose.override.yml** (local development):
```yaml
version: '3.8'
services:
  mcp-server:
    environment:
      - DEBUG=true
      - LOG_LEVEL=DEBUG
    volumes:
      - ./src:/app/src  # Hot reload
      - ./contrib:/app/contrib
```

**docker-compose.prod.yml** (production):
```yaml
version: '3.8'
services:
  mcp-server:
    restart: always
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"
    environment:
      - LOG_LEVEL=INFO
      - ENABLE_METRICS=true
```

## 📊 Monitoring and Observability

### Health Checks

Built-in health endpoints:

```bash
# Server health - Initialize session first
curl -X POST -H "Content-Type: application/json" -H "Accept: application/json, text/event-stream" \
  -d '{"jsonrpc":"2.0","id":"init","method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{"roots":{"listChanged":false}},"clientInfo":{"name":"test-client","version":"1.0.0"}}}' \
  http://localhost:8001/mcp/ -D /tmp/mcp_headers.txt

# Get server info using session ID
SESSION_ID=$(grep -i "mcp-session-id:" /tmp/mcp_headers.txt | cut -d' ' -f2 | tr -d '\r\n')
curl -X POST -H "Content-Type: application/json" -H "Accept: application/json, text/event-stream" \
  -H "mcp-session-id: $SESSION_ID" \
  -d '{"jsonrpc":"2.0","id":"test","method":"resources/read","params":{"uri":"info://server"}}' \
  http://localhost:8001/mcp/

# Metrics (if enabled)
curl http://localhost:8001/metrics
```

### Logging

Configure structured logging:

```yaml
# docker-compose.yml
services:
  mcp-server:
    environment:
      - LOG_FORMAT=json
      - LOG_LEVEL=INFO
    logging:
      driver: "fluentd"
      options:
        fluentd-address: localhost:24224
        tag: mcp-server
```

### Prometheus Metrics

Enable metrics collection:

```yaml
# docker-compose.yml
services:
  mcp-server:
    environment:
      - ENABLE_METRICS=true
      - METRICS_PORT=9090
    ports:
      - "9090:9090"  # Metrics endpoint

  prometheus:
    image: prom/prometheus
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
    ports:
      - "9091:9090"
```

## 🔒 Security Considerations

### Network Security

**Firewall Rules:**
```bash
# Allow MCP server access
ufw allow 8001/tcp

# Restrict metrics access (internal only)
ufw allow from 10.0.0.0/8 to any port 9090
```

**TLS Termination:**
```yaml
# docker-compose.yml
services:
  traefik:
    command:
      - "--certificatesresolvers.le.acme.email=admin@company.com"
      - "--certificatesresolvers.le.acme.storage=/letsencrypt/acme.json"
    labels:
      - "traefik.http.routers.mcp.tls.certresolver=le"
```

### Credential Management

**Docker Secrets:**
```yaml
# docker-compose.yml
services:
  mcp-server:
    secrets:
      - splunk_password
    environment:
      - SPLUNK_PASSWORD_FILE=/run/secrets/splunk_password

secrets:
  splunk_password:
    external: true
```

**Kubernetes Secrets:**
```yaml
apiVersion: v1
kind: Secret
metadata:
  name: splunk-credentials
type: Opaque
data:
  username: <base64-encoded-username>
  password: <base64-encoded-password>
```

## 🚨 Troubleshooting

### Common Issues

**Container Won't Start:**
```bash
# Check logs
docker logs mcp-server

# Check configuration
docker exec mcp-server env | grep SPLUNK

# Test manually
docker run -it --rm mcp-server-for-splunk:latest /bin/bash
```

**Network Connectivity:**
```bash
# Test from container
docker exec mcp-server curl -k https://splunk-server:8089/services/server/info

# Check DNS resolution
docker exec mcp-server nslookup splunk-server

# Verify port access
docker exec mcp-server telnet splunk-server 8089
```

**Performance Issues:**
```bash
# Monitor resource usage
docker stats mcp-server

# Check response times (using session-based health check)
curl -w "@curl-format.txt" -X POST -H "Content-Type: application/json" -H "Accept: application/json, text/event-stream" \
  -H "mcp-session-id: $SESSION_ID" \
  -d '{"jsonrpc":"2.0","id":"perf-test","method":"resources/read","params":{"uri":"info://server"}}' \
  http://localhost:8001/mcp/

# Review slow query logs
docker logs mcp-server | grep "slow_query"
```

## 📚 Deployment Guides

### Detailed Guides

- **[Production Deployment](production.md)** - Enterprise-ready deployment
- **[Docker Configuration](DOCKER.md)** - Container-specific setup
- Kubernetes Deployment (coming soon)
- Cloud Platforms (coming soon)

### Quick References

- **[Configuration Reference](../configuration/)** - All configuration options
- **[Security Guide](../security.md)**
- **[Monitoring Guide](../monitoring.md)**

## 🎯 Choosing Your Deployment

### Development & Testing
- **Local**: Individual developer setup
- **Docker Compose**: Team development, integration testing

### Production
- **Single Server**: Small deployments, proof of concept
- **Load Balanced**: High availability, multiple clients
- **Kubernetes**: Enterprise scale, auto-scaling
- **Cloud Native**: Cloud-managed infrastructure

### Decision Matrix

| Requirement | Local | Docker | Kubernetes | Cloud |
|-------------|-------|--------|------------|-------|
| **Development** | ✅ Best | ✅ Good | ❌ Overkill | ❌ Complex |
| **Testing** | ✅ Good | ✅ Best | ✅ Good | ✅ Good |
| **Small Production** | ❌ Risky | ✅ Good | ❌ Overkill | ✅ Best |
| **Enterprise** | ❌ No | ❌ Limited | ✅ Best | ✅ Best |
| **Multi-Tenant** | ❌ No | ✅ Limited | ✅ Best | ✅ Best |

---

**Ready to deploy?** Choose the guide that matches your environment and requirements!
