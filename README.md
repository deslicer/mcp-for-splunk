<div style="display: flex; justify-content: space-between; align-items: flex-start; width: 100%; padding: 1em 0;">
  <!-- Logo -->
  <div>
    <img align="left" src="media/deslicer_white.svg" alt="Deslicer" width="200">
  </div>
</div>

# MCP Server for Splunk

[![FastMCP](https://img.shields.io/badge/FastMCP-2.13.0.2%2B-blue)](https://gofastmcp.com/)
[![Python](https://img.shields.io/badge/Python-3.10+-green)](https://python.org)
[![Docker](https://img.shields.io/badge/Docker-Ready-blue)](https://docker.com)
[![MCP](https://img.shields.io/badge/MCP-Compatible-purple)](https://modelcontextprotocol.io/)
[![Tests Passing](https://img.shields.io/badge/tests-174%20passing-green)](#)
[![Community](https://img.shields.io/badge/Community-Driven-orange)](#)
[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)

> **Enable AI agents to interact seamlessly with Splunk environments through the Model Context Protocol (MCP)**

Transform your Splunk instance into an AI-native platform. Our community-driven MCP server bridges Large Language Models and Splunk Enterprise/Cloud with 20+ tools, 16 resources (including CIM data models), and production-ready security—all through a single, standardized protocol.

## 🌟 Why This Matters

- **🔌 Universal AI Connection**: One protocol connects any AI to Splunk data
- **⚡ Zero Custom Integration**: No more months of custom API development
- **🛡️ Production-Ready Security**: Client-scoped access with no credential exposure
- **🤖 AI-Powered Workflows**: Intelligent troubleshooting agents that work like experts
- **🤝 Community-Driven**: Extensible framework with contribution examples

> **🚀 NEW: [AI-Powered Troubleshooting Workflows](docs/guides/workflows/README.md)** - Transform reactive firefighting into intelligent, systematic problem-solving with specialist AI workflows.

## 📋 Table of Contents

- [🚀 Quick Start](#quick-start)
  - [Prerequisites](#prerequisites)
  - [Configuration](#configuration)
  - [One-Command Setup](#one-command-setup)
- [🎯 What You Can Do](#what-you-can-do)
  - [🤖 AI-Powered Troubleshooting](#ai-powered-troubleshooting-new)
  - [🛡️ ITSI MCP Server](#itsi-mcp-server-new)
- [📚 Documentation Hub](#documentation-hub)
- [🔧 Available Tools & Capabilities](#available-tools--capabilities)
  - [🤖 AI Workflows & Specialists](#ai-workflows--specialists-new)
  - [🔍 Search & Analytics](#search--analytics)
  - [📊 Data Discovery](#data-discovery)
  - [👥 Administration](#administration)
  - [🏥 Health Monitoring](#health-monitoring)
  - [🛡️ Splunk IT Service Intelligence](#splunk-it-service-intelligence-itsi-new)
- [🌐 Client Integration Examples](#client-integration-examples)
  - [🔄 Multi-Client Benefits](#multi-client-benefits)
  - [Cursor IDE](#cursor-ide)
  - [Google Agent Development Kit](#google-agent-development-kit)
- [🤝 Community & Contribution](#community--contribution)
  - [🛠️ Create Your Own Tools & Extensions](#create-your-own-tools--extensions)
  - [Contribution Categories](#contribution-categories)
- [🚀 Deployment Options](#deployment-options)
  - [Development (Local)](#development-local)
  - [Production (Docker)](#production-docker)
  - [Enterprise (Kubernetes)](#enterprise-kubernetes)
- [🆘 Support & Community](#support--community)
  - [Windows Support](#windows-support)
- [📈 Project Stats](#project-stats)
- [🎯 Ready to Get Started?](#ready-to-get-started)

<a name="quick-start"></a>

## 🚀 Quick Start

<a name="prerequisites"></a>

### Prerequisites

- Python 3.10+ and UV package manager
- Nodejs (optional used for mcp inspector)
- Docker (optional but recommended for full stack)
- Splunk instance with API access (or use included Docker Splunk)

> **📖 Complete Setup Guide**: [Installation Guide](docs/getting-started/installation.md)

<a name="configuration"></a>

### Configuration

**Before running the setup, configure your Splunk connection:**

```bash
# Copy the example configuration
cp env.example .env

# Edit .env with your Splunk credentials
# - Use your existing Splunk instance (local, cloud, or Splunk Cloud)
# - OR use the included Docker Splunk (requires Docker)

# Optional HTTP transport defaults (local runs)
# - Stateless HTTP avoids sticky-session requirements
# - JSON responses improve compatibility with some clients
# These are already the defaults for local runs via `mcp-server --local`
echo "MCP_STATELESS_HTTP=true" >> .env
echo "MCP_JSON_RESPONSE=true" >> .env
```

<a name="one-command-setup"></a>

### One-Command Setup

**Windows:**

```powershell
git clone https://github.com/deslicer/mcp-for-splunk.git
cd mcp-for-splunk

```python
# Start the MCP Server (project script)
uv run mcp-server --local --detached

# Verify the server
uv run mcp-server --test
# Optional: show detailed tools/resources and health output
uv run mcp-server --test --detailed
```

**macOS/Linux:**

```bash
git clone https://github.com/deslicer/mcp-for-splunk.git
cd mcp-for-splunk

# (Recommended) Preview what would be installed
./scripts/smart-install.sh --dry-run

# Install missing prerequisites (base: Python, uv, Git, Node)
./scripts/smart-install.sh

# Start the MCP Server (project script)
# Local runs default to HTTP stateless mode + JSON response
uv run mcp-server --local --detached

# Verify the server
uv run mcp-server --test
# Optional: show detailed tools/resources and health output
uv run mcp-server --test --detailed
```

> **💡 Deployment Options**: The `mcp-server` command will prompt you to choose:
>
> - **Docker** (Option 1): Full stack with Splunk, Traefik, MCP Inspector - recommended if Docker is installed
> - **Local** (Option 2): Lightweight FastMCP server only - for users without Docker

> Stopping services:
> - `uv run mcp-server --stop` stops only this project's compose services (dev/prod/splunk). It does not stop the Docker engine.

> Note on Splunk licensing: When using the `so1` Splunk container, you must supply your own Splunk Enterprise license if required. The compose files include a commented example mount:
> `# - ./lic/splunk.lic:/tmp/license/splunk.lic:ro`. Create a `lic/` directory and mount your license file, or add the license via the Splunk Web UI after startup.

<a name="what-you-can-do"></a>

## 🎯 What You Can Do

<a name="ai-powered-troubleshooting-new"></a>

### 🤖 **AI-Powered Troubleshooting** (NEW!)

Transform your Splunk troubleshooting from manual procedures to intelligent, automated workflows using the MCP server endpoints:

```python
# Discover and execute intelligent troubleshooting workflows
result = await list_workflows.execute(ctx, format_type="summary")
# Returns: missing_data_troubleshooting, performance_analysis, custom_workflows...

# Run AI-powered troubleshooting with a single command
result = await workflow_runner.execute(
    ctx=ctx,
    workflow_id="missing_data_troubleshooting",
    earliest_time="-24h",
    latest_time="now",
    focus_index="main"
)
# → Parallel execution, expert analysis, actionable recommendations
```

**🚀 Key Benefits:**

- **🧠 Natural Language Interface**: "Troubleshoot missing data" → automated workflow execution
- **⚡ Parallel Processing**: Multiple diagnostic tasks run simultaneously for faster resolution
- **🔧 Custom Workflows**: Build organization-specific troubleshooting procedures
- **📊 Intelligent Analysis**: AI agents follow proven Splunk best practices

**[📖 Read the Complete AI Workflows Guide →](docs/guides/workflows/README.md)** for detailed examples, workflow creation, and advanced troubleshooting techniques.

<a name="itsi-mcp-server-new"></a>

### 🛡️ **ITSI MCP Server** (NEW!)

A dedicated Model Context Protocol server for **Splunk IT Service Intelligence** ships in this repo at [`mcp_itsi/`](mcp_itsi/README.md). It targets ITSI 4.21 and adds **70 tools, 9 documentation resources, and 3 workflow prompts** for managing services, entities, KPIs, episodes, glass tables, deep dives, correlation searches, and aggregation policies.

You can deploy it two ways with **identical capabilities**:

- **Plugin** of `mcp-for-splunk` — auto-registers via the `mcp_splunk.plugins` Python entry point. One process, one URL, one credential set.
- **Standalone** — its own FastMCP HTTP/stdio process, behind Traefik on `/itsi/mcp` (Docker), via `mcp-itsi-server` (local Python), or as the `mcp_itsi` Docker image (anywhere).

Both modes share the **same per-request `X-Splunk-*` headers** as the parent server (basic auth, bearer token, splunkd session token), plus optional `X-ITSI-*` overrides for app/user namespace.

**[🚀 ITSI Getting Started →](docs/guides/itsi/getting-started.md)** | **[🏗️ ITSI Deployment Guide →](docs/guides/itsi/deployment.md)** | **[📦 Package README →](mcp_itsi/README.md)**

<a name="documentation-hub"></a>

## 📚 Documentation Hub

| Document | Purpose | Audience | Time |
|----------|---------|----------|------|
| **[🤖 AI-Powered Troubleshooting](docs/guides/workflows/README.md)** | **Intelligent workflows powered by the workflow tools** | **All users** | **5 min** |
| **[Getting Started](docs/getting-started/)** | Complete setup guide with prerequisites | New users | 15 min |
| **[Integration Guide](docs/guides/integration/)** | Connect AI clients | Developers | 30 min |
| **[Deployment Guide](docs/guides/deployment/)** | Production deployment | DevOps | 45 min |
| **[Workflows Guide](docs/guides/workflows/README.md)** | Create and run workflows (OpenAI env vars) | Developers | 10 min |
| **[API Reference](docs/reference/tools.md)** | Tool documentation | Integrators | Reference |
| **[Resources Reference](docs/reference/resources.md)** | **Access CIM data models and Splunk docs** | **All users** | **Reference** |
| **[Contributing](docs/contrib/contributing.md)** | Add your own tools | Contributors | 60 min |
| **[📖 Contrib Guide](contrib/README.md)** | **Complete contribution framework** | **Contributors** | **15 min** |
| **[Architecture](docs/architecture/)** | Technical deep-dive | Architects | Reference |
| **[Tests Quick Start](docs/tests.md)** | First success test steps | Developers | 2 min |
| **[Plugins](docs/guides/plugins.md)** | Extend with entry-point plugins (separate package) | Integrators | 5 min |
| **[ITSI MCP Server (Getting Started)](docs/guides/itsi/getting-started.md)** | Zero-to-working ITSI MCP server in 15 minutes | ITSI users | 15 min |
| **[ITSI MCP Server (Deployment)](docs/guides/itsi/deployment.md)** | Standalone vs plugin, Docker, scaling, security | DevOps / Splunk admins | 20 min |

<a name="available-tools--capabilities"></a>

## 🔧 Available Tools & Capabilities

<a name="ai-workflows--specialists-new"></a>

### 🤖 **AI Workflows & Specialists** (NEW!)

- **`list_workflows`**: Discover available troubleshooting workflows (core + contrib)
- **`workflow_runner`**: Execute any workflow with full parameter control and progress tracking
- **`workflow_builder`**: Create custom troubleshooting procedures for your organization
- **Built-in Workflows**: Missing data troubleshooting, performance analysis, and more
- **[📖 Complete Workflow Guide →](docs/guides/workflows/README.md)**

<a name="search--analytics"></a>

### 🔍 Search & Analytics

- **Smart Search**: Natural language to SPL conversion
- **Real-time Search**: Background job management with progress tracking
- **Saved Searches**: Create, execute, and manage search automation

<a name="data-discovery"></a>

### 📊 Data Discovery

- **Metadata Exploration**: Discover indexes, sources, and sourcetypes
- **Schema Analysis**: Understand your data structure
- **Usage Patterns**: Identify data volume and access patterns

<a name="administration"></a>

### 👥 Administration

- **App Management**: List, enable, disable Splunk applications
- **User Management**: Comprehensive user and role administration
- **Configuration Access**: Read and analyze Splunk configurations

<a name="health-monitoring"></a>

### 🏥 Health Monitoring

- **System Health**: Monitor Splunk infrastructure status
- **Degraded Feature Detection**: Proactive issue identification
- **Alert Management**: Track and analyze triggered alerts

<a name="splunk-it-service-intelligence-itsi-new"></a>

### 🛡️ Splunk IT Service Intelligence (ITSI) — NEW!

The companion `mcp_itsi` server (standalone or plugin — see [🛡️ ITSI MCP Server](#itsi-mcp-server-new)) adds **70 ITSI-specific tools**:

- **Service Insights**: services, service templates, KPI base searches, KPI threshold templates, glass tables, deep dives, home views — full CRUD plus `itsi_count_services` and `itsi_templatize_service`.
- **Entity Integration**: entities, entity types, alias inventory; full CRUD with the documented schema quirks (alias fields must also live at the document root).
- **Event Analytics**: notable events with `itsi_acknowledge_notable_event` / `itsi_close_notable_event` shortcuts, plus full CRUD on aggregation policies and correlation searches.
- **Teams, maintenance windows, supported object types, and bundled docs** as `itsi_*` tools and `itsi://docs/<slug>` resources.

**[📦 Browse the ITSI tool catalog →](mcp_itsi/README.md#capabilities-at-a-glance)**

<a name="client-integration-examples"></a>

## 🌐 Client Integration Examples

**💪 Multi-Client Configuration Strength**: One of the key advantages of this MCP Server for Splunk is its ability to support multiple client configurations simultaneously. You can run a single server instance and connect multiple clients with different Splunk environments, credentials, and configurations - all without restarting the server or managing separate processes.

<a name="multi-client-benefits"></a>

### 🔄 Multi-Client Benefits

**Session-Based Isolation**: Each client connection maintains its own Splunk session with independent authentication, preventing credential conflicts between different users or environments.

**Dynamic Configuration**: Switch between Splunk instances (on-premises, cloud, development, production) by simply changing headers - no server restart required.

**Scalable Architecture**: A single server can handle multiple concurrent clients, each with their own Splunk context, making it ideal for team environments, CI/CD pipelines, and multi-tenant deployments.

**Resource Efficiency**: Eliminates the need to run separate MCP server instances for each Splunk environment, reducing resource consumption and management overhead.

<a name="cursor-ide"></a>

### Cursor IDE

## Single Tenant ##

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

## Client Specified Tenant ##

```json
{
    "mcpServers": {
      "splunk-in-docker": {
        "url": "http://localhost:8002/mcp/",
        "headers": {
          "X-Splunk-Host": "so1",
          "X-Splunk-Port": "8089",
          "X-Splunk-Username": "admin",
          "X-Splunk-Password": "Chang3d!",
          "X-Splunk-Scheme": "http",
          "X-Splunk-Verify-SSL": "false",
          "X-Session-ID": "splunk-in-docker-session"
        }
    },
        "splunk-cloud-instance": {
        "url": "http://localhost:8002/mcp/",
        "headers": {
          "X-Splunk-Host": "myorg.splunkcloud.com",
          "X-Splunk-Port": "8089",
          "X-Splunk-Username": "admin@myorg.com",
          "X-Splunk-Password": "Chang3d!Cloud",
          "X-Splunk-Scheme": "https",
          "X-Splunk-Verify-SSL": "true",
          "X-Session-ID": "splunk-cloud-session"
        }
    }
  }
}
```

<a name="google-agent-development-kit"></a>

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

<a name="community--contribution"></a>

## 🤝 Community & Contribution

Quick links: [Contributing](CONTRIBUTING.md) · [Code of Conduct](CODE_OF_CONDUCT.md) · [Security Policy](SECURITY.md) · [Governance](GOVERNANCE.md) · [License](LICENSE)

<a name="create-your-own-tools--extensions"></a>

### 🛠️ **Create Your Own Tools & Extensions**

**🚀 Quick Start for Contributors:**

```bash
# Interactive tool generator (project script)
uv run generate-tool

# Browse existing tools for inspiration
./contrib/scripts/list_tools.py

# Validate your tool implementation (project script)
uv run validate-tools

# Test your contribution
./contrib/scripts/test_contrib.py
```

**[📖 Complete Contributing Guide →](contrib/README.md)** - Everything you need to know about creating tools, resources, and workflows for the MCP Server for Splunk.

<a name="contribution-categories"></a>

### **Contribution Categories**

- **🛡️ Security Tools**: Threat hunting, incident response, security analysis
- **⚙️ DevOps Tools**: Monitoring, alerting, operations, SRE workflows
- **📈 Analytics Tools**: Business intelligence, reporting, data analysis
- **💡 Example Tools**: Learning templates and patterns for new contributors
- **🔧 Custom Workflows**: AI-powered troubleshooting procedures for your organization

<a name="deployment-options"></a>

## 🚀 Deployment Options

<a name="development-local"></a>

### Development (Local)

- **Startup Time**: ~10 seconds
- **Resource Usage**: Minimal (single Python process)
- **Best For**: Development, testing, stdio-based AI clients
- **HTTP Defaults**: Local runs enable `MCP_STATELESS_HTTP=true` and `MCP_JSON_RESPONSE=true` by default for compatibility with Official MCP clients (no sticky sessions; JSON over SSE).
  - Endpoint: `http://localhost:8003/mcp/`
  - Required client headers:
    - `Accept: application/json, text/event-stream`
    - `MCP-Session-ID: <uuid>` (preferred; `X-Session-ID` optional)
    - `X-Splunk-*` headers (host, port, username, password, scheme, verify-ssl) or set via `.env`

<a name="production-docker"></a>

### Production (Docker)

- **Features**: Load balancing, health checks, monitoring
- **Includes**: Traefik, MCP Inspector, optional Splunk
- **Best For**: Multi-client access, web-based AI agents
- **Session Routing**: Traefik is configured with sticky sessions for streamable HTTP; alternatively, enable stateless HTTP for development scenarios.

<a name="enterprise-kubernetes"></a>

### Enterprise (Kubernetes)

- **Scalability**: Horizontal scaling, high availability
- **Security**: Pod-level isolation, secret management
- **Monitoring**: Comprehensive observability stack

### ITSI MCP Server

- **Plugin mode**: Auto-loads into `mcp-for-splunk` via the `mcp_splunk.plugins` entry point — single process, single URL.
- **Standalone mode**: Dedicated FastMCP container behind Traefik at `/itsi/mcp`, or `mcp-itsi-server` console script for local Python, or `mcp_itsi` Docker image for any orchestrator.
- **Auth parity**: Same `X-Splunk-*` headers as the parent server; optional `X-ITSI-App` / `X-ITSI-User-NS` / `X-ITSI-API-Version` for ITSI-specific namespacing.
- **Verification**: `uv run python scripts/test_itsi_mcp_both_modes.py` exercises both modes end-to-end against any live ITSI cluster.

**[📖 Full ITSI deployment guide →](docs/guides/itsi/deployment.md)**

<a name="support--community"></a>

## 🆘 Support & Community

- **🐛 Issues**: [GitHub Issues](https://github.com/deslicer/mcp-server-for-splunk/issues)
- **💬 Discussions**: [GitHub Discussions](https://github.com/deslicer/mcp-server-for-splunk/discussions)
- **📖 Documentation**: Complete guides and references
- **🔧 Interactive Testing**: MCP Inspector for real-time testing

<a name="windows-support"></a>

### Windows Support

Windows users get first-class support with PowerShell scripts and comprehensive troubleshooting guides. See our [Windows Setup Guide](docs/WINDOWS_GUIDE.md).

<a name="project-stats"></a>

## 📈 Project Stats

- ✅ **20+ Production Tools** - Comprehensive Splunk operations
- ✅ **16 Rich Resources** - System info, documentation, and CIM data models
- ✅ **Comprehensive Test Suite** - 170+ tests passing locally
- ✅ **Multi-Platform** - Windows, macOS, Linux support
- ✅ **Community-Ready** - Structured contribution framework
- ✅ **Enterprise-Proven** - Production deployment patterns

---

<a name="ready-to-get-started"></a>

## 🎯 Ready to Get Started?

Choose your adventure:

- **🚀 [Quick Start](docs/getting-started/)** - Get running in 15 minutes
- **💻 [Integration Examples](docs/guides/integration/)** - Connect your AI tools
- **🏗️ [Architecture Guide](docs/architecture/)** - Understand the system
- **🤝 [Contribute](docs/contrib/contributing.md)** - Add your own tools

**Learn More**: [Model Context Protocol](https://modelcontextprotocol.io/) | [FastMCP Framework](https://gofastmcp.com/)
