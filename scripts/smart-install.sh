#!/usr/bin/env bash

# Smart Prerequisites Installer for MCP Server for Splunk (macOS & Linux)
# - Installs Homebrew (macOS), Python 3.x, uv, and Git only if missing
# - Prints guidance for optional Node.js and Docker if missing
# - Idempotent and safe to re-run

set -euo pipefail

# Args
DRY_RUN=false
SHOW_HELP=false
INSTALL_ALL=false

while [[ $# -gt 0 ]]; do
  case "$1" in
    -n|--dry-run)
      DRY_RUN=true
      shift
      ;;
    -a|--all)
      INSTALL_ALL=true
      shift
      ;;
    -h|--help)
      SHOW_HELP=true
      shift
      ;;
    *)
      echo "Unknown argument: $1" >&2
      exit 1
      ;;
  esac
done

if [[ "$SHOW_HELP" == true ]]; then
  cat << 'EOF'
MCP for Splunk: Smart Prerequisites Installer (macOS & Linux)

Usage:
  ./scripts/smart-install.sh [--dry-run] [--all] [--help]

Options:
  -n, --dry-run   Describe what would be installed without making changes
  -a, --all       Also install Docker and Docker Compose (where supported)
  -h, --help      Show this help text
EOF
  exit 0
fi

if [[ "$DRY_RUN" == true ]]; then
  echo "=== MCP for Splunk: Smart Prerequisites Installer (dry run) ==="
else
  echo "=== MCP for Splunk: Smart Prerequisites Installer ==="
fi

OS_NAME=$(uname -s)

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

ok() { echo -e "${GREEN}✔${NC} $1"; }
note() { echo -e "${YELLOW}•${NC} $1"; }
err() { echo -e "${RED}✖${NC} $1"; }

# Detect package manager on Linux
detect_linux_pm() {
  if command -v apt >/dev/null 2>&1; then echo apt; return; fi
  if command -v dnf >/dev/null 2>&1; then echo dnf; return; fi
  if command -v yum >/dev/null 2>&1; then echo yum; return; fi
  if command -v pacman >/dev/null 2>&1; then echo pacman; return; fi
  if command -v zypper >/dev/null 2>&1; then echo zypper; return; fi
  echo unknown
}

# Determine desired Python version/spec from .python-version or pyproject.toml
resolve_python_request() {
  PY_REQUEST=""
  if [[ -f ".python-version" ]]; then
    PY_REQUEST=$(tr -d ' \t' < .python-version)
  fi

  if [[ -z "${PY_REQUEST}" && -f "pyproject.toml" ]]; then
    # Extract requires-python from [project] section
    PY_REQUEST=$(awk '
      BEGIN{inproj=0}
      /^\[project\]/{inproj=1; next}
      /^\[/{if(inproj==1){exit} inproj=0}
      inproj && $0 ~ /requires-python\s*=\s*"[^"]+"/ {print; exit}
    ' pyproject.toml | sed -E 's/.*requires-python\s*=\s*"([^"]+)".*/\1/')
  fi

  if [[ -z "${PY_REQUEST}" ]]; then
    PY_REQUEST="3.11"
    note "No Python requirement detected; defaulting to ${PY_REQUEST}"
  else
    note "Detected Python requirement: ${PY_REQUEST}"
  fi
}

# Install uv if missing. Prefer Homebrew on macOS, official installer otherwise
ensure_uv_installed() {
  if command -v uv >/dev/null 2>&1; then
    ok "uv already installed ($(uv --version))"
    return
  fi

  case "$(uname -s)" in
    Darwin)
      if command -v brew >/dev/null 2>&1; then
        if [[ "$DRY_RUN" == true ]]; then
          note "uv not found; would install uv via Homebrew"
        else
          note "Installing uv via Homebrew..."
          brew install uv
          ok "uv installed ($(uv --version))"
        fi
      else
        if [[ "$DRY_RUN" == true ]]; then
          note "uv not found; would install via official installer (curl -LsSf https://astral.sh/uv/install.sh | sh)"
        else
          note "Installing uv via official installer..."
          curl -LsSf https://astral.sh/uv/install.sh | sh
          # Ensure current session can find uv if installed to ~/.local/bin or ~/.cargo/bin
          export PATH="$HOME/.local/bin:$HOME/.cargo/bin:$PATH"
          if command -v uv >/dev/null 2>&1; then
            ok "uv installed ($(uv --version))"
          else
            err "uv installation failed - please install from https://astral.sh/uv"
            exit 1
          fi
        fi
      fi
      ;;
    Linux)
      if [[ "$DRY_RUN" == true ]]; then
        note "uv not found; would install via official installer (curl -LsSf https://astral.sh/uv/install.sh | sh)"
      else
        note "Installing uv via official installer..."
        curl -LsSf https://astral.sh/uv/install.sh | sh
        # Ensure current session can find uv if installed to ~/.local/bin or ~/.cargo/bin
        export PATH="$HOME/.local/bin:$HOME/.cargo/bin:$PATH"
        if command -v uv >/dev/null 2>&1; then
          ok "uv installed ($(uv --version))"
        else
          err "uv installation failed - please install from https://astral.sh/uv"
          exit 1
        fi
      fi
      ;;
    *)
      err "Unsupported OS for uv install"
      ;;
  esac
}

