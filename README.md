# MCP Server for Splunk

A **modular, community-driven** Model Context Protocol (MCP) server that provides seamless integration between Large Language Models (LLMs), AI agents, and Splunk instances (Enterprise/Cloud). This server exposes Splunk's powerful search and data management capabilities through standardized MCP tools with an extensible architecture designed for community contributions.

## ✨ Key Features

- **🏗️ Modular Architecture** - Core framework with automatic tool discovery and loading
- **👥 Community-Friendly** - Structured contribution system with examples and guidelines  
- **🔌 MCP-Compliant** - Full MCP specification support using FastMCP framework
- **🌐 Multiple Transports** - stdio (local) and HTTP (remote server) modes
- **⚙️ Flexible Configuration** - Server environment or client-provided Splunk settings
- **🔒 Enterprise-Ready** - Secure authentication and production deployment
- **🐳 Containerized** - Docker setup with Traefik load balancing
- **⚡ Fast Development** - Modern Python tooling with uv package manager
- **🧪 Comprehensive Testing** - Automated testing for core and community tools

## 🏗️ Architecture Overview

### Modular Design
The server is built on a modular architecture that separates core functionality from community contributions:

```
📦 Core Framework (src/core/)     - Base classes, discovery, registry
🔧 Core Tools (src/tools/)        - Essential Splunk operations  
🌟 Community Tools (contrib/)     - Community-contributed extensions
🔌 Plugin System (plugins/)       - External packages (future)
```

### Tool Categories

#### Core Tools (Maintained by Project)
- **🏥 Health & Monitoring** - Connection status, system health
- **🔍 Search Operations** - Oneshot and job-based searches  
- **📊 Metadata Discovery** - Indexes, sourcetypes, data sources
- **👥 Administration** - Apps, users, configurations
- **🗃️ KV Store Management** - Collections, data, creation

#### Community Tools (contrib/)
- **🔐 Security Tools** - Threat hunting, incident response
- **⚙️ DevOps Tools** - Monitoring, alerting, operations
- **📈 Analytics Tools** - Business intelligence, reporting
- **💡 Examples** - Learning templates and patterns

## 🚀 Quick Start

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

This automatically sets up the complete stack with the new modular server.

**Access URLs after setup:**
- 🔧 **Traefik Dashboard**: http://localhost:8080
- 🌐 **Splunk Web UI**: http://localhost:9000 (admin/Chang3d!)
- 🔌 **MCP Server**: http://localhost:8001/mcp/
- 📊 **MCP Inspector**: http://localhost:3001

### Option 2: Manual Development Setup

#### 1. Install Dependencies

```bash
# Install uv (fast Python package manager)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Create environment and install dependencies
uv sync --dev
```

#### 2. Configure Environment

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

#### 3. Run the Modular Server

**Local Development (stdio mode):**
```bash
# Start Splunk in Docker
docker-compose -f docker-compose-splunk.yml up -d

# Run modular MCP server locally
uv run python src/server.py
```

**Production Mode (HTTP with Docker stack):**
```bash
# Build and start full stack
docker-compose build
docker-compose up -d
```

## 🛠️ Tool Development

### Creating New Tools

The modular architecture makes it easy to create custom tools:

```bash
# Use the interactive tool generator
./contrib/scripts/generate_tool.py

# Browse existing tools for inspiration  
./contrib/scripts/list_tools.py --interactive

# Validate your implementation
./contrib/scripts/validate_tools.py
```

### Tool Development Workflow

1. **Choose Category** - Select from examples, security, devops, or analytics
2. **Create Tool Class** - Inherit from `BaseTool` with required metadata
3. **Implement Logic** - Add your Splunk operations in the `execute` method
4. **Add Tests** - Create comprehensive tests with mocks
5. **Validate** - Use validation scripts to ensure compliance

### Example: Custom Tool

```python
# contrib/tools/security/threat_hunting.py

from src.core.base import BaseTool, ToolMetadata
from fastmcp import Context

class ThreatHuntingTool(BaseTool):
    """Advanced threat hunting with custom SPL queries."""
    
    METADATA = ToolMetadata(
        name="threat_hunting",
        description="Hunt for security threats using custom SPL",
        category="security",
        tags=["security", "threat", "hunting"],
        requires_connection=True
    )
    
    async def execute(self, ctx: Context, query: str, timerange: str = "-24h") -> dict:
        """Execute threat hunting search."""
        # Your custom logic here
        results = await self.search_splunk(query, timerange)
        return self.format_success_response({"threats": results})
```

