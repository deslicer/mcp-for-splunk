"""
Test configuration and fixtures for MCP Server for Splunk tests.
"""
import pytest
import os
import sys
from unittest.mock import Mock, MagicMock, patch
from typing import Dict, Any, List

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

# Mock classes that match the actual structure
class MockSplunkService:
    """Mock Splunk service that mimics splunklib.client.Service"""
    
    def __init__(self):
        # Mock indexes
        self.indexes = [
            Mock(name="_internal"),
            Mock(name="main"),
            Mock(name="security"),
            Mock(name="test")
        ]
        for idx in self.indexes:
            idx.name = idx._mock_name
        
        # Mock info
        self.info = {
            "version": "9.0.0",
            "host": "localhost"
        }
        
        # Mock jobs for search operations
        self.jobs = Mock()
        
        # Mock apps
        self.apps = [
            Mock(name="search"),
            Mock(name="splunk_monitoring_console"),
            Mock(name="learned")
        ]
        for app in self.apps:
            app.name = app._mock_name
            app.content = {"version": "1.0", "visible": True}
        
        # Mock users
        self.users = [
            Mock(name="admin"),
            Mock(name="splunk-system-user")
        ]
        for user in self.users:
            user.name = user._mock_name
            user.content = {
                "roles": ["admin"], 
                "email": "admin@example.com",
                "realname": user._mock_name,
                "type": "Splunk",
                "defaultApp": "search"
            }
        
        # Mock KV Store
        self.kvstore = {}
        
        # Mock configurations
        self.confs = {}

class MockJob:
    """Mock search job object"""
    
    def __init__(self, is_done=True, results=None):
        self._is_done = is_done
        self._results = results or []
        self.content = {
            "scanCount": len(self._results),
            "eventCount": len(self._results),
            "duration": 0.123
        }
    
    def is_done(self):
        return self._is_done
    
    def __iter__(self):
        return iter(self._results)

class MockSplunkContext:
    """Mock Context that matches FastMCP Context structure"""
    
    def __init__(self, service=None):
        self.request_context = Mock()
        self.request_context.lifespan_context = Mock()
        self.request_context.lifespan_context.service = service or MockSplunkService()

class MockResultsReader:
    """Mock for splunklib.results.ResultsReader"""
    
    def __init__(self, results):
        self.results = results
    
    def __iter__(self):
        return iter(self.results)

@pytest.fixture
def mock_splunk_service():
    """Create a mock Splunk service for testing"""
    return MockSplunkService()

@pytest.fixture
def mock_context(mock_splunk_service):
    """Create a mock FastMCP Context with Splunk service"""
    return MockSplunkContext(service=mock_splunk_service)

@pytest.fixture
def mock_search_results():
    """Sample search results for testing"""
    return [
        {"_time": "2024-01-01T00:00:00", "source": "/var/log/system.log", "log_level": "INFO"},
        {"_time": "2024-01-01T00:01:00", "source": "/var/log/app.log", "log_level": "ERROR"},
        {"_time": "2024-01-01T00:02:00", "source": "/var/log/system.log", "log_level": "WARN"}
    ]

@pytest.fixture
def mock_oneshot_job(mock_search_results):
    """Create a mock oneshot job"""
    job = Mock()
    job.__iter__ = lambda: iter(mock_search_results)
    return job

@pytest.fixture
def mock_regular_job(mock_search_results):
    """Create a mock regular search job"""
    return MockJob(is_done=True, results=mock_search_results)

@pytest.fixture
def sample_env_vars():
    """Sample environment variables for testing"""
    return {
        "SPLUNK_HOST": "localhost",
        "SPLUNK_PORT": "8089",
        "SPLUNK_USERNAME": "admin",
        "SPLUNK_PASSWORD": "password",
        "SPLUNK_VERIFY_SSL": "false"
    }

@pytest.fixture
def mock_kvstore_collection_data():
    """Sample KV Store collection data"""
    return [
        {"_key": "1", "username": "admin", "role": "admin", "active": True},
        {"_key": "2", "username": "user1", "role": "user", "active": True},
        {"_key": "3", "username": "user2", "role": "user", "active": False}
    ]

@pytest.fixture(autouse=True)
def setup_test_environment(sample_env_vars):
    """Set up test environment variables"""
    with patch.dict(os.environ, sample_env_vars):
        yield

@pytest.fixture
def mock_results_reader():
    """Mock for ResultsReader"""
    return MockResultsReader

# Async test configuration for pytest-asyncio
pytest_plugins = ['pytest_asyncio'] """
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