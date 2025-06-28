"""
Test configuration and fixtures for MCP Server for Splunk tests.
"""
import json
import os
import sys
from typing import Any
from unittest.mock import AsyncMock, Mock, patch

import pytest

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

# Import FastMCP for proper testing
try:
    from fastmcp import Client, Context
    from fastmcp.server.context import set_context
except ImportError:
    # Create fallback if FastMCP not available
    Context = None
    Client = None

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
            "host": "so1"
        }

        # Mock jobs for search operations
        self.jobs = Mock()

        # Mock job creation and oneshot
        mock_job = Mock()
        mock_job.sid = "test_job_123"
        mock_job.is_done.return_value = True
        mock_job.content = {
            "scanCount": "100",
            "eventCount": "10",
            "isDone": "1",
            "isFinalized": "1",
            "isFailed": "0",
            "doneProgress": "1.0"
        }

        # Mock job results
        def mock_results():
            return [
                {"_time": "2024-01-01T00:00:00", "source": "/var/log/system.log", "log_level": "INFO"},
                {"_time": "2024-01-01T00:01:00", "source": "/var/log/app.log", "log_level": "ERROR"}
            ]

        mock_job.results.return_value = mock_results()

        self.jobs.oneshot.return_value = mock_results()
        self.jobs.create.return_value = mock_job

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

class MockFastMCPContext:
    """Mock FastMCP Context that matches the actual Context interface"""

    def __init__(self, service=None, is_connected=True):
        self.request_context = Mock()
        self.request_context.lifespan_context = Mock()
        self.request_context.lifespan_context.service = service or MockSplunkService()
        self.request_context.lifespan_context.is_connected = is_connected

        # Mock Context methods
        self.info = AsyncMock()
        self.debug = AsyncMock()
        self.warning = AsyncMock()
        self.error = AsyncMock()
        self.report_progress = AsyncMock()
        self.read_resource = AsyncMock()
        self.sample = AsyncMock()

        # Mock Context properties
        self.request_id = "test-request-123"
        self.client_id = "test-client-456"
        self.session_id = "test-session-789"

class MockResultsReader:
    """Mock for splunklib.results.ResultsReader"""

    def __init__(self, results):
        self.results = results

    def __iter__(self):
        return iter(self.results)

class MCPTestHelpers:
    """Helper functions for MCP testing using FastMCP patterns"""

    async def check_connection_health(self, client) -> dict[str, Any]:
        """Check MCP connection health and return status"""
        try:
            # Test basic connectivity by listing tools and resources
            tools = await client.list_tools()
            resources = await client.list_resources()

            # Test a simple tool call
            health_result = await client.call_tool("get_splunk_health")

            return {
                "ping": True,
                "tools_count": len(tools),
                "resources_count": len(resources),
                "tools": [tool.name for tool in tools],
                "resources": [resource.uri for resource in resources],
                "health_check": health_result
            }
        except Exception as e:
            return {
                "ping": False,
                "error": str(e),
                "tools_count": 0,
                "resources_count": 0,
                "tools": [],
                "resources": []
            }

@pytest.fixture
async def fastmcp_client():
    """Create FastMCP client for in-memory testing"""
    if Client is None:
        pytest.skip("FastMCP not available")

    # Import the actual server
    from src.server import mcp

    # Use FastMCP's in-memory transport for testing
    client = Client(mcp)
    yield client
    # Client cleanup is handled automatically

@pytest.fixture
def mcp_helpers():
    """Create MCP test helpers"""
    return MCPTestHelpers()

@pytest.fixture
def extract_tool_result():
    """Helper function to extract results from MCP tool calls"""
    def _extract(result):
        """Extract data from MCP tool call result"""
        if isinstance(result, dict):
            return result
        elif isinstance(result, list) and len(result) > 0:
            first_item = result[0]
            if hasattr(first_item, 'text'):
                try:
                    # Try to parse as JSON
                    return json.loads(first_item.text)
                except (json.JSONDecodeError, AttributeError):
                    # Return as raw text if not JSON
                    return {"raw_text": first_item.text}
            elif isinstance(first_item, dict):
                return first_item
            else:
                return {"raw_data": first_item}
        else:
            return {"empty_result": True}

    return _extract

@pytest.fixture
def splunk_test_query():
    """Sample Splunk query for testing"""
    return {
        "query": "index=_internal | head 5",
        "earliest_time": "-15m",
        "latest_time": "now",
        "max_results": 5
    }

@pytest.fixture
def mock_splunk_service():
    """Create a mock Splunk service for testing"""
    return MockSplunkService()

@pytest.fixture
def mock_context(mock_splunk_service):
    """Create a mock FastMCP Context with Splunk service"""
    return MockFastMCPContext(service=mock_splunk_service, is_connected=True)

@pytest.fixture
def mock_disconnected_context():
    """Create a mock FastMCP Context with disconnected Splunk service"""
    return MockFastMCPContext(service=None, is_connected=False)

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

# Legacy fixtures for backward compatibility (will be removed eventually)
@pytest.fixture
async def traefik_client():
    """Legacy fixture - use fastmcp_client instead"""
    pytest.skip("Use fastmcp_client fixture for proper FastMCP testing")

@pytest.fixture
async def direct_client():
    """Legacy fixture - use fastmcp_client instead"""
    pytest.skip("Use fastmcp_client fixture for proper FastMCP testing")

# Async test configuration for pytest-asyncio
pytest_plugins = ['pytest_asyncio']
