# Splunk Triage Agent Test Suite

This directory contains comprehensive test scripts for the `SplunkTriageAgentTool` using the FastMCP client library. The tests are designed to validate progress reporting, timeout handling, and connection monitoring.

## Files

- **`test_agent.py`** - Main test script with comprehensive monitoring
- **`run_test.py`** - Simple runner script with predefined scenarios
- **`TEST_README.md`** - This documentation file

## Prerequisites

1. **FastMCP Server Running**: Ensure your MCP server is running on the specified port (default: 8000)
2. **Environment Variables**: Set up required environment variables for Splunk connection
3. **Dependencies**: Install required Python packages

### Required Environment Variables

```bash
# Splunk connection
export SPLUNK_HOST=localhost
export SPLUNK_PORT=8089
export SPLUNK_USERNAME=admin
export SPLUNK_PASSWORD=your_password

# OpenAI API (required for the triage agent)
export OPENAI_API_KEY=your_openai_api_key
export OPENAI_MODEL=gpt-4o  # Optional, defaults to gpt-4o
export OPENAI_TEMPERATURE=0.7  # Optional
```

### Install Dependencies

```bash
pip install fastmcp
```

## Quick Start

### 1. Start the MCP Server

```bash
# Start the server (in the main project directory)
python src/server.py
```

### 2. Run the Default Test

```bash
# Run the missing data scenario (default)
python test_agent.py
```

### 3. Run with Different Scenarios

```bash
# Test missing data issue
python run_test.py missing_data

# Test performance issues
python run_test.py performance

# Test input/ingestion issues
python run_test.py inputs

# Test indexing issues
python run_test.py indexing

# Test general troubleshooting
python run_test.py general

# Run all scenarios
python run_test.py all
```

## Test Features

### 🔍 Progress Monitoring
- **Real-time Progress Updates**: Tracks progress reports from the agent
- **Timeout Detection**: Warns if no progress updates received for 30+ seconds
- **Progress History**: Maintains complete history of all progress updates
- **Gap Analysis**: Identifies long periods without progress updates

### 🔗 Connection Monitoring
- **Health Checks**: Periodic ping to verify server connectivity
- **Timeout Management**: Configurable timeout (default: 5 minutes)
- **Connection Loss Detection**: Monitors for unexpected disconnections
- **Background Monitoring**: Non-blocking connection health checks

### 📊 Result Analysis
- **Structured Data**: Displays structured results from the agent
- **Step Summary**: Shows detailed workflow execution steps
- **Tool Execution**: Lists all tools called during troubleshooting
- **Timing Analysis**: Provides detailed execution timing information

## Configuration

### Test Configuration

Modify the `TestConfig` class in `test_agent.py`:

```python
@dataclass
class TestConfig:
    server_url: str = "http://localhost:8000"
    timeout: float = 300.0  # 5 minutes
    test_input: str = "I cant find my data in index=cca_insights"
    earliest_time: str = "-24h"
    latest_time: str = "now"
    focus_index: Optional[str] = "cca_insights"
    focus_host: Optional[str] = None
    complexity_level: str = "moderate"
```

### Environment Variables

```bash
# Override server URL
export MCP_SERVER_URL=http://localhost:8001

# Set custom timeout (in seconds)
export TEST_TIMEOUT=600
```

## Test Scenarios

### Missing Data (`missing_data`)
- **Problem**: "I cant find my data in index=cca_insights"
- **Focus**: Index-specific troubleshooting
- **Complexity**: Moderate
- **Expected**: Routes to Missing Data Specialist

### Performance (`performance`)
- **Problem**: "My searches are running very slowly and timing out"
- **Focus**: System performance analysis
- **Complexity**: High
- **Expected**: Routes to Performance Specialist

### Inputs (`inputs`)
- **Problem**: "No new data is being ingested from my forwarders"
- **Focus**: Data ingestion troubleshooting
- **Complexity**: Moderate
- **Expected**: Routes to Inputs Specialist

### Indexing (`indexing`)
- **Problem**: "There are delays in data indexing and high latency"
- **Focus**: Indexing pipeline optimization
- **Complexity**: High
- **Expected**: Routes to Indexing Specialist

### General (`general`)
- **Problem**: "I'm experiencing various issues with my Splunk environment"
- **Focus**: General system health
- **Complexity**: Moderate
- **Expected**: Routes to General Specialist

## Expected Output