# Install a Python version via uv based on detected request
install_python_with_uv() {
  local req="$1"
  if [[ "$DRY_RUN" == true ]]; then
    note "Would install Python via uv: uv python install ${req}"
  else
    note "Installing Python via uv (${req})..."
    uv python install "${req}"
    ok "Python (${req}) installed via uv"
  fi

  if [[ "$DRY_RUN" == true ]]; then
    note "Would verify Python availability with: uv python find '${req}'"
  else
    if PY_PATH=$(uv python find "${req}" 2>/dev/null); then
      ok "Python available at: ${PY_PATH}"
    else
      err "uv could not find a compatible Python for request: ${req}"
      exit 1
    fi
  fi
}

install_mac() {
  # Homebrew
  if ! command -v brew >/dev/null 2>&1; then
    if [[ "$DRY_RUN" == true ]]; then
      note "Homebrew not found; would install Homebrew"
    else
      note "Homebrew not found; installing Homebrew..."
      /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
      ok "Homebrew installed"
    fi
  else
    ok "Homebrew already installed ($(brew --version | head -n1))"
  fi

  # uv (use shared installer to avoid duplication and ensure verification)
  ensure_uv_installed

  # Python via uv (respect .python-version or pyproject.toml)
  resolve_python_request
  install_python_with_uv "${PY_REQUEST}"

  # Git
  if ! command -v git >/dev/null 2>&1; then
    if [[ "$DRY_RUN" == true ]]; then
      note "Git not found; would install Git"
    else
      note "Installing Git..."
      brew install git
      ok "Git installed ($(git --version))"
    fi
  else
    ok "Git already installed ($(git --version))"
  fi

  # Node.js (base install)
  if ! command -v node >/dev/null 2>&1; then
    if [[ "$DRY_RUN" == true ]]; then
      note "Node.js not found; would install: brew install node"
    else
      note "Installing Node.js..."
      brew install node
      ok "Node.js installed ($(node --version))"
    fi
  else
    ok "Node.js already installed ($(node --version))"
  fi

  # Docker (only with --all)
  if [[ "$INSTALL_ALL" == true ]]; then
    if ! command -v docker >/dev/null 2>&1; then
      if [[ "$DRY_RUN" == true ]]; then
        note "Docker not found; would install: brew install --cask docker"
      else
        note "Installing Docker Desktop..."
        brew install --cask docker
        ok "Docker installed ($(docker --version | head -n1))"
      fi
    else
      ok "Docker already installed ($(docker --version | head -n1))"
    fi
  else
    note "Docker installation skipped (use --all to install)"
  fi
}

