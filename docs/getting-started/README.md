# Getting Started with MCP Server for Splunk

Welcome! This guide will take you from zero to a working MCP server connected to Splunk in just 15 minutes.

## 🎯 What You'll Achieve

By the end of this guide, you'll have:
- ✅ A running MCP server with 20+ Splunk tools
- ✅ AI agents that can search and analyze Splunk data
- ✅ Interactive testing environment (MCP Inspector)
- ✅ Understanding of basic operations and next steps

## 🏃‍♂️ Quick Path (5 minutes)

**Already have Python 3.10+ and want to get started immediately?**

```bash
# Clone and run in one shot
git clone https://github.com/your-org/mcp-server-for-splunk.git
cd mcp-server-for-splunk
./scripts/build_and_run.sh    # macOS/Linux
# OR
.\scripts\build_and_run.ps1   # Windows
```

Skip to [First Success Test](#first-success-test) →

## 📋 Prerequisites Check

### Required Tools
| Tool | Version | Installation | Check |
|------|---------|--------------|-------|
| **Python** | 3.10+ | [Download](https://python.org) | `python --version` |
| **UV** | Latest | [Install Guide](https://github.com/astral-sh/uv) | `uv --version` |
| **Git** | Any | [Download](https://git-scm.com) | `git --version` |

### Optional Tools
| Tool | Purpose | Installation |
|------|---------|--------------|
| **Docker** | Full stack deployment | [Docker Desktop](https://docker.com) |
| **Node.js 18+** | MCP Inspector (testing) | [Download](https://nodejs.org) |

### Splunk Access
- **Splunk instance** (Enterprise, Cloud, or local)
- **Valid credentials** with search permissions
- **Network access** to Splunk management port (8089)

> **💡 Don't have Splunk?** The server includes a Docker Splunk instance for testing!

## 🚀 Step-by-Step Installation

### Step 1: Clone the Repository

```bash
git clone https://github.com/your-org/mcp-server-for-splunk.git
cd mcp-server-for-splunk
```

### Step 2: Configure Your Environment

```bash
# Copy the example configuration
cp env.example .env

# Edit .env with your Splunk credentials
# - Use your existing Splunk instance (local, cloud, or Splunk Cloud)
# - OR use the included Docker Splunk (requires Docker)
```

### Step 3: Choose Your Deployment Mode

The setup script will automatically detect your environment and present options:

#### Option A: Docker (Default if Docker is installed)
- **Includes**: Complete stack with Splunk, MCP Inspector, monitoring
- **Best for**: Testing, development, multi-client access
- **Startup**: ~2 minutes

#### Option B: Local (For users without Docker)
- **Includes**: MCP server only
- **Best for**: AI client integration, lightweight development
- **Startup**: ~10 seconds

### Step 4: Run the Setup

**Windows (PowerShell):**
```powershell
.\scripts\build_and_run.ps1
```

**Windows (Command Prompt):**
```cmd
.\scripts\build_and_run.bat
```

**macOS/Linux:**
```bash
./scripts/build_and_run.sh
```

The script will:
1. Check prerequisites and install missing tools
2. Set up your environment
3. Load configuration from .env file
4. Start the MCP server
5. Launch MCP Inspector for testing (if Node.js is installed)

## ✅ First Success Test

### Verify Server Health

**Run the automated test script:**
```bash
uv run python scripts/test_setup.py
```

**Expected output:**
```
🔍 Testing MCP Server at http://localhost:8001/mcp/
--------------------------------------------------
✓ Connected to MCP Server

📋 Available Tools:
  1. run_oneshot_search
     Run a Splunk search and return results immediately...
  2. get_splunk_health
     Get Splunk server health information...
  ... and 27 more tools

📚 Available Resources:
  1. info://server
     Server Information
  ... and 8 more resources

✅ MCP Server is running and responding correctly!
```

### Interactive Testing

1. **Open MCP Inspector**: http://localhost:6274
2. **Configure connection**:
   - Ensure that Streamable HTTP is set
   - Update URL from default to: `http://localhost:8001/mcp/`
   - Click "Connect" button at the bottom
3. **Test a basic tool**: Try `get_splunk_health`

Expected result:
```json
{
  "status": "connected",
  "version": "9.0.x",
  "server_name": "splunk-server"
}
```

### Test an AI Integration

If you have Claude Desktop installed:

1. Add this to your `claude_desktop_config.json`:
```json
{
  "mcpServers": {
    "splunk": {
      "command": "fastmcp",
      "args": ["run", "/path/to/mcp-server-for-splunk/src/server.py"],
      "env": {
        "SPLUNK_HOST": "localhost",
        "SPLUNK_USERNAME": "admin",
        "SPLUNK_PASSWORD": "Chang3d!"
      }
    }
  }
}
```

2. Restart Claude Desktop
3. Ask: *"What's the health status of my Splunk server?"*

## 🎉 What You Can Do Now

### Basic Operations

**Search Splunk Data:**
```
"Search for errors in the last 24 hours"
"Show me the top 10 source types by volume"
```

**Explore Your Environment:**
```
"List all Splunk indexes"
"What apps are installed?"
"Show me recent alert activity"
```

**Health Monitoring:**
```
"Check Splunk system health"
"Are there any degraded features?"
```

### Available Tools

Your MCP server now includes:

#### 🔍 Search Tools
- `run_oneshot_search` - Quick SPL queries
- `run_splunk_search` - Background search jobs
- `list_saved_searches` - Manage saved searches

#### 📊 Data Discovery
- `list_indexes` - Available data indexes
- `list_sources` - Data source discovery
- `list_sourcetypes` - Data format types

#### 👥 Administration
- `list_apps` - Installed Splunk apps
- `list_users` - User management
- `get_configurations` - Configuration access

#### 🏥 Monitoring
- `get_splunk_health` - System health checks
- `list_triggered_alerts` - Alert monitoring

## 🔧 Configuration

### Environment Variables

The server supports flexible configuration:

```bash
# Method 1: Server environment
export SPLUNK_HOST=your-splunk.company.com
export SPLUNK_USERNAME=your-username
export SPLUNK_PASSWORD=your-password

# Method 2: Client environment (MCP-prefixed)
export MCP_SPLUNK_HOST=your-splunk.company.com
export MCP_SPLUNK_USERNAME=your-username
export MCP_SPLUNK_PASSWORD=your-password
```

### .env File (Recommended)

Create a `.env` file in the project root:

```env
SPLUNK_HOST=your-splunk-server.com
SPLUNK_USERNAME=your-username
SPLUNK_PASSWORD=your-password
SPLUNK_PORT=8089
SPLUNK_VERIFY_SSL=false
```

### Multi-tenant Configuration

For connecting different AI clients to different Splunk instances:

```bash
# Using HTTP headers
curl -H "X-Splunk-Host: prod-splunk.company.com" \
     -H "X-Splunk-Username: prod-user" \
     -H "X-Splunk-Password: prod-password" \
     http://localhost:8001/mcp/
```

## 🚨 Troubleshooting

### Common Issues

**"Command not found: uv"**
```bash
# Install UV package manager
curl -LsSf https://astral.sh/uv/install.sh | sh  # macOS/Linux
# OR
winget install astral-sh.uv  # Windows
```

**"Permission denied" on Windows**
```powershell
# Enable script execution
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

**"Port already in use"**
- The scripts auto-detect available ports
- Check what's running: `netstat -tulpn | grep 8001`
- Or use a different port: `fastmcp run src/server.py --port 8002`

**"Splunk connection failed"**
```bash
# Test Splunk connectivity
curl -k https://your-splunk:8089/services/server/info

# Check credentials
curl -k -u username:password https://your-splunk:8089/services/server/info
```

### Getting Help

1. **Check logs**: `docker logs mcp-server` (Docker) or console output (local)
2. **Test manually**: Use MCP Inspector to test individual tools
3. **Community support**: [GitHub Discussions](https://github.com/your-org/mcp-server-for-splunk/discussions)

## 🎯 Next Steps

### Learn More
- **[Integration Guide](../guides/integration/)** - Connect different AI clients
- **[Tools Reference](../reference/tools.md)** - Tool documentation
- **[Architecture](../architecture/)** - How it all works together

### Extend & Contribute
- **[Contributing Guide](../contrib/contributing.md)** - Add your own tools
- **[Tool Development](../contrib/tool_development.md)** - Build custom functionality

### Deploy to Production
- **[Deployment Guide](../guides/deployment/)** - Production-ready setup
- **[Security Guide](../guides/security.md)** - Production security practices

---

**🎉 Congratulations!** You now have AI agents that can natively interact with Splunk data. What will you build next?
