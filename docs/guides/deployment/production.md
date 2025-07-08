# Deployment Guide

This guide covers production deployment, configuration management, and operational considerations for the MCP Server for Splunk modular architecture.

## Deployment Options

### 1. Local Development (stdio Mode)

**Use Case:** Development, testing, local automation

```bash
# Setup environment
uv sync --dev
cp env.example .env

# Configure Splunk connection
# Edit .env with your Splunk details

# Start local server
uv run python src/server.py
```

**Client Configuration (Cursor):**
```json
{
  "mcpServers": {
    "mcp-server-for-splunk": {
      "command": "uv",
      "args": [
        "--directory", "/path/to/mcp-server-for-splunk/",
        "run", "python", "src/server.py"
      ],
      "env": {
        "SPLUNK_HOST": "localhost",
        "SPLUNK_PORT": "8089",
        "SPLUNK_USERNAME": "admin",
        "SPLUNK_PASSWORD": "Chang3d!",
        "SPLUNK_VERIFY_SSL": "false"
      }
    }
  }
}
```

### 2. Docker Development Stack

**Use Case:** Development with integrated services

```bash
# One-command setup
./scripts/build_and_run.sh

# Or manual setup
docker-compose build
docker-compose up -d
```

**Services Included:**
- MCP Server (modular) on port 8000
- Traefik Load Balancer on port 8001
- Splunk Enterprise on port 9000
- MCP Inspector on port 3001
- Traefik Dashboard on port 8080

### 3. Production HTTP Deployment

**Use Case:** Production environments, web agents, multiple clients

```bash
# Production docker-compose
docker-compose -f docker-compose.prod.yml up -d
```

**Production Features:**
- Load balancing with Traefik
- Health monitoring
- SSL termination
- Persistent volumes
- Restart policies
- Resource limits

## Configuration Management

### Environment Variables

**Core Configuration (.env):**
```bash
# Splunk Connection
SPLUNK_HOST=your-splunk-host.com
SPLUNK_PORT=8089
SPLUNK_USERNAME=service-account
SPLUNK_PASSWORD=secure-password
SPLUNK_VERIFY_SSL=true

# MCP Server
MCP_SERVER_HOST=0.0.0.0
MCP_SERVER_PORT=8000
MCP_SERVER_MODE=http
MCP_LOG_LEVEL=INFO

# Docker specific
COMPOSE_PROJECT_NAME=mcp-splunk
```

**Production Environment:**
```bash
# High-availability Splunk
SPLUNK_HOST=splunk-cluster.internal.com
SPLUNK_PORT=8089
SPLUNK_VERIFY_SSL=true

# Security
SPLUNK_USERNAME=mcp-service-account
SPLUNK_PASSWORD=${VAULT_SPLUNK_PASSWORD}

# Performance
MCP_WORKER_THREADS=10
MCP_CONNECTION_POOL_SIZE=20
MCP_REQUEST_TIMEOUT=300

# Monitoring
MCP_METRICS_ENABLED=true
MCP_HEALTH_CHECK_INTERVAL=30
```

### Configuration Files

**Tool Registry (config/tool_registry.yaml):**
```yaml
# Tool configuration management
tools:
  enabled_categories:
    - core
    - security
    - devops
  
  disabled_tools:
    - dangerous_tool
    - experimental_feature
  
  rate_limits:
    search_tools: 10/minute
    admin_tools: 5/minute
    
  timeouts:
    search_timeout: 300
    connection_timeout: 30
```

**Security Configuration (config/security.yaml):**
```yaml
# Security settings
authentication:
  enabled: true
  method: token  # token, oauth, ldap
  
authorization:
  rbac_enabled: true
  default_role: user
  
input_validation:
  max_query_length: 10000
  allowed_spl_commands:
    - search
    - stats
    - eval
    - where
  
  blocked_spl_commands:
    - delete
    - output
    - script
```

## Docker Production Setup

### Multi-stage Dockerfile

