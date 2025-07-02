"""
Pytest tests for MCP Server for Splunk

Tests both direct tool function calls (unit tests) and FastMCP client integration.
"""

import json
import time
from unittest.mock import patch

import pytest


# Unit tests - Test tool functions directly
@pytest.mark.unit
class TestSplunkToolsUnit:
    """Unit tests for Splunk-specific MCP tools"""

    def test_splunk_health_check_connected(self, mock_context):
        """Test Splunk health check tool when connected"""
        from src.server import get_splunk_health

        # Test with connected service
        mock_context.request_context.lifespan_context.is_connected = True
        mock_context.request_context.lifespan_context.service.info = {
            "version": "9.0.0",
            "host": "so1",
        }

        health_data = get_splunk_health.fn(mock_context)

        assert health_data["status"] == "connected"
        assert health_data["version"] == "9.0.0"
        assert health_data["server_name"] == "so1"

    def test_splunk_health_check_disconnected(self, mock_disconnected_context):
        """Test Splunk health check tool when disconnected"""
        from src.server import get_splunk_health

        health_data = get_splunk_health.fn(mock_disconnected_context)

        assert health_data["status"] == "disconnected"
        assert "error" in health_data
        assert "message" in health_data

    def test_list_indexes_success(self, mock_context):
        """Test listing Splunk indexes successfully"""
        from src.server import list_indexes

        # Test with connected service
        mock_context.request_context.lifespan_context.is_connected = True

        indexes_data = list_indexes.fn(mock_context)

        assert indexes_data["status"] == "success"
        assert "indexes" in indexes_data
        assert "count" in indexes_data
        assert indexes_data["count"] > 0
        assert isinstance(indexes_data["indexes"], list)

        # Check for expected customer indexes (internal indexes are filtered out)
        expected_indexes = ["main", "security"]
        for expected in expected_indexes:
            assert any(expected in idx for idx in indexes_data["indexes"])

    def test_list_indexes_disconnected(self, mock_disconnected_context):
        """Test listing indexes when Splunk is disconnected"""
        from src.server import list_indexes

        indexes_data = list_indexes.fn(mock_disconnected_context)

        assert indexes_data["status"] == "error"
        assert "error" in indexes_data
        assert indexes_data["count"] == 0

    def test_simple_oneshot_search_success(self, mock_context, mock_search_results):
        """Test running a simple oneshot search successfully"""
        from src.server import run_oneshot_search

        # Mock the service and jobs
        mock_context.request_context.lifespan_context.is_connected = True

        search_params = {
            "query": "index=_internal | head 5",
            "earliest_time": "-15m",
            "latest_time": "now",
            "max_results": 5,
        }

        with patch("src.server.ResultsReader") as mock_reader:
            mock_reader.return_value = iter(mock_search_results)

            search_data = run_oneshot_search.fn(mock_context, **search_params)

            assert search_data["status"] == "success"
            assert "results" in search_data
            assert "results_count" in search_data
            assert "query_executed" in search_data
            assert "duration" in search_data
            assert search_data["query_executed"] == "search index=_internal | head 5"

    def test_oneshot_search_disconnected(self, mock_disconnected_context):
        """Test oneshot search when Splunk is disconnected"""
        from src.server import run_oneshot_search

        search_params = {
            "query": "index=_internal | head 5",
            "earliest_time": "-15m",
            "latest_time": "now",
            "max_results": 5,
        }

        search_data = run_oneshot_search.fn(mock_disconnected_context, **search_params)

        assert search_data["status"] == "error"
        assert "error" in search_data

    def test_run_splunk_search_success(self, mock_context, mock_search_results):
        """Test running a normal Splunk search with job tracking"""
        from src.server import run_splunk_search

        # Test with connected service
        mock_context.request_context.lifespan_context.is_connected = True

        search_params = {
            "query": "index=_internal | stats count",
            "earliest_time": "-5m",
            "latest_time": "now",
        }

        with patch("src.server.ResultsReader") as mock_reader:
            mock_reader.return_value = iter(mock_search_results)

            search_data = run_splunk_search.fn(mock_context, **search_params)

            assert "job_id" in search_data
            assert search_data["is_done"] is True
            assert "results" in search_data
            assert "scan_count" in search_data
            assert "event_count" in search_data

    def test_list_apps_success(self, mock_context):
        """Test listing Splunk apps"""
        from src.server import list_apps

        # Test with connected service
        mock_context.request_context.lifespan_context.is_connected = True

        apps_data = list_apps.fn(mock_context)

        assert "apps" in apps_data
        assert "count" in apps_data
        assert apps_data["count"] > 0
        assert isinstance(apps_data["apps"], list)

        # Check for expected default apps
        app_names = [app["name"] for app in apps_data["apps"]]
        assert "search" in app_names

    def test_list_users_success(self, mock_context):
        """Test listing Splunk users"""
        from src.server import list_users

        # Test with connected service
        mock_context.request_context.lifespan_context.is_connected = True

        users_data = list_users.fn(mock_context)

        assert "users" in users_data
        assert "count" in users_data
        assert users_data["count"] > 0
        assert isinstance(users_data["users"], list)

        # Check for admin user
        usernames = [user["username"] for user in users_data["users"]]
        assert "admin" in usernames

    def test_health_check_resource(self):
        """Test health check resource"""
        from src.server import health_check

        result = health_check.fn()
        assert result == "OK"


