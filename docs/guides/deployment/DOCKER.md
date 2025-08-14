# MCP Server for Splunk - Docker Setup

This guide explains how to build and run the MCP Server for Splunk using Docker and docker-compose.

## 🚀 Quick Start

### Prerequisites

- Docker and Docker Compose installed
- Splunk Enterprise license file (if using licensed version)

### 1. Build and Run

The easiest way to get started is using the provided script:

```bash
./scripts/build_and_run.sh
```

This script will:
- Check for Docker availability
- Create a `.env` file from `env.example` if needed
- Build the Docker image
- Start all services with docker-compose
- Show service status and URLs

### 2. Manual Setup

If you prefer manual control:

```bash
# Create environment file
cp env.example .env
# Edit .env with your configuration

# Build and start services
docker-compose build
docker-compose up -d

# Check status
docker-compose ps
docker-compose logs mcp-server
```

## 🔧 Configuration

### Environment Variables

Edit the `.env` file to configure your setup:

```env
# Splunk Configuration
SPLUNK_HOST=localhost
SPLUNK_PORT=8089
SPLUNK_USERNAME=admin
SPLUNK_PASSWORD=Chang3d!
SPLUNK_VERIFY_SSL=false

# MCP Server Configuration
MCP_SERVER_MODE=docker
MCP_SERVER_HOST=0.0.0.0
MCP_SERVER_PORT=8000
```

### Service Architecture

The docker-compose setup includes:

- **so1**: Splunk Enterprise container
- **mcp-server**: MCP Server for Splunk (your custom server)
- **traefik**: Reverse proxy and load balancer

## 🌐 Service URLs

Once running, you can access:

- **Traefik Dashboard**: http://localhost:8080
- **Splunk Web UI**: http://localhost:9000 (admin/Chang3d!)
- **MCP Server**: http://localhost:8001
- **MCP Inspector**: http://localhost:6274

## 🔍 Testing the MCP Server

### Using the Test Script

```bash
# In another terminal, test the server
MCP_SERVER_MODE=docker python test_mcp_server.py
```

### Using MCP Inspector

Navigate to http://localhost:6274 to use the MCP Inspector for interactive testing.

### Using curl

```bash
# Test SSE endpoint
curl -v http://localhost:8001/mcp/sse

# Check server logs
docker-compose logs -f mcp-server
```

## 🐛 Troubleshooting

### Common Issues

1. **Port conflicts**: If ports 8000, 8001, 8080, or 9000 are in use, modify the docker-compose.yml

2. **Splunk not ready**: Wait for Splunk to fully initialize (2-3 minutes)

3. **MCP Server connection errors**: Check that SPLUNK_HOST in .env matches the service name

### Checking Logs

```bash
# All services
docker-compose logs

# Specific service
docker-compose logs mcp-server
docker-compose logs so1
docker-compose logs traefik

# Follow logs
docker-compose logs -f mcp-server
```

### Service Status

```bash
# Check container status
docker-compose ps

# Check container health
docker-compose exec mcp-server curl http://localhost:8000/mcp/sse
```

## 🔄 Development Workflow

### Rebuilding After Code Changes

```bash
# Stop services
docker-compose down

# Rebuild MCP server image
docker-compose build mcp-server

# Start services
docker-compose up -d

# Check logs
docker-compose logs -f mcp-server
```

### Running in Development Mode

For development, you can run the MCP server locally while keeping Splunk in Docker:

```bash
# Start only Splunk
docker-compose up -d so1

# Run MCP server locally
export MCP_SERVER_MODE=docker
python src/server.py
```

## 🛑 Stopping Services

```bash
# Stop all services
docker-compose down

# Stop and remove volumes (WARNING: loses Splunk data)
docker-compose down -v
```

## 📊 Network Configuration

The setup uses two Docker networks:

- **splunk-network**: For Splunk and MCP server communication
- **traefik-network**: For external access via Traefik

The MCP server can communicate with Splunk using the hostname `so1` or `localhost` depending on your configuration.

## 🔐 Security Notes

- Default Splunk credentials are `admin/Chang3d!`
- SSL verification is disabled by default for development
- For production use, enable SSL and use proper certificates
- Consider using Docker secrets for sensitive data

## 📈 Performance Tips

- Use volume mounts for Splunk data persistence in production
- Monitor container resource usage with `docker stats`
- Adjust Traefik load balancer settings for high traffic
- Consider using multiple MCP server replicas for scaling
