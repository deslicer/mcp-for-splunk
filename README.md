# MCP Server for Splunk

A Model Context Protocol (MCP) server that provides seamless integration between Large Language Models (LLMs), AI agents, and Splunk instances (Enterprise/Cloud). This server exposes Splunk's powerful search and data management capabilities through standardized MCP tools.

## Features

- **MCP-compliant server** using FastMCP framework
- **Multiple transport modes**: stdio (local) and HTTP (remote server)
- **Comprehensive Splunk integration** with secure authentication
- **Production-ready deployment** with Docker containerization and Traefik load balancing
- **Health monitoring** and automatic service discovery
- **Real-time communication** with MCP clients
- **Extensive tool set** for Splunk data operations
- **Modern Python tooling** with uv package manager for fast dependency management

## Available Tools

### Core Tools
- `get_splunk_health` - Check Splunk connection status and version information
- `list_indexes` - List all accessible Splunk indexes with count
- `run_oneshot_search` - Execute quick Splunk searches with immediate results (best for simple queries)
- `run_splunk_search` - Execute complex searches with progress tracking and detailed job information

### Data Discovery Tools
- `list_sourcetypes` - List all available sourcetypes using metadata command
- `list_sources` - List all data sources using metadata command
- `list_apps` - List installed Splunk apps with properties (name, version, author, etc.)
- `list_users` - List Splunk users and their properties (roles, email, default app, etc.)

### KV Store Tools
- `list_kvstore_collections` - List KV Store collections (all apps or specific app)
- `get_kvstore_data` - Retrieve data from KV Store collections with optional MongoDB-style queries
- `create_kvstore_collection` - Create new KV Store collections with field definitions and indexing

### Configuration Tools
- `get_configurations` - Retrieve Splunk configuration settings from .conf files

## Architecture

### Local MCP Server (stdio mode)
```
┌─────────────────┐    stdio     ┌─────────────────┐    HTTPS/REST    ┌─────────────────┐
│   MCP Client    │◄────────────►│   MCP Server    │◄───────────────►│  Splunk Server  │
│ (Cursor/Claude) │              │   (stdio mode)  │                 │   Port: 8089    │
│                 │              │   server.py     │                 │                 │
└─────────────────┘              └─────────────────┘                 └─────────────────┘
```

### Remote MCP Server (HTTP mode) - ✅ **FULLY IMPLEMENTED**
```
┌─────────────────┐    HTTP/SSE   ┌─────────────────┐    Docker   ┌─────────────────┐    ┌─────────────────┐
│   MCP Client    │◄─────────────►│     Traefik     │◄───────────►│   MCP Server    │◄──►│  Splunk Server  │
│  (Web Agents)   │               │  Load Balancer  │             │   (HTTP mode)   │    │   Port: 8089    │
│                 │               │   Port: 8001    │             │   Port: 8000    │    │                 │
└─────────────────┘               └─────────────────┘             └─────────────────┘    └─────────────────┘
```

### Production Docker Stack
```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│     Traefik     │    │   MCP Server    │    │  Splunk Server  │    │ MCP Inspector   │
│   Port: 8001    │    │   Port: 8000    │    │   Port: 9000    │    │   Port: 6274    │
│   Dashboard     │    │   (Docker)      │    │   (Docker)      │    │   (Browser)     │
│   Port: 8080    │    │                 │    │                 │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘    └─────────────────┘
```

## Quick Start

### Prerequisites

- **Python 3.10+** with uv package manager
- **Docker and Docker Compose** (for Splunk and HTTP deployment)
- **Splunk Enterprise or Cloud instance**
- Valid Splunk credentials

### Option 1: Automated Setup (Recommended)

```bash
# 1. Clone and setup
git clone <repository-url>
cd mcp-server-for-splunk

# 2. One-command setup (builds and runs everything)
./scripts/build_and_run.sh
```

This will automatically:
- ✅ Check Docker dependencies
- ✅ Create `.env` from template
- ✅ Build MCP server with uv
- ✅ Start Splunk + Traefik + MCP server
- ✅ Show all service URLs

**Access URLs after setup:**
- 🔧 **Traefik Dashboard**: http://localhost:8080
- 🌐 **Splunk Web UI**: http://localhost:9000 (admin/Chang3d!)
- 🔌 **MCP Server**: http://localhost:8001/mcp/
- 📊 **MCP Inspector**: http://localhost:6274

### Option 2: Manual Setup

#### 1. Install uv Package Manager

```bash
# Install uv (fast Python package manager)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Or using homebrew on macOS
brew install uv
```

