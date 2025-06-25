# #!/bin/bash
# set -e
# # Determine the directory of the script
# SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# cd "$SCRIPT_DIR"/..
# echo "🛑 Stopping any running Docker containers"
# docker compose down

# # Check if running on ARM macOS
# if [[ "$(uname -m)" == "arm64" ]]; then
#     echo "🔧 Detected ARM64 architecture, setting Docker platform"
#     export DOCKER_DEFAULT_PLATFORM=linux/amd64
# fi

# echo "🐳 Starting Docker containers"
# docker compose up -d --build --wait

# echo "🚀 Done! It is now running at http://localhost:9000"

#!/bin/bash
set -e

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Determine the directory of the script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$SCRIPT_DIR/.."

# Function to log messages with emoji and color
log() {
    local emoji=$1
    local color=$2
    local message=$3
    echo -e "${color}${emoji} ${message}${NC}"
}

# Function to check if a command exists
check_command() {
    if ! command -v "$1" &> /dev/null; then
        log "❌" "$RED" "Error: $1 is not installed"
        exit 1
    fi
}

# Function to check required dependencies
check_dependencies() {
    log "🔍" "$BLUE" "Checking dependencies..."
    # check_command "python3"
    # check_command "pip"
    check_command "docker"
    check_command "docker-compose"
}

# Function to clean up on script exit
cleanup() {
    if [ $? -ne 0 ]; then
        log "❌" "$RED" "Script failed! Check the error messages above"
        # Optionally stop containers on failure
        if [ "$STOP_ON_FAILURE" = true ]; then
            log "🛑" "$YELLOW" "Stopping Docker containers..."
            docker compose -f docker-compose-splunk.yml down
        fi
    fi
}

# Set up trap for cleanup
trap cleanup EXIT

# Function to wait for Splunk to be ready
wait_for_splunk() {
    local max_attempts=30
    local attempt=1
    local splunk_url="http://localhost:9000"

    log "⏳" "$BLUE" "Waiting for Splunk to be ready..."
    while [ $attempt -le $max_attempts ]; do
        if curl -s -k "$splunk_url" > /dev/null; then
            log "✅" "$GREEN" "Splunk is ready!"
            return 0
        fi
        log "⏳" "$YELLOW" "Attempt $attempt/$max_attempts - Waiting for Splunk to start..."
        sleep 5
        ((attempt++))
    done

    log "❌" "$RED" "Splunk failed to start within the expected time"
    return 1
}

# Function to handle arguments
handle_args() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            --rebuild)
                REBUILD_DOCKER=true
                shift
                ;;
            *)
                log "❌" "$RED" "Unknown option: $1"
                exit 1
                ;;
        esac
    done
}

# Main execution starts here
main() {
    cd "$PROJECT_ROOT"

    # Handle command line arguments
    handle_args "$@"

    # Check dependencies
    check_dependencies

    # Stop any running containers
    log "🛑" "$BLUE" "Stopping any running Docker containers"
    docker compose -f docker-compose-splunk.yml down

    # # Set up Python environment
    # log "🐍" "$BLUE" "Setting up Python environment"
    # if [ ! -d ".venv" ]; then
    #     python3 -m venv .venv
    # fi
    # source .venv/bin/activate

    # # Install dependencies
    # log "📦" "$BLUE" "Installing Python dependencies"
    # pip install -r requirements.txt

    # # Build the project
    # log "🏗" "$BLUE" "Building the project with ucc-gen"
    # ucc-gen build

    # Check for ARM architecture
    if [[ "$(uname -m)" == "arm64" ]]; then
        log "🔧" "$YELLOW" "Detected ARM64 architecture, setting Docker platform"
        export DOCKER_DEFAULT_PLATFORM=linux/amd64
    fi

    # Start Docker containers
    log "🐳" "$BLUE" "Starting Docker containers"
    if [ "$REBUILD_DOCKER" = true ]; then
        log "🔄" "$BLUE" "Rebuilding Docker image"
        docker compose -f docker-compose-splunk.yml up -d --build
    else
        log "⏭️" "$BLUE" "Using existing Docker image"
        docker compose -f docker-compose-splunk.yml up -d
    fi

    # Wait for Splunk to be ready
    wait_for_splunk

    # Print success message
    log "🚀" "$GREEN" "Development environment is ready!"
    log "🌐" "$GREEN" "Splunk is running at http://localhost:9000"
    log "👤" "$GREEN" "Username: admin"
    log "🔑" "$GREEN" "Password: Chang3d!"

    # Print additional information
    log "ℹ️" "$BLUE" "Useful commands:"
    log "📝" "$BLUE" "  - View logs: docker compose -f docker-compose-splunk.yml logs"
    log "🛑" "$BLUE" "  - Stop environment: docker compose -f docker-compose-splunk.yml down"
    # log "🔄" "$BLUE" "  - Rebuild add-on: ucc-gen build"
    # log "🐳" "$BLUE" "  - Rebuild Docker: $0 --rebuild"
}

# Execute main function with all arguments
main "$@"
