# MCP Server for Splunk

[![FastMCP](https://img.shields.io/badge/FastMCP-2.3.4+-blue)](https://gofastmcp.com/)
[![Python](https://img.shields.io/badge/Python-3.10+-green)](https://python.org)
[![Docker](https://img.shields.io/badge/Docker-Ready-blue)](https://docker.com)
[![MCP](https://img.shields.io/badge/MCP-Compatible-purple)](https://modelcontextprotocol.io/)
[![Tests Passing](https://img.shields.io/badge/tests-174%20passing-green)](#)
[![Community](https://img.shields.io/badge/Community-Driven-orange)](#)

> **Enable AI agents to interact seamlessly with Splunk environments through the Model Context Protocol (MCP)**

Transform your Splunk instance into an AI-native platform. Our community-driven MCP server bridges Large Language Models and Splunk Enterprise/Cloud with 20+ tools, 14 resources, and production-ready security—all through a single, standardized protocol.

## 🌟 Why This Matters

- **🔌 Universal AI Connection**: One protocol connects any AI to Splunk data
- **⚡ Zero Custom Integration**: No more months of custom API development
- **🛡️ Production-Ready Security**: Client-scoped access with no credential exposure
- **🤖 AI-Powered Workflows**: Intelligent troubleshooting agents that work like experts
- **🤝 Community-Driven**: Extensible framework with contribution examples

> **🚀 NEW: [AI-Powered Troubleshooting Agents](docs/agents-as-tools-readme.md)** - Transform reactive firefighting into intelligent, systematic problem-solving with specialist AI workflows.

## 🚀 Quick Start

### Prerequisites
- Python 3.10+ and UV package manager
- Docker (optional but recommended for full stack)
- Splunk instance with API access (or use included Docker Splunk)

> **📖 Complete Setup Guide**: [Installation Guide](docs/getting-started/installation.md)

### Configuration

**Before running the setup, configure your Splunk connection:**

```bash
# Copy the example configuration
cp env.example .env

# Edit .env with your Splunk credentials
# - Use your existing Splunk instance (local, cloud, or Splunk Cloud)
# - OR use the included Docker Splunk (requires Docker)
```

### One-Command Setup

**Windows:**
```powershell
git clone https://github.com/your-org/mcp-server-for-splunk.git
cd mcp-server-for-splunk
.\scripts\build_and_run.ps1
```

**macOS/Linux:**
```bash
git clone https://github.com/your-org/mcp-server-for-splunk.git
cd mcp-server-for-splunk
./scripts/build_and_run.sh
```

> **💡 Deployment Options**: The script will prompt you to choose:
> - **Docker** (Option 1): Full stack with Splunk, Traefik, MCP Inspector - recommended if Docker is installed
> - **Local** (Option 2): Lightweight FastMCP server only - for users without Docker

### First Success Test

**Run the automated tests:**
```bash
# Run full test suite (fast path)
uv run pytest -q

# Or run with Splunk container ready
make test-with-splunk
```

**Interactive testing with MCP Inspector:**
```bash
open http://localhost:6274  # MCP Inspector web interface
```

1. Ensure that Streamable HTTP is set
2. Update URL from default to: `http://localhost:8001/mcp/` (Docker) or `http://localhost:8002/mcp/` (dev compose)
3. Click "Connect" button at the bottom
4. Test tools and resources interactively

**✅ Success**: You now have AI agents that can search, analyze, and manage Splunk data!

## 🎯 What You Can Do

### 🤖 **AI-Powered Troubleshooting** (NEW!)
```python
# Instead of manual troubleshooting procedures:
# 1. Check server health
# 2. Verify data ingestion
# 3. Analyze search performance
# 4. Review configurations
# 5. Generate recommendations

# Your AI agent intelligently handles everything:
await dynamic_troubleshoot_agent.execute(
    problem_description="Dashboard shows no data for the last 2 hours",
    workflow_type="missing_data_troubleshooting"
)
# → Parallel execution, expert analysis, actionable recommendations
```

### For AI Developers
```python
# Instead of complex Splunk SDK integration:
service = splunk.connect(host, port, username, password)
job = service.jobs.create("search index=main error")
results = job.results()

# Your AI agent simply says:
"Search for errors in the main index from the last 24 hours"
```

### For Splunk Administrators
- **🧠 Intelligent Workflows**: AI specialists that follow proven troubleshooting procedures
- **Health Monitoring**: AI agents that detect degraded features
- **Automated Analysis**: Natural language queries to SPL conversion
- **Configuration Management**: AI-assisted Splunk administration

### For Security Teams
- **🛡️ AI-Driven Investigation**: Specialist workflows for threat hunting and incident response
- **Threat Hunting**: AI-powered investigation workflows
- **Incident Response**: Automated data gathering and analysis
- **Compliance Reporting**: AI-generated security reports

## 📚 Documentation Hub

| Document | Purpose | Audience | Time |
|----------|---------|----------|------|
| **[🤖 AI-Powered Troubleshooting](docs/agents-as-tools-readme.md)** | **Intelligent workflows and specialist agents** | **All users** | **5 min** |
| **[Getting Started](docs/getting-started/)** | Complete setup guide with prerequisites | New users | 15 min |
| **[Integration Guide](docs/guides/integration/)** | Connect AI clients | Developers | 30 min |
| **[Deployment Guide](docs/guides/deployment/)** | Production deployment | DevOps | 45 min |
| **[OpenAI Agent Integration](docs/guides/openai-agent-integration.md)** | Configure OpenAI agents and retry behavior | Developers | 10 min |
| **[Template Replacement Guide](docs/guides/template-replacement-guide.md)** | Handle agent instruction templates | Developers | 5 min |
| **[API Reference](docs/api/)** | Complete tool documentation | Integrators | Reference |
| **[Contributing](docs/community/contributing.md)** | Add your own tools | Contributors | 60 min |
| **[Architecture](docs/architecture/)** | Technical deep-dive | Architects | Reference |

## 🔧 Available Tools & Capabilities

### 🤖 **AI Workflows & Specialists** (NEW!)
- **Dynamic Troubleshoot Agent**: Intelligent problem routing to specialist workflows
- **Missing Data Troubleshooting**: 10-step systematic analysis following Splunk best practices
- **Performance Analysis**: Comprehensive system diagnostics with parallel execution
- **Workflow Builder**: Create custom troubleshooting procedures for your organization
- **Workflow Runner**: Execute any workflow with full parameter control

### 🔍 Search & Analytics
- **Smart Search**: Natural language to SPL conversion
- **Real-time Search**: Background job management with progress tracking
- **Saved Searches**: Create, execute, and manage search automation

### 📊 Data Discovery
- **Metadata Exploration**: Discover indexes, sources, and sourcetypes
- **Schema Analysis**: Understand your data structure
- **Usage Patterns**: Identify data volume and access patterns

### 👥 Administration
- **App Management**: List, enable, disable Splunk applications
- **User Management**: Comprehensive user and role administration
- **Configuration Access**: Read and analyze Splunk configurations

### 🏥 Health Monitoring
- **System Health**: Monitor Splunk infrastructure status
- **Degraded Feature Detection**: Proactive issue identification
- **Alert Management**: Track and analyze triggered alerts

## 🌐 Client Integration Examples

### Cursor IDE
```json
{
  "mcpServers": {
    "splunk": {
      "command": "fastmcp",
      "args": ["run", "/path/to/src/server.py"],
      "env": {
        "MCP_SPLUNK_HOST": "your-splunk.com",
        "MCP_SPLUNK_USERNAME": "your-user"
      }
    }
  }
}
```

### Claude Desktop
```json
{
  "mcpServers": {
    "splunk": {
      "command": "fastmcp",
      "args": ["run", "/path/to/mcp-server-for-splunk/src/server.py"]
    }
  }
}
```

### Google Agent Development Kit
```python
from google.adk.tools.mcp_tool.mcp_toolset import MCPToolset

splunk_agent = LlmAgent(
    model='gemini-2.0-flash',
    tools=[MCPToolset(connection_params=StdioServerParameters(
        command='fastmcp',
        args=['run', '/path/to/src/server.py']
    ))]
)
```

## 🤝 Community & Contribution

### Create Your Own Tools
```bash
# Interactive tool generator
./contrib/scripts/generate_tool.py

# Validate implementation
./contrib/scripts/validate_tools.py

# Test your contribution
./contrib/scripts/test_contrib.py
```

### Contribution Categories
- **🛡️ Security Tools**: Threat hunting, incident response
- **⚙️ DevOps Tools**: Monitoring, alerting, operations
- **📈 Analytics Tools**: Business intelligence, reporting
- **💡 Example Tools**: Learning templates and patterns

## 🚀 Deployment Options

### Development (Local)
- **Startup Time**: ~10 seconds
- **Resource Usage**: Minimal (single Python process)
- **Best For**: Development, testing, stdio-based AI clients

### Production (Docker)
- **Features**: Load balancing, health checks, monitoring
- **Includes**: Traefik, MCP Inspector, optional Splunk
- **Best For**: Multi-client access, web-based AI agents

### Enterprise (Kubernetes)
- **Scalability**: Horizontal scaling, high availability
- **Security**: Pod-level isolation, secret management
- **Monitoring**: Comprehensive observability stack

## 🆘 Support & Community

- **🐛 Issues**: [GitHub Issues](https://github.com/your-org/mcp-server-for-splunk/issues)
- **💬 Discussions**: [GitHub Discussions](https://github.com/your-org/mcp-server-for-splunk/discussions)
- **📖 Documentation**: Complete guides and references
- **🔧 Interactive Testing**: MCP Inspector for real-time testing

### Windows Support
Windows users get first-class support with PowerShell scripts and comprehensive troubleshooting guides. See our [Windows Setup Guide](docs/WINDOWS_GUIDE.md).

## 📈 Project Stats

- ✅ **20+ Production Tools** - Comprehensive Splunk operations
- ✅ **14 Rich Resources** - System info and documentation access
- ✅ **Comprehensive Test Suite** - 170+ tests passing locally
- ✅ **Multi-Platform** - Windows, macOS, Linux support
- ✅ **Community-Ready** - Structured contribution framework
- ✅ **Enterprise-Proven** - Production deployment patterns

---

**Ready to empower your AI with Splunk?** 🎯

Choose your adventure:
- **🚀 [Quick Start](docs/getting-started/)** - Get running in 15 minutes
- **💻 [Integration Examples](docs/guides/integration/)** - Connect your AI tools
- **🏗️ [Architecture Guide](docs/architecture/)** - Understand the system
- **🤝 [Contribute](docs/community/contributing.md)** - Add your own tools

**Learn More**: [Model Context Protocol](https://modelcontextprotocol.io/) | [FastMCP Framework](https://gofastmcp.com/)