```dockerfile
# Build stage
FROM python:3.11-slim as builder

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

# Set environment
ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy

# Install dependencies
WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-install-project --no-dev

# Production stage
FROM python:3.11-slim

# Create non-root user
RUN groupadd --gid 1000 mcpuser && \
    useradd --uid 1000 --gid 1000 --shell /bin/bash --create-home mcpuser

# Copy virtual environment
COPY --from=builder --chown=mcpuser:mcpuser /app/.venv /app/.venv

# Copy application
COPY --chown=mcpuser:mcpuser . /app
WORKDIR /app

# Set environment
ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONPATH="/app"

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Switch to non-root user
USER mcpuser

# Expose port
EXPOSE 8000

# Start server
CMD ["python", "src/server.py", "--host", "0.0.0.0", "--port", "8000"]
```

### Production docker-compose.yml

```yaml
version: '3.8'

services:
  mcp-server:
    build: .
    container_name: mcp-server
    environment:
      - SPLUNK_HOST=${SPLUNK_HOST}
      - SPLUNK_PORT=${SPLUNK_PORT}
      - SPLUNK_USERNAME=${SPLUNK_USERNAME}
      - SPLUNK_PASSWORD=${SPLUNK_PASSWORD}
      - MCP_SERVER_HOST=0.0.0.0
      - MCP_SERVER_PORT=8000
    volumes:
      - ./config:/app/config:ro
      - ./logs:/app/logs
    networks:
      - mcp-network
    restart: unless-stopped
    deploy:
      resources:
        limits:
          memory: 512M
          cpus: "0.5"
        reservations:
          memory: 256M
          cpus: "0.25"
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s

  traefik:
    image: traefik:v3.0
    container_name: mcp-traefik
    command:
      - "--api.dashboard=true"
      - "--api.insecure=true"
      - "--providers.docker=true"
      - "--providers.docker.exposedbydefault=false"
      - "--entrypoints.web.address=:80"
      - "--entrypoints.websecure.address=:443"
      - "--certificatesresolvers.letsencrypt.acme.tlschallenge=true"
      - "--certificatesresolvers.letsencrypt.acme.email=${LETSENCRYPT_EMAIL}"
      - "--certificatesresolvers.letsencrypt.acme.storage=/letsencrypt/acme.json"
    ports:
      - "80:80"
      - "443:443"
      - "8080:8080"
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock:ro
      - ./letsencrypt:/letsencrypt
    networks:
      - mcp-network
    restart: unless-stopped
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.mcp-server.rule=Host(`${MCP_DOMAIN}`)"
      - "traefik.http.routers.mcp-server.entrypoints=websecure"
      - "traefik.http.routers.mcp-server.tls.certresolver=letsencrypt"
      - "traefik.http.services.mcp-server.loadbalancer.server.port=8000"

networks:
  mcp-network:
    driver: bridge

volumes:
  letsencrypt:
```

## Kubernetes Deployment

### Deployment Manifest

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: mcp-server
  namespace: mcp-splunk
spec:
  replicas: 3
  selector:
    matchLabels:
      app: mcp-server
  template:
    metadata:
      labels:
        app: mcp-server
    spec:
      serviceAccountName: mcp-server
      containers:
      - name: mcp-server
        image: mcp-server:latest
        ports:
        - containerPort: 8000
        env:
        - name: SPLUNK_HOST
          valueFrom:
            secretKeyRef:
              name: splunk-credentials
              key: host
        - name: SPLUNK_USERNAME
          valueFrom:
            secretKeyRef:
              name: splunk-credentials
              key: username
        - name: SPLUNK_PASSWORD
          valueFrom:
            secretKeyRef:
              name: splunk-credentials
              key: password
        resources:
          requests:
            memory: "256Mi"
            cpu: "250m"
          limits:
            memory: "512Mi"
            cpu: "500m"
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /ready
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 5
        volumeMounts:
        - name: config
          mountPath: /app/config
          readOnly: true
      volumes:
      - name: config
        configMap:
          name: mcp-server-config
```

### Service and Ingress

```yaml
apiVersion: v1
kind: Service
metadata:
  name: mcp-server-service
  namespace: mcp-splunk
spec:
  selector:
    app: mcp-server
  ports:
  - port: 80
    targetPort: 8000
  type: ClusterIP