The tool is **automatically discovered** and loaded - no manual registration needed!

## 📦 Available Tools

### Core Tools (12 tools)
- `get_splunk_health` - Check connection status and version
- `list_indexes` - List accessible Splunk indexes  
- `run_oneshot_search` - Quick searches with immediate results
- `run_splunk_search` - Complex searches with progress tracking
- `list_sourcetypes` - Discover all sourcetypes
- `list_sources` - List data sources
- `list_apps` - Show installed Splunk apps
- `list_users` - List Splunk users and properties
- `list_kvstore_collections` - KV Store collection management
- `get_kvstore_data` - Retrieve KV Store data with queries
- `create_kvstore_collection` - Create new collections
- `get_configurations` - Access Splunk configuration files

### Community Tools
See `contrib/tools/` for community-contributed tools organized by category.

## 🏛️ Architecture Deep Dive

### Core Framework (`src/core/`)
- **Base Classes** - `BaseTool`, `BaseResource`, `BasePrompt` for consistent interfaces
- **Discovery System** - Automatic scanning and loading of tools
- **Registry** - Centralized component management  
- **Context Management** - Shared state and connection handling
- **Utilities** - Common functions for error handling and validation

### Tool Organization (`src/tools/`)
Core tools are organized by functional domain:
- `search/` - Search operations and job management
- `metadata/` - Data discovery and catalog operations  
- `health/` - System monitoring and diagnostics
- `admin/` - Administrative and configuration tools
- `kvstore/` - KV Store operations and management

### Community Framework (`contrib/`)
Structured system for community contributions:
- `tools/` - Community tools by category (security, devops, analytics)
- `resources/` - Shared resources and data
- `prompts/` - Custom prompt templates
- `scripts/` - Development and validation tools

## 🔧 Development Workflows

### Using the Makefile

```bash
# Development setup
make install          # Install dependencies with uv
make dev-setup        # Complete development environment

# Testing  
make test             # Run all tests
make test-contrib     # Test community tools specifically
make test-fast        # Quick tests only

# Code quality
make lint             # Run linting  
make format           # Format code

# Docker operations
make docker-up        # Start services
make docker-rebuild   # Rebuild modular server
make docker-logs      # Show logs
```

### Community Development

```bash
# Generate new tool interactively
./contrib/scripts/generate_tool.py

# Validate contributions
./contrib/scripts/validate_tools.py contrib/tools/your_category/

# Test community tools
./contrib/scripts/test_contrib.py your_category

# List and explore existing tools
./contrib/scripts/list_tools.py --interactive
```

## 🧪 Testing

### Test Architecture
- **Core Tests** - Framework and core tool validation (52+ tests)
- **Community Tests** - Automatic testing for contrib tools
- **Integration Tests** - End-to-end MCP client testing  
- **Mock Framework** - Comprehensive Splunk service mocking

### Running Tests

```bash
# Quick test workflows
make test-fast        # Fast tests + linting
make test-contrib     # Community tools only
make test-all         # Full suite with coverage

# Detailed testing
uv run pytest tests/ -v                    # All tests
uv run pytest tests/contrib/ -k security   # Category-specific
uv run pytest --cov=src                   # With coverage
```

## 🌐 Integration Examples

### MCP Inspector (Web Testing)

```bash
# Start full stack with integrated inspector
./scripts/build_and_run.sh

# Access web-based testing UI
open http://localhost:3001

# Connect to: http://localhost:8002/mcp/
```

### Cursor IDE Integration

**Option 1: Server Environment Configuration**
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

**Option 2: Client-Provided Configuration (New!)**
```json
{
  "mcpServers": {
    "mcp-server-for-splunk": {
      "command": "uv",
      "args": [
        "--directory", "/path/to/mcp-server-for-splunk/",
        "run", "python", "src/server.py"
      ]
    }
  }
}
```

Then provide Splunk configuration directly in your requests:
```
Check the health of our production Splunk:
- splunk_host: prod-splunk.company.com
- splunk_username: monitoring-user
- splunk_password: secure-password
- splunk_verify_ssl: true
```

