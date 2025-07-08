# OpenAI Agent Integration Guide

This guide explains how to use the OpenAI Agent tool for intelligent Splunk troubleshooting within the MCP Server for Splunk.

## Overview

The OpenAI Agent tool integrates OpenAI's language models with the existing MCP tools and troubleshooting prompts to provide intelligent analysis and recommendations for Splunk issues. The agent can:

- Execute specialized troubleshooting workflows
- Access all available MCP tools and resources
- Provide contextual analysis based on dynamic prompts
- Update progress through FastMCP context
- Handle errors gracefully with detailed reporting

## Architecture

### Components

1. **OpenAI Agent Tool** (`src/tools/agents/openai_agent.py`)
   - Main tool implementation
   - Handles OpenAI API integration
   - Manages prompt retrieval and tool discovery

2. **Configuration Management**
   - Environment-based configuration
   - Support for custom models and parameters
   - Secure API key handling

3. **Prompt Integration**
   - Dynamic prompt selection based on type and component
   - Integration with existing troubleshooting prompts
   - Fallback prompt handling

4. **Tool Discovery**
   - Automatic discovery of available MCP tools
   - Dynamic function schema generation
   - Self-exclusion to prevent recursion

## Setup and Configuration

### Prerequisites

1. **OpenAI API Access**
   - Valid OpenAI API key
   - Sufficient API credits
   - Network connectivity to OpenAI services

2. **Splunk MCP Server**
   - Configured Splunk connection
   - Running MCP server instance
   - Access to troubleshooting prompts

### Environment Variables

Add the following variables to your `.env` file:

```bash
# OpenAI Agent Settings
OPENAI_API_KEY=your_openai_api_key_here
OPENAI_MODEL=gpt-4o
OPENAI_TEMPERATURE=0.7
OPENAI_MAX_TOKENS=4000
```

### Installation

The OpenAI dependency is automatically included in the project:

```bash
uv add openai
```

## Usage

### Basic Usage

The OpenAI Agent tool can be called through the MCP protocol:

```json
{
  "method": "tools/call",
  "params": {
    "name": "execute_openai_agent",
    "arguments": {
      "agent_type": "troubleshooting",
      "component": "performance"
    }
  }
}
```

### Available Parameters

#### Required Parameters

- `agent_type` (string): Type of agent to execute
  - Default: `"troubleshooting"`
  - Available: `["troubleshooting"]`

- `component` (string): Component to focus analysis on
  - Default: `"performance"`
  - Available: `["performance", "inputs", "indexing", "inputs_multi"]`

#### Optional Parameters

All troubleshooting prompt parameters are supported:

- `earliest_time` (string): Start time for analysis (e.g., "-24h", "-7d")
- `latest_time` (string): End time for analysis (e.g., "now", "-1h")
- `focus_index` (string): Specific index to analyze
- `focus_host` (string): Specific host to analyze
- Additional prompt-specific parameters

### Agent Types and Components

#### Troubleshooting Agent

**Performance Component**
- System resource utilization analysis
- Processing efficiency evaluation
- Capacity planning recommendations
- Throughput optimization suggestions

**Inputs Component**
- Data input troubleshooting
- Ingestion pipeline analysis
- Input source validation
- Connection diagnostics

**Indexing Component**
- Indexing performance analysis
- Delay pattern identification
- Resource correlation
- Pipeline optimization

**Inputs Multi Component**
- Advanced multi-agent analysis
- Parallel execution workflows
- Cross-validation of findings
- Comprehensive validation protocols

## Examples

### Performance Troubleshooting

```json
{
  "method": "tools/call",
  "params": {
    "name": "execute_openai_agent",
    "arguments": {
      "agent_type": "troubleshooting",
      "component": "performance",
      "earliest_time": "-24h",
      "latest_time": "now"
    }
  }
}
```

### Input Analysis with Focus

```json
{
  "method": "tools/call",
  "params": {
    "name": "execute_openai_agent",
    "arguments": {
      "agent_type": "troubleshooting",
      "component": "inputs",
      "earliest_time": "-7d",
      "latest_time": "now",
      "focus_index": "main",
      "focus_host": "splunk-forwarder-01"
    }
  }
}
```

### Indexing Performance Deep Dive

```json
{
  "method": "tools/call",
  "params": {
    "name": "execute_openai_agent",
    "arguments": {
      "agent_type": "troubleshooting",
      "component": "indexing",
      "earliest_time": "-4h",
      "latest_time": "now",
      "analysis_depth": "comprehensive",
      "include_delay_analysis": true
    }
  }
}
```

## Response Format

### Success Response

