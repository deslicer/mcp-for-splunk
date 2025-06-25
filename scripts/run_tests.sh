#!/bin/bash

# Test runner script for MCP Server for Splunk
set -e

echo "🧪 Running MCP Server for Splunk Tests"
echo "======================================"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
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

# Default values
COVERAGE=true
VERBOSE=false
MARKERS=""
PATTERN=""
FAILFAST=false
PARALLEL=false

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --no-coverage)
            COVERAGE=false
            shift
            ;;
        -v|--verbose)
            VERBOSE=true
            shift
            ;;
        -m|--markers)
            MARKERS="$2"
            shift 2
            ;;
        -k|--pattern)
            PATTERN="$2"
            shift 2
            ;;
        -x|--failfast)
            FAILFAST=true
            shift
            ;;
        -n|--parallel)
            PARALLEL=true
            shift
            ;;
        -h|--help)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --no-coverage     Skip coverage reporting"
            echo "  -v, --verbose     Verbose output"
            echo "  -m, --markers     Run only tests with specific markers (e.g., 'unit', 'integration')"
            echo "  -k, --pattern     Run only tests matching pattern"
            echo "  -x, --failfast    Stop on first failure"
            echo "  -n, --parallel    Run tests in parallel"
            echo "  -h, --help        Show this help message"
            echo ""
            echo "Examples:"
            echo "  $0                      # Run all tests with coverage"
            echo "  $0 --no-coverage       # Run tests without coverage"
            echo "  $0 -m unit             # Run only unit tests"
            echo "  $0 -k health           # Run only tests matching 'health'"
            echo "  $0 -x                  # Stop on first failure"
            exit 0
            ;;
        *)
            print_error "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Check if we're in a virtual environment
if [[ -z "$VIRTUAL_ENV" ]] && [[ ! -f "pyproject.toml" ]]; then
    print_warning "Not in a virtual environment and no pyproject.toml found"
    print_warning "Consider running: uv venv && source .venv/bin/activate"
fi

# Check if dependencies are installed
print_status "Checking dependencies..."
if ! command -v uv &> /dev/null; then
    print_error "uv not found. Install from: https://docs.astral.sh/uv/"
    exit 1
fi

# Build pytest command with uv run
PYTEST_CMD="uv run pytest --ignore=tests/test_mcp_server.py"

# Add coverage options
if [ "$COVERAGE" = true ]; then
    PYTEST_CMD="$PYTEST_CMD --cov=src --cov-report=term-missing --cov-report=html:htmlcov"
fi

# Add verbose option
if [ "$VERBOSE" = true ]; then
    PYTEST_CMD="$PYTEST_CMD -v"
fi

# Add markers
if [ -n "$MARKERS" ]; then
    PYTEST_CMD="$PYTEST_CMD -m $MARKERS"
fi

# Add pattern
if [ -n "$PATTERN" ]; then
    PYTEST_CMD="$PYTEST_CMD -k $PATTERN"
fi

# Add failfast
if [ "$FAILFAST" = true ]; then
    PYTEST_CMD="$PYTEST_CMD -x"
fi

# Add parallel execution
if [ "$PARALLEL" = true ]; then
    if command -v pytest-xdist &> /dev/null; then
        PYTEST_CMD="$PYTEST_CMD -n auto"
    else
        print_warning "pytest-xdist not installed. Install with: uv add --dev pytest-xdist"
        print_warning "Falling back to sequential execution"
    fi
fi

# Run the tests
print_status "Running tests..."
echo "Command: $PYTEST_CMD"
echo ""

if eval $PYTEST_CMD; then
    print_success "All core tests passed! ✅"
    
    if [ "$COVERAGE" = true ]; then
        echo ""
        print_status "Coverage report generated:"
        print_status "  • Terminal: See above"
        print_status "  • HTML: htmlcov/index.html"
    fi
    
    echo ""
    print_status "Note: Integration tests (test_mcp_server.py) excluded by default"
    print_status "      To run integration tests: uv run pytest tests/test_mcp_server.py"
else
    print_error "Tests failed! ❌"
    exit 1
fi

# Summary
echo ""
echo "🎉 Test execution completed!"
echo ""
echo "Available test commands:"
echo "  • Unit tests only:       ./scripts/run_tests.sh -m unit"
echo "  • Transport tests:       ./scripts/run_tests.sh -k transport"
echo "  • Splunk tools tests:    ./scripts/run_tests.sh -k splunk_tools"
echo "  • Integration tests:     uv run pytest tests/test_mcp_server.py"
echo "  • Quick tests:           ./scripts/run_tests.sh --no-coverage -x"
echo "  • Specific test:         ./scripts/run_tests.sh -k test_health_check" 