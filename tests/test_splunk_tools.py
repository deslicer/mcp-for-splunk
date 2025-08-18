"""
Tests for Splunk tools functionality using FastMCP in-memory testing patterns.

This test suite follows the FastMCP testing best practices by using the Client
with the server instance for in-memory testing, avoiding external server processes.
"""


import pytest
from fastmcp.exceptions import ToolError


class TestSplunkHealthTool:
    """Test the health check functionality using FastMCP in-memory testing"""

    async def test_health_check_success(self, fastmcp_client, extract_tool_result):
        """Test successful health check using FastMCP client"""
        async with fastmcp_client as client:
            # Call the health check tool
            result = await client.call_tool("get_splunk_health")
            data = extract_tool_result(result)

            # Verify the health check response structure
            assert "status" in data
            # In test environment, we might get either connected, disconnected, or error
            assert data["status"] in ["connected", "disconnected", "error"]

            if data["status"] == "connected":
                assert "version" in data
                assert "server_name" in data

    async def test_health_check_with_custom_params(self, fastmcp_client, extract_tool_result):
        """Test health check with custom connection parameters"""
        async with fastmcp_client as client:
            # Test with custom Splunk connection parameters
            result = await client.call_tool(
                "get_splunk_health",
                {
                    "splunk_host": "test.example.com",
                    "splunk_port": 8089,
                    "splunk_username": "testuser",
                    "splunk_password": "testpass",
                    "splunk_scheme": "https",
                    "splunk_verify_ssl": False,
                },
            )
            data = extract_tool_result(result)

            # Should return status information
            assert "status" in data


class TestIndexTools:
    """Test index-related tools using FastMCP"""

    async def test_list_indexes_success(self, fastmcp_client, extract_tool_result):
        """Test successful index listing"""
        async with fastmcp_client as client:
            # ListIndexes doesn't take any parameters according to the tool definition
            result = await client.call_tool("list_indexes")
            data = extract_tool_result(result)

            # Check expected response structure
            assert "indexes" in data or "status" in data

            if "indexes" in data:
                assert "count" in data
                assert isinstance(data["indexes"], list)
                assert isinstance(data["count"], int)


class TestMetadataTools:
    """Test metadata tools (sourcetypes and sources) using FastMCP"""

    async def test_list_sourcetypes_success(self, fastmcp_client, extract_tool_result):
        """Test successful sourcetype listing"""
        async with fastmcp_client as client:
            # ListSourcetypes doesn't take any parameters
            result = await client.call_tool("list_sourcetypes")
            data = extract_tool_result(result)

            # Check expected response structure
            assert "sourcetypes" in data or "status" in data

            if "sourcetypes" in data:
                assert "count" in data
                assert isinstance(data["sourcetypes"], list)

    async def test_list_sources_success(self, fastmcp_client, extract_tool_result):
        """Test successful source listing"""
        async with fastmcp_client as client:
            # ListSources doesn't take any parameters
            result = await client.call_tool("list_sources")
            data = extract_tool_result(result)

            # Check expected response structure
            assert "sources" in data or "status" in data

            if "sources" in data:
                assert "count" in data
                assert isinstance(data["sources"], list)


class TestSearchTools:
    """Test search functionality using FastMCP"""

    async def test_run_oneshot_search_basic(self, fastmcp_client, extract_tool_result):
        """Test basic oneshot search"""
        async with fastmcp_client as client:
            result = await client.call_tool(
                "run_oneshot_search",
                {
                    "query": "index=main",
                    "earliest_time": "-1h",
                    "latest_time": "now",
                    "max_results": 10,
                },
            )
            data = extract_tool_result(result)

            # Verify response structure
            assert "status" in data or "results" in data

            if "results" in data:
                assert "results_count" in data
                assert "query_executed" in data
                assert isinstance(data["results"], list)

    async def test_run_oneshot_search_with_pipe(self, fastmcp_client, extract_tool_result):
        """Test oneshot search with pipe command"""
        async with fastmcp_client as client:
            result = await client.call_tool(
                "run_oneshot_search", {"query": "| stats count by log_level"}
            )
            data = extract_tool_result(result)

            # Should have some response structure
            assert isinstance(data, dict)
            # In test environment, might return error or results
            assert "status" in data or "results" in data

    async def test_run_oneshot_search_with_search_prefix(self, fastmcp_client, extract_tool_result):
        """Test oneshot search that already has search prefix"""
        async with fastmcp_client as client:
            result = await client.call_tool("run_oneshot_search", {"query": "search index=main"})
            data = extract_tool_result(result)

            assert isinstance(data, dict)
            assert "status" in data or "results" in data

    async def test_run_oneshot_search_max_results_limit(self, fastmcp_client, extract_tool_result):
        """Test oneshot search with max results limiting"""
        async with fastmcp_client as client:
            result = await client.call_tool(
                "run_oneshot_search", {"query": "index=main", "max_results": 5}
            )
            data = extract_tool_result(result)

            assert isinstance(data, dict)
            if "results" in data:
                # If we get results, they should respect the limit
                assert len(data["results"]) <= 5

    async def test_run_splunk_search_job(self, fastmcp_client, extract_tool_result):
        """Test job-based search functionality"""
        async with fastmcp_client as client:
            result = await client.call_tool(
                "run_splunk_search",
                {"query": "index=main | head 5", "earliest_time": "-1h", "latest_time": "now"},
            )
            data = extract_tool_result(result)

            assert isinstance(data, dict)
            assert "status" in data or "results" in data


