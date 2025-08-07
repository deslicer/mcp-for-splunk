# Prerequisites Guide - MCP Server for Splunk

This guide provides comprehensive installation instructions for all prerequisites needed to run the MCP Server for Splunk on Windows, macOS, and Linux systems.

## 📋 Overview

Before running the MCP Server for Splunk, ensure you have the following prerequisites installed on your system:

## 🖥️ **System Requirements**

| Requirement | Minimum Version | Recommended | Platform Support |
|-------------|-----------------|-------------|------------------|
| **Python** | 3.10+ | 3.11+ | Windows, macOS, Linux |
| **UV Package Manager** | Latest | Latest | Windows, macOS, Linux |
| **Node.js** (Optional) | 18+ | 20+ LTS | For MCP Inspector testing |
| **Docker** (Optional) | 20+ | Latest | For full containerized stack |
| **Git** | 2.0+ | Latest | For cloning repository |

## 🐍 **Python Installation**

### **Windows:**
```powershell
# Option 1: Microsoft Store (Recommended)
# Search "Python" in Microsoft Store and install Python 3.11+

# Option 2: Official installer
# Download from https://python.org/downloads/
# ✅ Check "Add Python to PATH" during installation

# Option 3: Winget
winget install Python.Python.3.12

# Option 4: Chocolatey
choco install python

# Verify installation
python --version
pip --version
```

### **macOS:**
```bash
# Option 1: Homebrew (Recommended)
brew install python@3.11

# Option 2: Official installer
# Download from https://python.org/downloads/

# Option 3: pyenv
brew install pyenv
pyenv install 3.11.0
pyenv global 3.11.0

# Verify installation
python3 --version
pip3 --version
```

### **Linux (Ubuntu/Debian):**
```bash
# Update package list
sudo apt update

# Install Python 3.11+
sudo apt install python3.11 python3.11-pip python3.11-venv

# Alternative: deadsnakes PPA for latest versions
sudo add-apt-repository ppa:deadsnakes/ppa
sudo apt update
sudo apt install python3.11 python3.11-pip python3.11-venv

# Verify installation
python3 --version
pip3 --version
```

### **Linux (RHEL/CentOS/Fedora):**
```bash
# Fedora
sudo dnf install python3.11 python3.11-pip

# RHEL/CentOS with EPEL
sudo yum install epel-release
sudo yum install python3.11 python3.11-pip

# Verify installation
python3 --version
pip3 --version
```

## ⚡ **UV Package Manager Installation**

UV is a fast Python package installer and dependency resolver, required for this project.

### **Windows:**
```powershell
# Option 1: Official installer (Recommended)
irm https://astral.sh/uv/install.ps1 | iex

# Option 2: Winget
winget install astral-sh.uv

# Option 3: Pip fallback
pip install uv

# Verify installation
uv --version
```

### **macOS/Linux:**
```bash
# Official installer (Recommended)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Add to PATH (add to your shell profile)
export PATH="$HOME/.cargo/bin:$PATH"

# Alternative: Homebrew (macOS)
brew install uv

# Alternative: Pip fallback
pip install uv

# Verify installation
uv --version
```

## 🌐 **Node.js Installation (Optional - for MCP Inspector)**

Node.js enables the interactive MCP Inspector for testing tools and resources.

### **Windows:**
```powershell
# Option 1: Official installer (Recommended)
# Download from https://nodejs.org/

# Option 2: Winget
winget install OpenJS.NodeJS

# Option 3: Chocolatey
choco install nodejs

# Verify installation
node --version
npm --version
```

### **macOS:**
```bash
# Option 1: Homebrew (Recommended)
brew install node

# Option 2: Official installer
# Download from https://nodejs.org/

# Option 3: Node Version Manager (nvm)
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.0/install.sh | bash
nvm install --lts
nvm use --lts

# Verify installation
node --version
npm --version
```

### **Linux:**
```bash
# Ubuntu/Debian - NodeSource repository (Recommended)
curl -fsSL https://deb.nodesource.com/setup_lts.x | sudo -E bash -
sudo apt-get install -y nodejs

# Alternative: Package manager
sudo apt install nodejs npm

# RHEL/CentOS/Fedora
sudo dnf install nodejs npm

# Verify installation
node --version
npm --version
```

## 🐳 **Docker Installation (Optional - for Full Stack)**

Docker enables the complete development stack with Splunk, Traefik, and monitoring.

### **Windows:**
```powershell
# Docker Desktop (Recommended)
# Download from https://docker.com/products/docker-desktop/

# Winget
winget install Docker.DockerDesktop

# After installation, ensure Docker Desktop is running
docker --version
docker-compose --version
```

### **macOS:**
```bash
# Docker Desktop (Recommended)
# Download from https://docker.com/products/docker-desktop/

# Homebrew
brew install --cask docker

# Verify installation
docker --version
docker-compose --version
```

