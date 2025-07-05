# MCP Server for Splunk

[![FastMCP](https://img.shields.io/badge/FastMCP-2.3.4+-blue)](https://gofastmcp.com/)
[![Python](https://img.shields.io/badge/Python-3.10+-green)](https://python.org)
[![Docker](https://img.shields.io/badge/Docker-Ready-blue)](https://docker.com)
[![MCP](https://img.shields.io/badge/MCP-Compatible-purple)](https://modelcontextprotocol.io/)

> **Enable AI agents to interact seamlessly with Splunk environments through the Model Context Protocol (MCP)**

A **community-driven**, **modular** MCP server that bridges Large Language Models (LLMs), AI agents, and Splunk instances (Enterprise/Cloud). Built with [FastMCP](https://gofastmcp.com/), it provides a standardized way for AI to search, analyze, and manage Splunk data while maintaining enterprise security and extensibility.

## 🌟 What is MCP?

The [Model Context Protocol (MCP)](https://modelcontextprotocol.io/introduction) is like **"USB-C for AI"** - a standardized way to connect AI models to different data sources and tools. Think of it as an API specifically designed for LLM interactions.

- **🔌 Universal Connection**: One protocol to connect AI to any data source
- **🔧 Tool Integration**: Enable AI to perform actions, not just consume data  
- **📚 Resource Access**: Provide structured information for AI context
- **🎯 Prompt Templates**: Reusable interaction patterns

Learn more: [Anthropic's MCP Announcement](https://www.anthropic.com/news/model-context-protocol)

## ✨ Key Features

### 🏗️ **Modular Architecture**
- **Core Framework**: Automatic discovery and loading of tools, resources, and prompts
- **Community-Friendly**: Structured contribution system with examples and guidelines
- **Plugin System**: Easy extension without core modifications

### 🔧 **Comprehensive Splunk Integration**
- **20+ Core Tools**: Search, metadata, admin, KV store, health monitoring
- **14 Rich Resources**: Documentation, configuration, and system context
- **Smart Prompts**: Troubleshooting workflows and operation templates

### 🌐 **Flexible Deployment**
- **Multiple Transports**: stdio (local) and HTTP (remote server) modes
- **Configuration Options**: Server environment, client environment, or HTTP headers
- **Docker Ready**: Complete containerized stack with monitoring

### 🔒 **Enterprise Ready**
- **Secure by Design**: No credential exposure, client-scoped access
- **Multi-tenant Support**: Different Splunk instances per client
- **Production Deployment**: Load balancing, health checks, observability

## 🚀 Quick Start

## 📋 Prerequisites

> **📖 Complete Installation Guide**: See our comprehensive [Prerequisites Guide](docs/prerequisites.md) for detailed, platform-specific installation instructions.

### **Quick Requirements Check:**

| Tool | Required | Purpose |
|------|----------|---------|
| **Python 3.10+** | ✅ Required | Core runtime |
| **UV Package Manager** | ✅ Required | Dependency management |
| **Git** | ✅ Required | Repository cloning |
| **Node.js 18+** | 🌟 Optional | MCP Inspector testing |
| **Docker** | 🌟 Optional | Full containerized stack |

### **🚀 Quick Install (One Command):**

```bash
# Check what you need first
./scripts/check-prerequisites.sh    # macOS/Linux
.\scripts\check-prerequisites.ps1   # Windows

# Platform-specific quick install commands are provided by the checker
```

### **📱 Verification Scripts:**

We provide smart verification scripts that check your system and provide exact installation commands:

- **Windows:** `.\scripts\check-prerequisites.ps1` 
- **macOS/Linux:** `./scripts/check-prerequisites.sh`

**Features:**
- ✅ Checks all required and optional tools
- 🎯 Provides platform-specific installation commands  
- 📊 Shows system information and compatibility
- 🔧 Auto-detects package managers and suggests quick-install options

---

### 🏢 **Splunk Requirements**

- **Splunk instance** (Enterprise or Cloud)
- Valid Splunk credentials with appropriate permissions:
  - Search capabilities for your intended indexes
  - Admin access (for admin tools)
  - KV Store access (for KV Store tools)

---

### 🔍 **First Time Setup - Check Prerequisites**

**Before running any setup commands, we recommend verifying your system has all required prerequisites:**

#### **Windows:**
```powershell
# Clone the repository
git clone https://github.com/your-org/mcp-server-for-splunk.git
cd mcp-server-for-splunk

# Check prerequisites first
.\scripts\check-prerequisites.ps1

# If all requirements are met, proceed with setup
.\scripts\build_and_run.ps1
```

#### **macOS/Linux:**
```bash
# Clone the repository
git clone https://github.com/your-org/mcp-server-for-splunk.git
cd mcp-server-for-splunk

# Check prerequisites first
./scripts/check-prerequisites.sh

# If all requirements are met, proceed with setup
./scripts/build_and_run.sh
```

> **💡 Smart Verification**: The prerequisites checker will tell you exactly what to install if anything is missing, with platform-specific commands and quick-install options.

> **⚡ Auto-Install**: If you're missing only a few tools, the checker provides one-command install scripts for your platform.

---

### Option 1: One-Command Setup (Recommended)

**Linux/macOS:**
```bash
git clone https://github.com/your-org/mcp-server-for-splunk.git
cd mcp-server-for-splunk

# Automated setup - builds and runs everything
./scripts/build_and_run.sh
```

**Windows (PowerShell):**
```powershell
git clone https://github.com/your-org/mcp-server-for-splunk.git
cd mcp-server-for-splunk

# Automated setup - builds and runs everything
.\scripts\build_and_run.ps1
```

**Windows (Command Prompt/Batch):**
```cmd
git clone https://github.com/your-org/mcp-server-for-splunk.git
cd mcp-server-for-splunk

# Automated setup - builds and runs everything (calls PowerShell script)
.\scripts\build_and_run.bat
```

**🎯 Access Points after setup:**
- **MCP Server**: http://localhost:8001/mcp/ (Docker) or http://localhost:8000+ (Local - auto-detects available port)
- **MCP Inspector (Testing)**: http://localhost:6274 (Local) or http://localhost:3001 (Docker)
- **Splunk Web UI**: http://localhost:9000 (admin/Chang3d!) - Docker only
- **Traefik Dashboard**: http://localhost:8080 - Docker only

> **💡 Smart Port Management**: The local setup automatically detects port conflicts and uses the next available port (8000, 8001, 8002, etc.)

> **🪟 Windows Users**: Both scripts provide identical functionality! The PowerShell version includes Windows-specific optimizations and better error handling for Windows environments.

### Option 2: Local Development

**Linux/macOS:**
```bash
# Install dependencies
curl -LsSf https://astral.sh/uv/install.sh | sh
uv sync --dev

# Configure Splunk connection
cp env.example .env
# Edit .env with your Splunk details

# Run with FastMCP CLI
uv run fastmcp run src/server.py
```

**Windows (PowerShell):**
```powershell
# Install uv (auto-detects best method: winget, pip, or direct download)
# This is handled automatically by the build script, or manually:
winget install astral-sh.uv
# OR: pip install uv

# Install dependencies
uv sync --dev

# Configure Splunk connection
Copy-Item env.example .env
# Edit .env with your Splunk details

# Run with FastMCP CLI
uv run fastmcp run src/server.py
```

### Option 3: Using FastMCP CLI

```bash
# Install globally
pip install fastmcp

# Run server directly
fastmcp run src/server.py

# Run with custom configuration
fastmcp run src/server.py --transport http --port 8001
```

## 🔧 Configuration Options

The MCP server supports **three flexible configuration methods** with **automatic .env file loading**:

### 1. Server Environment Variables (Traditional)
```bash
export SPLUNK_HOST=localhost
export SPLUNK_USERNAME=admin
export SPLUNK_PASSWORD=Chang3d!
```

### 2. Client Environment Variables (MCP Clients)
```bash
export MCP_SPLUNK_HOST=prod-splunk.company.com
export MCP_SPLUNK_USERNAME=monitoring-user
export MCP_SPLUNK_PASSWORD=secure-password
```

### 3. HTTP Headers (Multi-tenant)
```bash
curl -H "X-Splunk-Host: prod-splunk.company.com" \
     -H "X-Splunk-Username: monitoring-user" \
     -H "X-Splunk-Password: secure-password" \
     http://localhost:8001/mcp/
```

### 4. .env File (Recommended for Local Development)
```bash
# The script automatically creates .env from env.example if missing
# and loads all variables with configuration validation

SPLUNK_HOST=your-splunk.company.com
SPLUNK_USERNAME=your-username
SPLUNK_PASSWORD=your-password
SPLUNK_VERIFY_SSL=false
```

> **💡 Smart Configuration**: The build script automatically loads `.env` files, shows configuration summaries, and validates Splunk connectivity settings.

> **🔒 Security**: Passwords and sensitive values are masked in output logs for security.

## 🛠️ Available Tools & Resources

### Core Tools (20+ tools)

| Category | Tools | Description |
|----------|-------|-------------|
| **🔍 Search** | `run_oneshot_search`, `run_splunk_search`, `list_saved_searches` | Execute searches and manage saved searches |
| **📊 Metadata** | `list_indexes`, `list_sourcetypes`, `list_sources` | Discover data sources and structure |
| **👥 Admin** | `list_apps`, `list_users`, `get_configurations` | Manage Splunk applications and users |
| **🗃️ KV Store** | `list_kvstore_collections`, `get_kvstore_data`, `create_kvstore_collection` | Manage KV Store operations |
| **🏥 Health** | `get_splunk_health` | Monitor system health and connectivity |
| **🚨 Alerts** | `list_triggered_alerts` | Monitor alert status |

### Rich Resources (14 resources)

| Type | Resources | Description |
|------|-----------|-------------|
| **📋 System Info** | `splunk://health/status`, `splunk://apps/installed` | Real-time system information |
| **⚙️ Configuration** | `splunk://config/{file}` | Access to configuration files |
| **📚 Documentation** | `splunk-docs://cheat-sheet`, `splunk-docs://{version}/spl-reference/{command}` | Version-aware Splunk documentation |
| **🔍 Search Context** | `splunk://search/results/recent`, `splunk://savedsearches/list` | Search history and saved searches |

### Smart Prompts

| Prompt | Description |
|--------|-------------|
| **troubleshooting_assistant** | Guided troubleshooting workflows |
| **search_optimization** | SPL query optimization help |
| **security_analysis** | Security investigation patterns |

## 📱 Client Integration Examples

### Cursor IDE Integration

```json
{
  "mcpServers": {
    "mcp-server-for-splunk": {
      "command": "fastmcp",
      "args": ["run", "/path/to/src/server.py"],
      "env": {
        "MCP_SPLUNK_HOST": "your-splunk.com",
        "MCP_SPLUNK_USERNAME": "your-username",
        "MCP_SPLUNK_PASSWORD": "your-password"
      }
    }
  }
}
```

### Google Agent Development Kit (ADK)

```python
from google.adk.tools.mcp_tool.mcp_toolset import MCPToolset, StdioServerParameters

splunk_agent = LlmAgent(
    model='gemini-2.0-flash',
    tools=[
        MCPToolset(
            connection_params=StdioServerParameters(
                command='fastmcp',
                args=['run', '/path/to/src/server.py']
            )
        )
    ]
)
```

### Claude Desktop

```json
{
  "mcpServers": {
    "splunk": {
      "command": "fastmcp",
      "args": ["run", "/path/to/mcp-server-for-splunk/src/server.py"],
      "env": {
        "MCP_SPLUNK_HOST": "localhost",
        "MCP_SPLUNK_PASSWORD": "Chang3d!"
      }
    }
  }
}
```

## 👥 Community Contributions

### Creating New Tools

We provide interactive tools to make contributing easy:

```bash
# Generate new tool interactively
./contrib/scripts/generate_tool.py

# Browse existing tools for inspiration
./contrib/scripts/list_tools.py --interactive

# Validate your implementation
./contrib/scripts/validate_tools.py

# Test your contributions
./contrib/scripts/test_contrib.py
```

### Tool Categories

| Category | Purpose | Examples |
|----------|---------|----------|
| **🛡️ Security** | Threat hunting, incident response | User behavior analysis, IOC searching |
| **⚙️ DevOps** | Monitoring, alerting, operations | Performance monitoring, capacity planning |
| **📈 Analytics** | Business intelligence, reporting | KPI dashboards, trend analysis |
| **💡 Examples** | Learning templates and patterns | Tutorial tools, best practices |

### Example: Custom Security Tool

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
    
    async def execute(self, ctx: Context, 
                     query: str, 
                     timerange: str = "-24h") -> dict:
        """Execute threat hunting search."""
        results = await self.search_splunk(query, timerange)
        return self.format_success_response({"threats": results})
```

**✨ Auto-Discovery**: Your tool is automatically discovered and loaded - no manual registration needed!

## 🐳 Docker Deployment

### Development Stack

```bash
# Start complete development environment
docker-compose up -d

# With hot reload for development
docker-compose -f docker-compose-dev.yml up -d
```

### Production Deployment

```bash
# Production-ready stack with monitoring
docker-compose -f docker-compose.prod.yml up -d
```

**Included Services:**
- **Traefik**: Load balancer and reverse proxy
- **MCP Server**: Your Splunk MCP server
- **MCP Inspector**: Web-based testing interface
- **Splunk Enterprise**: Complete Splunk instance

## 🧪 Testing & Validation

### Interactive Testing with MCP Inspector

1. Start the stack: `./scripts/build_and_run.sh`
2. Open http://localhost:3001
3. Connect to: `http://localhost:8001/mcp/`
4. Test tools and resources interactively

### Automated Testing

```bash
# Quick tests
make test-fast

# Full test suite
make test

# Community tools only
make test-contrib

# With coverage
pytest --cov=src tests/
```

### Testing HTTP Headers (Multi-tenant)

The MCP Inspector is perfect for testing different Splunk configurations:

1. Add custom `X-Splunk-*` headers in the inspector
2. Test connections to different Splunk instances
3. Validate client-scoped access

## 📚 Documentation

| Document | Description |
|----------|-------------|
| **[Prerequisites Guide](docs/prerequisites.md)** | Complete installation guide for all platforms |
| **[Architecture Guide](ARCHITECTURE.md)** | Detailed architecture overview |
| **[Contribution Guide](contrib/README.md)** | How to contribute tools and resources |
| **[Docker Guide](DOCKER.md)** | Container deployment and configuration |
| **[Testing Guide](TESTING.md)** | Comprehensive testing documentation |
| **[API Reference](docs/api/)** | Complete API documentation |

## 🏗️ Architecture Overview

### Modular Design

```
📦 src/core/              # Core framework and discovery
├── base.py              # Base classes for all components
├── discovery.py         # Automatic component discovery
├── registry.py          # Component registration and management
└── loader.py            # Dynamic loading into FastMCP

🔧 src/tools/            # Core tools (maintained by project)
├── search/              # Search operations
├── metadata/            # Data discovery
├── admin/               # Administration
├── kvstore/             # KV Store management
└── health/              # System monitoring

📚 src/resources/        # Core resources
├── splunk_config.py     # Configuration and system info
├── splunk_docs.py       # Documentation resources
└── processors/          # Content processing

🌟 contrib/              # Community contributions
├── tools/               # Community tools by category
├── scripts/             # Development helpers
└── README.md            # Contribution guide
```

### Discovery & Loading Process

1. **🔍 Discovery**: Automatically scan `src/tools/` and `contrib/tools/`
2. **📝 Registration**: Register components with metadata validation
3. **🔌 Loading**: Dynamically load into FastMCP server
4. **🚀 Runtime**: Tools, resources, and prompts available to clients

## 🔄 Migration & Compatibility

The project maintains **full backward compatibility**:

- ✅ **Existing integrations** continue to work
- ✅ **Original server** (`server.py`) remains functional  
- ✅ **Gradual migration** supported
- ✅ **API compatibility** maintained

## 🆘 Support & Community

- **🐛 Issues**: [GitHub Issues](https://github.com/your-org/mcp-server-for-splunk/issues)
- **💬 Discussions**: [GitHub Discussions](https://github.com/your-org/mcp-server-for-splunk/discussions)
- **📖 Documentation**: Complete guides in `/docs`
- **🔧 Interactive Testing**: MCP Inspector at http://localhost:3001

### 🪟 Windows-Specific Troubleshooting

> **📖 Complete Windows Guide**: See the [Prerequisites Guide](docs/prerequisites.md#-windows-specific-troubleshooting) for comprehensive Windows installation instructions and troubleshooting.

**Quick Fixes:**
- **PowerShell Policy**: `Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser`
- **Port Conflicts**: Scripts auto-detect and use available ports
- **Missing Tools**: Run `.\scripts\check-prerequisites.ps1` for exact install commands

**Debugging:**
```powershell
# Check all prerequisites at once
.\scripts\check-prerequisites.ps1 -Detailed

# View build script help
.\scripts\build_and_run.ps1 -Help
```

## 🚀 Getting Started Checklist

**Linux/macOS:**
- [ ] Clone the repository
- [ ] Run `./scripts/build_and_run.sh`
- [ ] Open MCP Inspector at http://localhost:3001 or http://localhost:6274
- [ ] Connect to http://localhost:8001/mcp/ or http://localhost:8000+
- [ ] Test basic tools like `get_splunk_health`
- [ ] Explore resources like `splunk://health/status`
- [ ] Try creating a custom tool with `./contrib/scripts/generate_tool.py`

**Windows:**
- [ ] Clone the repository
- [ ] Run `.\scripts\build_and_run.ps1` (PowerShell) or `.\scripts\build_and_run.bat` (Command Prompt)
- [ ] Open MCP Inspector at http://localhost:3001 or http://localhost:6274
- [ ] Connect to http://localhost:8001/mcp/ or http://localhost:8000+
- [ ] Test basic tools like `get_splunk_health`
- [ ] Explore resources like `splunk://health/status`
- [ ] Try creating a custom tool with `.\contrib\scripts\generate_tool.py`

## 📊 Project Stats

- ✅ **20+ Core Tools** - Essential Splunk operations
- ✅ **14 Rich Resources** - System info and documentation  
- ✅ **Modular Architecture** - Easy extension and contribution
- ✅ **89 Tests Passing** - Comprehensive test coverage
- ✅ **Docker Ready** - Production deployment with monitoring
- ✅ **Community Framework** - Structured contribution system

---

**Ready to empower your AI with Splunk?** 🎯

**Linux/macOS:**
- **🚀 Quick Start**: `./scripts/build_and_run.sh`
- **🛠️ Create Tools**: `./contrib/scripts/generate_tool.py`
- **🔍 Explore**: `./contrib/scripts/list_tools.py --interactive`

**Windows:**
- **🚀 Quick Start**: `.\scripts\build_and_run.ps1` or `.\scripts\build_and_run.bat`
- **🛠️ Create Tools**: `.\contrib\scripts\generate_tool.py`
- **🔍 Explore**: `.\contrib\scripts\list_tools.py --interactive`

**📖 Learn More**: Check out the [FastMCP documentation](https://gofastmcp.com/) and [MCP specification](https://modelcontextprotocol.io/)
