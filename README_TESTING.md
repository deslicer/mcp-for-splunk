# Splunk SDK Testing Guide

This directory contains comprehensive test scripts for testing the Splunk SDK functionality using your environment credentials and the `get_splunk_service` function from the MCP server.

## Test Files

### 1. `test_splunk_comprehensive.py` (Recommended)
A streamlined, comprehensive test suite that covers all major Splunk SDK functionality:

- **Connection Testing**: Validates basic Splunk connection using environment credentials
- **Index Operations**: Lists and inspects Splunk indexes
- **Search Execution**: Tests basic and custom search capabilities  
- **BaseTool Integration**: Tests the MCP server's `get_splunk_service` method

### 2. `test_splunk_sdk.py` 
A basic test suite focusing on core functionality:

- Connection testing
- Index operations
- Search execution
- BaseTool integration

### 3. `test_splunk_sdk_comprehensive.py`
An extensive test suite with detailed functionality testing (currently incomplete).

## Prerequisites

### 1. Environment Configuration
Create a `.env` file in the project root with your Splunk credentials:

```env
SPLUNK_HOST=your_splunk_host
SPLUNK_PORT=8089
SPLUNK_USERNAME=your_username  
SPLUNK_PASSWORD=your_password
SPLUNK_SCHEME=https
SPLUNK_VERIFY_SSL=false
```

### 2. Dependencies
Ensure you have the required Python packages installed:

```bash
# Install from the project requirements
uv sync

# Or install manually if needed
pip install splunk-sdk python-dotenv fastmcp
```

## Usage

### Quick Test (Recommended)
Run the comprehensive test suite:

```bash
python test_splunk_comprehensive.py
```

This will automatically run all tests and provide a summary.

### Interactive Testing
The comprehensive test includes an interactive mode if you need to test specific functionality:

```bash
python test_splunk_comprehensive.py
# Follow the prompts to select specific tests
```

### Basic Testing
For minimal testing:

```bash
python test_splunk_sdk.py
```

## Test Coverage

The comprehensive test suite covers:

### ✅ Core Functionality
- **Connection**: Environment-based authentication
- **Service Info**: Splunk version, server details, license state
- **BaseTool Integration**: MCP server's `get_splunk_service` method

### ✅ Data Access
- **Indexes**: List, inspect, and access index information
- **Search Execution**: Basic queries and result handling
- **Job Management**: Job creation, monitoring, and cleanup

### ✅ Advanced Features  
- **Real-time Search**: Real-time query capabilities
- **Custom Searches**: User-defined search queries
- **Error Handling**: Comprehensive error catching and reporting

## Example Output

```
🚀 Splunk SDK Test Suite
==================================================
🔌 Testing Connection...
Connecting to splunk-server:8089
✅ Connected to splunk-server v9.1.0

🔧 Testing BaseTool...
✅ BaseTool connection to splunk-server

📚 Testing Indexes...
Found 15 indexes
  1. main: 1234567 events
  2. _internal: 987654 events
  ...

🔎 Testing Search...
✅ Search completed: 1 results

======================================================================
🏁 TEST SUMMARY
======================================================================
Duration: 0:00:05.123456
Tests: 4/4 passed

connection               ✅ PASS
                         splunk-server v9.1.0
base_tool               ✅ PASS
                         Connected to splunk-server
indexes                 ✅ PASS
                         Found 15 indexes
search                  ✅ PASS
                         1 results
```

## Customization

### Testing Custom Searches
You can test specific SPL queries by modifying the test files or using the interactive mode:

```python
# Example custom search
await test_custom_search(service, "index=main | head 10", "My custom search")
```

### Adding New Tests
To add new functionality tests, follow this pattern:

```python
async def test_my_feature(service: client.Service, test_results: TestResults):
    """Test my specific feature."""
    print("\n🔧 Testing My Feature...")
    try:
        # Your test logic here
        result = service.my_feature()
        
        test_results.add_result("my_feature", True, f"Found {len(result)} items")
        return True
    except Exception as e:
        test_results.add_result("my_feature", False, str(e))
        return False
```

## Troubleshooting

### Common Issues

1. **Connection Failed**
   - Verify `.env` file exists and has correct credentials
   - Check network connectivity to Splunk server
   - Ensure Splunk management port (8089) is accessible

2. **Import Errors**
   - Ensure you're running from the project root directory
   - Check that `src/` directory is in the Python path
   - Verify all dependencies are installed

3. **Permission Errors**
   - Ensure your Splunk user has appropriate permissions
   - Check if your user can access the indexes being tested

### Debug Mode
For detailed debugging, you can modify the test files to add more verbose logging:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## Integration with MCP Server

These test files are designed to work with the MCP server's Splunk integration:

- Uses the same environment variables as the server
- Tests the `BaseTool.get_splunk_service()` method
- Validates the connection logic used by MCP tools
- Ensures compatibility with the server's Splunk client implementation

This makes them ideal for validating that your Splunk configuration will work correctly with the MCP server before deploying tools and resources. 