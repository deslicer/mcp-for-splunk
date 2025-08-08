# Build and Run MCP Server for Splunk - Windows PowerShell Version
# This script builds the Docker image and runs it with docker-compose, or falls back to local mode

param(
    [switch]$LocalOnly,
    [switch]$DockerOnly,
    [switch]$Help
)

# Set strict mode for better error handling
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

# Change to the project root directory (parent of scripts)
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$projectRoot = Split-Path -Parent $scriptDir
Set-Location $projectRoot

# Show help if requested
if ($Help) {
    Write-Host @"
MCP Server for Splunk - Build and Run Script (Windows)

Usage:
    .\scripts\build_and_run.ps1 [options]

Options:
    -LocalOnly      Force local development mode (bypass Docker)
    -DockerOnly     Force Docker mode (fail if Docker unavailable)
    -Help           Show this help message

Examples:
    .\scripts\build_and_run.ps1                    # Auto-detect best mode
    .\scripts\build_and_run.ps1 -LocalOnly         # Use local development mode
    .\scripts\build_and_run.ps1 -DockerOnly        # Use Docker mode only

Prerequisites:
    - Python 3.10+ (for local mode)
    - uv package manager (auto-installed if missing)
    - Docker Desktop (for Docker mode)
    - Node.js/npm (optional, for MCP Inspector)

Configuration:
    - Edit .env file with your Splunk credentials
    - Or set MCP_SPLUNK_* environment variables
"@
    exit 0
}

Write-Host "🚀 Building and Running MCP Server for Splunk (Windows)" -ForegroundColor Cyan
Write-Host "=============================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "📚 Need help with prerequisites? See: docs/getting-started/installation.md" -ForegroundColor Yellow
Write-Host ""

# Color functions for consistent output
function Write-Status {
    param([string]$Message)
    Write-Host "[INFO] $Message" -ForegroundColor Blue
}

function Write-Success {
    param([string]$Message)
    Write-Host "[SUCCESS] $Message" -ForegroundColor Green
}

function Write-Warning {
    param([string]$Message)
    Write-Host "[WARNING] $Message" -ForegroundColor Yellow
}

function Write-Error {
    param([string]$Message)
    Write-Host "[ERROR] $Message" -ForegroundColor Red
}

function Write-Local {
    param([string]$Message)
    Write-Host "[LOCAL] $Message" -ForegroundColor Magenta
}

# Function to ensure logs directory exists
function Ensure-LogsDir {
    if (-not (Test-Path "logs")) {
        Write-Local "Creating logs directory..."
        New-Item -ItemType Directory -Path "logs" -Force | Out-Null
    }
}

