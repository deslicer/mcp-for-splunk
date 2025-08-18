"""
Pytest tests for MCP Server for Splunk

Tests using FastMCP's in-memory testing patterns following best practices from:
https://gofastmcp.com/patterns/testing
"""

import time

import pytest
from fastmcp.exceptions import ToolError


# Integration tests using FastMCP Client (recommended approach)
@pytest.mark.integration
class TestMCPClientIntegration:
    """Integration tests using FastMCP in-memory client following FastMCP best practices"""

    async def test_fastmcp_client_health_check(self, fastmcp_client, extract_tool_result):
        """Test health check via FastMCP client"""
        async with fastmcp_client as client:
            # Call the health check tool
            result = await client.call_tool("get_splunk_health")
            health_data = extract_tool_result(result)

            # The test should handle all possible states
            assert "status" in health_data
            assert health_data["status"] in ["connected", "disconnected", "error"]

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


@pytest.mark.integration
class TestSplunkToolsIntegration:
    """Integration tests for Splunk tools using FastMCP in-memory testing"""

    async def test_splunk_health_check(self, fastmcp_client, extract_tool_result):
        """Test Splunk health check tool via FastMCP client"""
        async with fastmcp_client as client:
            result = await client.call_tool("get_splunk_health")
            health_data = extract_tool_result(result)

            assert "status" in health_data
            # In test environment without Splunk connection, we expect error or disconnected
            assert health_data["status"] in ["connected", "disconnected", "error"]

            if health_data["status"] == "connected":
                assert "version" in health_data
                assert "server_name" in health_data

    async def test_list_indexes(self, fastmcp_client, extract_tool_result):
        """Test listing Splunk indexes via FastMCP client"""
        async with fastmcp_client as client:
            result = await client.call_tool("list_indexes")
            indexes_data = extract_tool_result(result)

            # Should have either success response or error response
            if "status" in indexes_data and indexes_data["status"] == "success":
                assert "indexes" in indexes_data
                assert "count" in indexes_data
                assert isinstance(indexes_data["indexes"], list)
            elif "status" in indexes_data and indexes_data["status"] == "error":
                assert "error" in indexes_data

    async def test_oneshot_search(self, fastmcp_client, extract_tool_result):
        """Test oneshot search via FastMCP client"""
        async with fastmcp_client as client:
            search_params = {
                "query": "index=_internal | head 5",
                "earliest_time": "-15m",
                "latest_time": "now",
                "max_results": 5,
            }

            result = await client.call_tool("run_oneshot_search", search_params)
            search_data = extract_tool_result(result)

            # Should have either results or error
            if "status" in search_data and search_data["status"] == "success":
                assert "results" in search_data
                assert "results_count" in search_data
                assert "query_executed" in search_data
            elif "status" in search_data and search_data["status"] == "error":
                assert "error" in search_data

    async def test_job_search(self, fastmcp_client, extract_tool_result):
        """Test job-based search via FastMCP client"""
        async with fastmcp_client as client:
            search_params = {
                "query": "index=_internal | stats count",
                "earliest_time": "-5m",
                "latest_time": "now",
            }

            result = await client.call_tool("run_splunk_search", search_params)
            search_data = extract_tool_result(result)

            # Should have either results or error
            if "job_id" in search_data:
                assert "results" in search_data
                assert "scan_count" in search_data or "event_count" in search_data
            elif "status" in search_data and search_data["status"] == "error":
                assert "error" in search_data

    async def test_list_apps(self, fastmcp_client, extract_tool_result):
        """Test listing Splunk apps via FastMCP client"""
        async with fastmcp_client as client:
            result = await client.call_tool("list_apps")
            apps_data = extract_tool_result(result)

            # Should have either apps or error
            if "apps" in apps_data:
                assert "count" in apps_data
                assert isinstance(apps_data["apps"], list)
            elif "status" in apps_data and apps_data["status"] == "error":
                assert "error" in apps_data

    async def test_list_users(self, fastmcp_client, extract_tool_result):
        """Test listing Splunk users via FastMCP client"""
        async with fastmcp_client as client:
            result = await client.call_tool("list_users")
            users_data = extract_tool_result(result)

            # Should have either users or error
            if "users" in users_data:
                assert "count" in users_data
                assert isinstance(users_data["users"], list)
            elif "status" in users_data and users_data["status"] == "error":
                assert "error" in users_data


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
@pytest.mark.integration
class TestErrorHandling:
    """Test error handling and edge cases using FastMCP patterns"""

    async def test_invalid_tool_call(self, fastmcp_client):
        """Test calling non-existent tool"""
        async with fastmcp_client as client:
            with pytest.raises(ToolError):
                await client.call_tool("non_existent_tool")

    async def test_invalid_tool_parameters(self, fastmcp_client):
        """Test calling tool with invalid parameters"""
        async with fastmcp_client as client:
            # Missing required parameter should raise an error
            with pytest.raises(ToolError):
                await client.call_tool("get_configurations", {})

    async def test_search_with_invalid_query(self, fastmcp_client, extract_tool_result):
        """Test search tool with invalid query"""
        async with fastmcp_client as client:
            search_params = {
                "query": "index=nonexistent_index invalid_command",
                "earliest_time": "-1h",
                "max_results": 5,
            }

            result = await client.call_tool("run_oneshot_search", search_params)
            search_data = extract_tool_result(result)

            # Should return an error status or handle gracefully
            if "status" in search_data:
                assert search_data["status"] in ["success", "error"]