class TestAppAndUserTools:
    """Test app and user management tools using FastMCP"""

    async def test_list_apps_success(self, fastmcp_client, extract_tool_result):
        """Test successful app listing"""
        async with fastmcp_client as client:
            # ListApps doesn't take any parameters
            result = await client.call_tool("list_apps")
            data = extract_tool_result(result)

            assert "apps" in data or "status" in data

            if "apps" in data:
                assert "count" in data
                assert isinstance(data["apps"], list)

    async def test_list_users_success(self, fastmcp_client, extract_tool_result):
        """Test successful user listing"""
        async with fastmcp_client as client:
            # ListUsers doesn't take any parameters
            result = await client.call_tool("list_users")
            data = extract_tool_result(result)

            assert "users" in data or "status" in data

            if "users" in data:
                assert "count" in data
                assert isinstance(data["users"], list)


class TestKVStoreTools:
    """Test KV Store tools using FastMCP"""

    async def test_list_kvstore_collections(self, fastmcp_client, extract_tool_result):
        """Test listing KV Store collections"""
        async with fastmcp_client as client:
            result = await client.call_tool("list_kvstore_collections")
            data = extract_tool_result(result)

            assert "collections" in data or "status" in data

            if "collections" in data:
                assert "count" in data

    async def test_list_kvstore_collections_specific_app(self, fastmcp_client, extract_tool_result):
        """Test listing KV Store collections for specific app"""
        async with fastmcp_client as client:
            result = await client.call_tool("list_kvstore_collections", {"app": "search"})
            data = extract_tool_result(result)

            assert "collections" in data or "status" in data

    async def test_get_kvstore_data_success(self, fastmcp_client, extract_tool_result):
        """Test KV Store data retrieval"""
        async with fastmcp_client as client:
            result = await client.call_tool(
                "get_kvstore_data", {"collection": "users", "app": "search"}
            )
            data = extract_tool_result(result)

            assert "documents" in data or "status" in data


class TestConfigurationTools:
    """Test configuration management tools using FastMCP"""

    async def test_get_configurations_all_stanzas(self, fastmcp_client, extract_tool_result):
        """Test getting all configuration stanzas"""
        async with fastmcp_client as client:
            result = await client.call_tool("get_configurations", {"conf_file": "props"})
            data = extract_tool_result(result)

            assert "file" in data or "status" in data

            if "file" in data:
                assert "stanzas" in data

    async def test_get_configurations_specific_stanza(self, fastmcp_client, extract_tool_result):
        """Test getting specific configuration stanza"""
        async with fastmcp_client as client:
            result = await client.call_tool(
                "get_configurations", {"conf_file": "props", "stanza": "default"}
            )
            data = extract_tool_result(result)

            assert "stanza" in data or "status" in data


