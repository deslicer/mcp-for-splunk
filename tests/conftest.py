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
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

# Import FastMCP for proper testing
try:
    from fastmcp import Client, Context
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
            Mock(name="test"),
        ]
        for idx in self.indexes:
            idx.name = idx._mock_name

        # Mock info
        self.info = {"version": "9.0.0", "host": "so1"}

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
            "doneProgress": "1.0",
        }

        # Mock job results
        def mock_results():
            return [
                {
                    "_time": "2024-01-01T00:00:00",
                    "source": "/var/log/system.log",
                    "log_level": "INFO",
                },
                {
                    "_time": "2024-01-01T00:01:00",
                    "source": "/var/log/app.log",
                    "log_level": "ERROR",
                },
            ]

        mock_job.results.return_value = mock_results()

        self.jobs.oneshot.return_value = mock_results()
        self.jobs.create.return_value = mock_job

        # Mock apps
        self.apps = [
            Mock(name="search"),
            Mock(name="splunk_monitoring_console"),
            Mock(name="learned"),
        ]
        for app in self.apps:
            app.name = app._mock_name
            app.content = {"version": "1.0", "visible": True}

        # Mock users
        self.users = [Mock(name="admin"), Mock(name="splunk-system-user")]
        for user in self.users:
            user.name = user._mock_name
            user.content = {
                "roles": ["admin"],
                "email": "admin@example.com",
                "realname": user._mock_name,
                "type": "Splunk",
                "defaultApp": "search",
            }

        # Mock KV Store
        self.kvstore = {}

        # Mock configurations
        self.confs = {}

        # Mock configuration files with stanzas
        self._setup_mock_configurations()

        # In-memory dashboards store
        self._dashboards: dict[str, dict] = {}

    def post(self, endpoint: str, **kwargs):
        """Mock POST handler for Splunk REST endpoints used by dashboard tools."""
        # Basic response mock
        mock_response = Mock()

        # Create dashboard
        if endpoint.endswith("/data/ui/views") and "name" in kwargs:
            name = kwargs.get("name")
            # Simulate conflict for overwrite path testing
            if name == "exists_dashboard":
                raise RuntimeError("409 Conflict: Dashboard already exists")

            label = kwargs.get("label") or name
            description = kwargs.get("description") or ""
            eai_data = kwargs.get("eai:data") or ""
            owner = "nobody"
            app = "search"

            entry = {
                "name": name,
                "id": f"https://localhost:8089/servicesNS/{owner}/{app}/data/ui/views/{name}",
                "content": {
                    "label": label,
                    "description": description,
                    "eai:data": eai_data,
                    "version": "1.0",
                },
                "acl": {
                    "app": app,
                    "owner": owner,
                    "sharing": "global",
                    "perms": {"read": ["*"], "write": ["admin"]},
                },
            }

            self._dashboards[name] = entry
            payload = {"entry": [entry]}
            mock_response.body.read.return_value = json.dumps(payload).encode("utf-8")
            return mock_response

        # Update dashboard (overwrite)
        if "/data/ui/views/" in endpoint and not endpoint.endswith("/acl"):
            # Endpoint like /servicesNS/owner/app/data/ui/views/{name}
            name = endpoint.split("/data/ui/views/")[-1]
            existing = self._dashboards.get(name)

            label = kwargs.get("label") or (existing or {}).get("content", {}).get("label", name)
            description = kwargs.get("description") or (existing or {}).get("content", {}).get(
                "description", ""
            )
            eai_data = kwargs.get("eai:data") or (existing or {}).get("content", {}).get(
                "eai:data", ""
            )

            if existing:
                existing["content"]["label"] = label
                existing["content"]["description"] = description
                existing["content"]["eai:data"] = eai_data
                entry = existing
            else:
                entry = {
                    "name": name,
                    "id": endpoint.replace("http://", "https://"),
                    "content": {
                        "label": label,
                        "description": description,
                        "eai:data": eai_data,
                        "version": "1.0",
                    },
                    "acl": {
                        "app": "search",
                        "owner": "nobody",
                        "sharing": "global",
                        "perms": {"read": ["*"], "write": ["admin"]},
                    },
                }
                self._dashboards[name] = entry

            payload = {"entry": [entry]}
            mock_response.body.read.return_value = json.dumps(payload).encode("utf-8")
            return mock_response

        # ACL update
        if endpoint.endswith("/acl"):
            # Extract dashboard name
            parts = endpoint.split("/data/ui/views/")[-1].split("/")
            name = parts[0]
            entry = self._dashboards.get(name)
            if entry:
                sharing = kwargs.get("sharing")
                read_perms = kwargs.get("perms.read")
                write_perms = kwargs.get("perms.write")
                if sharing:
                    entry["acl"]["sharing"] = sharing
                if read_perms:
                    entry["acl"]["perms"]["read"] = read_perms.split(",")
                if write_perms:
                    entry["acl"]["perms"]["write"] = write_perms.split(",")
            mock_response.body.read.return_value = json.dumps({"success": True}).encode("utf-8")
            return mock_response

        # Default empty response
        mock_response.body.read.return_value = json.dumps({}).encode("utf-8")
        return mock_response

    def _setup_mock_configurations(self):
        """Set up mock configuration files with stanzas"""
        # Mock configuration stanzas for different conf files
        mock_configs = {
            "props": {
                "default": {"SHOULD_LINEMERGE": "true", "BREAK_ONLY_BEFORE_DATE": "true"},
                "source::/var/log/messages": {"sourcetype": "linux_messages_syslog"},
                "splunk_web_access": {"EXTRACT-status": r"(?i)\s(?P<status>\d+)\s"},
            },
            "transforms": {
                "force_sourcetype_for_syslog": {
                    "DEST_KEY": "_MetaData:Sourcetype",
                    "FORMAT": "syslog",
                },
                "dnslookup": {"external_cmd": "dnslookup.py", "fields_list": "clientip"},
            },
            "tags": {
                "eventtype=failed_login": {"authentication": "enabled", "failure": "enabled"},
                "sourcetype=syslog": {"os": "enabled", "unix": "enabled"},
            },
            "macros": {
                "get_eventtype(1)": {"definition": 'eventtype="$eventtype$"', "args": "eventtype"},
                "index_earliest": {"definition": "earliest=-24h@h"},
            },
            "inputs": {
                "default": {"host": "$decideOnStartup"},
                "monitor:///var/log/messages": {
                    "sourcetype": "linux_messages_syslog",
                    "disabled": "false",
                },
            },
            "outputs": {
                "tcpout": {"defaultGroup": "splunk_indexers", "disabled": "false"},
                "tcpout:splunk_indexers": {"server": "10.1.1.100:9997", "compressed": "true"},
            },
            "server": {
                "general": {"serverName": "splunk-server", "sessionTimeout": "1h"},
                "license": {"active_group": "Enterprise"},
            },
            "web": {
                "settings": {"httpport": "8000", "mgmtHostPort": "127.0.0.1:8089"},
                "feature:quarantine_files": {"enable": "true"},
            },
        }

        # Create mock configuration objects
        for conf_name, stanzas in mock_configs.items():
            mock_conf = Mock()
            mock_conf.name = conf_name

            # Create mock stanza objects
            mock_stanzas = []
            for stanza_name, content in stanzas.items():
                mock_stanza = Mock()
                mock_stanza.name = stanza_name
                mock_stanza.content = content
                mock_stanzas.append(mock_stanza)

            # Make the conf object iterable to return stanzas
            mock_conf.__iter__ = lambda stanzas=mock_stanzas: iter(stanzas)

            # Allow accessing specific stanzas by name
            mock_conf.__getitem__ = lambda key, stanzas_dict=stanzas: Mock(
                name=key, content=stanzas_dict.get(key, {})
            )

            self.confs[conf_name] = mock_conf


