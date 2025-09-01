#!/bin/bash

# MCP Server for Splunk - Prerequisites Checker (Unix/Linux/macOS)
# This script verifies that all required prerequisites are installed

set -e

# Default options
DETAILED=false
HELP=false

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --detailed|-d)
            DETAILED=true
            shift
            ;;
        --help|-h)
            HELP=true
            shift
            ;;
        *)
            echo "Unknown option: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

# Show help if requested
if [[ "$HELP" == "true" ]]; then
    cat << 'EOF'
MCP Server for Splunk - Prerequisites Checker (Unix/Linux/macOS)

Usage:
    ./scripts/check-prerequisites.sh [options]

Options:
    --detailed, -d    Show detailed version information and installation paths
    --help, -h        Show this help message

Examples:
    ./scripts/check-prerequisites.sh           # Basic check
    ./scripts/check-prerequisites.sh --detailed # Detailed information

EOF
    exit 0
fi

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Emoji support check
if command -v locale >/dev/null 2>&1 && [[ "$(locale charmap 2>/dev/null)" == "UTF-8" ]]; then
    EMOJI_SUCCESS="✅"
    EMOJI_WARNING="⚠️ "
    EMOJI_ERROR="❌"
    EMOJI_INFO="ℹ️ "
else
    EMOJI_SUCCESS="[OK]"
    EMOJI_WARNING="[WARN]"
    EMOJI_ERROR="[ERR]"
    EMOJI_INFO="[INFO]"
fi

# Output functions
print_success() {
    echo -e "${GREEN}${EMOJI_SUCCESS} $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}${EMOJI_WARNING} $1${NC}"
}

print_error() {
    echo -e "${RED}${EMOJI_ERROR} $1${NC}"
}

print_info() {
    echo -e "${BLUE}${EMOJI_INFO} $1${NC}"
}

print_header() {
    echo -e "${CYAN}$1${NC}"
}

# Track installation status
missing_requirements=()
optional_missing=()
installation_tips=()

echo -e "${CYAN}🔍 Checking Prerequisites for MCP Server for Splunk...${NC}"
echo -e "${CYAN}============================================================${NC}"
echo

# Function to check if a command exists and get version
check_command() {
    local name="$1"
    local command="$2"
    local version_arg="$3"
    local optional="$4"
    local install_tip="$5"

    if command -v "$command" >/dev/null 2>&1; then
        local version_output
        version_output=$($command $version_arg 2>/dev/null | head -n1)

        if [[ "$DETAILED" == "true" ]]; then
            local path
            path=$(command -v "$command")
            print_success "$name: $version_output"
            print_info "    Location: $path"
        else
            print_success "$name: $version_output"
        fi
        return 0
    else
        if [[ "$optional" == "true" ]]; then
            print_warning "$name: Not installed (optional)"
            optional_missing+=("$name")
        else
            print_error "$name: Not installed (required)"
            missing_requirements+=("$name")
        fi
        installation_tips+=("📦 $name: $install_tip")
        return 1
    fi
}

# Check required tools
print_header "🔧 Required Tools:"
echo "--------------------"

check_command "Python" "python3" "--version" "false" "Install with package manager or from python.org"
check_command "UV Package Manager" "uv" "--version" "false" "Run: curl -LsSf https://astral.sh/uv/install.sh | sh"
check_command "Git" "git" "--version" "false" "Install with package manager: apt install git / brew install git / dnf install git"

echo

# Check optional tools
print_header "🌟 Optional Tools:"
echo "--------------------"

check_command "Node.js" "node" "--version" "true" "Install from nodejs.org or package manager (enables MCP Inspector)"
check_command "NPM" "npm" "--version" "true" "Installed with Node.js"
check_command "Docker" "docker" "--version" "true" "Install Docker Engine or Docker Desktop (enables full containerized stack)"

# Check for docker-compose (could be plugin or standalone)
if command -v docker-compose >/dev/null 2>&1; then
    check_command "Docker Compose" "docker-compose" "--version" "true" "Installed with Docker"
elif command -v docker >/dev/null 2>&1 && docker compose version >/dev/null 2>&1; then
    if [[ "$DETAILED" == "true" ]]; then
        docker_path=$(command -v docker)
        print_success "Docker Compose: $(docker compose version | head -n1)"
        print_info "    Location: $docker_path (plugin)"
    else
        print_success "Docker Compose: $(docker compose version | head -n1)"
    fi
else
    print_warning "Docker Compose: Not installed (optional)"
    optional_missing+=("Docker Compose")
    installation_tips+=("📦 Docker Compose: Installed with Docker Desktop or Docker Engine")
fi

echo

# Additional system checks
print_header "💻 System Information:"
echo "--------------------"

# Operating System
if [[ -f /etc/os-release ]]; then
    source /etc/os-release
    print_info "OS: $PRETTY_NAME"
elif [[ "$OSTYPE" == "darwin"* ]]; then
    macos_version=$(sw_vers -productVersion 2>/dev/null || echo "Unknown")
    print_info "OS: macOS $macos_version"
else
    print_info "OS: $(uname -s) $(uname -r)"