# Integration tests using FastMCP Client
@pytest.mark.integration
class TestMCPClientIntegration:
    """Integration tests using FastMCP in-memory client"""

    async def test_fastmcp_client_health_check(self, fastmcp_client):
        """Test health check via FastMCP client"""
        async with fastmcp_client as client:
            # Call the health check tool
            result = await client.call_tool("get_splunk_health")

            # Extract the result (FastMCP returns TextContent objects)
            if hasattr(result[0], "text"):
                # Parse JSON from text content
                health_data = json.loads(result[0].text)
            else:
                health_data = result[0]

            # The test will depend on actual Splunk connection
            assert "status" in health_data
            assert health_data["status"] in ["connected", "disconnected"]

    async def test_fastmcp_client_list_tools(self, fastmcp_client):
        """Test listing tools via FastMCP client"""
        async with fastmcp_client as client:
            tools = await client.list_tools()

            # Check that we have the expected tools
            tool_names = [tool.name for tool in tools]
            expected_tools = [
                "get_splunk_health",
                "list_indexes",
                "run_oneshot_search",
                "run_splunk_search",
                "list_apps",
                "list_users",
            ]

            for expected_tool in expected_tools:
                assert expected_tool in tool_names

    async def test_fastmcp_client_list_resources(self, fastmcp_client):
        """Test listing resources via FastMCP client"""
        async with fastmcp_client as client:
            resources = await client.list_resources()

            # Check that we have the health resource
            resource_uris = [str(resource.uri) for resource in resources]
            assert "health://status" in resource_uris

    async def test_fastmcp_client_read_health_resource(self, fastmcp_client):
        """Test reading health resource via FastMCP client"""
        async with fastmcp_client as client:
            result = await client.read_resource("health://status")

            assert len(result) > 0
            assert hasattr(result[0], "text")
            assert result[0].text == "OK"

    async def test_fastmcp_client_ping(self, fastmcp_client):
        """Test ping functionality"""
        async with fastmcp_client as client:
            # Should not raise an exception
            await client.ping()


# Helper function tests
@pytest.mark.unit
class TestHelperFunctions:
    """Test helper functions and utilities"""

    def test_extract_tool_result_with_json(self, extract_tool_result):
        """Test extracting JSON from tool result"""

        class MockContent:
            text = '{"status": "success", "data": "test"}'

        mock_result = [MockContent()]
        result = extract_tool_result(mock_result)

        assert result["status"] == "success"
        assert result["data"] == "test"

    def test_extract_tool_result_with_plain_text(self, extract_tool_result):
        """Test extracting plain text from tool result"""

        class MockContent:
            text = "plain text response"

        mock_result = [MockContent()]
        result = extract_tool_result(mock_result)

        assert result["raw_text"] == "plain text response"

    def test_extract_tool_result_with_direct_data(self, extract_tool_result):
        """Test extracting data that's already in the right format"""
        direct_data = {"status": "success", "count": 5}
        result = extract_tool_result(direct_data)

        assert result == direct_data


# Error handling tests
@pytest.mark.unit
class TestErrorHandling:
    """Test error handling and edge cases"""

    def test_search_with_exception(self, mock_context):
        """Test search tool when an exception occurs"""
        from src.server import run_oneshot_search

        # Test with connected service but force an exception
        mock_context.request_context.lifespan_context.is_connected = True

        search_params = {
            "query": "index=nonexistent_index invalid_command",
            "earliest_time": "-1h",
            "max_results": 5,
        }

        # Mock the jobs.oneshot to raise an exception
        mock_context.request_context.lifespan_context.service.jobs.oneshot.side_effect = Exception(
            "Search failed"
        )

        search_data = run_oneshot_search.fn(mock_context, **search_params)

        # Should return an error status
        assert search_data["status"] == "error"
        assert "error" in search_data


# Performance/load testing
@pytest.mark.slow
class TestPerformance:
    """Performance and load tests"""

    def test_multiple_rapid_health_checks(self, mock_context):
        """Test multiple rapid health check calls"""
        from src.server import get_splunk_health

        # Test with connected service
        mock_context.request_context.lifespan_context.is_connected = True
        mock_context.request_context.lifespan_context.service.info = {
            "version": "9.0.0",
            "host": "so1",
        }

        start_time = time.time()

        # Call health check multiple times
        for _ in range(100):
            result = get_splunk_health.fn(mock_context)
            assert result["status"] == "connected"

        end_time = time.time()
        duration = end_time - start_time

        # Should complete 100 calls in under 1 second
        assert duration < 1.0, f"Health checks took too long: {duration}s"


# Backward compatibility tests (will be removed eventually)
@pytest.mark.integration
class TestBackwardCompatibility:
    """Test backward compatibility with old fixtures"""

    @pytest.mark.skip(reason="Legacy fixtures deprecated - use fastmcp_client")
    async def test_traefik_connection(self, traefik_client, mcp_helpers):
        """Legacy test - use fastmcp_client instead"""
        pass

    @pytest.mark.skip(reason="Legacy fixtures deprecated - use fastmcp_client")
    async def test_direct_connection(self, direct_client, mcp_helpers):
        """Legacy test - use fastmcp_client instead"""
        pass