# Function to load environment variables from .env file
function Load-EnvFile {
    if (Test-Path ".env") {
        Write-Local "Loading environment variables from .env file..."
        
        $envVars = @{}
        $sensitiveVars = @("PASSWORD", "SECRET", "TOKEN")
        
        Get-Content ".env" | ForEach-Object {
            $line = $_.Trim()
            
            # Skip empty lines and comments
            if ($line -eq "" -or $line.StartsWith("#")) {
                return
            }
            
            # Parse variable assignment
            if ($line -match "^([A-Za-z_][A-Za-z0-9_]*)=(.*)$") {
                $varName = $matches[1]
                $varValue = $matches[2]
                
                # Remove surrounding quotes if present
                $varValue = $varValue -replace '^"(.*)"$', '$1' -replace "^'(.*)'$", '$1'
                
                # Set environment variable
                [Environment]::SetEnvironmentVariable($varName, $varValue, "Process")
                $envVars[$varName] = $varValue
                
                # Only show non-sensitive variables
                $isSensitive = $sensitiveVars | Where-Object { $varName -like "*$_*" }
                if ($isSensitive) {
                    Write-Local "Loaded: $varName=***"
                } else {
                    Write-Local "Loaded: $varName=$varValue"
                }
            }
        }
        
        Write-Success "Environment variables loaded from .env file!"
        
        # Show summary of important Splunk configuration
        Write-Host ""
        Write-Status "📋 Splunk Configuration Summary:"
        Write-Host "   🌐 Host: $($env:SPLUNK_HOST ?? 'Not set')"
        Write-Host "   🔌 Port: $($env:SPLUNK_PORT ?? '8089 (default)')"
        Write-Host "   👤 User: $($env:SPLUNK_USERNAME ?? 'Not set')"
        
        # Show last 3 chars of password for verification
        if ($env:SPLUNK_PASSWORD) {
            $passDisplay = "***" + $env:SPLUNK_PASSWORD.Substring([Math]::Max(0, $env:SPLUNK_PASSWORD.Length - 3))
            Write-Host "   🔐 Pass: $passDisplay"
        } else {
            Write-Host "   🔐 Pass: Not set"
        }
        
        Write-Host "   🔒 SSL:  $($env:SPLUNK_VERIFY_SSL ?? 'Not set')"
        
        # Check for alternative MCP_SPLUNK_* variables
        if ($env:MCP_SPLUNK_HOST -or $env:MCP_SPLUNK_USERNAME -or $env:MCP_SPLUNK_PASSWORD) {
            Write-Host ""
            Write-Status "📋 Alternative MCP Splunk Configuration Found:"
            Write-Host "   🌐 Host: $($env:MCP_SPLUNK_HOST ?? 'Not set')"
            Write-Host "   👤 User: $($env:MCP_SPLUNK_USERNAME ?? 'Not set')"
            
            # Show last 3 chars of MCP password for verification
            if ($env:MCP_SPLUNK_PASSWORD) {
                $mcpPassDisplay = "***" + $env:MCP_SPLUNK_PASSWORD.Substring([Math]::Max(0, $env:MCP_SPLUNK_PASSWORD.Length - 3))
                Write-Host "   🔐 Pass: $mcpPassDisplay"
            } else {
                Write-Host "   🔐 Pass: Not set"
            }
            
            Write-Local "These MCP_SPLUNK_* variables will override the SPLUNK_* variables in the MCP server."
        }
        
        Write-Host ""
    } else {
        Write-Warning "No .env file found. Using system environment variables only."
        
        # Check if any Splunk environment variables are set in the system
        if ($env:SPLUNK_HOST -or $env:MCP_SPLUNK_HOST) {
            Write-Status "📋 System Environment Splunk Configuration:"
            Write-Host "   🌐 Host: $($env:SPLUNK_HOST ?? $env:MCP_SPLUNK_HOST ?? 'Not set')"
            Write-Host "   👤 User: $($env:SPLUNK_USERNAME ?? $env:MCP_SPLUNK_USERNAME ?? 'Not set')"
            
            # Show last 3 chars of password for verification
            $sysPassword = $env:SPLUNK_PASSWORD ?? $env:MCP_SPLUNK_PASSWORD
            if ($sysPassword) {
                $sysPassDisplay = "***" + $sysPassword.Substring([Math]::Max(0, $sysPassword.Length - 3))
                Write-Host "   🔐 Pass: $sysPassDisplay"
            } else {
                Write-Host "   🔐 Pass: Not set"
            }
        } else {
            Write-Warning "No Splunk configuration found in environment variables."
            Write-Warning "The MCP server may not be able to connect to Splunk without configuration."
        }
    }
}

# Function to check if uv is installed
function Test-UV {
    try {
        $null = Get-Command "uv" -ErrorAction Stop
        return $true
    } catch {
        return $false
    }
}

# Function to install uv
function Install-UV {
    Write-Status "Installing uv package manager..."
    
    try {
        # Use the official uv installation method for Windows
        if (Get-Command "curl" -ErrorAction SilentlyContinue) {
            $installer = Invoke-WebRequest -Uri "https://astral.sh/uv/install.ps1" -UseBasicParsing
            Invoke-Expression $installer.Content
        } elseif (Get-Command "winget" -ErrorAction SilentlyContinue) {
            Write-Status "Using winget to install uv..."
            winget install --id=astral-sh.uv --source=winget
        } else {
            Write-Status "Using pip to install uv..."
            python -m pip install uv
        }
        
        # Refresh PATH to ensure uv is available
        $env:PATH = [System.Environment]::GetEnvironmentVariable("PATH", "Machine") + ";" + [System.Environment]::GetEnvironmentVariable("PATH", "User")
        
        # Verify installation
        if (Test-UV) {
            Write-Success "uv installed successfully!"
        } else {
            throw "uv installation verification failed"
        }
    } catch {
        Write-Error "Failed to install uv. Please install manually:"
        Write-Error "  Option 1: pip install uv"
        Write-Error "  Option 2: Download from https://astral.sh/uv/"
        Write-Error "  Option 3: winget install astral-sh.uv"
        Write-Host ""
        Write-Error "📚 For detailed installation instructions, see:"
        Write-Error "   docs/getting-started/installation.md#-uv-package-manager-installation"
        exit 1
    }
}