### Google ADK Integration

```python
from google.adk.tools.mcp_tool.mcp_toolset import MCPToolset, StdioServerParameters

splunk_agent = LlmAgent(
    model='gemini-2.0-flash',
    tools=[
        MCPToolset(
            connection_params=StdioServerParameters(
                command='uv',
                args=['--directory', '/path/to/mcp-server-for-splunk/',
                      'run', 'python', 'src/server.py']
            )
        )
    ]
)
```

## 🐳 Production Deployment

### Docker Stack Features
- **Traefik Load Balancer** - Automatic service discovery and routing
- **Multi-stage Builds** - Optimized with uv for fast dependency management
- **Health Monitoring** - Built-in health checks for all services
- **Security Best Practices** - Non-root users and minimal attack surface
- **Development Mode** - File watching and auto-rebuild support

### Service URLs
| Service | URL | Purpose |
|---------|-----|---------|
| **MCP Server (Traefik)** | http://localhost:8001/mcp/ | Primary MCP endpoint |
| **MCP Server (Direct)** | http://localhost:8002/mcp/ | Direct access |
| **MCP Inspector** | http://localhost:3001 | Web testing UI |
| **Traefik Dashboard** | http://localhost:8080 | Load balancer monitoring |
| **Splunk Web UI** | http://localhost:9000 | Splunk interface |

## 👥 Contributing

**🚀 New Contributors? Get started quickly:**

```bash
# Interactive tool creation
./contrib/scripts/generate_tool.py

# Explore existing tools  
./contrib/scripts/list_tools.py

# Validate your work
./contrib/scripts/validate_tools.py

# Test your contributions
./contrib/scripts/test_contrib.py
```

**For detailed contribution guidelines**, see:
- 📖 [`contrib/README.md`](contrib/README.md) - Complete contribution guide
- 🛠️ [`contrib/scripts/README.md`](contrib/scripts/README.md) - Helper script documentation  
- 🏗️ [`ARCHITECTURE.md`](ARCHITECTURE.md) - Architecture deep dive
- 📋 [`docs/contrib/`](docs/contrib/) - Detailed development guides

### Development Best Practices

```bash
# Before committing
make format          # Format code
make lint           # Check quality
make test-fast      # Quick validation

# Before pushing  
make ci-test        # Full CI validation
```

## 📚 Documentation

- **[Architecture Guide](ARCHITECTURE.md)** - Detailed architecture overview
- **[Refactoring Summary](REFACTORING_SUMMARY.md)** - Migration from monolithic to modular
- **[Contribution Guide](contrib/README.md)** - Community contribution process
- **[Testing Guide](TESTING.md)** - Comprehensive testing documentation
- **[Docker Guide](DOCKER.md)** - Container deployment and configuration

## 🔄 Migration from Monolithic Version

The project maintains backward compatibility:
- **Original server** (`server.py`) remains functional
- **New modular server** provides identical API and functionality
- **Gradual migration** is supported
- **All existing integrations** continue to work

To migrate: replace `python src/server.py` with the modular server in your deployment scripts.

## 📊 Project Status

- ✅ **Modular Architecture** - Complete with automatic discovery
- ✅ **Core Tools** - 12 essential Splunk tools implemented
- ✅ **Community Framework** - Contribution system with examples
- ✅ **Development Tools** - Interactive generators and validators
- ✅ **Testing Suite** - Comprehensive test coverage (63%+)
- ✅ **Documentation** - Complete guides and examples
- ✅ **Production Deployment** - Docker stack with monitoring
- ✅ **MCP Inspector Integration** - Web-based testing and debugging

## 🆘 Support

- **🐛 Issues**: Report bugs via GitHub Issues
- **📖 Documentation**: Check `/docs` directory for guides
- **🔧 Interactive Testing**: Use MCP Inspector at http://localhost:3001
- **💬 Community**: Join GitHub Discussions for help
- **📊 Monitoring**: Traefik Dashboard at http://localhost:8080

---

**🚀 Ready to start?** 
- **Quick Setup**: `./scripts/build_and_run.sh`
- **Create Tools**: `./contrib/scripts/generate_tool.py`  
- **Explore**: `./contrib/scripts/list_tools.py --interactive`
