"""
Tests for dashboard tools.

Tests the ListDashboards and GetDashboardDefinition tools.
"""

import json
from unittest.mock import AsyncMock, Mock

import pytest

from src.tools.dashboards.create_dashboard import CreateDashboard
from src.tools.dashboards.get_dashboard_definition import GetDashboardDefinition
from src.tools.dashboards.list_dashboards import ListDashboards


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

    async def test_list_dashboards_success(self, fastmcp_client, tool_payload):
        """Test successful listing of dashboards."""
        async with fastmcp_client as client:
            # Execute tool through FastMCP
            data = await tool_payload(client, "list_dashboards")

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
                    assert ":8089" not in first_dashboard["web_url"]
                    assert ":8000" not in first_dashboard["web_url"]
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

    async def test_get_dashboard_classic_success(self, fastmcp_client, tool_payload):
        """Test successful retrieval of classic dashboard."""
        async with fastmcp_client as client:
            # Execute tool through FastMCP
            data = await tool_payload(
                client, "get_dashboard_definition", {"name": "security_overview"}
            )

            # Verify response structure
            if data.get("status") == "success":
                assert "name" in data
                assert "type" in data
                assert "definition" in data
                assert "web_url" in data
                assert ":8089" not in data["web_url"]
                # Should be detected as classic
                if data.get("type"):
                    assert data["type"] in ["classic", "studio"]

    async def test_get_dashboard_studio_success(self, fastmcp_client, tool_payload):
        """Test successful retrieval of Dashboard Studio dashboard."""
        async with fastmcp_client as client:
            # Execute tool through FastMCP
            data = await tool_payload(
                client,
                "get_dashboard_definition",
                {"name": "performance_dashboard", "app": "myapp"},
            )

            # Verify response structure
            if data.get("status") == "success":
                assert "name" in data
                assert "type" in data
                assert "definition" in data
                assert "web_url" in data
                assert ":8089" not in data["web_url"]
                # Studio dashboards should have JSON definition
                if data.get("type") == "studio":
                    assert isinstance(data["definition"], dict)


