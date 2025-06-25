"""
Pytest tests for MCP Server for Splunk

Test both Traefik-proxied and direct connections to the MCP server,
as well as basic functionality of the MCP tools.
"""

import pytest
import json
from typing import Dict, Any


@pytest.mark.integration
class TestMCPConnections:
    """Test MCP server connections and basic functionality"""
    
    async def test_traefik_connection(self, traefik_client, mcp_helpers):
        """Test connection via Traefik proxy"""
        result = await mcp_helpers.check_connection_health(traefik_client)
        
        assert result["ping"] is True
        assert result["tools_count"] == 12
        assert result["resources_count"] == 1
        assert "get_splunk_health" in result["tools"]
        assert "list_indexes" in result["tools"]
    
    async def test_direct_connection(self, direct_client, mcp_helpers):
        """Test direct connection to MCP server"""
        result = await mcp_helpers.check_connection_health(direct_client)
        
        assert result["ping"] is True
        assert result["tools_count"] == 12
        assert result["resources_count"] == 1
        assert "get_splunk_health" in result["tools"]
        assert "list_indexes" in result["tools"]
    
    async def test_health_resource(self, traefik_client):
        """Test health resource endpoint"""
        result = await traefik_client.read_resource("health://status")
        
        assert len(result) > 0
        assert result[0].text == "OK"


@pytest.mark.integration
class TestSplunkTools:
    """Test Splunk-specific MCP tools"""
    
    async def test_splunk_health_check(self, traefik_client, extract_tool_result):
        """Test Splunk health check tool"""
        result = await traefik_client.call_tool("get_splunk_health")
        health_data = extract_tool_result(result)
        
        assert health_data["status"] == "connected"
        assert "version" in health_data
        assert "server_name" in health_data
        assert health_data["server_name"] == "so1"
    
    async def test_list_indexes(self, traefik_client, extract_tool_result):
        """Test listing Splunk indexes"""
        result = await traefik_client.call_tool("list_indexes")
        indexes_data = extract_tool_result(result)
        
        assert indexes_data["status"] == "success"
        assert "indexes" in indexes_data
        assert "count" in indexes_data
        assert indexes_data["count"] > 0
        assert isinstance(indexes_data["indexes"], list)
        
        # Check for expected system indexes
        expected_indexes = ["_audit", "_internal"]
        for expected in expected_indexes:
            assert any(expected in idx for idx in indexes_data["indexes"])
    
    async def test_list_sourcetypes(self, traefik_client, extract_tool_result):
        """Test listing Splunk sourcetypes"""
        result = await traefik_client.call_tool("list_sourcetypes")
        sourcetypes_data = extract_tool_result(result)
        
        assert "sourcetypes" in sourcetypes_data
        assert "count" in sourcetypes_data
        assert sourcetypes_data["count"] > 0
        assert isinstance(sourcetypes_data["sourcetypes"], list)
    
    async def test_simple_search(self, traefik_client, extract_tool_result, splunk_test_query):
        """Test running a simple Splunk search"""
        result = await traefik_client.call_tool("run_oneshot_search", splunk_test_query)
        search_data = extract_tool_result(result)
        
        assert search_data["status"] == "success"
        assert "results" in search_data
        assert "results_count" in search_data
        assert "query_executed" in search_data
        assert "duration" in search_data
        assert search_data["query_executed"] == "search index=_internal | head 5"
    
    async def test_run_splunk_search(self, traefik_client, extract_tool_result):
        """Test running a normal Splunk search with job tracking"""
        search_params = {
            "query": "index=_internal | stats count",
            "earliest_time": "-5m",
            "latest_time": "now"
        }
        
        result = await traefik_client.call_tool("run_splunk_search", search_params)
        search_data = extract_tool_result(result)
        
        assert "job_id" in search_data
        assert search_data["is_done"] is True
        assert "results" in search_data
        assert "scan_count" in search_data
        assert "event_count" in search_data


@pytest.mark.integration 
class TestSplunkAppsAndUsers:
    """Test Splunk apps and users tools"""
    
    async def test_list_apps(self, traefik_client, extract_tool_result):
        """Test listing Splunk apps"""
        result = await traefik_client.call_tool("list_apps")
        apps_data = extract_tool_result(result)
        
        assert "apps" in apps_data
        assert "count" in apps_data
        assert apps_data["count"] > 0
        assert isinstance(apps_data["apps"], list)
        
        # Check for expected default apps
        app_names = [app["name"] for app in apps_data["apps"]]
        assert "search" in app_names
    
    async def test_list_users(self, traefik_client, extract_tool_result):
        """Test listing Splunk users"""
        result = await traefik_client.call_tool("list_users")
        users_data = extract_tool_result(result)
        
        assert "users" in users_data
        assert "count" in users_data
        assert users_data["count"] > 0
        assert isinstance(users_data["users"], list)
        
        # Check for admin user
        usernames = [user["username"] for user in users_data["users"]]
        assert "admin" in usernames


@pytest.mark.integration
class TestKVStore:
    """Test KV Store functionality"""
    
    async def test_list_kvstore_collections(self, traefik_client, extract_tool_result):
        """Test listing KV Store collections"""
        result = await traefik_client.call_tool("list_kvstore_collections")
        collections_data = extract_tool_result(result)
        
        assert "collections" in collections_data
        assert "count" in collections_data
        assert isinstance(collections_data["collections"], list)


@pytest.mark.slow
@pytest.mark.integration
class TestSplunkConfiguration:
    """Test Splunk configuration tools"""
    
    async def test_get_configurations(self, traefik_client, extract_tool_result):
        """Test getting Splunk configurations"""
        result = await traefik_client.call_tool("get_configurations", {"conf_file": "inputs"})
        config_data = extract_tool_result(result)
        
        assert "file" in config_data or "stanzas" in config_data


@pytest.mark.integration 
class TestErrorHandling:
    """Test error handling and edge cases"""
    
    async def test_invalid_tool_call(self, traefik_client):
        """Test calling a non-existent tool"""
        with pytest.raises(Exception):
            await traefik_client.call_tool("non_existent_tool")
    
    async def test_search_with_invalid_query(self, traefik_client, extract_tool_result):
        """Test search with invalid SPL query"""
        invalid_query = {
            "query": "index=nonexistent_index invalid_command",
            "earliest_time": "-1h",
            "max_results": 5
        }
        
        result = await traefik_client.call_tool("run_oneshot_search", invalid_query)
        search_data = extract_tool_result(result)
        
        # Should return an error or empty results
        assert "status" in search_data
        # The query might fail or return no results, both are acceptable


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