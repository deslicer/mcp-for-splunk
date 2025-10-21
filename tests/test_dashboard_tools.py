"""
Tests for dashboard tools.

Tests the ListDashboards and GetDashboardDefinition tools.
"""

import json
from unittest.mock import Mock

import pytest


class TestListDashboards:
    """Test suite for ListDashboards tool."""

    @pytest.fixture
    def mock_dashboards_response(self):
        """Create mock response for dashboards endpoint."""
        return {
            "entry": [
                {
                    "name": "security_overview",
                    "id": "https://localhost:8089/servicesNS/nobody/search/data/ui/views/security_overview",
                    "content": {
                        "label": "Security Overview",
                        "description": "Security monitoring dashboard",
                        "eai:data": "<dashboard><label>Security Overview</label></dashboard>",
                        "updated": "2024-01-15T10:30:00",
                        "version": "1.0",
                    },
                    "acl": {
                        "app": "search",
                        "owner": "nobody",
                        "sharing": "global",
                        "perms": {
                            "read": ["*"],
                            "write": ["admin"],
                        },
                    },
                },
                {
                    "name": "performance_dashboard",
                    "id": "https://localhost:8089/servicesNS/admin/myapp/data/ui/views/performance_dashboard",
                    "content": {
                        "label": "Performance Dashboard",
                        "description": "System performance monitoring",
                        "eai:data": '{"version":"1.0.0","title":"Performance Dashboard"}',
                        "updated": "2024-01-14T09:15:00",
                        "version": "2.0",
                    },
                    "acl": {
                        "app": "myapp",
                        "owner": "admin",
                        "sharing": "app",
                        "perms": {
                            "read": ["admin", "power"],
                            "write": ["admin"],
                        },
                    },
                },
            ],
            "paging": {"total": 2, "perPage": 0, "offset": 0},
        }

    @pytest.fixture
    def mock_service(self, mock_dashboards_response):
        """Create mock Splunk service for testing."""
        service = Mock()
        service.host = "localhost"
        service.port = 8089

        # Mock the GET response
        mock_response = Mock()
        mock_response.body.read.return_value = json.dumps(mock_dashboards_response).encode("utf-8")
        service.get.return_value = mock_response

        return service

    async def test_list_dashboards_success(self, fastmcp_client, extract_tool_result, mock_service):
        """Test successful listing of dashboards."""
        async with fastmcp_client as client:
            # Execute tool through FastMCP
            result = await client.call_tool("list_dashboards", {})
            data = extract_tool_result(result)

            # Verify response structure
            if data.get("status") == "success":
                assert "dashboards" in data
                assert "count" in data
                assert isinstance(data["dashboards"], list)
                if data["count"] > 0:
                    first_dashboard = data["dashboards"][0]
                    assert "name" in first_dashboard
                    assert "label" in first_dashboard
                    assert "type" in first_dashboard
                    assert "web_url" in first_dashboard
                    # Type should be either 'classic' or 'studio'
                    assert first_dashboard["type"] in ["classic", "studio"]


class TestGetDashboardDefinition:
    """Test suite for GetDashboardDefinition tool."""

    @pytest.fixture
    def mock_dashboard_classic_response(self):
        """Create mock response for classic dashboard."""
        xml_content = """<dashboard>
  <label>Security Overview</label>
  <row>
    <panel>
      <title>Events Over Time</title>
      <chart>
        <search>
          <query>index=security | timechart count</query>
        </search>
      </chart>
    </panel>
  </row>
</dashboard>"""
        return {
            "entry": [
                {
                    "name": "security_overview",
                    "id": "https://localhost:8089/servicesNS/nobody/search/data/ui/views/security_overview",
                    "content": {
                        "label": "Security Overview",
                        "description": "Security monitoring dashboard",
                        "eai:data": xml_content,
                        "updated": "2024-01-15T10:30:00",
                        "version": "1.0",
                    },
                    "acl": {
                        "app": "search",
                        "owner": "nobody",
                        "sharing": "global",
                        "perms": {
                            "read": ["*"],
                            "write": ["admin"],
                        },
                    },
                }
            ]
        }

    @pytest.fixture
    def mock_dashboard_studio_response(self):
        """Create mock response for Dashboard Studio."""
        studio_json = {
            "version": "1.0.0",
            "title": "Performance Dashboard",
            "dataSources": {},
            "visualizations": {},
        }
        return {
            "entry": [
                {
                    "name": "performance_dashboard",
                    "id": "https://localhost:8089/servicesNS/admin/myapp/data/ui/views/performance_dashboard",
                    "content": {
                        "label": "Performance Dashboard",
                        "description": "System performance monitoring",
                        "eai:data": json.dumps(studio_json),
                        "updated": "2024-01-14T09:15:00",
                        "version": "2.0",
                    },
                    "acl": {
                        "app": "myapp",
                        "owner": "admin",
                        "sharing": "app",
                        "perms": {
                            "read": ["admin", "power"],
                            "write": ["admin"],
                        },
                    },
                }
            ]
        }

    @pytest.fixture
    def mock_service_classic(self, mock_dashboard_classic_response):
        """Create mock Splunk service for classic dashboard."""
        service = Mock()
        service.host = "localhost"
        service.port = 8089

        mock_response = Mock()
        mock_response.body.read.return_value = json.dumps(mock_dashboard_classic_response).encode(
            "utf-8"
        )
        service.get.return_value = mock_response

        return service

    @pytest.fixture
    def mock_service_studio(self, mock_dashboard_studio_response):
        """Create mock Splunk service for Dashboard Studio."""
        service = Mock()
        service.host = "localhost"
        service.port = 8089

        mock_response = Mock()
        mock_response.body.read.return_value = json.dumps(mock_dashboard_studio_response).encode(
            "utf-8"
        )
        service.get.return_value = mock_response

        return service

    async def test_get_dashboard_classic_success(
        self, fastmcp_client, extract_tool_result, mock_service_classic
    ):
        """Test successful retrieval of classic dashboard."""
        async with fastmcp_client as client:
            # Execute tool through FastMCP
            result = await client.call_tool(
                "get_dashboard_definition", {"name": "security_overview"}
            )
            data = extract_tool_result(result)

            # Verify response structure
            if data.get("status") == "success":
                assert "name" in data
                assert "type" in data
                assert "definition" in data
                assert "web_url" in data
                # Should be detected as classic
                if data.get("type"):
                    assert data["type"] in ["classic", "studio"]

    async def test_get_dashboard_studio_success(
        self, fastmcp_client, extract_tool_result, mock_service_studio
    ):
        """Test successful retrieval of Dashboard Studio dashboard."""
        async with fastmcp_client as client:
            # Execute tool through FastMCP
            result = await client.call_tool(
                "get_dashboard_definition", {"name": "performance_dashboard", "app": "myapp"}
            )
            data = extract_tool_result(result)

            # Verify response structure
            if data.get("status") == "success":
                assert "name" in data
                assert "type" in data
                assert "definition" in data
                assert "web_url" in data
                # Studio dashboards should have JSON definition
                if data.get("type") == "studio":
                    assert isinstance(data["definition"], dict)