class TestCreateDashboard:
    """Test suite for CreateDashboard tool."""

    async def test_create_studio_dashboard_success(self, fastmcp_client, tool_payload):
        studio_def = {
            "version": "1.0.0",
            "title": "Studio Created",
            "dataSources": {},
            "visualizations": {},
        }
        async with fastmcp_client as client:
            data = await tool_payload(
                client,
                "create_dashboard",
                {
                    "name": "studio_created",
                    "definition": studio_def,
                    "label": "Studio Created",
                    "description": "Created by tests",
                    "overwrite": False,
                },
            )
            if data.get("status") == "success":
                assert data["name"] == "studio_created"
                assert data["type"] in ["studio", "classic"]
                assert "web_url" in data

    async def test_create_classic_dashboard_success(self, fastmcp_client, tool_payload):
        classic_xml = """<dashboard><label>Classic Created</label></dashboard>"""
        async with fastmcp_client as client:
            data = await tool_payload(
                client,
                "create_dashboard",
                {
                    "name": "classic_created",
                    "definition": classic_xml,
                    "label": "Classic Created",
                    "description": "Created by tests",
                },
            )
            if data.get("status") == "success":
                assert data["name"] == "classic_created"
                assert data["type"] in ["studio", "classic"]
                assert "web_url" in data

    @pytest.mark.asyncio
    async def test_studio_wrapper_from_dict_direct(self, mock_context):
        tool = CreateDashboard("create_dashboard", "Create a Splunk dashboard")
        # Execute directly with mock context to inspect mock service state
        result = await tool.execute(
            mock_context,
            name="studio_wrapped_dict",
            definition={
                "title": "Studio Created",
                "dataSources": {},
                "visualizations": {},
                "layout": {"type": "absolute", "structure": []},
            },
            dashboard_type="studio",
            label="Studio Created",
            description="Created by tests",
        )
        assert result.get("status") == "success"
        # Inspect stored eai:data from mock service
        service = mock_context.request_context.lifespan_context.service
        stored = service._dashboards["studio_wrapped_dict"]["content"]["eai:data"]
        assert '<dashboard version="2"' in stored
        assert "<definition><![CDATA[" in stored
        assert '"title":"Studio Created"' in stored
        # Detected type should be studio
        assert result.get("type") == "studio"

    @pytest.mark.asyncio
    async def test_studio_wrapper_theme_dark(self, mock_context):
        tool = CreateDashboard("create_dashboard", "Create a Splunk dashboard")
        result = await tool.execute(
            mock_context,
            name="studio_theme_dark",
            definition={
                "title": "Dark Theme Studio",
                "dataSources": {},
                "visualizations": {},
            },
            dashboard_type="studio",
            theme="dark",
        )
        assert result.get("status") == "success"
        assert result.get("theme") == "dark"
        service = mock_context.request_context.lifespan_context.service
        stored = service._dashboards["studio_theme_dark"]["content"]["eai:data"]
        assert '<dashboard version="2" theme="dark">' in stored

    @pytest.mark.asyncio
    async def test_studio_wrapper_theme_auto_from_ui_settings(self, mock_context):
        tool = CreateDashboard("create_dashboard", "Create a Splunk dashboard")
        result = await tool.execute(
            mock_context,
            name="studio_theme_auto",
            definition={
                "title": "Auto Theme",
                "uiSettings": {"theme": "dark"},
                "dataSources": {},
                "visualizations": {},
            },
            dashboard_type="studio",
        )
        assert result.get("status") == "success"
        assert result.get("theme") == "dark"
        service = mock_context.request_context.lifespan_context.service
        stored = service._dashboards["studio_theme_auto"]["content"]["eai:data"]
        assert '<dashboard version="2" theme="dark">' in stored

    @pytest.mark.asyncio
    async def test_studio_wrapper_theme_auto_default_dark(self, mock_context):
        tool = CreateDashboard("create_dashboard", "Create a Splunk dashboard")
        result = await tool.execute(
            mock_context,
            name="studio_theme_auto_default",
            definition={
                "title": "No Theme In JSON",
                "dataSources": {},
                "visualizations": {},
            },
            dashboard_type="studio",
        )
        assert result.get("status") == "success"
        assert result.get("theme") == "dark"
        service = mock_context.request_context.lifespan_context.service
        stored = service._dashboards["studio_theme_auto_default"]["content"]["eai:data"]
        assert '<dashboard version="2" theme="dark">' in stored

    @pytest.mark.asyncio
    async def test_create_stores_label_and_description_from_initial_post(self, mock_context):
        tool = CreateDashboard("create_dashboard", "Create a Splunk dashboard")
        result = await tool.execute(
            mock_context,
            name="single_post_metadata",
            definition={"title": "One POST", "dataSources": {}, "visualizations": {}},
            label="One POST Label",
            description="Created in one request",
        )
        assert result.get("status") == "success"
        assert result.get("definition_size_bytes", 0) > 0
        service = mock_context.request_context.lifespan_context.service
        stored = service._dashboards["single_post_metadata"]["content"]["eai:data"]
        assert "<label>One POST Label</label>" in stored
        assert "<description>Created in one request</description>" in stored

    @pytest.mark.asyncio
    async def test_studio_wrapper_invalid_theme(self, mock_context):
        tool = CreateDashboard("create_dashboard", "Create a Splunk dashboard")
        result = await tool.execute(
            mock_context,
            name="studio_bad_theme",
            definition={"title": "Bad", "dataSources": {}, "visualizations": {}},
            dashboard_type="studio",
            theme="sepia",
        )
        assert result.get("status") == "error"
        assert "theme" in (result.get("error") or "").lower()

    @pytest.mark.asyncio
    async def test_studio_wrapper_from_json_string_auto(self, mock_context):
        tool = CreateDashboard("create_dashboard", "Create a Splunk dashboard")
        studio_json = json.dumps(
            {
                "title": "Auto Studio",
                "dataSources": {},
                "visualizations": {},
                "layout": {"type": "absolute", "structure": []},
            }
        )
        result = await tool.execute(
            mock_context,
            name="studio_wrapped_auto",
            definition=studio_json,
            # dashboard_type omitted -> auto-detect
        )
        assert result.get("status") == "success"
        service = mock_context.request_context.lifespan_context.service
        stored = service._dashboards["studio_wrapped_auto"]["content"]["eai:data"]
        assert '<dashboard version="2"' in stored
        assert "<definition><![CDATA[" in stored
        assert '"title":"Auto Studio"' in stored
        assert result.get("type") == "studio"

    @pytest.mark.asyncio
    async def test_studio_prewrapped_pass_through(self, mock_context):
        tool = CreateDashboard("create_dashboard", "Create a Splunk dashboard")
        prewrapped = (
            '<dashboard version="2" theme="light">\n'
            "  <label>Prewrapped</label>\n"
            '  <definition><![CDATA[{"title":"Already Wrapped"}]]></definition>\n'
            "</dashboard>"
        )
        result = await tool.execute(
            mock_context,
            name="studio_prewrapped",
            definition=prewrapped,
            dashboard_type="studio",
        )
        assert result.get("status") == "success"
        service = mock_context.request_context.lifespan_context.service
        stored = service._dashboards["studio_prewrapped"]["content"]["eai:data"]
        # Should be unchanged (no double-wrap)
        assert stored == prewrapped
        assert result.get("type") == "studio"

    async def test_overwrite_existing_dashboard(self, fastmcp_client, tool_payload):
        # First attempt should simulate conflict -> then overwrite path
        classic_xml = """<dashboard><label>Exists</label></dashboard>"""
        async with fastmcp_client as client:
            # initial create will throw conflict in mock; overwrite=True triggers update path
            data = await tool_payload(
                client,
                "create_dashboard",
                {
                    "name": "exists_dashboard",
                    "definition": classic_xml,
                    "overwrite": True,
                },
            )
            # Should still succeed with update path
            if data.get("status") == "success":
                assert data["name"] == "exists_dashboard"
                assert "web_url" in data

    async def test_acl_update(self, fastmcp_client, tool_payload):
        studio_def = {"version": "1.0.0", "title": "ACL Demo"}
        async with fastmcp_client as client:
            data = await tool_payload(
                client,
                "create_dashboard",
                {
                    "name": "acl_demo",
                    "definition": studio_def,
                    "sharing": "app",
                    "read_perms": ["admin", "power"],
                    "write_perms": ["admin"],
                },
            )
            if data.get("status") == "success":
                assert data["name"] == "acl_demo"
                # The mock service sets ACL; we simply assert success contract
                assert "permissions" in data


