# Testing Guide

This project uses `pytest` with `uv` for dependency management and testing.

## Quick Start

```bash
# Install dependencies
make install

# Run all tests
make test

# Run only fast tests (recommended for development)
make test-fast

# Run only unit tests
make test-unit

# Run only connection tests
make test-connections
```

## Test Structure

```
tests/
├── __init__.py
├── conftest.py          # Shared fixtures and configuration
└── test_mcp_server.py   # Main test suite
```

## Test Categories

### 🔧 Unit Tests (`@pytest.mark.unit`)
- Helper function tests
- Utility function tests  
- No external dependencies

### 🌐 Integration Tests (`@pytest.mark.integration`)
- MCP server connection tests
- Splunk API integration tests
- End-to-end functionality tests

### 🐌 Slow Tests (`@pytest.mark.slow`)
- Tests that take longer to run
- Heavy Splunk operations

## Test Commands

| Command | Description |
|---------|-------------|
| `make test` | Run all tests |
| `make test-unit` | Run only unit tests |
| `make test-integration` | Run only integration tests |
| `make test-fast` | Run tests excluding slow ones |
| `make test-connections` | Test MCP connections only |
| `make test-health` | Test health checks only |
| `make test-splunk` | Test Splunk tools only |
| `make test-apps` | Test Splunk apps and users |
| `make test-kvstore` | Test KV Store functionality |

## Configuration

Testing is configured in `pyproject.toml`:

```toml
[tool.pytest.ini_options]
addopts = [
    "-v",
    "--tb=short", 
    "--strict-markers",
    "--disable-warnings",
    "--asyncio-mode=auto"
]
asyncio_mode = "auto"
markers = [
    "slow: marks tests as slow",
    "integration: marks tests as integration tests",
    "unit: marks tests as unit tests"
]
```

## Running Specific Tests

```bash
# Run a specific test class
uv run pytest tests/test_mcp_server.py::TestMCPConnections -v

# Run a specific test method
uv run pytest tests/test_mcp_server.py::TestMCPConnections::test_traefik_connection -v

# Run tests matching a pattern
uv run pytest tests/ -k "connection" -v

# Run tests with coverage
uv run pytest tests/ --cov=src --cov-report=html
```

## Test Dependencies

The test environment requires:
- **Docker containers running** (MCP server and Splunk)
- **Network connectivity** to `localhost:8001` (Traefik) and `localhost:8002` (direct)
- **Splunk instance** accessible and healthy

## Expected Results

✅ **Passing Tests (13/16):**
- MCP connections (Traefik & Direct)
- Health checks
- Basic Splunk operations
- Error handling
- Helper functions

⚠️ **Known Issues (3/16):**
- Some tests may fail due to Splunk disk space limitations
- Search operations depend on Splunk having sufficient resources
- These are environment issues, not code issues

## Troubleshooting

### Async Test Issues
If you see "async def functions are not natively supported":
```bash
# Ensure pytest-asyncio is installed
uv add --dev pytest-asyncio

# Check pytest plugins
uv run pytest --version
```

### Connection Issues
If connection tests fail:
```bash
# Check Docker containers
docker-compose ps

# Check MCP server logs
make docker-logs

# Test connections manually
curl http://localhost:8001/mcp/
curl http://localhost:8002/mcp/
```

### Splunk Issues
If Splunk tests fail:
```bash
# Check Splunk health
curl -k https://localhost:8089/services/server/info

# Restart Splunk if needed
docker-compose restart so1
```

## CI/CD Integration

For continuous integration:

```bash
# Full test suite with coverage
make ci-test

# Quick development checks  
make dev-test
```

The test suite is designed to be robust and will gracefully handle Splunk connectivity issues while still validating core MCP functionality. 