#### 2. Setup Python Environment

```bash
# Create virtual environment and install all dependencies
uv sync

# Add development dependencies (optional)
uv sync --dev
```

#### 3. Configure Environment

```bash
# Copy and edit environment configuration
cp env.example .env

# Edit .env with your Splunk details
SPLUNK_HOST=so1
SPLUNK_PORT=8089
SPLUNK_USERNAME=admin
SPLUNK_PASSWORD=Chang3d!
SPLUNK_VERIFY_SSL=false
```

#### 4. Start Services

**For HTTP/Production Mode (Recommended):**
```bash
# Build and start full Docker stack with Traefik
docker-compose build
docker-compose up -d

# Check status
docker-compose ps
docker-compose logs -f mcp-server
```

**For Local Development (stdio mode):**
```bash
# Start only Splunk
docker-compose -f docker-compose-splunk.yml up -d

# Run MCP server locally
uv run python src/server.py
```

## Development Workflows

### Using the Makefile

The project includes a comprehensive Makefile with uv integration:

```bash
# Development setup
make install          # Install dependencies with uv
make dev-setup        # Complete development environment setup

# Testing
make test             # Run all tests
make test-connections # Test MCP connections specifically
make test-fast        # Quick tests (excluding slow ones)
make test-all         # Comprehensive test suite with coverage

# Code quality
make lint             # Run linting (ruff + mypy)
make format           # Format code (black + ruff)

# Docker operations
make docker-up        # Start Docker services
make docker-down      # Stop Docker services  
make docker-rebuild   # Rebuild and restart MCP server
make docker-logs      # Show MCP server logs

# Development workflow
make dev-test         # Quick development tests (fast tests + linting)
make ci-test          # Full CI test suite
```

### Package Management with uv