class MockJob:
    """Mock search job object"""

    def __init__(self, is_done=True, results=None):
        self._is_done = is_done
        self._results = results or []
        self.content = {
            "scanCount": len(self._results),
            "eventCount": len(self._results),
            "duration": 0.123,
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
                "health_check": health_result,
            }
        except Exception as e:
            return {
                "ping": False,
                "error": str(e),
                "tools_count": 0,
                "resources_count": 0,
                "tools": [],
                "resources": [],
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
        # Fast path: CallToolResult-like with .data
        if hasattr(result, "data"):
            return result.data
        # Handle content-style results
        if hasattr(result, "contents") and getattr(result, "contents", None):
            first = result.contents[0]
            if hasattr(first, "text"):
                try:
                    return json.loads(first.text)
                except (json.JSONDecodeError, AttributeError):
                    return {"raw_text": first.text}
        if isinstance(result, dict):
            return result
        elif isinstance(result, list) and len(result) > 0:
            first_item = result[0]
            if hasattr(first_item, "text"):
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
        "max_results": 5,
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
        {"_time": "2024-01-01T00:02:00", "source": "/var/log/system.log", "log_level": "WARN"},
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
        # Use local Splunk container defaults when available
        "SPLUNK_HOST": "localhost",
        "SPLUNK_PORT": "8089",
        "SPLUNK_USERNAME": "admin",
        "SPLUNK_PASSWORD": "Chang3d!",
        "SPLUNK_VERIFY_SSL": "false",
    }