```json
{
  "status": "success",
  "agent_type": "troubleshooting",
  "component": "performance",
  "analysis": "Detailed analysis and recommendations from the AI agent...",
  "tools_available": 25,
  "prompt_used": "Truncated prompt content for reference..."
}
```

### Error Response

```json
{
  "status": "error",
  "error": "Error description",
  "error_type": "validation_error|execution_error"
}
```

## Integration with Existing Tools

### Prompt System Integration

The agent automatically integrates with the existing prompt system:

1. **Dynamic Prompt Retrieval**: Selects appropriate prompts based on agent type and component
2. **Parameter Forwarding**: Passes all additional parameters to the prompt system
3. **Fallback Handling**: Uses basic prompts when specific prompts are unavailable

### Tool Discovery

The agent discovers and can utilize all available MCP tools:

1. **Registry Integration**: Queries the tool registry for available tools
2. **Schema Generation**: Creates OpenAI-compatible function schemas
3. **Self-Exclusion**: Prevents recursive calls to the agent tool itself

### Context Management

Progress updates are provided through FastMCP context:

```python
await ctx.info("Initializing OpenAI agent...")
await ctx.info("Retrieving troubleshooting prompt...")
await ctx.info("Discovering available tools...")
await ctx.info("Executing agent workflow...")
await ctx.info("Agent execution completed successfully")
```

## Development and Testing

### Running Tests

```bash
# Run OpenAI agent tests
python -m pytest tests/test_openai_agent.py -v

# Run integration tests
python -m pytest tests/test_openai_agent.py tests/test_splunk_tools.py -v
```

### Demo Script

```bash
# Run the demonstration script
python examples/openai_agent_demo.py
```

### Mock Testing

Tests use comprehensive mocking to avoid API costs:

```python
@pytest.fixture
def mock_openai_client():
    """Mock OpenAI client for testing."""
    with patch("src.tools.agents.openai_agent.OpenAI") as mock_openai:
        mock_client = Mock()
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = "Test response"
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai.return_value = mock_client
        yield mock_client
```

## Best Practices

### API Usage

1. **Cost Management**: Monitor OpenAI API usage and costs
2. **Rate Limiting**: Implement appropriate rate limiting for production use
3. **Error Handling**: Always handle API errors gracefully
4. **Token Management**: Monitor token usage and optimize prompts

### Security

1. **API Key Security**: Store API keys securely, never in code
2. **Input Validation**: Validate all user inputs before processing
3. **Output Sanitization**: Review agent outputs for sensitive information
4. **Access Control**: Implement appropriate access controls for agent usage

### Performance

1. **Prompt Optimization**: Keep prompts concise but comprehensive
2. **Tool Selection**: Limit tool availability to relevant tools when possible
3. **Caching**: Consider caching frequently used prompts and tool schemas
4. **Async Operations**: Use async/await for all I/O operations

## Troubleshooting

### Common Issues

**API Key Not Set**
```
ValueError: OPENAI_API_KEY environment variable is required
```
Solution: Set the `OPENAI_API_KEY` environment variable

**Invalid Agent Type**
```
Unknown agent type 'invalid_type'. Available types: ['troubleshooting']
```
Solution: Use a valid agent type from the available options

**Invalid Component**
```
Unknown component 'invalid_component' for type 'troubleshooting'
```
Solution: Use a valid component for the specified agent type

**OpenAI API Error**
```
Agent execution failed: OpenAI API error
```
Solution: Check API key validity, network connectivity, and API status

### Debugging

Enable debug logging to troubleshoot issues:

```python
import logging
logging.getLogger("src.tools.agents.openai_agent").setLevel(logging.DEBUG)
```

### Performance Monitoring

Monitor agent performance:

1. **Execution Time**: Track how long agents take to complete
2. **Token Usage**: Monitor OpenAI token consumption
3. **Success Rate**: Track successful vs. failed executions
4. **Tool Usage**: Monitor which tools are being used most frequently

## Future Enhancements

### Planned Features

1. **Multi-Model Support**: Support for different OpenAI models and other providers
2. **Streaming Responses**: Real-time streaming of agent responses
3. **Tool Execution**: Direct execution of MCP tools by the agent
4. **Result Caching**: Caching of agent results for similar queries
5. **Custom Agents**: Support for user-defined agent types and workflows

### Extension Points

1. **Custom Prompts**: Add new prompt types and components
2. **Tool Filters**: Implement filters to control tool availability
3. **Response Processors**: Add post-processing of agent responses
4. **Integration Hooks**: Add hooks for external system integration

## Support and Resources

- **Documentation**: See `docs/` directory for additional guides
- **Examples**: Check `examples/` directory for usage examples  
- **Tests**: Review `tests/test_openai_agent.py` for implementation details
- **Issues**: Report issues on the project repository
- **Community**: Join discussions in the project community channels 