# Function to setup local environment
function Setup-LocalEnv {
    Write-Local "Setting up local development environment..."
    
    # Check if uv is available
    if (-not (Test-UV)) {
        Write-Warning "uv not found. Installing uv..."
        Install-UV
    }
    
    # Check if virtual environment and dependencies are installed
    if (-not (Test-Path ".venv") -or -not (Test-Path ".venv/pyvenv.cfg")) {
        Write-Local "Creating virtual environment and installing dependencies..."
        & uv sync --dev
        if ($LASTEXITCODE -ne 0) {
            Write-Error "Failed to create virtual environment and install dependencies"
            exit 1
        }
    } else {
        Write-Local "Virtual environment exists. Checking if sync is needed..."
        
        # Check if uv.lock is newer than .venv (Windows compatible)
        $uvLockTime = (Get-Item "uv.lock" -ErrorAction SilentlyContinue)?.LastWriteTime
        $pyprojectTime = (Get-Item "pyproject.toml" -ErrorAction SilentlyContinue)?.LastWriteTime
        $venvTime = (Get-Item ".venv/pyvenv.cfg" -ErrorAction SilentlyContinue)?.LastWriteTime
        
        if (($uvLockTime -and $venvTime -and $uvLockTime -gt $venvTime) -or 
            ($pyprojectTime -and $venvTime -and $pyprojectTime -gt $venvTime)) {
            Write-Local "Dependencies may be outdated. Running uv sync..."
            & uv sync --dev
            if ($LASTEXITCODE -ne 0) {
                Write-Error "Failed to sync dependencies"
                exit 1
            }
        } else {
            Write-Local "Dependencies are up to date."
        }
    }
    
    # Check if .env file exists
    if (-not (Test-Path ".env")) {
        Write-Warning ".env file not found. Creating from env.example..."
        Copy-Item "env.example" ".env"
        Write-Warning "Created .env file. You may want to edit it with your Splunk configuration."
        Write-Warning "For local development, you can also use MCP_SPLUNK_* environment variables."
    }
    
    # Load environment variables from .env file
    Load-EnvFile
    
    Write-Success "Local environment setup complete!"
}

# Function to find an available port
function Find-AvailablePort {
    param([int]$StartPort = 8001)
    
    $maxAttempts = 10
    $port = $StartPort
    
    for ($i = 0; $i -lt $maxAttempts; $i++) {
        $portAvailable = $true
        
        # First check if anything is listening on the port
        try {
            $tcpConnections = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue
            if ($tcpConnections) {
                $portAvailable = $false
            }
        } catch {
            # If Get-NetTCPConnection isn't available, try TcpListener
            try {
                $listener = [System.Net.Sockets.TcpListener]::new([System.Net.IPAddress]::Any, $port)
                $listener.Start()
                $listener.Stop()
                # If we got here, port is available
                return $port
            } catch {
                $portAvailable = $false
            }
        }
        
        if ($portAvailable) {
            # Double-check by trying to bind
            try {
                $listener = [System.Net.Sockets.TcpListener]::new([System.Net.IPAddress]::Any, $port)
                $listener.Start()
                $listener.Stop()
                return $port
            } catch {
                $portAvailable = $false
            }
        }
        
        if (-not $portAvailable) {
            Write-Local "Port $port is in use, trying next port..."
        }
        
        $port++
    }
    
    # If we can't find a port, return the original
    Write-Warning "Could not find an available port after $maxAttempts attempts"
    return $StartPort
}

# Function to test if a port is listening
function Test-PortListening {
    param([int]$Port)
    
    try {
        $tcpClient = New-Object System.Net.Sockets.TcpClient
        $tcpClient.ConnectAsync("localhost", $Port).Wait(1000)
        $isListening = $tcpClient.Connected
        $tcpClient.Close()
        return $isListening
    } catch {
        return $false
    }
}

