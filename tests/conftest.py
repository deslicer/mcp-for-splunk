"""
Pytest configuration and shared fixtures for MCP Server for Splunk tests
"""

import pytest
import asyncio
import json
from typing import Dict, Any, Optional
from fastmcp import Client


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
def mcp_urls():
    """URLs for MCP server connections"""
    return {
        "traefik": "http://localhost:8001/mcp/",
        "direct": "http://localhost:8002/mcp/"
    }


@pytest.fixture
async def traefik_client(mcp_urls):
    """Async fixture for Traefik-proxied MCP client"""
    async with Client(mcp_urls["traefik"]) as client:
        yield client


@pytest.fixture
async def direct_client(mcp_urls):
    """Async fixture for direct MCP client"""
    async with Client(mcp_urls["direct"]) as client:
        yield client


@pytest.fixture
def extract_tool_result():
    """Helper function to extract tool results from FastMCP response format"""
    def _extract(result) -> Dict[str, Any]:
        if isinstance(result, list) and len(result) > 0:
            content = result[0]
            if hasattr(content, 'text'):
                try:
                    return json.loads(content.text)
                except json.JSONDecodeError:
                    return {"raw_text": content.text}
        return result
    return _extract


@pytest.fixture(scope="session")
def splunk_test_query():
    """Standard test query for Splunk searches"""
    return {
        "query": "index=_internal | head 5",
        "earliest_time": "-1h",
        "max_results": 5
    }


class MCPTestHelpers:
    """Helper class for common MCP test operations"""
    
    @staticmethod
    async def check_connection_health(client):
        """Check basic connection health"""
        ping_result = await client.ping()
        tools = await client.list_tools()
        resources = await client.list_resources()
        
        return {
            "ping": ping_result,
            "tools_count": len(tools),
            "tools": [tool.name for tool in tools],
            "resources_count": len(resources),
            "resources": [resource.uri for resource in resources]
        }


@pytest.fixture
def mcp_helpers():
    """Fixture providing MCP test helper methods"""
    return MCPTestHelpers() 