@pytest.fixture
def mock_kvstore_collection_data():
    """Sample KV Store collection data"""
    return [
        {"_key": "1", "username": "admin", "role": "admin", "active": True},
        {"_key": "2", "username": "user1", "role": "user", "active": True},
        {"_key": "3", "username": "user2", "role": "user", "active": False},
    ]


@pytest.fixture(autouse=True)
def setup_test_environment(sample_env_vars):
    """Set up test environment variables"""
    with patch.dict(os.environ, sample_env_vars):
        yield


@pytest.fixture(autouse=True)
def mock_splunk_get_service(mock_splunk_service):
    """Autouse fixture to mock Splunk service access for all tools.

    This keeps tests in-memory while avoiding dependence on a running Splunk.
    """

    async def _get_service(*args, **kwargs):
        return mock_splunk_service

    patches = []
    try:
        # Import tool classes and patch their get_splunk_service
        from src.tools.admin.apps import ListApps
        from src.tools.admin.users import ListUsers
        from src.tools.health.status import GetSplunkHealth
        from src.tools.kvstore.collections import ListKvstoreCollections
        from src.tools.kvstore.data import GetKvstoreData
        from src.tools.metadata.indexes import ListIndexes
        from src.tools.metadata.sources import ListSources
        from src.tools.metadata.sourcetypes import ListSourcetypes
        from src.tools.search.job_search import JobSearch
        from src.tools.search.oneshot_search import OneshotSearch
        from src.tools.search.saved_search_tools import (
            CreateSavedSearch,
            DeleteSavedSearch,
            ExecuteSavedSearch,
            GetSavedSearchDetails,
            ListSavedSearches,
            UpdateSavedSearch,
        )

        targets = [
            GetSplunkHealth,
            OneshotSearch,
            JobSearch,
            ListApps,
            ListUsers,
            ListIndexes,
            ListSources,
            ListSourcetypes,
            ListKvstoreCollections,
            GetKvstoreData,
            CreateSavedSearch,
            DeleteSavedSearch,
            ExecuteSavedSearch,
            GetSavedSearchDetails,
            ListSavedSearches,
            UpdateSavedSearch,
        ]

        for cls in targets:
            p = patch.object(cls, "get_splunk_service", AsyncMock(side_effect=_get_service))
            p.start()
            patches.append(p)

        yield
    finally:
        for p in patches:
            try:
                p.stop()
            except Exception:
                pass


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
pytest_plugins = ["pytest_asyncio"]