# Function to run local server
function Start-LocalServer {
    Write-Local "Starting MCP server locally with FastMCP CLI..."
    
    # Check if Node.js/npm is available for MCP Inspector
    $inspectorAvailable = $false
    $inspectorSupported = $true
    if (Get-Command "npx" -ErrorAction SilentlyContinue) {
        $inspectorSupported = $true
        Write-Local "Node.js/npx detected. MCP Inspector will start after MCP server is running..."
    } else {
        Write-Warning "Node.js/npx not found. MCP Inspector will not be available."
        Write-Warning "To install Node.js: https://nodejs.org/"
        Write-Host ""
        Write-Warning "📚 For detailed installation instructions, see:"
        Write-Warning "   docs/getting-started/installation.md#-nodejs-installation-optional---for-mcp-inspector"
    }
    
    Write-Host ""
    Write-Status "Starting MCP server..."
    
    # Test if the FastMCP command works first
    Write-Local "Testing FastMCP installation..."
    try {
        & uv run python -c "import fastmcp; print('FastMCP import successful')"
        if ($LASTEXITCODE -ne 0) {
            throw "FastMCP import failed"
        }
    } catch {
        Write-Error "FastMCP import failed. Checking installation..."
        Write-Local "Installing FastMCP..."
        & uv add fastmcp
        & uv sync --dev
        if ($LASTEXITCODE -ne 0) {
            Write-Error "Failed to install FastMCP"
            exit 1
        }
    }
    
    # Start the server with uv and better error handling
    Write-Local "Finding available port for MCP server..."
    # Start from 8001 to avoid conflict with Splunk Web UI (port 8000)
    $mcpPort = Find-AvailablePort -StartPort 8001
    
    if ($mcpPort -ne 8001) {
        Write-Warning "Port 8001 is in use. Using port $mcpPort instead."
    } else {
        Write-Local "Using port $mcpPort for MCP server."
    }
    
    Write-Local "Starting MCP server on port $mcpPort..."
    Write-Local "Command: uv run fastmcp run src/server.py --transport http --port $mcpPort"
    
    # Ensure logs directory exists
    Ensure-LogsDir
    
    # Start server in background to check if it starts successfully
    try {
        $serverProcess = Start-Process -FilePath "uv" -ArgumentList "run", "fastmcp", "run", "src/server.py", "--transport", "http", "--port", $mcpPort -RedirectStandardOutput "logs/mcp_server.log" -RedirectStandardError "logs/mcp_server_error.log" -PassThru -NoNewWindow
        
        # Give server time to start
        Write-Local "Waiting for MCP server to start..."
        Start-Sleep -Seconds 3
        
        # Check if the server process is still running
        if ($serverProcess.HasExited) {
            Write-Error "MCP server failed to start. Check the logs:"
            Write-Host ""
            if (Test-Path "logs/mcp_server.log") {
                Write-Error "=== MCP Server Log ==="
                Get-Content "logs/mcp_server.log" | Write-Host
                Write-Host ""
            }
            if (Test-Path "logs/mcp_server_error.log") {
                Write-Error "=== MCP Server Error Log ==="
                Get-Content "logs/mcp_server_error.log" | Write-Host
                Write-Host ""
            }
            
            Write-Error "Troubleshooting steps:"
            Write-Host "1. Check if src/server.py exists and is valid"
            Write-Host "2. Verify FastMCP installation: uv run python -c 'import fastmcp'"
            Write-Host "3. Try running manually: uv run fastmcp run src/server.py --help"
            Write-Host "4. Check Python environment: uv run python --version"
            Write-Host ""
            Write-Error "📚 For prerequisite installation help, see:"
            Write-Error "   docs/getting-started/installation.md"
            Write-Host ""
            Write-Error "🔧 Run the prerequisite checker to see what's missing:"
            Write-Error "   .\scripts\check-prerequisites.ps1"
            
            Stop-AllProcesses
            exit 1
        }
        
        # Check if the chosen port is actually listening
        Write-Local "Checking if MCP server is listening on port $mcpPort..."
        $portCheckAttempts = 0
        $maxPortAttempts = 5
        $serverListening = $false
        
        while ($portCheckAttempts -lt $maxPortAttempts) {
            if (Test-PortListening -Port $mcpPort) {
                $serverListening = $true
                break
            }
            
            Start-Sleep -Seconds 2
            $portCheckAttempts++
            Write-Local "Port check attempt $portCheckAttempts/$maxPortAttempts..."
        }
        
        if ($serverListening) {
            Write-Success "MCP server is listening on port $mcpPort!"
            
            # Also test basic connectivity
            try {
                $response = Invoke-WebRequest -Uri "http://localhost:$mcpPort" -TimeoutSec 5 -UseBasicParsing
                Write-Success "Server responds with HTTP $($response.StatusCode)"
            } catch {
                Write-Warning "Server running but HTTP request failed: $_"
            }
            
            # Start MCP Inspector now that the actual port is known
            if ($inspectorSupported) {
                Write-Status "Starting MCP Inspector..."
                if (Test-PortListening -Port 6274) {
                    Write-Warning "MCP Inspector appears to already be running on port 6274"
                    Write-Success "Using existing MCP Inspector instance"
                    $inspectorAvailable = $true
                } else {
                    # Configure environment for inspector (env vars, not CLI flags)
                    $env:DANGEROUSLY_OMIT_AUTH = "true"
                    $env:MCP_AUTO_OPEN_ENABLED = "false"
                    $env:DEFAULT_TRANSPORT = "streamable-http"
                    $env:DEFAULT_SERVER_URL = "http://localhost:$mcpPort/mcp"

                    Ensure-LogsDir

                    try {
                        $inspectorProcess = Start-Process -FilePath "npx" -ArgumentList "--yes", "@modelcontextprotocol/inspector" -RedirectStandardOutput "logs/inspector.log" -RedirectStandardError "logs/inspector_error.log" -PassThru -NoNewWindow
                        Write-Local "Waiting for MCP Inspector to start..."
                        $attempts = 0
                        $maxAttempts = 10
                        $inspectorRunning = $false
                        while ($attempts -lt $maxAttempts) {
                            Start-Sleep -Seconds 2
                            if ($inspectorProcess.HasExited) {
                                Write-Error "MCP Inspector process died. Check logs/inspector.log for details."
                                break
                            }
                            if (Test-PortListening -Port 6274) {
                                $inspectorRunning = $true
                                break
                            }
                            $attempts++
                            Write-Local "Attempt $attempts/$maxAttempts - waiting for inspector..."
                        }
                        if ($inspectorRunning) {
                            Write-Success "MCP Inspector started successfully on port 6274"
                            $inspectorProcess.Id | Out-File ".inspector_pid" -Encoding ASCII
                            $inspectorAvailable = $true
                        } else {
                            Write-Warning "Failed to start MCP Inspector"
                            if (Test-Path "logs/inspector.log") {
                                Write-Warning "Inspector log (last 10 lines):"
                                Get-Content "logs/inspector.log" -Tail 10 | Write-Host
                            }
                            if (-not $inspectorProcess.HasExited) { $inspectorProcess.Kill() }
                            $inspectorAvailable = $false
                        }
                    } catch {
                        Write-Warning "Failed to start MCP Inspector: $_"
                        $inspectorAvailable = $false
                    }
                }
            }
        } else {
            Write-Error "MCP server is not listening on port $mcpPort"
            Write-Error "Server process ID: $($serverProcess.Id)"
            
            # Show server logs for debugging
            if (Test-Path "logs/mcp_server.log") {
                Write-Error "=== MCP Server Log (last 20 lines) ==="
                Get-Content "logs/mcp_server.log" -Tail 20 | Write-Host
                Write-Host ""
            }
            
            Write-Error "Attempting to restart server in foreground for debugging..."
            $serverProcess.Kill()
            Start-Sleep -Seconds 2
            
            Write-Local "Running server in foreground mode for debugging..."
            Write-Local "If this works, there might be a background process issue..."
            
            # Try running in foreground (this will block)
            & uv run fastmcp run src/server.py --transport http --port $mcpPort
            exit 1
        }
        
        # Save server PID for cleanup
        $serverProcess.Id | Out-File ".server_pid" -Encoding ASCII
        
        # Show final summary with access points
        Write-Host ""
        Write-Success "✅ MCP Server setup complete!"
        Write-Host ""
        Write-Status "🎉 Local MCP Server Ready!"
        Write-Host ""
        Write-Status "📋 Access Points:"
        Write-Host "   🔌 MCP Server (stdio): Available for MCP clients"
        Write-Host "   🔌 MCP Server (HTTP):  http://localhost:$mcpPort"
        
        if ($inspectorSupported) {
            Write-Host "   📊 MCP Inspector:      http://localhost:6274"
            Write-Host ""
            Write-Status "🎯 Testing Instructions:"
            Write-Host "   1. Open http://localhost:6274 in your browser"
            Write-Host "   2. Ensure that Streamable HTTP is set"
            Write-Host "   3. Update URL from default to: http://localhost:$mcpPort/mcp/"
            Write-Host "   4. Click 'Connect' button at the bottom"
            Write-Host "   5. Test tools and resources interactively"
        } else {
            Write-Host ""
            Write-Status "🎯 Alternative Testing:"
            Write-Host "   1. Open https://inspector.mcp.dev/ in your browser"
            Write-Host "   2. Ensure that Streamable HTTP is set"
            Write-Host "   3. Update URL from default to: http://localhost:$mcpPort/mcp/"
            Write-Host "   4. Click 'Connect' button at the bottom"
            Write-Host "   5. Test tools and resources interactively"
            Write-Host ""
            Write-Warning "💡 MCP Inspector Troubleshooting:"
            Write-Host "   • Check if Node.js is installed: node --version"
            Write-Host "   • Check inspector logs: Get-Content logs/inspector.log"
            Write-Host "   • Try manual install: npm install -g @modelcontextprotocol/inspector"
            Write-Host "   • Manual start: `$env:DANGEROUSLY_OMIT_AUTH='true'; `$env:DEFAULT_TRANSPORT='streamable-http'; `$env:DEFAULT_SERVER_URL='http://localhost:$mcpPort/mcp'; npx @modelcontextprotocol/inspector"
        }
        
        Write-Host ""
        Write-Status "📊 Log Files:"
        Write-Host "   📄 MCP Server:    logs/mcp_server.log"
        if ($inspectorSupported) {
            Write-Host "   📄 MCP Inspector: logs/inspector.log"
        }
        
        Write-Host ""
        Write-Status "🛑 To stop the server:"
        Write-Host "   Press Ctrl+C or run Stop-Process -Name 'uv'"
        
        Write-Host ""
        Write-Local "Server is running in background. Use Ctrl+C to stop."
        
        # Monitor both processes
        try {
            while ($true) {
                # Check if server is still running
                if ($serverProcess.HasExited) {
                    Write-Error "MCP server process died unexpectedly!"
                    if (Test-Path "logs/mcp_server.log") {
                        Write-Error "=== Recent server logs ==="
                        Get-Content "logs/mcp_server.log" -Tail 10 | Write-Host
                    }
                    break
                }
                
                Start-Sleep -Seconds 5
            }
        } finally {
            Stop-AllProcesses
        }
    } catch {
        Write-Error "Failed to start MCP server: $_"
        Stop-AllProcesses
        exit 1
    }
}