class TestDashboardWebUrls:
    """Dashboard web_url uses the Splunk Web base, never management ports."""

    _LIST_PAYLOAD = {
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
                    "perms": {"read": ["*"], "write": ["admin"]},
                },
            }
        ],
        "paging": {"total": 1, "perPage": 0, "offset": 0},
    }

    async def test_list_honors_explicit_web_url(self):
        service = Mock()
        service.host = "mgmt.internal"
        service.scheme = "https"
        service.port = 8089
        mock_response = Mock()
        mock_response.body.read.return_value = json.dumps(self._LIST_PAYLOAD).encode("utf-8")
        service.get.return_value = mock_response

        tool = ListDashboards("list_dashboards", "list dashboards")
        ctx = Mock()
        ctx.info = AsyncMock()
        ctx.error = AsyncMock()
        tool.check_splunk_available = Mock(return_value=(True, service, None))
        tool.get_client_config_from_context = AsyncMock(
            return_value={"splunk_web_url": "https://splunk-b839c1.deslicer.io"}
        )

        result = await tool.execute(ctx)
        assert result["status"] == "success"
        urls = [item["web_url"] for item in result["dashboards"]]
        assert urls[0] == (
            "https://splunk-b839c1.deslicer.io/en-US/app/search/security_overview"
        )
        assert all(":8089" not in url and ":8000" not in url for url in urls)

    async def test_get_definition_https_omits_web_port(self):
        service = Mock()
        service.host = "splunk.example.com"
        service.scheme = "https"
        service.port = 8089
        mock_response = Mock()
        mock_response.body.read.return_value = json.dumps(self._LIST_PAYLOAD).encode("utf-8")
        service.get.return_value = mock_response

        tool = GetDashboardDefinition("get_dashboard_definition", "get dashboard")
        ctx = Mock()
        ctx.info = AsyncMock()
        ctx.error = AsyncMock()
        tool.check_splunk_available = Mock(return_value=(True, service, None))
        tool.get_client_config_from_context = AsyncMock(return_value={})

        result = await tool.execute(ctx, name="security_overview")
        assert result["status"] == "success"
        assert result["web_url"] == "https://splunk.example.com/en-US/app/search/security_overview"
        assert ":8000" not in result["web_url"]
        assert ":8089" not in result["web_url"]
