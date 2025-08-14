# Windows Setup Guide for MCP Server for Splunk

This guide provides Windows-specific instructions for setting up and running the MCP Server for Splunk.

## 📋 Prerequisites

### Required Software

| Software | Version | Installation Method | Notes |
|----------|---------|-------------------|-------|
| **PowerShell** | 5.1+ or Core 7+ | Built-in or [Microsoft Store](https://aka.ms/powershell) | Required for main script |
| **Python** | 3.10+ | [Microsoft Store](https://apps.microsoft.com/store/detail/python-310/9PJPW5LDXLZ5) or [python.org](https://python.org) | Use Microsoft Store version for best PATH handling |
| **Git** | Latest | [git-scm.com](https://git-scm.com/download/win) | For cloning the repository |

### Optional Software

| Software | Purpose | Installation |
|----------|---------|--------------|
| **Docker Desktop** | Full-stack deployment | [docker.com](https://docker.com/products/docker-desktop) |
| **Node.js** | MCP Inspector testing | [nodejs.org](https://nodejs.org/) |
| **Windows Terminal** | Better terminal experience | [Microsoft Store](https://aka.ms/terminal) |

## 🚀 Quick Start

### Option 1: PowerShell Script (Recommended)

```powershell
# Clone the repository
git clone https://github.com/your-org/mcp-server-for-splunk.git
cd mcp-server-for-splunk

# Run the setup script
.\scripts\build_and_run.ps1
```

### Option 2: Batch File (Alternative)

```cmd
# Clone the repository
git clone https://github.com/your-org/mcp-server-for-splunk.git
cd mcp-server-for-splunk

# Run the setup script (calls PowerShell internally)
.\scripts\build_and_run.bat
```

### Option 3: Manual Setup

```powershell
# Install uv package manager
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

## ⚙️ Configuration

### Environment Variables

Create or edit the `.env` file:

```env
# Splunk Connection
SPLUNK_HOST=your-splunk-host.com
SPLUNK_PORT=8089
SPLUNK_USERNAME=your-username
SPLUNK_PASSWORD=your-password
SPLUNK_VERIFY_SSL=false

# Optional: MCP-specific overrides
MCP_SPLUNK_HOST=dev-splunk.company.com
MCP_SPLUNK_USERNAME=dev-user
MCP_SPLUNK_PASSWORD=dev-password
```

### PowerShell Execution Policy

If you encounter execution policy errors:

```powershell
# Check current policy
Get-ExecutionPolicy -List

# Set policy for current user (recommended)
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser

# Or temporarily bypass for one session
PowerShell -ExecutionPolicy Bypass -File .\scripts\build_and_run.ps1
```

## 🐳 Docker Setup

### Prerequisites for Docker Mode

1. **Install Docker Desktop**:
   - Download from [docker.com](https://docker.com/products/docker-desktop)
   - Enable WSL2 backend during installation
   - Ensure Docker Desktop is running

2. **Verify Docker Installation**:
   ```powershell
   docker --version
   docker info
   ```

### Running with Docker

```powershell
# Force Docker mode
.\scripts\build_and_run.ps1 -DockerOnly

# Or let the script auto-detect (recommended)
.\scripts\build_and_run.ps1
```

## 🔧 Script Options

The PowerShell script supports several options:

```powershell
# Show help
.\scripts\build_and_run.ps1 -Help

# Force local development mode (no Docker)
.\scripts\build_and_run.ps1 -LocalOnly

# Force Docker mode (fail if Docker unavailable)
.\scripts\build_and_run.ps1 -DockerOnly
```

## 🎯 Access Points

After successful setup, you can access:

| Service | URL | Description |
|---------|-----|-------------|
| **MCP Server (HTTP)** | http://localhost:8000+ | Auto-detects available port |
| **MCP Inspector** | http://localhost:6274 | Local testing interface |
| **Splunk Web** | http://localhost:9000 | Docker mode only (admin/Chang3d!) |
| **Traefik Dashboard** | http://localhost:8080 | Docker mode only |

## 🛠️ Troubleshooting

### Common Issues

#### PowerShell Execution Policy
```powershell
# Error: "execution of scripts is disabled on this system"
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

#### Python Not Found
```powershell
# Check Python installation
python --version
py --version

# Add Python to PATH (if needed)
$env:PATH += ";C:\Users\$env:USERNAME\AppData\Local\Programs\Python\Python310"
```

#### uv Installation Issues
```powershell
# Try different installation methods
winget install astral-sh.uv
# OR
pip install uv
# OR download from https://astral.sh/uv/
```

#### Docker Desktop Issues
- Ensure WSL2 is enabled: `wsl --install`
- Restart Docker Desktop after installation
- Check Docker settings: Enable "Expose daemon on tcp://localhost:2375"

#### Port Conflicts
The script automatically detects port conflicts and uses available ports:
- MCP Server: 8000, 8001, 8002, etc.
- MCP Inspector: 6274 (fixed)

#### Node.js/NPM Issues
```powershell
# Check Node.js installation
node --version
npm --version

# Install if missing
winget install OpenJS.NodeJS
```

### Debugging Commands

```powershell
# Check all prerequisites
python --version
uv --version
docker --version
node --version
git --version

# Check PowerShell version
$PSVersionTable.PSVersion

# Test Docker connectivity
docker run hello-world

# View detailed script help
.\scripts\build_and_run.ps1 -Help

# Check Windows version
Get-ComputerInfo | Select WindowsProductName, WindowsVersion
```

### Log Files

When running locally, check these log files:

```powershell
# MCP Server logs
Get-Content logs\mcp_server.log -Tail 20

# MCP Inspector logs
Get-Content logs\inspector.log -Tail 20

# Error logs
Get-Content logs\mcp_server_error.log -Tail 20
Get-Content logs\inspector_error.log -Tail 20
```

## 🔍 Testing

### Using MCP Inspector

1. **Start the server**: `.\scripts\build_and_run.ps1`
2. **Open MCP Inspector**: http://localhost:6274
3. **Connect to server**: http://localhost:8000 (or shown port)
4. **Test tools**:
   - Try `get_splunk_health`
   - Explore `splunk://health/status`
   - Test search tools

### Manual Testing

```powershell
# Test HTTP endpoint
Invoke-WebRequest -Uri "http://localhost:8000" -UseBasicParsing

# Test specific port
Test-NetConnection -ComputerName localhost -Port 8000
```

## 📦 Development

### Setting up Development Environment

```powershell
# Install development dependencies
uv sync --dev

# Run tests
uv run pytest

# Format code
uv run black .

# Lint code
uv run flake8
```

### Creating Custom Tools

```powershell
# Use the interactive tool generator
.\contrib\scripts\generate_tool.py

# Browse existing tools
.\contrib\scripts\list_tools.py --interactive

# Validate your tools
.\contrib\scripts\validate_tools.py
```

## 🆘 Getting Help

### Resources
- **Documentation**: `/docs` folder
- **Examples**: `/examples` folder
- **Contributing**: `/contrib` folder

### Support Channels
- **Issues**: [GitHub Issues](https://github.com/your-org/mcp-server-for-splunk/issues)
- **Discussions**: [GitHub Discussions](https://github.com/your-org/mcp-server-for-splunk/discussions)

### Windows-Specific Help

For Windows-specific issues, include this information when seeking help:

```powershell
# System information
Get-ComputerInfo | Select WindowsProductName, WindowsVersion, TotalPhysicalMemory

# PowerShell version
$PSVersionTable

# Python information
python --version
pip --version

# Docker information (if using Docker)
docker --version
docker info

# Error logs
Get-Content logs\mcp_server.log -Tail 50
```

## 🎉 Success Indicators

You'll know the setup is working when you see:

✅ **Environment Setup**
- Python 3.10+ detected
- uv package manager installed
- Dependencies synchronized

✅ **Server Running**
- MCP server listening on http://localhost:8000+
- No error messages in logs
- Health check responds successfully

✅ **MCP Inspector** (if Node.js available)
- Inspector accessible at http://localhost:6274
- Can connect to MCP server
- Tools and resources load correctly

✅ **Docker Mode** (if using Docker)
- All containers running
- Splunk accessible at http://localhost:9000
- Traefik dashboard at http://localhost:8080

---

**Need more help?** Check the main [README.md](../README.md) or create an issue on GitHub!