# Function to determine if Splunk should be run in Docker
function Test-ShouldRunSplunkDocker {
    # Check if SPLUNK_HOST is not set or is set to 'so1' (our Docker Splunk container)
    if (-not $env:SPLUNK_HOST -or $env:SPLUNK_HOST -eq "so1") {
        return $true  # run Splunk in Docker
    } else {
        return $false  # use external Splunk
    }
}

# Function to get Docker compose command with profiles
function Get-DockerComposeCmd {
    param([string]$Mode)
    
    $baseCmd = "docker-compose"
    
    switch ($Mode) {
        "dev" {
            $baseCmd = "docker-compose -f docker-compose-dev.yml"
        }
        default {
            $baseCmd = "docker-compose"
        }
    }
    
    # Add Splunk profile if needed
    if (Test-ShouldRunSplunkDocker) {
        if ($Mode -eq "dev") {
            $baseCmd = "$baseCmd --profile dev --profile splunk"
        } else {
            $baseCmd = "$baseCmd --profile splunk"
        }
        Write-Local "Including Splunk Enterprise container (SPLUNK_HOST=$($env:SPLUNK_HOST ?? 'not set') indicates local Splunk)"
    } else {
        Write-Local "Using external Splunk instance: $env:SPLUNK_HOST"
    }
    
    return $baseCmd
}