---
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: mcp-server-ingress
  namespace: mcp-splunk
  annotations:
    kubernetes.io/ingress.class: nginx
    cert-manager.io/cluster-issuer: letsencrypt-prod
    nginx.ingress.kubernetes.io/cors-allow-origin: "*"
spec:
  tls:
  - hosts:
    - mcp.your-domain.com
    secretName: mcp-server-tls
  rules:
  - host: mcp.your-domain.com
    http:
      paths:
      - path: /mcp
        pathType: Prefix
        backend:
          service:
            name: mcp-server-service
            port:
              number: 80
```

## Security Hardening

### SSL/TLS Configuration

**Certificate Management:**
```bash
# Generate self-signed certificate for development
openssl req -x509 -newkey rsa:4096 -keyout key.pem -out cert.pem -days 365 -nodes

# Production with Let's Encrypt
certbot certonly --standalone -d mcp.your-domain.com
```

**Traefik SSL Configuration:**
```yaml
# traefik.yml
entryPoints:
  websecure:
    address: ":443"
    http:
      tls:
        options: default

tls:
  options:
    default:
      sslProtocols:
        - "TLSv1.2"
        - "TLSv1.3"
      cipherSuites:
        - "TLS_ECDHE_RSA_WITH_AES_256_GCM_SHA384"
        - "TLS_ECDHE_RSA_WITH_CHACHA20_POLY1305"
        - "TLS_ECDHE_RSA_WITH_AES_128_GCM_SHA256"
```

### Authentication and Authorization

**JWT Token Authentication:**
```python
# Security middleware
class AuthenticationMiddleware:
    def __init__(self, secret_key: str):
        self.secret_key = secret_key
    
    async def authenticate(self, request: Request) -> Optional[User]:
        token = request.headers.get("Authorization")
        
        if not token or not token.startswith("Bearer "):
            return None
            
        try:
            payload = jwt.decode(token[7:], self.secret_key, algorithms=["HS256"])
            return User.from_payload(payload)
        except jwt.InvalidTokenError:
            return None
```

**Role-Based Access Control:**
```python
# RBAC implementation
class RBACMiddleware:
    def __init__(self, permissions: Dict[str, List[str]]):
        self.permissions = permissions
    
    def check_permission(self, user: User, tool_name: str) -> bool:
        user_permissions = self.permissions.get(user.role, [])
        return tool_name in user_permissions or "admin" in user_permissions
```

## Monitoring and Observability

### Health Checks

**Application Health Endpoint:**
```python
@app.get("/health")
async def health_check():
    """Comprehensive health check."""
    
    checks = {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": __version__,
        "checks": {
            "database": await check_database(),
            "splunk": await check_splunk_connection(),
            "memory": check_memory_usage(),
            "disk": check_disk_space()
        }
    }
    
    # Determine overall status
    if any(not check["healthy"] for check in checks["checks"].values()):
        checks["status"] = "unhealthy"
        
    return checks
```

### Metrics and Logging

**Prometheus Metrics:**
```python
from prometheus_client import Counter, Histogram, Gauge

# Metrics
tool_requests_total = Counter('mcp_tool_requests_total', 'Total tool requests', ['tool_name', 'status'])
tool_duration_seconds = Histogram('mcp_tool_duration_seconds', 'Tool execution time', ['tool_name'])
active_connections = Gauge('mcp_active_connections', 'Active Splunk connections')

# Usage in tools
async def execute_with_metrics(self, ctx: Context, **kwargs):
    start_time = time.time()
    
    try:
        result = await self.execute(ctx, **kwargs)
        tool_requests_total.labels(tool_name=self.METADATA.name, status='success').inc()
        return result
        
    except Exception as e:
        tool_requests_total.labels(tool_name=self.METADATA.name, status='error').inc()
        raise
        
    finally:
        duration = time.time() - start_time
        tool_duration_seconds.labels(tool_name=self.METADATA.name).observe(duration)
```

**Structured Logging:**
```python
import structlog

# Configure structured logging
logging.basicConfig(
    format="%(message)s",
    stream=sys.stdout,
    level=logging.INFO,
)