### **Linux:**
```bash
# Ubuntu/Debian - Install Docker Engine
sudo apt update
sudo apt install apt-transport-https ca-certificates curl software-properties-common
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo apt-key add -
sudo add-apt-repository "deb [arch=amd64] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable"
sudo apt update
sudo apt install docker-ce docker-ce-cli containerd.io docker-compose-plugin

# Start and enable Docker
sudo systemctl start docker
sudo systemctl enable docker

# Add user to docker group (logout/login required)
sudo usermod -aG docker $USER

# Verify installation
docker --version
docker compose version
```

## 🔧 **Additional Tools**

### **Git:**
- **Windows:** `winget install Git.Git` or download from [git-scm.com](https://git-scm.com/)
- **macOS:** `brew install git` or use Xcode Command Line Tools
- **Linux:** `sudo apt install git` (Ubuntu/Debian) or `sudo dnf install git` (Fedora)

### **curl (for testing):**
- **Windows:** Included in Windows 10+ or `winget install cURL.cURL`
- **macOS:** Pre-installed or `brew install curl`
- **Linux:** `sudo apt install curl` or `sudo dnf install curl`

## ✅ **Prerequisites Verification**

We've included comprehensive scripts to verify all prerequisites are correctly installed:

### **Windows (PowerShell):**
```powershell
# Run the prerequisites checker
.\scripts\check-prerequisites.ps1

# For detailed information including installation paths
.\scripts\check-prerequisites.ps1 -Detailed

# For help and usage information
.\scripts\check-prerequisites.ps1 -Help
```

### **macOS/Linux (Bash):**
```bash
# Run the prerequisites checker
./scripts/check-prerequisites.sh

# For detailed information including installation paths
./scripts/check-prerequisites.sh --detailed

# For help and usage information
./scripts/check-prerequisites.sh --help
```

**The verification scripts will:**
- ✅ Check all required and optional tools
- 📊 Show system information (OS, architecture, available space)
- 🎯 Provide specific installation commands for missing tools
- 🔧 Detect your package manager and suggest appropriate commands
- 📋 Give you a clear summary of what needs to be installed

## 🎯 **Quick Setup Commands**

### **Windows (PowerShell as Administrator):**
```powershell
# Install all prerequisites at once
winget install Python.Python.3.12 astral-sh.uv OpenJS.NodeJS Docker.DockerDesktop Git.Git

# Verify installations
python --version; uv --version; node --version; docker --version; git --version
```

### **macOS (with Homebrew):**
```bash
# Install Homebrew if not installed
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Install all prerequisites
brew install python@3.11 uv node git
brew install --cask docker

# Verify installations
python3 --version && uv --version && node --version && docker --version && git --version
```

### **Linux (Ubuntu/Debian):**
```bash
# Update system and install prerequisites
sudo apt update
sudo apt install -y python3.11 python3.11-pip python3.11-venv nodejs npm git curl

# Install UV
curl -LsSf https://astral.sh/uv/install.sh | sh
export PATH="$HOME/.cargo/bin:$PATH"

# Install Docker (optional)
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER

# Verify installations
python3 --version && uv --version && node --version && git --version
```

## 🏢 **Splunk Requirements**

- **Splunk instance** (Enterprise or Cloud)
- Valid Splunk credentials with appropriate permissions:
  - Search capabilities for your intended indexes
  - Admin access (for admin tools)
  - KV Store access (for KV Store tools)

## 🪟 **Windows-Specific Troubleshooting**

### **PowerShell Execution Policy:**
```powershell
# If you get execution policy errors, run:
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### **Common Windows Issues:**
- **uv installation**: Try `winget install astral-sh.uv` or `pip install uv`
- **Docker Desktop**: Ensure WSL2 backend is enabled
- **Port conflicts**: Windows script auto-detects and uses available ports
- **Node.js/npm**: Download from [nodejs.org](https://nodejs.org/) for MCP Inspector
- **Python PATH**: Use Microsoft Store Python or ensure Python is in PATH

### **Debugging Commands:**
```powershell
# Check Python installation
python --version

# Check uv installation  
uv --version

# Check Docker
docker --version
docker info

# Check Node.js
node --version
npx --version

# View detailed help
.\scripts\build_and_run.ps1 -Help
```

## 🔄 **Next Steps**

Once all prerequisites are installed:

1. **Clone the repository:**
   ```bash
   git clone https://github.com/your-org/mcp-server-for-splunk.git
   cd mcp-server-for-splunk
   ```

2. **Run the verification script:**
   - **Windows:** `.\scripts\check-prerequisites.ps1`
   - **macOS/Linux:** `./scripts/check-prerequisites.sh`

3. **Choose your setup method:**
   - **Windows:** `.\scripts\build_and_run.ps1`
   - **macOS/Linux:** `./scripts/build_and_run.sh`

4. **The script will automatically:**
   - Install Python dependencies with UV
   - Create configuration files
   - Start the MCP server
   - Launch MCP Inspector (if Node.js available)
   - Set up Docker stack (if Docker available)

## 📚 **Additional Resources**

- **[Main README](../README.md)** - Project overview and quick start
- **[Docker Guide](../DOCKER.md)** - Container deployment details
- **[Testing Guide](../TESTING.md)** - Testing and validation
- **[Architecture Guide](../ARCHITECTURE.md)** - Technical architecture overview
- **[Contributing Guide](../contrib/README.md)** - How to contribute to the project 