fi

# Architecture
print_info "Architecture: $(uname -m)"

# Shell
print_info "Shell: $SHELL"

# Available disk space
if command -v df >/dev/null 2>&1; then
    disk_space=$(df -h . 2>/dev/null | awk 'NR==2 {print $4}' | head -n1)
    if [[ -n "$disk_space" ]]; then
        print_success "Available Disk Space: $disk_space"
    fi
fi

# Memory information
if command -v free >/dev/null 2>&1; then
    memory=$(free -h 2>/dev/null | awk 'NR==2{print $7}' | head -n1)
    if [[ -n "$memory" ]]; then
        print_info "Available Memory: $memory"
    fi
elif [[ "$OSTYPE" == "darwin"* ]]; then
    # macOS memory check
    if command -v vm_stat >/dev/null 2>&1; then
        free_pages=$(vm_stat | grep "Pages free" | awk '{print $3}' | sed 's/\.//')
        if [[ -n "$free_pages" && "$free_pages" =~ ^[0-9]+$ ]]; then
            free_mb=$((free_pages * 4096 / 1024 / 1024))
            print_info "Available Memory: ${free_mb}MB"
        fi
    fi
fi

echo

# Detect package manager for installation tips
PACKAGE_MANAGER=""
INSTALL_COMMAND=""

if command -v apt >/dev/null 2>&1; then
    PACKAGE_MANAGER="apt"
    INSTALL_COMMAND="sudo apt update && sudo apt install -y"
elif command -v dnf >/dev/null 2>&1; then
    PACKAGE_MANAGER="dnf"
    INSTALL_COMMAND="sudo dnf install -y"
elif command -v yum >/dev/null 2>&1; then
    PACKAGE_MANAGER="yum"
    INSTALL_COMMAND="sudo yum install -y"
elif command -v brew >/dev/null 2>&1; then
    PACKAGE_MANAGER="brew"
    INSTALL_COMMAND="brew install"
elif command -v pacman >/dev/null 2>&1; then
    PACKAGE_MANAGER="pacman"
    INSTALL_COMMAND="sudo pacman -S"
fi

# Summary
print_header "📊 Summary:"
echo "--------------------"

if [[ ${#missing_requirements[@]} -eq 0 ]]; then
    print_success "All required prerequisites are installed! 🎉"

    if [[ ${#optional_missing[@]} -eq 0 ]]; then
        print_success "All optional tools are also available!"
        echo
        echo -e "${GREEN}🚀 You're ready to run: uv run mcp-server --local -d${NC}"
    else
        print_info "Some optional tools are missing, but you can still proceed."
        echo
        echo -e "${GREEN}🚀 You can run: uv run mcp-server --local -d${NC}"
        echo "   (Some features like MCP Inspector or Docker stack may not be available)"
    fi
else
    print_error "Missing required prerequisites: $(IFS=', '; echo "${missing_requirements[*]}")"
    echo
    print_header "📋 Installation Commands:"
    echo "--------------------"

    # Show installation tips for missing requirements
    for tip in "${installation_tips[@]}"; do
        for req in "${missing_requirements[@]}"; do
            if [[ "$tip" == *"$req"* ]]; then
                echo -e "${CYAN}$tip${NC}"
            fi
        done
    done

    echo
    print_header "🎯 Quick Install Commands:"

    if [[ "$PACKAGE_MANAGER" == "apt" ]]; then
        echo -e "${CYAN}$INSTALL_COMMAND python3.11 python3.11-pip python3.11-venv nodejs npm git curl${NC}"
        echo -e "${CYAN}curl -LsSf https://astral.sh/uv/install.sh | sh${NC}"
    elif [[ "$PACKAGE_MANAGER" == "brew" ]]; then
        echo -e "${CYAN}$INSTALL_COMMAND python@3.11 uv node git${NC}"
    elif [[ "$PACKAGE_MANAGER" == "dnf" ]]; then
        echo -e "${CYAN}$INSTALL_COMMAND python3.11 python3.11-pip nodejs npm git curl${NC}"
        echo -e "${CYAN}curl -LsSf https://astral.sh/uv/install.sh | sh${NC}"
    else
        echo -e "${CYAN}Please install missing packages using your system's package manager${NC}"
        echo -e "${CYAN}Then run: curl -LsSf https://astral.sh/uv/install.sh | sh${NC}"
    fi
fi

if [[ ${#optional_missing[@]} -gt 0 && ${#missing_requirements[@]} -eq 0 ]]; then
    echo
    print_header "🌟 Optional Installation Commands:"
    echo "--------------------"

    # Show installation tips for missing optional tools
    for tip in "${installation_tips[@]}"; do
        for opt in "${optional_missing[@]}"; do
            if [[ "$tip" == *"$opt"* ]]; then
                echo -e "${CYAN}$tip${NC}"
            fi
        done
    done
fi

echo
print_info "📚 For detailed installation instructions, see the Prerequisites section in README.md"

# Exit with appropriate code
if [[ ${#missing_requirements[@]} -gt 0 ]]; then
    exit 1
else
    exit 0
fi