logger = structlog.get_logger()

# Usage in tools
async def execute(self, ctx: Context, **kwargs):
    logger.info(
        "Tool execution started",
        tool=self.METADATA.name,
        session_id=ctx.session.session_id,
        parameters=kwargs
    )
    
    try:
        result = await self._perform_operation(kwargs)
        
        logger.info(
            "Tool execution completed",
            tool=self.METADATA.name,
            session_id=ctx.session.session_id,
            duration=time.time() - start_time,
            result_count=len(result.get('data', []))
        )
        
        return self.format_success_response(result)
        
    except Exception as e:
        logger.error(
            "Tool execution failed",
            tool=self.METADATA.name,
            session_id=ctx.session.session_id,
            error=str(e),
            exc_info=True
        )
        raise
```

## Performance Optimization

### Connection Pooling

```python
from sqlalchemy.pool import QueuePool

class SplunkConnectionPool:
    def __init__(self, max_connections: int = 20):
        self.pool = QueuePool(
            self._create_connection,
            max_overflow=10,
            pool_size=max_connections,
            recycle=3600  # Recycle connections every hour
        )
    
    async def get_connection(self):
        return await self.pool.connect()
    
    def _create_connection(self):
        return splunklib.client.connect(**splunk_config)
```

### Caching Strategy

```python
from functools import lru_cache
import redis

# Redis caching for search results
redis_client = redis.Redis(host='redis', port=6379, db=0)

async def cached_search(query: str, timerange: str, ttl: int = 300):
    """Cache search results with TTL."""
    
    cache_key = f"search:{hash(query + timerange)}"
    
    # Try cache first
    cached_result = redis_client.get(cache_key)
    if cached_result:
        return json.loads(cached_result)
    
    # Execute search
    result = await execute_search(query, timerange)
    
    # Cache result
    redis_client.setex(cache_key, ttl, json.dumps(result))
    
    return result
```

### Resource Limits

```yaml
# Resource limits in docker-compose
deploy:
  resources:
    limits:
      memory: 1G
      cpus: "1.0"
    reservations:
      memory: 512M
      cpus: "0.5"

# Process limits
ulimits:
  nofile: 65536
  nproc: 4096
```

## Backup and Recovery

### Configuration Backup

```bash
#!/bin/bash
# backup_config.sh

BACKUP_DIR="/backups/mcp-server"
DATE=$(date +%Y%m%d_%H%M%S)

# Create backup directory
mkdir -p "$BACKUP_DIR/$DATE"

# Backup configuration files
cp -r config/ "$BACKUP_DIR/$DATE/"
cp .env "$BACKUP_DIR/$DATE/"
cp docker-compose.yml "$BACKUP_DIR/$DATE/"

# Backup custom tools
cp -r contrib/ "$BACKUP_DIR/$DATE/"

# Create archive
tar -czf "$BACKUP_DIR/mcp-server-config-$DATE.tar.gz" -C "$BACKUP_DIR" "$DATE"

# Clean old backups (keep last 30 days)
find "$BACKUP_DIR" -type f -name "*.tar.gz" -mtime +30 -delete

echo "Backup completed: $BACKUP_DIR/mcp-server-config-$DATE.tar.gz"
```

### Disaster Recovery

```bash
#!/bin/bash
# restore_config.sh

BACKUP_FILE="$1"
RESTORE_DIR="/tmp/mcp-restore"

if [ -z "$BACKUP_FILE" ]; then
    echo "Usage: $0 <backup-file.tar.gz>"
    exit 1
fi

# Extract backup
mkdir -p "$RESTORE_DIR"
tar -xzf "$BACKUP_FILE" -C "$RESTORE_DIR"

# Stop services
docker-compose down

# Restore files
cp -r "$RESTORE_DIR"/*/* ./

# Restart services
docker-compose up -d

echo "Configuration restored from $BACKUP_FILE"
```

This deployment guide provides comprehensive coverage of production deployment scenarios, from simple Docker setups to enterprise Kubernetes deployments, with security, monitoring, and operational best practices. 