# Function to run Docker setup
function Start-DockerSetup {
    Write-Status "Using Docker deployment mode..."
    
    # Check if docker-compose is available
    if (-not (Get-Command "docker-compose" -ErrorAction SilentlyContinue)) {
        Write-Error "docker-compose not found. Please install docker-compose or use local mode."
        Write-Error "To install docker-compose: https://docs.docker.com/compose/install/"
        Write-Host ""
        Write-Error "📚 For detailed installation instructions, see:"
        Write-Error "   docs/getting-started/installation.md#-docker-installation-optional---for-full-stack"
        exit 1
    }
    
    # If uv is available, ensure uv.lock is up to date for Docker build
    if (Test-UV) {
        Write-Status "uv detected. Ensuring uv.lock is up to date for Docker build..."
        
        # Check if uv.lock exists and is current
        $uvLockTime = (Get-Item "uv.lock" -ErrorAction SilentlyContinue)?.LastWriteTime
        $pyprojectTime = (Get-Item "pyproject.toml" -ErrorAction SilentlyContinue)?.LastWriteTime
        
        if (-not (Test-Path "uv.lock") -or ($pyprojectTime -and $uvLockTime -and $pyprojectTime -gt $uvLockTime)) {
            Write-Status "Updating uv.lock file..."
            & uv sync --dev
            if ($LASTEXITCODE -eq 0) {
                Write-Success "uv.lock updated successfully!"
            } else {
                Write-Error "Failed to update uv.lock file"
                exit 1
            }
        } else {
            Write-Status "uv.lock is already up to date."
        }
    } else {
        Write-Warning "uv not found. Docker will use existing uv.lock file (if present)."
        if (-not (Test-Path "uv.lock")) {
            Write-Warning "No uv.lock file found. Docker build may fail."
            Write-Warning "Consider installing uv to generate the lock file: https://astral.sh/uv/"
        }
    }
    
    # Check if .env file exists
    if (-not (Test-Path ".env")) {
        Write-Warning ".env file not found. Creating from env.example..."
        Copy-Item "env.example" ".env"
        Write-Warning "Created .env file. You may want to edit it with your Splunk configuration."
    }
    
    # Load environment variables from .env file for Docker Compose
    Load-EnvFile
    
    # Ask user for Docker deployment mode
    Write-Host ""
    Write-Status "Choose Docker deployment mode:"
    Write-Host "  1) Production (default) - Optimized for performance, no hot reload"
    Write-Host "  2) Development - Hot reload enabled, enhanced debugging"
    Write-Host ""
    
    do {
        $dockerChoice = Read-Host "Enter your choice (1 or 2, default: 1)"
        if ([string]::IsNullOrEmpty($dockerChoice)) { $dockerChoice = "1" }
    } while ($dockerChoice -notin @("1", "2"))
    
    $dockerMode = ""
    $serviceName = "mcp-server"
    
    switch ($dockerChoice) {
        "1" {
            $dockerMode = "prod"
            Write-Status "Using Production mode (optimized performance)"
        }
        "2" {
            $dockerMode = "dev"
            $serviceName = "mcp-server-dev"
            Write-Status "Using Development mode (hot reload enabled)"
        }
    }
    
    # Get the appropriate docker-compose command
    $composeCmd = Get-DockerComposeCmd -Mode $dockerMode
    
    Write-Status "Building Docker image..."
    $buildCmd = "$composeCmd build $serviceName"
    Invoke-Expression $buildCmd
    
    if ($LASTEXITCODE -eq 0) {
        Write-Success "Docker image built successfully!"
    } else {
        Write-Error "Failed to build Docker image"
        exit 1
    }
    
    Write-Status "Starting services with docker-compose..."
    $upCmd = "$composeCmd up -d"
    Invoke-Expression $upCmd
    
    if ($LASTEXITCODE -eq 0) {
        Write-Success "Services started successfully!"
    } else {
        Write-Error "Failed to start services"
        exit 1
    }
    
    # Wait a moment for services to start
    Start-Sleep -Seconds 5
    
    Write-Status "Checking service status..."
    $psCmd = "$composeCmd ps"
    Invoke-Expression $psCmd
    
    Write-Status "Checking MCP server logs..."
    $logsCmd = "$composeCmd logs $serviceName --tail=20"
    Invoke-Expression $logsCmd
    
    Write-Host ""
    Write-Success "🎉 Docker setup complete!"
    Write-Host ""
    Write-Status "📋 Service URLs:"
    Write-Host "   🔧 Traefik Dashboard: http://localhost:8080"
    if (Test-ShouldRunSplunkDocker) {
        Write-Host "   🌐 Splunk Web UI:     http://localhost:9000 (admin/Chang3d!)"
    } else {
        Write-Host "   🌐 External Splunk:   $env:SPLUNK_HOST (configured in .env)"
    }
    Write-Host "   🔌 MCP Server:        http://localhost:8001/mcp/"
    Write-Host "   📊 MCP Inspector:     http://localhost:6274"
    Write-Host ""
    Write-Status "🔍 To check logs:"
    Write-Host "   $composeCmd logs -f $serviceName"
    Write-Host ""
    Write-Status "🛑 To stop all services:"
    Write-Host "   $composeCmd down"
    
    if ($dockerMode -eq "dev") {
        Write-Host ""
        Write-Status "🚀 Development Mode Features:"
        Write-Host "   • Hot reload enabled - changes sync automatically"
        Write-Host "   • Enhanced debugging and logging"
        Write-Host "   • Use: $composeCmd logs -f $serviceName"
    }
}

