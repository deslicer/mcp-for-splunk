# Test Suite for MCP Server for Splunk

A comprehensive test suite covering all aspects of the MCP Server for Splunk implementation.

## Test Structure

### Core Test Files

1. **`test_splunk_tools.py`** - Tests for all 12 MCP Splunk tools (19 tests)
   - Health checks (`get_splunk_health`)
   - Index operations (`list_indexes`)
   - Metadata tools (`list_sourcetypes`, `list_sources`)
   - Search operations (`run_oneshot_search`, `run_splunk_search`)
   - App/user management (`list_apps`, `list_users`)
   - KV Store operations (`list_kvstore_collections`, `get_kvstore_data`, `create_kvstore_collection`)
   - Configuration management (`get_configurations`)

2. **`test_transport.py`** - Transport layer testing (27 tests)
   - stdio transport configuration and execution
   - streamable-http transport with various configurations
   - Environment variable handling
   - Error conditions and security scenarios
   - Docker environment compatibility

3. **`test_splunk_client.py`** - Splunk connection testing (6 tests)
   - Connection establishment and failure scenarios
   - Credential validation
   - Port handling and conversion

4. **`test_mcp_server.py`** - Integration tests (17 tests - currently excluded)
   - Requires additional FastMCP client dependencies
   - End-to-end testing with real MCP clients
   - Currently excluded from default test runs

### Test Configuration

- **`conftest.py`** - Comprehensive pytest fixtures and mocks
- **`pyproject.toml`** - Pytest configuration and coverage settings
- **`scripts/run_tests.sh`** - Enhanced test runner with multiple options

## Running Tests

### Quick Start

```bash
# Run all core tests (excluding integration tests)
uv run scripts/run_tests.sh

# Or directly with pytest
uv run pytest --ignore=tests/test_mcp_server.py
```

### Test Categories

```bash
# Transport layer tests only
uv run scripts/run_tests.sh -k transport

# Splunk tools tests only  
uv run scripts/run_tests.sh -k splunk_tools

# Splunk client tests only
uv run scripts/run_tests.sh -k splunk_client

# Integration tests (requires additional setup)
uv run pytest tests/test_mcp_server.py
```

### Test Options

```bash
# Quick tests without coverage
uv run scripts/run_tests.sh --no-coverage -x

# Verbose output
uv run scripts/run_tests.sh -v

# Specific test pattern
uv run scripts/run_tests.sh -k health_check

# Fail on first error
uv run scripts/run_tests.sh -x
```

## Coverage

Current test coverage: **63% overall**
- `src/server.py`: 59% (272 statements)
- `src/splunk_client.py`: 85% (41 statements)  
- `src/__init__.py`: 100% (2 statements)

Coverage reports are generated in:
- Terminal output
- HTML report: `htmlcov/index.html`

## Test Results

✅ **52 core tests passing**
- 19 Splunk tools tests
- 27 transport tests
- 6 Splunk client tests

❌ **17 integration tests excluded** (require FastMCP client dependencies)

## Mock Architecture

The test suite uses extensive mocking to simulate Splunk services:

- **Mock Splunk Service**: Simulates complete Splunk SDK client
- **Mock Context**: FastMCP context with lifespan management
- **Mock Search Results**: Realistic search response data
- **Mock KV Store**: Collection and document structures
- **Mock Configurations**: Splunk configuration stanzas

## Dependencies

Testing dependencies managed via `uv`:
- `pytest` - Test framework
- `pytest-asyncio` - Async test support
- `pytest-mock` - Enhanced mocking
- `pytest-cov` - Coverage reporting

## Future Enhancements

1. **Integration Test Completion**: Add FastMCP client fixtures for full end-to-end testing
2. **Performance Tests**: Add benchmarking for large search results
3. **Error Scenario Expansion**: More comprehensive failure mode testing
4. **Parallel Execution**: Add pytest-xdist for faster test runs
5. **Property-Based Testing**: Use hypothesis for edge case discovery

## Contributing

When adding new tests:
1. Follow the existing class-based organization
2. Use descriptive test names explaining the scenario
3. Include comprehensive assertions
4. Update this README for new test categories
5. Maintain >60% coverage threshold

## Notes

- Integration tests (`test_mcp_server.py`) are excluded by default due to missing FastMCP client fixtures
- All core functionality is thoroughly tested with unit tests
- The test suite is compatible with both uv and traditional pip environments
- Mock objects closely mirror real Splunk SDK behavior for accuracy 