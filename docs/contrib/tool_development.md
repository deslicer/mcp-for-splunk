# Tool Development Guide

This guide provides detailed information for developing custom tools in the MCP Server for Splunk modular architecture.

## Overview

The modular architecture enables easy creation of custom tools that integrate seamlessly with the MCP server. Tools are automatically discovered and loaded, making development straightforward and deployment automatic.

## Tool Architecture

### Base Classes

All tools inherit from `BaseTool` which provides:
- **Consistent Error Handling** - Standardized error responses
- **Context Management** - Access to MCP context and Splunk connections
- **Logging Integration** - Built-in logging with context
- **Response Formatting** - Standardized success/error response formats
- **Validation Framework** - Parameter and response validation

### Tool Metadata

Every tool must include a `METADATA` class attribute that describes the tool:

```python
from src.core.base import ToolMetadata

METADATA = ToolMetadata(
    name="your_tool_name",           # Tool identifier (snake_case)
    description="Tool description",   # Brief description for users
    category="security",             # Category (security, devops, analytics, examples)
    tags=["security", "search"],     # Searchable tags
    requires_connection=True,        # Whether tool needs Splunk connection
    version="1.0.0"                 # Tool version (optional)
)
```

## Creating a New Tool

### Step 1: Choose Tool Location

Tools should be placed in the appropriate directory based on their purpose:

```
contrib/tools/
├── examples/     # Learning examples and templates
├── security/     # Security analysis, threat hunting, incident response
├── devops/       # Monitoring, alerting, operational tasks
└── analytics/    # Business intelligence, reporting, dashboards
```

### Step 2: Tool Class Structure

```python
from typing import Any, Dict, Optional
from fastmcp import Context
from src.core.base import BaseTool, ToolMetadata

class YourToolName(BaseTool):
    """Brief description of what your tool does."""

    METADATA = ToolMetadata(
        name="your_tool_name",
        description="Detailed description for users",
        category="security",  # or devops, analytics, examples
        tags=["relevant", "tags"],
        requires_connection=True  # Set to False if no Splunk connection needed
    )

    async def execute(self, ctx: Context, **kwargs) -> Dict[str, Any]:
        """
        Main tool execution method.

        Args:
            ctx: MCP context with connection info
            **kwargs: Tool-specific parameters

        Returns:
            Dict with tool results or error information
        """
        try:
            # Your tool logic here
            result = await self._perform_operation(kwargs)
            return self.format_success_response(result)

        except Exception as e:
            return self.format_error_response(f"Tool execution failed: {str(e)}")

    async def _perform_operation(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Private method for tool-specific logic."""
        # Implement your tool's core functionality
        return {"status": "completed", "data": []}
```

### Step 3: Implement Tool Logic

#### Accessing Splunk Connection

```python
async def execute(self, ctx: Context, query: str) -> Dict[str, Any]:
    """Execute a Splunk search operation."""
    try:
        # Get Splunk service from context
        service = await self.get_splunk_service(ctx)

        # Perform search
        search_kwargs = {
            'search': f"search {query}",
            'earliest_time': '-24h',
            'latest_time': 'now'
        }

        job = service.jobs.oneshot(**search_kwargs)
        results = []

        for result in job:
            results.append(dict(result))

        return self.format_success_response({
            "query": query,
            "results": results,
            "count": len(results)
        })

    except Exception as e:
        return self.format_error_response(f"Search failed: {str(e)}")
```

#### Parameter Validation

```python
async def execute(self, ctx: Context, query: str, timerange: str = "-24h") -> Dict[str, Any]:
    """Execute threat hunting search with validation."""

    # Validate required parameters
    if not query or not query.strip():
        return self.format_error_response("Query parameter is required")

    # Validate timerange format
    valid_timeranges = ["-1h", "-24h", "-7d", "-30d"]
    if timerange not in valid_timeranges:
        return self.format_error_response(
            f"Invalid timerange. Must be one of: {', '.join(valid_timeranges)}"
        )

    # Continue with execution...
```

#### Error Handling Best Practices