install_linux() {
  PM=$(detect_linux_pm)
  note "Detected package manager: $PM"

  case "$PM" in
    apt)
      if [[ "$DRY_RUN" == true ]]; then
        note "Would run: sudo apt update"
      else
        sudo apt update
      fi

      # Git & curl
      if ! command -v git >/dev/null 2>&1; then
        if [[ "$DRY_RUN" == true ]]; then note "Would install: git"; else sudo apt install -y git; ok "Git installed ($(git --version))"; fi
      else ok "Git already installed ($(git --version))"; fi
      if ! command -v curl >/dev/null 2>&1; then
        if [[ "$DRY_RUN" == true ]]; then note "Would install: curl"; else sudo apt install -y curl; ok "curl installed ($(curl --version | head -n1))"; fi
      else ok "curl already installed ($(curl --version | head -n1))"; fi

      # uv
      ensure_uv_installed

      # Python via uv (respect .python-version or pyproject.toml)
      resolve_python_request
      install_python_with_uv "${PY_REQUEST}"

      # Node.js (base install)
      if ! command -v node >/dev/null 2>&1; then
        if [[ "$DRY_RUN" == true ]]; then
          note "Node.js not found; would install: sudo apt install -y nodejs npm"
        else
          note "Installing Node.js..."
          sudo apt install -y nodejs npm
          ok "Node.js installed ($(node --version))"
        fi
      else
        ok "Node.js already installed ($(node --version))"
      fi

      # Docker (only with --all)
      if [[ "$INSTALL_ALL" == true ]]; then
        if ! command -v docker >/dev/null 2>&1; then
          if [[ "$DRY_RUN" == true ]]; then
            note "Would install Docker Engine and Compose plugin (apt): add repo, apt update, install docker-ce docker-ce-cli containerd.io docker-compose-plugin, add user to docker group"
          else
            note "Installing Docker Engine and Compose plugin..."
            sudo apt install -y apt-transport-https ca-certificates curl software-properties-common
            curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo apt-key add -
            sudo add-apt-repository "deb [arch=$(dpkg --print-architecture)] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable"
            sudo apt update
            sudo apt install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
            sudo usermod -aG docker "$USER" || true
            ok "Docker installed ($(docker --version | head -n1))"
          fi
        else
          ok "Docker already installed ($(docker --version | head -n1))"
        fi
      else
        note "Docker installation skipped (use --all to install)"
      fi
      ;;
    dnf|yum)
      # Git & curl
      if ! command -v git >/dev/null 2>&1; then
        if [[ "$DRY_RUN" == true ]]; then note "Would install: sudo $PM install -y git"; else sudo $PM install -y git; ok "Git installed ($(git --version))"; fi
      else ok "Git already installed ($(git --version))"; fi
      if ! command -v curl >/dev/null 2>&1; then
        if [[ "$DRY_RUN" == true ]]; then note "Would install: sudo $PM install -y curl"; else sudo $PM install -y curl; ok "curl installed ($(curl --version | head -n1))"; fi
      else ok "curl already installed ($(curl --version | head -n1))"; fi

      # uv
      ensure_uv_installed

      # Python via uv (respect .python-version or pyproject.toml)
      resolve_python_request
      install_python_with_uv "${PY_REQUEST}"

      # Node.js (base install)
      if ! command -v node >/dev/null 2>&1; then
        if [[ "$DRY_RUN" == true ]]; then
          note "Node.js not found; would install: sudo $PM install -y nodejs npm"
        else
          note "Installing Node.js..."
          sudo $PM install -y nodejs npm
          ok "Node.js installed ($(node --version))"
        fi
      else
        ok "Node.js already installed ($(node --version))"
      fi

      # Docker (only with --all)
      if [[ "$INSTALL_ALL" == true ]]; then
        if ! command -v docker >/dev/null 2>&1; then
          if [[ "$DRY_RUN" == true ]]; then
            note "Would install Docker Engine and Compose plugin (dnf/yum): add repo, install docker-ce docker-ce-cli containerd.io docker-compose-plugin, enable/start docker, add user to docker group"
          else
            note "Installing Docker Engine and Compose plugin..."
            if command -v dnf >/dev/null 2>&1; then
              sudo dnf -y install dnf-plugins-core
              sudo dnf config-manager --add-repo https://download.docker.com/linux/fedora/docker-ce.repo
              sudo dnf install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
              sudo systemctl enable --now docker
            else
              sudo yum -y install yum-utils
              sudo yum-config-manager --add-repo https://download.docker.com/linux/centos/docker-ce.repo
              sudo yum install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
              sudo systemctl enable --now docker
            fi
            sudo usermod -aG docker "$USER" || true
            ok "Docker installed ($(docker --version | head -n1))"
          fi
        else
          ok "Docker already installed ($(docker --version | head -n1))"
        fi
      else
        note "Docker installation skipped (use --all to install)"
      fi
      ;;
    pacman|zypper|unknown)
      note "Unsupported package manager for automatic install. Please install: python3, pip, git, curl, uv"
      note "Then (optional): nodejs npm, docker"
      ;;
  esac
}

case "$OS_NAME" in
  Darwin)
    install_mac
    ;;
  Linux)
    install_linux
    ;;
  *)
    err "Unsupported OS: $OS_NAME"
    exit 1
    ;;
esac

echo

# Final verification
note "Verifying core dependencies..."

missing=()
if ! command -v uv >/dev/null 2>&1; then missing+=("uv"); fi
if ! command -v git >/dev/null 2>&1; then missing+=("git"); fi

if [[ ${#missing[@]} -gt 0 ]]; then
  err "Missing core dependencies: ${missing[*]}"
  err "Please install manually and ensure they are in your PATH"
  exit 1
fi

ok "All core dependencies verified"

# Check optionals
if ! command -v node >/dev/null 2>&1; then
  note "Node.js not found (optional for MCP Inspector)"
else
  ok "Node.js verified ($(node --version))"
fi

if ! command -v docker >/dev/null 2>&1; then
  note "Docker not found (optional for containerized deployment)"
else
  ok "Docker verified ($(docker --version | head -n1))"
fi

ok "Prerequisite check/install complete"
note "You can now follow the next steps in the lab"

# Additional check: ensure a usable Python executable is discoverable by uv
if PY_FOUND=$(uv python find 2>/dev/null); then
  ok "uv can find Python (${PY_FOUND})"
else
  err "uv cannot find a Python interpreter. Please re-run this installer or install Python via uv manually."
  exit 1
fi