### Successful Test Run

```
================================================================================
STARTING SPLUNK TRIAGE AGENT TEST
================================================================================
Server URL: http://localhost:8000
Test Input: I cant find my data in index=cca_insights
Timeout: 300.0s
Time Range: -24h to now
Focus Index: cca_insights
================================================================================
🚀 Connecting to FastMCP server...
📡 Testing server connection...
✅ Server connection successful
🔍 Listing available tools...
✅ Found triage tool: execute_splunk_missing_data_troubleshooting
🔧 Executing Splunk triage agent...
[5.2s] Progress: 10.0% - Starting Splunk triage analysis
[12.8s] Progress: 40.0% - Agent analysis in progress
[25.1s] Progress: 70.0% - Specialist: Step 3: Checking permissions
[45.6s] Progress: 90.0% - Specialist: Step 8: Analyzing scheduled search issues
[52.3s] Progress: 100.0% - Analysis complete
✅ Tool execution completed in 52.3s
```

### Progress Tracking

```
📊 Progress Summary:
   Total execution time: 52.3s
   Progress updates: 12
   Final progress: 100.0
   Average update interval: 4.4s
   Longest gap between updates: 8.2s
```

### Results Display

```
📋 Structured Results:
   status: success
   workflow_type: triage_system
   routed_to_specialist: Splunk Missing Data Specialist
   troubleshooting_results: [Detailed analysis results...]
   
📄 Content Results:
   Content 1: The official Splunk "I can't find my data!" troubleshooting workflow...
```

## Troubleshooting

### Common Issues

#### 1. Connection Failed
```
❌ Server connection failed: Connection refused
```
**Solution**: Ensure the MCP server is running on the specified port.

#### 2. Tool Not Found
```
❌ Splunk triage tool not found in available tools
```
**Solution**: Verify the `SplunkTriageAgentTool` is registered in the server.

#### 3. Timeout Errors
```
❌ Tool execution timed out after 300.0s
```
**Solution**: Increase timeout or check server performance.

#### 4. No Progress Updates
```
⚠️  No progress updates received - check progress reporting implementation
```
**Solution**: Verify progress reporting is implemented in the agent.

### Debug Mode

Enable debug logging:

```python
# In test_agent.py, change logging level
logging.basicConfig(level=logging.DEBUG)
```

### Server Logs

Check server logs for detailed execution information:

```bash
# If server logging is configured
tail -f logs/server.log
```

## Advanced Usage

### Custom Test Input

```python
# Modify test_agent.py directly
config = TestConfig(
    test_input="Custom problem description",
    focus_index="my_index",
    complexity_level="high"
)
```

### Multiple Server Testing

```bash
# Test against different server instances
MCP_SERVER_URL=http://server1:8000 python run_test.py missing_data
MCP_SERVER_URL=http://server2:8000 python run_test.py performance
```

### Batch Testing

```bash
# Run all scenarios and save results
python run_test.py all > test_results.log 2>&1
```

## Integration with CI/CD

### GitHub Actions Example

```yaml
name: Test Splunk Triage Agent
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: 3.9
      - name: Install dependencies
        run: pip install -r requirements.txt
      - name: Start MCP Server
        run: python src/server.py &
      - name: Run tests
        run: python run_test.py all
        env:
          OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
          SPLUNK_HOST: localhost
          SPLUNK_USERNAME: admin
          SPLUNK_PASSWORD: ${{ secrets.SPLUNK_PASSWORD }}
```

## Performance Benchmarks

### Expected Performance

- **Connection Setup**: < 2 seconds
- **Tool Discovery**: < 1 second
- **Agent Execution**: 30-120 seconds (depending on complexity)
- **Progress Updates**: Every 3-10 seconds
- **Total Test Time**: 1-3 minutes per scenario

### Performance Monitoring

The test scripts automatically track:
- Total execution time
- Progress update frequency
- Connection health
- Timeout detection
- Gap analysis between updates

## Contributing

When adding new test scenarios:

1. Add the scenario to `get_test_scenarios()` in `run_test.py`
2. Include appropriate test input and complexity level
3. Document expected behavior and routing
4. Test with various timeout configurations
5. Verify progress reporting works correctly

## Support

For issues with the test scripts:
1. Check server logs for errors
2. Verify environment variables are set
3. Ensure OpenAI API key is valid
4. Test with simple scenarios first
5. Enable debug logging for detailed information 