```python
async def execute(self, ctx: Context, **kwargs) -> Dict[str, Any]:
    """Tool with comprehensive error handling."""
    try:
        # Validate parameters first
        validation_result = self._validate_parameters(kwargs)
        if not validation_result["valid"]:
            return self.format_error_response(validation_result["error"])

        # Perform operation with specific exception handling
        result = await self._safe_operation(kwargs)
        return self.format_success_response(result)

    except ConnectionError as e:
        return self.format_error_response(f"Splunk connection failed: {str(e)}")
    except ValueError as e:
        return self.format_error_response(f"Invalid parameter: {str(e)}")
    except Exception as e:
        # Log unexpected errors for debugging
        self.logger.error(f"Unexpected error in {self.METADATA.name}: {str(e)}")
        return self.format_error_response("An unexpected error occurred")

def _validate_parameters(self, params: Dict[str, Any]) -> Dict[str, Any]:
    """Validate input parameters."""
    # Implement validation logic
    return {"valid": True, "error": None}
```

## Advanced Patterns

### Complex Search Operations

```python
async def _execute_complex_search(self, ctx: Context, search_query: str) -> Dict[str, Any]:
    """Execute a complex search with job monitoring."""
    service = await self.get_splunk_service(ctx)

    # Create search job
    job = service.jobs.create(search_query, **{
        'earliest_time': '-24h',
        'latest_time': 'now'
    })

    # Monitor job progress
    while not job.is_done():
        await asyncio.sleep(1)
        job.refresh()

        # Optional: provide progress updates
        progress = {
            "progress": float(job["doneProgress"]) * 100,
            "scanned": int(job["scanCount"]),
            "matched": int(job["eventCount"])
        }

        # You could emit progress events here

    # Get results
    results = []
    for result in job.results():
        results.append(dict(result))

    return {
        "results": results,
        "job_id": job.sid,
        "statistics": {
            "scan_count": int(job["scanCount"]),
            "event_count": int(job["eventCount"]),
            "run_duration": float(job["runDuration"])
        }
    }
```

### Configuration-Driven Tools

```python
class ConfigurableAnalyticsTool(BaseTool):
    """Tool that uses configuration for flexible behavior."""

    METADATA = ToolMetadata(
        name="configurable_analytics",
        description="Analytics tool with configurable queries",
        category="analytics",
        tags=["analytics", "configurable"]
    )

    def __init__(self):
        super().__init__()
        self.queries = {
            "performance": "index=_internal | stats avg(cpu_usage) by host",
            "errors": "index=main error | stats count by source",
            "usage": "index=_audit | stats count by user"
        }

    async def execute(self, ctx: Context, analysis_type: str) -> Dict[str, Any]:
        """Execute configurable analytics."""

        if analysis_type not in self.queries:
            available = ", ".join(self.queries.keys())
            return self.format_error_response(
                f"Unknown analysis type. Available: {available}"
            )

        query = self.queries[analysis_type]
        result = await self._execute_search(ctx, query)

        return self.format_success_response({
            "analysis_type": analysis_type,
            "query": query,
            "results": result
        })
```

### Resource Management

```python
async def execute(self, ctx: Context, large_query: str) -> Dict[str, Any]:
    """Tool that manages resources carefully."""

    # Limit result size
    MAX_RESULTS = 10000

    search_query = f"{large_query} | head {MAX_RESULTS}"

    try:
        service = await self.get_splunk_service(ctx)

        # Use streaming for large results
        job = service.jobs.create(search_query)

        results = []
        result_count = 0

        # Stream results to manage memory
        for result in job.results():
            if result_count >= MAX_RESULTS:
                break

            results.append(dict(result))
            result_count += 1

            # Optional: yield control periodically
            if result_count % 1000 == 0:
                await asyncio.sleep(0)  # Yield to event loop

        return self.format_success_response({
            "results": results,
            "count": result_count,
            "limited": result_count >= MAX_RESULTS
        })

    except Exception as e:
        return self.format_error_response(f"Query execution failed: {str(e)}")
```

## Testing Your Tools

### Test Structure

Create comprehensive tests for your tools in `tests/contrib/`:

```python
# tests/contrib/security/test_threat_hunting.py

import pytest
from unittest.mock import Mock, AsyncMock
from contrib.tools.security.threat_hunting import ThreatHuntingTool

class TestThreatHuntingTool:
    """Test suite for ThreatHuntingTool."""

    @pytest.fixture
    def tool(self):
        """Create tool instance for testing."""
        return ThreatHuntingTool()

    @pytest.fixture
    def mock_context(self):
        """Create mock MCP context."""
        ctx = Mock()
        ctx.session = Mock()
        return ctx

    @pytest.mark.asyncio
    async def test_successful_execution(self, tool, mock_context):
        """Test successful threat hunting execution."""

        # Mock Splunk service and results
        mock_service = Mock()
        mock_job = Mock()
        mock_job.__iter__ = Mock(return_value=iter([
            {"_time": "2024-01-01", "threat": "malware", "_raw": "threat data"}
        ]))
        mock_service.jobs.oneshot.return_value = mock_job

        # Mock the get_splunk_service method
        tool.get_splunk_service = AsyncMock(return_value=mock_service)

        # Execute tool
        result = await tool.execute(mock_context, query="threat analysis")

        # Assertions
        assert result["success"] is True
        assert "threats" in result["data"]
        assert len(result["data"]["threats"]) == 1

    @pytest.mark.asyncio
    async def test_empty_query_error(self, tool, mock_context):
        """Test error handling for empty query."""

        result = await tool.execute(mock_context, query="")

        assert result["success"] is False
        assert "required" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_connection_error(self, tool, mock_context):
        """Test handling of Splunk connection errors."""

        # Mock connection failure
        tool.get_splunk_service = AsyncMock(side_effect=ConnectionError("Connection failed"))

        result = await tool.execute(mock_context, query="test query")

        assert result["success"] is False
        assert "connection" in result["error"].lower()
```

### Mock Patterns

For tools that interact with Splunk, use these common mock patterns:

```python
@pytest.fixture
def mock_splunk_service():
    """Mock Splunk service with common responses."""
    service = Mock()

    # Mock search results
    mock_results = [
        {"_time": "2024-01-01", "field1": "value1"},
        {"_time": "2024-01-01", "field2": "value2"}
    ]

    # Mock oneshot search
    service.jobs.oneshot.return_value = iter(mock_results)

    # Mock job creation
    mock_job = Mock()
    mock_job.sid = "test_job_123"
    mock_job.is_done.return_value = True
    mock_job.results.return_value = iter(mock_results)
    service.jobs.create.return_value = mock_job

    return service
```

## Tool Discovery and Loading

### Automatic Discovery

Tools are automatically discovered if they:
1. Are located in `contrib/tools/` or `src/tools/` directories
2. Inherit from `BaseTool`
3. Have a `METADATA` class attribute
4. Are in a `.py` file (not `__init__.py`)

### Registration Process

The discovery process:
1. **Scans directories** recursively for Python files
2. **Imports modules** and inspects for BaseTool subclasses
3. **Validates metadata** and tool structure
4. **Registers tools** with the MCP server
5. **Makes available** for client requests

### Debugging Discovery

If your tool isn't being discovered:

```python
# Add this to test tool discovery
from src.core.discovery import discover_tools

# Run discovery manually
tools = discover_tools()
for tool_class in tools:
    print(f"Discovered: {tool_class.METADATA.name}")
```

## Best Practices

### Performance
- **Limit result sizes** for large queries
- **Use streaming** for memory efficiency
- **Cache connections** when appropriate
- **Implement timeouts** for long operations

### Security
- **Validate all inputs** before processing
- **Sanitize queries** to prevent injection
- **Handle credentials** securely
- **Log security events** appropriately

### Maintainability
- **Use descriptive names** for tools and methods
- **Document complex logic** with comments
- **Follow consistent patterns** across tools
- **Keep tools focused** on single responsibilities

### Error Handling
- **Provide specific error messages** for debugging
- **Log errors** with appropriate levels
- **Handle expected exceptions** gracefully
- **Use consistent error response formats**

## Tool Categories

### Security Tools
Focus on threat detection, incident response, and security analysis:
- Threat hunting queries
- IOC searches
- Security event correlation
- Incident investigation tools

### DevOps Tools
Operational monitoring and automation:
- System health checks
- Performance monitoring
- Alert management
- Capacity planning

### Analytics Tools
Business intelligence and reporting:
- KPI dashboards
- Trend analysis
- Custom reporting
- Data visualization support

### Example Tools
Learning templates and patterns:
- Simple operation examples
- Best practice demonstrations
- Testing patterns
- Common use cases

This comprehensive guide should help you create robust, maintainable tools that integrate seamlessly with the MCP Server for Splunk modular architecture.