# Performance/load testing
@pytest.mark.slow
@pytest.mark.integration
class TestPerformance:
    """Performance and load tests using FastMCP patterns"""

    async def test_multiple_rapid_health_checks(self, fastmcp_client, extract_tool_result):
        """Test multiple rapid health check calls"""
        async with fastmcp_client as client:
            start_time = time.time()

            # Call health check multiple times
            for _ in range(10):  # Reduced from 100 to be more reasonable
                result = await client.call_tool("get_splunk_health")
                health_data = extract_tool_result(result)
                assert "status" in health_data

            end_time = time.time()
            duration = end_time - start_time

            # Should complete 10 calls in under 5 seconds
            assert duration < 5.0, f"Health checks took too long: {duration}s"


# Workflow integration tests
@pytest.mark.integration
class TestWorkflowIntegration:
    """Test realistic workflows using FastMCP patterns"""

    async def test_discovery_workflow(self, fastmcp_client, extract_tool_result):
        """Test a realistic discovery workflow"""
        async with fastmcp_client as client:
            # 1. Check health first
            health_result = await client.call_tool("get_splunk_health")
            health_data = extract_tool_result(health_result)
            assert "status" in health_data

            # 2. List available indexes
            indexes_result = await client.call_tool("list_indexes")
            indexes_data = extract_tool_result(indexes_result)

            # 3. List apps
            apps_result = await client.call_tool("list_apps")
            apps_data = extract_tool_result(apps_result)

            # All should return structured data
            for data in [health_data, indexes_data, apps_data]:
                assert isinstance(data, dict)

    async def test_search_workflow(self, fastmcp_client, extract_tool_result):
        """Test a realistic search workflow"""
        async with fastmcp_client as client:
            # 1. Start with a simple search
            simple_search = await client.call_tool(
                "run_oneshot_search", {"query": "| metadata type=hosts", "max_results": 5}
            )
            simple_data = extract_tool_result(simple_search)
            assert isinstance(simple_data, dict)

            # 2. Try a more complex search
            complex_search = await client.call_tool(
                "run_splunk_search",
                {
                    "query": "| rest /services/server/info",
                    "earliest_time": "-1m",
                    "latest_time": "now",
                },
            )
            complex_data = extract_tool_result(complex_search)
            assert isinstance(complex_data, dict)


# Backward compatibility tests (for migration period)
@pytest.mark.integration
class TestBackwardCompatibility:
    """Test backward compatibility during migration to FastMCP patterns"""

    @pytest.mark.skip(reason="Legacy fixtures deprecated - use fastmcp_client")
    async def test_traefik_connection(self, traefik_client, mcp_helpers):
        """Legacy test - use fastmcp_client instead"""
        pass

    @pytest.mark.skip(reason="Legacy fixtures deprecated - use fastmcp_client")
    async def test_direct_connection(self, direct_client, mcp_helpers):
        """Legacy test - use fastmcp_client instead"""
        pass

    async def test_resource_access_patterns(self, fastmcp_client):
        """Test that resources are accessible in expected ways"""
        async with fastmcp_client as client:
            # Test resource listing
            resources = await client.list_resources()
            assert len(resources) > 0

            # Test specific resource access
            health_resource = await client.read_resource("health://status")
            assert len(health_resource) > 0