# Function to check if Docker is running
function Test-Docker {
    try {
        & docker info 2>&1 | Out-Null
        return ($LASTEXITCODE -eq 0)
    } catch {
        return $false
    }
}

# Function to stop all processes
function Stop-AllProcesses {
    Write-Local "Shutting down services..."
    
    # Kill MCP Server if it was started by this script
    if (Test-Path ".server_pid") {
        $serverPid = Get-Content ".server_pid" -ErrorAction SilentlyContinue
        if ($serverPid) {
            try {
                $serverProcess = Get-Process -Id $serverPid -ErrorAction SilentlyContinue
                if ($serverProcess) {
                    Write-Local "Stopping MCP Server (PID: $serverPid)..."
                    Stop-Process -Id $serverPid -Force -ErrorAction SilentlyContinue
                }
            } catch {
                # Process might already be stopped
            }
        }
        Remove-Item ".server_pid" -ErrorAction SilentlyContinue
    }
    
    # Kill MCP Inspector if it was started by this script
    if (Test-Path ".inspector_pid") {
        $inspectorPid = Get-Content ".inspector_pid" -ErrorAction SilentlyContinue
        if ($inspectorPid) {
            try {
                $inspectorProcess = Get-Process -Id $inspectorPid -ErrorAction SilentlyContinue
                if ($inspectorProcess) {
                    Write-Local "Stopping MCP Inspector (PID: $inspectorPid)..."
                    Stop-Process -Id $inspectorPid -Force -ErrorAction SilentlyContinue
                }
            } catch {
                # Process might already be stopped
            }
        }
        Remove-Item ".inspector_pid" -ErrorAction SilentlyContinue
    }
    
    # Clean up log files
    Remove-Item "logs/inspector.log", "logs/inspector_error.log", "logs/mcp_server.log", "logs/mcp_server_error.log" -ErrorAction SilentlyContinue
    
    Write-Success "Cleanup complete!"
}

