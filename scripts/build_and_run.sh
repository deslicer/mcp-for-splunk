#!/bin/bash

# Build and run MCP Server for Splunk
# This script builds the Docker image and runs it with docker-compose, or falls back to local mode

set -e  # Exit on error

# Change to the project root directory (parent of scripts)
cd "$(dirname "$0")/.."

echo "🚀 Building and Running MCP Server for Splunk"
echo "============================================="
echo
echo "📚 Need help with prerequisites? See: docs/getting-started/installation.md"
echo

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_local() {
    echo -e "${PURPLE}[LOCAL]${NC} $1"
}

# Function to ensure logs directory exists
ensure_logs_dir() {
    if [ ! -d "logs" ]; then
        print_local "Creating logs directory..."
        mkdir -p logs
    fi
}

# Function to load environment variables from .env file
load_env_file() {
    if [ -f .env ]; then
        print_local "Loading environment variables from .env file..."

        # Export variables from .env file, handling comments and empty lines
        while IFS= read -r line || [ -n "$line" ]; do
            # Skip empty lines and comments
            if [[ "$line" =~ ^[[:space:]]*$ ]] || [[ "$line" =~ ^[[:space:]]*# ]]; then
                continue
            fi

            # Check if line contains an assignment
            if [[ "$line" =~ ^[[:space:]]*([A-Za-z_][A-Za-z0-9_]*)=(.*)$ ]]; then
                local var_name="${BASH_REMATCH[1]}"
                local var_value="${BASH_REMATCH[2]}"

                # Remove surrounding quotes if present
                var_value=$(echo "$var_value" | sed -e 's/^"//' -e 's/"$//' -e "s/^'//" -e "s/'$//")

                # Export the variable
                export "$var_name=$var_value"

                # Only show non-sensitive variables
                if [[ "$var_name" == *"PASSWORD"* ]] || [[ "$var_name" == *"SECRET"* ]] || [[ "$var_name" == *"TOKEN"* ]]; then
                    print_local "Loaded: $var_name=***"
                else
                    print_local "Loaded: $var_name=$var_value"
                fi
            fi
        done < .env

        print_success "Environment variables loaded from .env file!"

        # Show summary of important Splunk configuration
        echo
        print_status "📋 Splunk Configuration Summary:"
        echo "   🌐 Host: ${SPLUNK_HOST:-'Not set'}"
        echo "   🔌 Port: ${SPLUNK_PORT:-'8089 (default)'}"
        echo "   👤 User: ${SPLUNK_USERNAME:-'Not set'}"

        # Show last 3 chars of password for verification
        if [ -n "$SPLUNK_PASSWORD" ]; then
            local pass_display="***${SPLUNK_PASSWORD: -3}"
            echo "   🔐 Pass: $pass_display"
        else
            echo "   🔐 Pass: Not set"
        fi

        echo "   🔒 SSL:  ${SPLUNK_VERIFY_SSL:-'Not set'}"

        # Check for alternative MCP_SPLUNK_* variables
        if [ -n "$MCP_SPLUNK_HOST" ] || [ -n "$MCP_SPLUNK_USERNAME" ] || [ -n "$MCP_SPLUNK_PASSWORD" ]; then
            echo
            print_status "📋 Alternative MCP Splunk Configuration Found:"
            echo "   🌐 Host: ${MCP_SPLUNK_HOST:-'Not set'}"
            echo "   👤 User: ${MCP_SPLUNK_USERNAME:-'Not set'}"

            # Show last 3 chars of MCP password for verification
            if [ -n "$MCP_SPLUNK_PASSWORD" ]; then
                local mcp_pass_display="***${MCP_SPLUNK_PASSWORD: -3}"
                echo "   🔐 Pass: $mcp_pass_display"
            else
                echo "   🔐 Pass: Not set"
            fi

            print_local "These MCP_SPLUNK_* variables will override the SPLUNK_* variables in the MCP server."
        fi

        echo
    else
        print_warning "No .env file found. Using system environment variables only."

        # Check if any Splunk environment variables are set in the system
        if [ -n "$SPLUNK_HOST" ] || [ -n "$MCP_SPLUNK_HOST" ]; then
            print_status "📋 System Environment Splunk Configuration:"
            echo "   🌐 Host: ${SPLUNK_HOST:-${MCP_SPLUNK_HOST:-'Not set'}}"
            echo "   👤 User: ${SPLUNK_USERNAME:-${MCP_SPLUNK_USERNAME:-'Not set'}}"

            # Show last 3 chars of password for verification
            local sys_password="${SPLUNK_PASSWORD:-$MCP_SPLUNK_PASSWORD}"
            if [ -n "$sys_password" ]; then
                local sys_pass_display="***${sys_password: -3}"
                echo "   🔐 Pass: $sys_pass_display"
            else
                echo "   🔐 Pass: Not set"
            fi
        else
            print_warning "No Splunk configuration found in environment variables."
            print_warning "The MCP server may not be able to connect to Splunk without configuration."
        fi
    fi
}

# Function to check if uv is installed
check_uv() {
    if command -v uv &> /dev/null; then
        return 0
    else
        return 1
    fi
}

# Function to install uv
install_uv() {
    print_status "Installing uv package manager..."
    if command -v curl &> /dev/null; then
        curl -LsSf https://astral.sh/uv/install.sh | sh
        # Source the shell to get uv in PATH
        export PATH="$HOME/.cargo/bin:$PATH"
    elif command -v wget &> /dev/null; then
        wget -qO- https://astral.sh/uv/install.sh | sh
        export PATH="$HOME/.cargo/bin:$PATH"
    else
        print_error "Neither curl nor wget found. Please install uv manually:"
        print_error "  pip install uv"
        echo
        print_error "📚 For detailed installation instructions, see:"
        print_error "   docs/getting-started/installation.md#-uv-package-manager-installation"
        exit 1
    fi

    # Verify installation
    if check_uv; then
        print_success "uv installed successfully!"
    else
        print_error "Failed to install uv. Please install manually and try again."
        echo
        print_error "📚 For detailed installation instructions, see:"
        print_error "   docs/getting-started/installation.md#-uv-package-manager-installation"
        exit 1
    fi
}

# Function to setup local environment
setup_local_env() {
    print_local "Setting up local development environment..."

    # Check if uv is available
    if ! check_uv; then
        print_warning "uv not found. Installing uv..."
        install_uv
    fi

    # Check if virtual environment and dependencies are installed
    if [ ! -d ".venv" ] || [ ! -f ".venv/pyvenv.cfg" ]; then
        print_local "Creating virtual environment and installing dependencies..."
        uv sync --dev
    else
        print_local "Virtual environment exists. Checking if sync is needed..."
        # Check if uv.lock is newer than .venv
        if [ "uv.lock" -nt ".venv/pyvenv.cfg" ] || [ "pyproject.toml" -nt ".venv/pyvenv.cfg" ]; then
            print_local "Dependencies may be outdated. Running uv sync..."
            uv sync --dev
        else
            print_local "Dependencies are up to date."
        fi
    fi

    # Check if .env file exists
    if [ ! -f .env ]; then
        print_warning ".env file not found. Creating from env.example..."
        cp env.example .env
        print_warning "Created .env file. You may want to edit it with your Splunk configuration."
        print_warning "For local development, you can also use MCP_SPLUNK_* environment variables."
    fi

    # Load environment variables from .env file
    load_env_file

    print_success "Local environment setup complete!"
}

# Function to run local server
run_local_server() {
    print_local "Starting MCP server locally with FastMCP CLI..."
    
    # Define cleanup function early to be available for error handling
    cleanup() {
        print_local "Cleaning up..."
        
        # Kill MCP Inspector if PID file exists
        if [ -f .inspector_pid ]; then
            local pid=$(cat .inspector_pid)
            if kill -0 $pid 2>/dev/null; then
                print_local "Stopping MCP Inspector (PID: $pid)..."
                kill $pid 2>/dev/null
            fi
            rm -f .inspector_pid
        fi
        
        # Clean up any server processes
        pkill -f "fastmcp run" 2>/dev/null || true
        
        # Clean up log files
        rm -f logs/inspector.log logs/mcp_server.log
        
        print_success "Cleanup complete!"
    }

    # Check if Node.js/npm is available for MCP Inspector
    local inspector_available=false
    if command -v npx &> /dev/null; then
        inspector_available=true
        print_local "Node.js/npx detected. Starting MCP Inspector..."

        # Start MCP Inspector in the background
        print_status "Starting MCP Inspector..."

        # Check if inspector is already running
        if (command -v lsof &> /dev/null && lsof -i :6274 &> /dev/null) || (command -v netstat &> /dev/null && netstat -an | grep ":6274 " | grep LISTEN &> /dev/null); then
            print_warning "MCP Inspector appears to already be running on port 6274"
            print_success "Using existing MCP Inspector instance"
            inspector_available=true
        else
            # Try to install and run MCP Inspector with proper configuration
            print_local "Installing/updating MCP Inspector..."
            print_local "This may take a moment on first install..."

            # Set environment variables for the inspector (this is the correct way)
            export DANGEROUSLY_OMIT_AUTH=true
            # Prevent browser from opening automatically when running in background
            export BROWSER=none

            # Ensure logs directory exists
            ensure_logs_dir

            # Check if inspector package needs to be installed
            if ! ls ~/.npm/_npx/*/node_modules/@modelcontextprotocol/inspector 2>/dev/null | grep -q inspector; then
                print_local "MCP Inspector not found in cache. Downloading package..."
            else
                print_local "MCP Inspector found in cache. Starting..."
            fi

            # Start inspector (it will use its default ports: 6274 for UI, 6277 for proxy)
            # Use --yes to automatically install if not present
            npx --yes @modelcontextprotocol/inspector > logs/inspector.log 2>&1 &
            local inspector_pid=$!

            # Give inspector more time to start and check multiple times
            print_local "Waiting for MCP Inspector to start..."
            local attempts=0
            local max_attempts=10
            local inspector_running=false
            local last_log_size=0

            while [ $attempts -lt $max_attempts ]; do
                sleep 2

                # Check if process is still running
                if ! kill -0 $inspector_pid 2>/dev/null; then
                    print_error "MCP Inspector process died. Check inspector.log for details."
                    break
                fi

                # Show progress by monitoring log file
                if [ -f logs/inspector.log ]; then
                    local current_log_size=$(wc -c < logs/inspector.log 2>/dev/null || echo 0)
                    if [ $current_log_size -gt $last_log_size ]; then
                        # New content in log, show last meaningful line
                        local last_line=$(tail -1 logs/inspector.log | grep -v "^$" || true)
                        if [ -n "$last_line" ]; then
                            print_local "Inspector: $last_line"
                        fi
                        last_log_size=$current_log_size
                    fi
                fi

                # Check if the inspector's default port (6274) is listening
                if command -v lsof &> /dev/null; then
                    if lsof -i :6274 &> /dev/null; then
                        inspector_running=true
                        break
                    fi
                elif command -v netstat &> /dev/null; then
                    if netstat -an | grep ":6274 " | grep LISTEN &> /dev/null; then
                        inspector_running=true
                        break
                    fi
                else
                    # If no port checking tools, check the log for success message
                    if [ -f logs/inspector.log ] && grep -q "MCP Inspector is up and running" logs/inspector.log; then
                        inspector_running=true
                        break
                    fi
                    # Also check for the simple case after some attempts
                    if [ $attempts -ge 5 ]; then
                        inspector_running=true
                        break
                    fi
                fi

                attempts=$((attempts + 1))
                print_local "Attempt $attempts/$max_attempts - waiting for inspector..."
            done

            if [ "$inspector_running" = true ]; then
                print_success "MCP Inspector started successfully on port 6274"
                echo $inspector_pid > .inspector_pid  # Save PID for cleanup
            else
                print_warning "Failed to start MCP Inspector"
                print_warning "Checking what went wrong..."

                # Show last few lines of log for debugging
                if [ -f logs/inspector.log ]; then
                    print_warning "Inspector log (last 10 lines):"
                    tail -10 logs/inspector.log
                    echo
                fi

                # Kill the failed process
                if kill -0 $inspector_pid 2>/dev/null; then
                    kill $inspector_pid 2>/dev/null
                fi
                inspector_available=false
            fi
        fi
    else
        print_warning "Node.js/npx not found. MCP Inspector will not be available."
        print_warning "To install Node.js: https://nodejs.org/"
        echo
        print_warning "📚 For detailed installation instructions, see:"
        print_warning "   docs/getting-started/installation.md#-nodejs-installation-optional---for-mcp-inspector"
    fi



    echo
    print_status "Starting MCP server..."

    # Test if the FastMCP command works first
    print_local "Testing FastMCP installation..."
    if ! uv run python -c "import fastmcp; print('FastMCP import successful')"; then
        print_error "FastMCP import failed. Checking installation..."
        print_local "Installing FastMCP..."
        uv add fastmcp
        uv sync --dev
    fi

    # Start the server with uv and better error handling
    print_local "Finding available port for MCP server..."
    # Start from 8001 to avoid conflict with Splunk Web UI (port 8000)
    local mcp_port=$(find_available_port 8001)

    if [ "$mcp_port" -ne 8001 ] 2>/dev/null; then
        print_warning "Port 8001 is in use. Using port $mcp_port instead."
    else
        print_local "Using port $mcp_port for MCP server."
    fi

    print_local "Starting MCP server on port $mcp_port..."
    print_local "Command: uv run fastmcp run src/server.py --transport http --port $mcp_port"

    # Ensure logs directory exists
    ensure_logs_dir

    # Start server in background to check if it starts successfully
    uv run fastmcp run src/server.py --transport http --port $mcp_port > logs/mcp_server.log 2>&1 &
    local server_pid=$!

    # Give server time to start
    print_local "Waiting for MCP server to start..."
    sleep 3

    # Check if the server process is still running
    if ! kill -0 $server_pid 2>/dev/null; then
        print_error "MCP server failed to start. Check the logs:"
        echo
        if [ -f logs/mcp_server.log ]; then
            print_error "=== MCP Server Log ==="
            cat logs/mcp_server.log
            echo
        fi

        print_error "Troubleshooting steps:"
        echo "1. Check if src/server.py exists and is valid"
        echo "2. Verify FastMCP installation: uv run python -c 'import fastmcp'"
        echo "3. Try running manually: uv run fastmcp run src/server.py --help"
        echo "4. Check Python environment: uv run python --version"
        echo
        print_error "📚 For prerequisite installation help, see:"
        print_error "   docs/getting-started/installation.md"
        echo
        print_error "🔧 Run the prerequisite checker to see what's missing:"
        print_error "   ./scripts/check-prerequisites.sh"

        cleanup
        exit 1
    fi

    # Check if the chosen port is actually listening
    print_local "Checking if MCP server is listening on port $mcp_port..."
    local port_check_attempts=0
    local max_port_attempts=5
    local server_listening=false

    while [ $port_check_attempts -lt $max_port_attempts ]; do
        if command -v lsof &> /dev/null; then
            if lsof -i :$mcp_port &> /dev/null; then
                server_listening=true
                break
            fi
        elif command -v netstat &> /dev/null; then
            if netstat -an | grep ":$mcp_port " | grep LISTEN &> /dev/null; then
                server_listening=true
                break
            fi
        elif command -v curl &> /dev/null; then
            # Try to actually connect to the server
            if curl -s -o /dev/null -w "%{http_code}" "http://localhost:$mcp_port" | grep -q "200\|404\|500"; then
                server_listening=true
                break
            fi
        fi

        sleep 2
        port_check_attempts=$((port_check_attempts + 1))
        print_local "Port check attempt $port_check_attempts/$max_port_attempts..."
    done

    if [ "$server_listening" = true ]; then
        print_success "MCP server is listening on port $mcp_port!"

        # Also test basic connectivity
        if command -v curl &> /dev/null; then
            print_local "Testing server connectivity..."
            local response=$(curl -s -o /dev/null -w "%{http_code}" "http://localhost:$mcp_port" 2>/dev/null || echo "failed")
            if [ "$response" != "failed" ]; then
                print_success "Server responds with HTTP $response"
            else
                print_warning "Server running but HTTP request failed"
            fi
        fi
    else
        print_error "MCP server is not listening on port $mcp_port"
        print_error "Server process ID: $server_pid"

        # Show server logs for debugging
        if [ -f logs/mcp_server.log ]; then
            print_error "=== MCP Server Log (last 20 lines) ==="
            tail -20 logs/mcp_server.log
            echo
        fi

        print_error "Attempting to restart server in foreground for debugging..."
        kill $server_pid 2>/dev/null
        sleep 2

        print_local "Running server in foreground mode for debugging..."
        print_local "If this works, there might be a background process issue..."

        # Try running in foreground
        exec uv run fastmcp run src/server.py --transport http --port $mcp_port
    fi

    # Update cleanup function to include server PID
    cleanup() {
        print_local "Shutting down services..."

        # Kill MCP Server if it was started by this script
        if [ -n "$server_pid" ] && kill -0 $server_pid 2>/dev/null; then
            print_local "Stopping MCP Server (PID: $server_pid)..."
            kill $server_pid 2>/dev/null
        fi

        # Kill MCP Inspector if it was started by this script
        if [ -f .inspector_pid ]; then
            local pid=$(cat .inspector_pid)
            if kill -0 $pid 2>/dev/null; then
                print_local "Stopping MCP Inspector (PID: $pid)..."
                kill $pid 2>/dev/null
            fi
            rm -f .inspector_pid
        fi

        # Clean up log files
        rm -f logs/inspector.log logs/inspector_alt.log logs/mcp_server.log

        print_success "Cleanup complete!"
        exit 0
    }

    # Re-set up signal handling for cleanup with updated function
    trap cleanup INT TERM

    # Keep the script running and monitoring
    print_success "✅ MCP Server setup complete!"

    # Show final summary with access points
    echo
    print_status "🎉 Local MCP Server Ready!"
    echo
    print_status "📋 Access Points:"
    echo "   🔌 MCP Server (stdio): Available for MCP clients"
    echo "   🔌 MCP Server (HTTP):  http://localhost:$mcp_port"

    if [ "$inspector_available" = true ]; then
        echo "   📊 MCP Inspector:      http://localhost:6274"
        echo
        print_status "🎯 Testing Instructions:"
        echo "   1. Open http://localhost:6274 in your browser"
        echo "   2. Ensure that Streamable HTTP is set"
        echo "   3. Update URL from default to: http://localhost:$mcp_port/mcp/"
        echo "   4. Click 'Connect' button at the bottom"
        echo "   5. Test tools and resources interactively"
    else
        echo
        print_status "🎯 Alternative Testing:"
        echo "   1. Open https://inspector.mcp.dev/ in your browser"
        echo "   2. Ensure that Streamable HTTP is set"
        echo "   3. Update URL from default to: http://localhost:$mcp_port/mcp/"
        echo "   4. Click 'Connect' button at the bottom"
        echo "   5. Test tools and resources interactively"
        echo
        print_warning "💡 MCP Inspector Troubleshooting:"
        echo "   • Check if Node.js is installed: node --version"
        echo "   • Check inspector logs: cat logs/inspector.log"
        echo "   • Try manual install: npm install -g @modelcontextprotocol/inspector"
        echo "   • Manual start: DANGEROUSLY_OMIT_AUTH=true npx @modelcontextprotocol/inspector"
    fi

    echo
    print_status "📊 Log Files:"
    echo "   📄 MCP Server:    logs/mcp_server.log"
    if [ "$inspector_available" = true ]; then
        echo "   📄 MCP Inspector: logs/inspector.log"
    fi

    echo
    print_status "🛑 To stop the server:"
    echo "   Press Ctrl+C or run: pkill -f 'fastmcp run'"

    echo
    print_local "Server is running in background. Use Ctrl+C to stop."

    # Monitor both processes
    while true; do
        # Check if server is still running
        if ! kill -0 $server_pid 2>/dev/null; then
            print_error "MCP server process died unexpectedly!"
            if [ -f logs/mcp_server.log ]; then
                print_error "=== Recent server logs ==="
                tail -10 logs/mcp_server.log
            fi
            break
        fi

        sleep 5
    done
}

# Function to determine if Splunk should be run in Docker
should_run_splunk_docker() {
    # Check if SPLUNK_HOST is not set or is set to 'so1' (our Docker Splunk container)
    if [ -z "$SPLUNK_HOST" ] || [ "$SPLUNK_HOST" = "so1" ]; then
        return 0  # true - run Splunk in Docker
    else
        return 1  # false - use external Splunk
    fi
}

# Function to get Docker compose command with profiles
get_docker_compose_cmd() {
    local mode=$1
    local base_cmd="docker compose"

    case $mode in
        "dev")
            base_cmd="docker compose -f docker-compose-dev.yml"
            ;;
        "prod"|"")
            base_cmd="docker compose"
            ;;
    esac

    # Add Splunk profile if needed
    if should_run_splunk_docker; then
        if [ "$mode" = "dev" ]; then
            base_cmd="$base_cmd --profile dev --profile splunk"
        else
            base_cmd="$base_cmd --profile splunk"
        fi
    fi

    echo "$base_cmd"
}

# Function to run Docker setup
run_docker_setup() {
    print_status "Using Docker deployment mode..."

    # Check if docker-compose is available
    if ! command -v docker-compose &> /dev/null; then
        print_error "docker-compose not found. Please install docker-compose or use local mode."
        print_error "To install docker-compose: https://docs.docker.com/compose/install/"
        echo
        print_error "📚 For detailed installation instructions, see:"
        print_error "   docs/getting-started/installation.md#-docker-installation-optional---for-full-stack"
        exit 1
    fi

    # If uv is available, ensure uv.lock is up to date for Docker build
    if check_uv; then
        print_status "uv detected. Ensuring uv.lock is up to date for Docker build..."

        # Check if uv.lock exists and is current
        if [ ! -f "uv.lock" ] || [ "pyproject.toml" -nt "uv.lock" ]; then
            print_status "Updating uv.lock file..."
            uv sync --dev
            print_success "uv.lock updated successfully!"
        else
            print_status "uv.lock is already up to date."
        fi
    else
        print_warning "uv not found. Docker will use existing uv.lock file (if present)."
        if [ ! -f "uv.lock" ]; then
            print_warning "No uv.lock file found. Docker build may fail."
            print_warning "Consider installing uv to generate the lock file: curl -LsSf https://astral.sh/uv/install.sh | sh"
        fi
    fi

    # Check if .env file exists
    if [ ! -f .env ]; then
        print_warning ".env file not found. Creating from env.example..."
        cp env.example .env
        print_warning "Created .env file. You may want to edit it with your Splunk configuration."
    fi

    # Load environment variables from .env file for Docker Compose
    load_env_file

    # Ask user for Docker deployment mode
    echo
    print_status "Choose Docker deployment mode:"
    echo "  1) Production (default) - Optimized for performance, no hot reload"
    echo "  2) Development - Hot reload enabled, enhanced debugging"
    echo
    read -p "Enter your choice (1 or 2, default: 1): " docker_choice
    docker_choice=${docker_choice:-1}

    local docker_mode=""
    local service_name="mcp-server"

    case $docker_choice in
        1)
            docker_mode="prod"
            print_status "Using Production mode (optimized performance)"
            ;;
        2)
            docker_mode="dev"
            service_name="mcp-server-dev"
            print_status "Using Development mode (hot reload enabled)"
            ;;
        *)
            print_warning "Invalid choice. Using Production mode (default)."
            docker_mode="prod"
            ;;
    esac

    # Get the appropriate docker-compose command
    local compose_cmd
    compose_cmd=$(get_docker_compose_cmd "$docker_mode")

    # Show Splunk configuration info
    if should_run_splunk_docker; then
        print_local "Including Splunk Enterprise container (SPLUNK_HOST=${SPLUNK_HOST:-'not set'} indicates local Splunk)"
    else
        print_local "Using external Splunk instance: $SPLUNK_HOST"
    fi

    print_status "Building Docker image..."
    eval "$compose_cmd build $service_name"

    if [ $? -eq 0 ]; then
        print_success "Docker image built successfully!"
    else
        print_error "Failed to build Docker image"
        exit 1
    fi

    print_status "Starting services with docker-compose..."
    eval "$compose_cmd up -d"

    if [ $? -eq 0 ]; then
        print_success "Services started successfully!"
    else
        print_error "Failed to start services"
        exit 1
    fi

    # Wait a moment for services to start
    sleep 5

    print_status "Checking service status..."
    eval "$compose_cmd ps"

    print_status "Checking MCP server logs..."
    eval "$compose_cmd logs $service_name --tail=20"

    echo
    print_success "🎉 Docker setup complete!"
    echo
    print_status "📋 Service URLs:"
    echo "   🔧 Traefik Dashboard: http://localhost:8080"
    if should_run_splunk_docker; then
        echo "   🌐 Splunk Web UI:     http://localhost:9000 (admin/Chang3d!)"
    else
        echo "   🌐 External Splunk:   $SPLUNK_HOST (configured in .env)"
    fi
    echo "   🔌 MCP Server:        http://localhost:8001/mcp/"
    echo "   📊 MCP Inspector:     http://localhost:6274"
    echo
    print_status "🔍 To check logs:"
    echo "   $compose_cmd logs -f $service_name"
    echo
    print_status "🛑 To stop all services:"
    echo "   $compose_cmd down"

    if [ "$docker_mode" = "dev" ]; then
        echo
        print_status "🚀 Development Mode Features:"
        echo "   • Hot reload enabled - changes sync automatically"
        echo "   • Enhanced debugging and logging"
        echo "   • Use: $compose_cmd logs -f $service_name"
    fi
}

# Function to find an available port
find_available_port() {
    local start_port=$1
    local max_attempts=10
    local port=$start_port

    for ((i=0; i<max_attempts; i++)); do
        local port_available=true
        
        # Check if any process is actively listening on the port
        if command -v lsof &> /dev/null; then
            # Only check for LISTEN state, ignore CLOSED connections
            if lsof -i :$port 2>/dev/null | grep -q "LISTEN"; then
                port_available=false
            fi
        elif command -v netstat &> /dev/null; then
            # netstat is more reliable - only shows LISTEN state
            if netstat -an | grep ":$port " | grep -q "LISTEN"; then
                port_available=false
            fi
        fi
        
        # If port seems available, try a more direct test
        if [ "$port_available" = true ]; then
            # Try to bind to the port using Python (most reliable cross-platform)
            if command -v python3 &> /dev/null; then
                if python3 -c "import socket; s=socket.socket(); s.bind(('127.0.0.1', $port)); s.close()" 2>/dev/null; then
                    echo $port
                    return 0
                else
                    port_available=false
                fi
            elif command -v nc &> /dev/null; then
                # Fallback to nc if Python not available
                # Try to connect first - if we can't connect, port is likely free
                if ! nc -z -w 1 localhost $port 2>/dev/null; then
                    echo $port
                    return 0
                else
                    port_available=false
                fi
            else
                # Last resort: try /dev/tcp
                if ! (echo >/dev/tcp/localhost/$port) 2>/dev/null; then
                    echo $port
                    return 0
                else
                    port_available=false
                fi
            fi
        fi
        
        if [ "$port_available" = false ]; then
            print_local "Port $port is in use, trying next port..." >&2
        fi
        
        port=$((port + 1))
    done

    # If we can't find a port, return the original
    print_warning "Could not find an available port after $max_attempts attempts" >&2
    echo $start_port
    return 1
}

# Main logic: Check Docker availability and choose deployment method
print_status "Checking available deployment options..."

# Check if Docker is running
if docker info > /dev/null 2>&1; then
    print_success "Docker is available and running."

    # Ask user preference if both Docker and uv are available
    if check_uv; then
        echo
        print_status "Both Docker and local development options are available."
        echo "Choose deployment method:"
        echo "  1) Docker (full stack with Splunk, Traefik, MCP Inspector)"
        echo "  2) Local (FastMCP server only, lighter weight)"
        echo
        read -p "Enter your choice (1 or 2, default: 1): " choice
        choice=${choice:-1}

        case $choice in
            1)
                run_docker_setup
                ;;
            2)
                setup_local_env
                run_local_server
                ;;
            *)
                print_warning "Invalid choice. Using Docker deployment (default)."
                run_docker_setup
                ;;
        esac
    else
        # Docker available but no uv, use Docker
        run_docker_setup
    fi

elif check_uv; then
    # Docker not available but uv is available, use local mode
    print_warning "Docker is not available. Setting up local development mode..."
    setup_local_env
    run_local_server

else
    # Neither Docker nor uv available
    print_error "Neither Docker nor uv package manager are available."
    print_error "Please install one of the following:"
    print_error "1. Docker: https://docs.docker.com/get-docker/"
    print_error "2. uv: curl -LsSf https://astral.sh/uv/install.sh | sh"
    echo
    print_error "📚 For detailed installation instructions, see:"
    print_error "   docs/getting-started/installation.md"
    print_error ""
    print_error "🔧 You can also run our prerequisite checker to see what's missing:"
    print_error "   ./scripts/check-prerequisites.sh"
    exit 1
fi