This project uses [uv](https://github.com/astral-sh/uv) for ultra-fast Python package management:

```bash
# Install dependencies (faster than pip)
uv sync                    # Install all dependencies
uv sync --dev             # Include development dependencies
uv sync --frozen          # Use exact versions from uv.lock

# Dependency management
uv add requests           # Add new dependency
uv add --dev pytest       # Add development dependency
uv remove requests        # Remove dependency
uv lock --upgrade         # Update dependencies

# Running commands
uv run python src/server.py    # Run with proper environment
uv run pytest tests/           # Run tests
uv run black src/              # Format code

# Environment information
uv tree                   # Show dependency tree
uv show                   # Show project information
```

**Key uv Files:**
- `pyproject.toml` - Project configuration and dependencies
- `uv.lock` - Locked dependency versions for reproducible builds
- `.python-version` - Python version specification

### Docker Development

#### Full Stack Development

```bash
# Build and start everything
./scripts/build_and_run.sh

# Or manually:
docker-compose build mcp-server
docker-compose up -d

# Development with auto-rebuild
docker-compose up --build mcp-server

# Check logs
make docker-logs
# or
docker-compose logs -f mcp-server
```

#### Local MCP + Docker Splunk

```bash
# Start only Splunk in Docker
docker-compose -f docker-compose-splunk.yml up -d

# Run MCP server locally for faster development
uv run python src/server.py

# Test with MCP Inspector
npx @modelcontextprotocol/inspector uv run python src/server.py
```

## Testing

### Running Tests

```bash
# Quick test commands
make test-connections     # Test MCP connections
make test-health         # Test health endpoints
make test-fast           # Fast tests only
make test-all            # Full test suite with coverage

# Detailed pytest commands
uv run pytest tests/ -v                    # All tests
uv run pytest tests/ -k "connection" -v    # Connection tests only
uv run pytest tests/ --cov=src            # With coverage
```

### Test Architecture

The project includes comprehensive tests for:

1. **MCP Connection Tests**
   - ✅ Traefik-proxied connections (http://localhost:8001/mcp/)
   - ✅ Direct connections (http://localhost:8002/mcp/)
   - ✅ Health resource endpoints

2. **Splunk Integration Tests**
   - ✅ Health checks and connectivity
   - ✅ Index and data source discovery
   - ✅ Search operations
   - ✅ KV Store operations
   - ✅ Configuration management

3. **Error Handling Tests**
   - ✅ Connection failures
   - ✅ Invalid parameters
   - ✅ Timeout scenarios

### Test Environment

Tests require:
- **Docker containers running** (MCP server, Traefik, Splunk)
- **Network connectivity** to localhost:8001 and localhost:8002
- **Healthy Splunk instance** with default data

## Integration Examples

### MCP Inspector (Web Testing)

```bash
# Test local stdio server
npx @modelcontextprotocol/inspector uv run python src/server.py

# Test remote HTTP server
npx @modelcontextprotocol/inspector http://localhost:8001/mcp/

# Or use the direct access URL
open http://localhost:6274
```

### Cursor IDE Integration

Add to your Cursor MCP settings (`~/.cursor/mcp.json`):

**For Local Development (stdio):**
```json
{
  "mcpServers": {
    "mcp-server-for-splunk": {
      "command": "uv",
      "args": [
        "--directory",
        "/path/to/mcp-server-for-splunk/",
        "run",
        "python",
        "src/server.py"
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

**For Remote HTTP Server:**
```json
{
  "mcpServers": {
    "mcp-server-for-splunk-http": {
      "command": "npx",
      "args": [
        "@modelcontextprotocol/inspector",
        "http://localhost:8001/mcp/"
      ]
    }
  }
}
```

### Google ADK Integration

Based on the [Google ADK MCP documentation](https://google.github.io/adk-docs/tools/mcp-tools/#mcptoolset-class):

#### Local stdio Mode
```python
from google.adk.agents.llm_agent import LlmAgent
from google.adk.tools.mcp_tool.mcp_toolset import MCPToolset, StdioServerParameters

splunk_agent = LlmAgent(
    model='gemini-2.0-flash',
    name='splunk_assistant',
    instruction="""You are a Splunk expert assistant. Use the available Splunk tools to analyze data, check system health, and manage Splunk resources.""",
    tools=[
        MCPToolset(
            connection_params=StdioServerParameters(
                command='uv',
                args=[
                    '--directory', '/path/to/mcp-server-for-splunk/',
                    'run', 'python', 'src/server.py'
                ],
                env={
                    'SPLUNK_HOST': 'localhost',
                    'SPLUNK_PORT': '8089',
                    'SPLUNK_USERNAME': 'admin',
                    'SPLUNK_PASSWORD': 'Chang3d!',
                    'SPLUNK_VERIFY_SSL': 'false'
                }
            )
        )
    ]
)
```

#### Remote HTTP Mode
```python
from google.adk.tools.mcp_tool.mcp_toolset import SseServerParams

# For HTTP server integration
MCPToolset(
    connection_params=SseServerParams(
        url="http://localhost:8001/mcp/",
        headers={"Authorization": "Bearer your-token"}  # Optional
    ),
    tool_filter=[
        'get_splunk_health',
        'run_oneshot_search', 
        'list_indexes',
        'list_sourcetypes'
    ]
)
```

## Production Deployment

### Traefik Configuration

The HTTP mode includes full Traefik integration with:

- ✅ **Load balancing** and service discovery
- ✅ **CORS headers** for web client compatibility
- ✅ **Health checks** and monitoring
- ✅ **Path-based routing** (`/mcp/` prefix)
- ✅ **Dashboard** for monitoring (http://localhost:8080)

### Docker Configuration

**Dockerfile Features:**
- 🚀 **Multi-stage build** with uv for fast dependency installation
- 📦 **Optimized layers** for better caching
- 🔒 **Security best practices** with non-root user and minimal image
- 📊 **Health checks** built-in
- 🏗️ **uv integration** for reproducible builds

**docker-compose.yml Features:**
- 🌐 **Traefik reverse proxy** with automatic service discovery
- 🔄 **Auto-restart policies** for production reliability
- 📡 **Network isolation** with dedicated networks
- 💾 **Volume persistence** for Splunk data
- 🔍 **Health monitoring** for all services
- 🔧 **Development mode** with file watching and auto-rebuild

### Environment Configuration

```bash
# Production environment variables
SPLUNK_HOST=production-splunk.company.com
SPLUNK_PORT=8089
SPLUNK_USERNAME=service-account
SPLUNK_PASSWORD=secure-password
SPLUNK_VERIFY_SSL=true
MCP_SERVER_HOST=0.0.0.0
MCP_SERVER_PORT=8000
MCP_SERVER_MODE=docker
```

## Available Scripts and Automation

### Automated Build Script

```bash
# One-command setup
./scripts/build_and_run.sh

# Features:
# ✅ Dependency checking (Docker, docker-compose)
# ✅ Environment setup (.env creation)
# ✅ Docker build with uv
# ✅ Service startup and health checks
# ✅ URL display and status reporting
```

### Splunk Development Script

```bash
# Start Splunk development environment
chmod +x scripts/run_splunk.sh
./scripts/run_splunk.sh

# Features:
# ✅ ARM64/Apple Silicon compatibility
# ✅ Health monitoring and wait logic
# ✅ Color-coded status output
# ✅ Connection info and helpful commands
```

## Project Documentation

### Implementation Status

- ✅ **stdio MCP Server**: Fully implemented and tested
- ✅ **HTTP MCP Server**: Fully implemented with Traefik integration
- ✅ **Splunk Integration**: Complete with 12 tools covering all major operations
- ✅ **Local Development**: Full setup with docker-compose-splunk.yml
- ✅ **Production Docker Stack**: Complete with Traefik load balancing
- ✅ **MCP Inspector Support**: Working with both local and remote modes
- ✅ **Cursor IDE Integration**: Configured and tested for both modes
- ✅ **Testing Suite**: Comprehensive tests for connections and functionality
- ✅ **uv Package Management**: Fast dependency management and builds
- ✅ **Automated Setup**: One-command deployment scripts
- ✅ **Google ADK Integration**: Documented with examples for both modes
- ✅ **Production Deployment**: Docker setup with monitoring and health checks

### Configuration Files

- **pyproject.toml**: Python project configuration with uv package management
- **uv.lock**: Locked dependency versions for reproducible builds
- **docker-compose.yml**: Full production stack with Traefik load balancing
- **docker-compose-splunk.yml**: Standalone Splunk development environment
- **Dockerfile**: Multi-stage build with uv integration
- **.env**: Environment variables for Splunk connection and server configuration
- **Makefile**: Development workflow automation with uv commands
- **scripts/build_and_run.sh**: Automated setup and deployment script

### Documentation Structure

```
docs/
├── business-case.md           # Business justification and use cases
├── DOCKER.md                  # Docker setup and configuration guide
├── TESTING.md                 # Testing setup and procedures
└── prds/
    ├── main-prd-mcp-server-for-splunk.md  # Main product requirements
    └── mvp-prd.md             # MVP specifications
```

## Monitoring and Troubleshooting

### Health Checks

```bash
# MCP server health (HTTP mode)
curl http://localhost:8001/mcp/resources/health%3A%2F%2Fstatus

# MCP server health (direct)
curl http://localhost:8002/mcp/resources/health%3A%2F%2Fstatus

# Splunk connection
uv run python -c "from src.splunk_client import get_splunk_service; print(get_splunk_service().info)"

# Docker services
docker-compose ps
make docker-logs
```

### Service URLs Summary

| Service | URL | Purpose |
|---------|-----|---------|
| **MCP Server (Traefik)** | http://localhost:8001/mcp/ | Primary MCP endpoint |
| **MCP Server (Direct)** | http://localhost:8002/mcp/ | Direct access |
| **MCP Inspector** | http://localhost:6274 | Web-based testing |
| **Traefik Dashboard** | http://localhost:8080 | Load balancer monitoring |
| **Splunk Web UI** | http://localhost:9000 | Splunk interface |
| **Splunk Management** | https://localhost:8089 | API endpoint |

### Common Issues and Solutions

1. **Build Failures**
   ```bash
   # Clean and rebuild
docker-compose down
docker system prune -f
./scripts/build_and_run.sh
   ```

2. **Connection Issues** 
   ```bash
   # Check service status
   make docker-logs
   docker-compose ps
   
   # Test connections
   make test-connections
   ```

3. **uv Issues**
   ```bash
   # Update uv
   curl -LsSf https://astral.sh/uv/install.sh | sh
   
   # Refresh lock file
   uv lock --upgrade
   uv sync --dev
   ```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Follow the development setup (Option 1 or 2)
4. Use `make dev-test` for quick validation
5. Add tests for new functionality
6. Run full test suite with `make ci-test`
7. Update documentation
8. Submit a pull request

### Development Best Practices

```bash
# Before committing
make format          # Format code
make lint           # Check code quality  
make test-fast      # Quick test validation
make dev-test       # Complete dev workflow

# Before pushing
make ci-test        # Full CI validation
```

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

- **Issues**: Report bugs and feature requests via GitHub Issues
- **Documentation**: Check the `/docs` directory for detailed guides
- **MCP Inspector**: Use http://localhost:6274 for interactive testing
- **Community**: Join discussions for help and best practices
- **Traefik Dashboard**: Monitor load balancing at http://localhost:8080

---

**🚀 Ready to use!** Start with `./scripts/build_and_run.sh` for immediate setup, or choose your preferred development workflow above.