# Set up signal handling for cleanup
$null = Register-EngineEvent -SourceIdentifier PowerShell.Exiting -Action {
    Stop-AllProcesses
}

# Main logic: Check Docker availability and choose deployment method
try {
    Write-Status "Checking available deployment options..."
    
    # Handle command line parameters
    if ($DockerOnly) {
        if (Test-Docker) {
            Start-DockerSetup
        } else {
            Write-Error "Docker mode requested but Docker is not available"
            exit 1
        }
    } elseif ($LocalOnly) {
        Setup-LocalEnv
        Start-LocalServer
    } else {
        # Auto-detect best mode
        if (Test-Docker) {
            Write-Success "Docker is available and running."
            
            # Ask user preference if both Docker and uv are available
            if (Test-UV) {
                Write-Host ""
                Write-Status "Both Docker and local development options are available."
                Write-Host "Choose deployment method:"
                Write-Host "  1) Docker (full stack with Splunk, Traefik, MCP Inspector)"
                Write-Host "  2) Local (FastMCP server only, lighter weight)"
                Write-Host ""
                
                do {
                    $choice = Read-Host "Enter your choice (1 or 2, default: 1)"
                    if ([string]::IsNullOrEmpty($choice)) { $choice = "1" }
                } while ($choice -notin @("1", "2"))
                
                switch ($choice) {
                    "1" { Start-DockerSetup }
                    "2" { 
                        Setup-LocalEnv
                        Start-LocalServer
                    }
                }
            } else {
                # Docker available but no uv, use Docker
                Start-DockerSetup
            }
        } elseif (Test-UV) {
            # No Docker but uv available, use local
            Write-Warning "Docker is not available. Setting up local development mode..."
            Setup-LocalEnv
            Start-LocalServer
        } else {
            # Neither Docker nor uv available
            Write-Warning "Neither Docker nor uv is available."
            Write-Host ""
            Write-Warning "📚 For detailed installation instructions, see:"
            Write-Warning "   docs/getting-started/installation.md"
            Write-Host ""
            Write-Warning "🔧 You can also run our prerequisite checker to see what's missing:"
            Write-Warning "   .\scripts\check-prerequisites.ps1"
            Write-Host ""
            Write-Status "Attempting to install uv automatically..."
            Install-UV
            Setup-LocalEnv
            Start-LocalServer
        }
    }
} catch {
    Write-Error "An error occurred: $_"
    Stop-AllProcesses
    exit 1
} 