class TestSavedSearchTools:
    """Test saved search functionality using FastMCP"""

    async def test_list_saved_searches(self, fastmcp_client, extract_tool_result):
        """Test listing saved searches"""
        async with fastmcp_client as client:
            result = await client.call_tool("list_saved_searches")
            data = extract_tool_result(result)

            assert "saved_searches" in data or "status" in data

    async def test_create_saved_search(self, fastmcp_client, extract_tool_result):
        """Test creating a saved search"""
        async with fastmcp_client as client:
            result = await client.call_tool(
                "create_saved_search",
                {
                    "name": "Test Search",
                    "search": "index=main | stats count",
                    "description": "Test saved search",
                    "is_visible": True,
                },
            )
            data = extract_tool_result(result)

            assert "name" in data or "status" in data

    async def test_execute_saved_search(self, fastmcp_client, extract_tool_result):
        """Test executing a saved search"""
        async with fastmcp_client as client:
            result = await client.call_tool(
                "execute_saved_search", {"name": "Messages by minute last 3 hours"}
            )
            data = extract_tool_result(result)

            # Should return some kind of response
            assert isinstance(data, dict)


class TestToolIntegration:
    """Test integration between multiple tools using FastMCP"""

    async def test_health_check_before_operations(self, fastmcp_client, extract_tool_result):
        """Test health check workflow before operations"""
        async with fastmcp_client as client:
            # First check health
            health_result = await client.call_tool("get_splunk_health")
            health_data = extract_tool_result(health_result)
            assert "status" in health_data

            # Then perform operation - no parameters needed
            indexes_result = await client.call_tool("list_indexes")
            indexes_data = extract_tool_result(indexes_result)
            assert isinstance(indexes_data, dict)

    async def test_search_workflow(self, fastmcp_client, extract_tool_result):
        """Test complete search workflow"""
        async with fastmcp_client as client:
            # First list indexes - no parameters needed
            indexes_result = await client.call_tool("list_indexes")
            indexes_data = extract_tool_result(indexes_result)
            assert isinstance(indexes_data, dict)

            # Then perform search
            search_result = await client.call_tool(
                "run_oneshot_search", {"query": "index=main | head 5"}
            )
            search_data = extract_tool_result(search_result)
            assert isinstance(search_data, dict)

    async def test_mcp_connectivity(self, fastmcp_client, mcp_helpers):
        """Test MCP server connectivity and available tools"""
        async with fastmcp_client as client:
            # Test basic connectivity
            connectivity = await mcp_helpers.check_connection_health(client)

            assert connectivity["ping"] is True
            assert connectivity["tools_count"] > 0
            assert "get_splunk_health" in connectivity["tools"]


class TestMCPServerCapabilities:
    """Test MCP server capabilities and tool discovery"""

    async def test_list_available_tools(self, fastmcp_client):
        """Test that all expected tools are available"""
        async with fastmcp_client as client:
            tools = await client.list_tools()
            tool_names = [tool.name for tool in tools]

            # Check for key tools
            expected_tools = [
                "get_splunk_health",
                "list_indexes",
                "list_sourcetypes",
                "list_sources",
                "run_oneshot_search",
                "run_splunk_search",
                "list_apps",
                "list_users",
                "get_configurations",
                "list_kvstore_collections",
                "get_kvstore_data",
                "list_saved_searches",
            ]

            for tool in expected_tools:
                assert tool in tool_names, f"Tool {tool} not found in available tools"

    async def test_list_available_resources(self, fastmcp_client):
        """Test that resources are available"""
        async with fastmcp_client as client:
            resources = await client.list_resources()
            # Convert URIs to strings for string operations
            resource_uris = [str(resource.uri) for resource in resources]

            # Check for expected resources
            assert len(resource_uris) > 0

            # Should have health and info resources
            health_resources = [uri for uri in resource_uris if "health" in uri]
            info_resources = [uri for uri in resource_uris if "info" in uri]

            assert len(health_resources) > 0
            assert len(info_resources) > 0

    async def test_tool_descriptions_present(self, fastmcp_client):
        """Test that tools have proper descriptions"""
        async with fastmcp_client as client:
            tools = await client.list_tools()

            for tool in tools:
                assert tool.name is not None
                assert tool.description is not None
                assert len(tool.description) > 0
                assert tool.inputSchema is not None


class TestErrorHandling:
    """Test error handling in various scenarios"""

    async def test_invalid_tool_call(self, fastmcp_client):
        """Test calling a non-existent tool"""
        async with fastmcp_client as client:
            with pytest.raises(ToolError):
                await client.call_tool("non_existent_tool")

    async def test_invalid_parameters(self, fastmcp_client):
        """Test calling tools with invalid parameters"""
        async with fastmcp_client as client:
            # Test with missing required parameters - this should raise an exception
            with pytest.raises(ToolError):
                await client.call_tool("get_configurations", {})
