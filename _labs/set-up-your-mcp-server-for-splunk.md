
# Set up MCP for Splunk (🔧)

Install prerequisites, prepare your environment, and run the MCP server.

## 1. Install prerequisites

This guide provides comprehensive installation instructions for all prerequisites needed to run the MCP for Splunk on Windows, macOS, and Linux systems.

### 📋 Overview

Before running the MCP for Splunk, ensure you have the following prerequisites installed on your system:

### 🖥️ **System Requirements**

| Requirement | Minimum Version | Recommended | Platform Support |
|-------------|-----------------|-------------|------------------|
| **Python** | 3.10+ | 3.11+ | Windows, macOS, Linux |
| **UV Package Manager** | Latest | Latest | Windows, macOS, Linux |
| **Node.js** (Optional) | 18+ | 20+ LTS | For MCP Inspector testing |
| **Docker** (Optional) | 20+ | Latest | For full containerized stack |
| **Git** | 2.0+ | Latest | For cloning repository |

### 1.1 Choose your path

For this guide, "Beginner" means you don’t have Git or a code editor installed and you’re not comfortable using the terminal/PowerShell yet.

- ***If you're a beginner: go to [Beginners Setup](docs/mcp/BEGINNERS_SETUP.md)***
- ***If you need to install prerequisites on your OS:***
  - [Windows Users](docs/mcp/WINDOWS_GUIDE.md)
  - [macOS Users](docs/mcp/MACOS_GUIDE.md)
  - [Linux Users](docs/mcp/LINUX_GUIDE.md)

- ***If you already have all prerequisites installed: jump to [Clone GitHub Repository](#clone-repo)***

<a id="clone-repo"></a>
### 1.2 Clone GitHub Repository

```bash
git clone https://github.com/deslicer/mcp-for-splunk.git
cd mcp-for-splunk
# Checkout dev1666 branch in git, this branch has a prepared .env file for you.
git checkout dev1666
```

<a id="prepare-env"></a>
## 2. Prepare your environment

### Prerequisites

- Python 3.10+ and UV package manager
- Splunk test instance will be provided to you by email, let the instructor know if you haven't received an email.

### 2.1 Sync project dependencies

Run this first to install all project dependencies as defined by the lockfile. Syncing ensures everything is up-to-date before you start the server.

```bash
uv sync
```

### 2.2 Run the MCP server

#### Option 1 - Local Service - Recommended

```bash
# Start the uv application using command line
# Linux/MacOS
./scripts/build_and_run.sh --local

# Windows PowerShell
.\scripts\build_and_run.ps1 --local

# Windows (CMD)
.\scripts\build_and_run.bat --local
```

#### Option 2 - Docker Solution - Optional

```bash
# Ensure that Docker Desktop is started on your laptop
docker ps
# Download and build the MCP server using Docker
# Linux/MacOS
./scripts/build_and_run.sh --docker
# To stop the containers
./scripts/build_and_run.sh --stop

# Windows PowerShell
.\scripts\build_and_run.ps1 --docker

# Windows (CMD)
.\scripts\build_and_run.bat --docker
```

### 2.3 Verify the MCP server

You can verify in one of two ways:

- Using MCP Inspector: follow the sections below:
  - Part 1 - Verification - Local Service
  - Verification - Docker Solution (for Docker)
- Run the automated test script:

#### 1. Automated test script
```bash
uv run python scripts/test_setup.py
```

Expected output:

```text
🔍 Testing MCP Server at http://localhost:8003/mcp/
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

***If you see ✅ MCP Server is running and responding correctly! in the output you have complete this Lab ✅ ***

#### 2. MCP Inspector

- Open `http://localhost:6274`
- Click Connect to browse and run tools

<p align="center">
  <img src="media/mcp_server_connect.png" alt="MCP Inspector connected to local server" />
  
</p>

#### Part 1 - Verification - Local Service

1. Connect and list `server_info` resource.
2. After you have connected to the MCP server, click the
`server_info` in the **Resources** column.
3. To the right, the response message from `server_info` is displayed.

4. Click on the green text in text: value field.

***If you see ```"status":"running"``` in the text you have complete this Lab ✅***

<p align="center">
  <img src="media/mcp_server_connect_docker.png" alt="MCP Inspector connected to Docker server" />
  
</p>

#### Verification - Docker Solution

1. Connect and list `server_info` resource.
2. After you have connected to the MCP server, click the
`server_info` in the **Resources** column.
3. To the right, the response message from `server_info` is displayed.

4. Click on the green text in text: value field.

***If you see ```"status":"running"``` in the text you have complete this Lab ✅***
