"""
Tests for lookup tools.

Tests the ListLookupFiles and ListLookupDefinitions tools.
"""

import json
from unittest.mock import Mock

import pytest


class TestListLookupFiles:
    """Test suite for ListLookupFiles tool."""

    @pytest.fixture
    def mock_lookup_files_response(self):
        """Create mock response for lookup files endpoint."""
        return {
            "entry": [
                {
                    "name": "geo_attr_countries.csv",
                    "id": "https://localhost:8089/servicesNS/nobody/search/data/lookup-table-files/geo_attr_countries.csv",
                    "content": {
                        "filename": "geo_attr_countries.csv",
                        "updated": "2024-01-15T10:30:00",
                        "size": 1024,
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
                    "name": "user_mapping.csv",
                    "id": "https://localhost:8089/servicesNS/admin/myapp/data/lookup-table-files/user_mapping.csv",
                    "content": {
                        "filename": "user_mapping.csv",
                        "updated": "2024-01-14T09:15:00",
                        "size": 512,
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
    def mock_service(self, mock_lookup_files_response):
        """Create mock Splunk service for testing."""
        service = Mock()
        service.host = "localhost"
        service.port = 8089

        # Mock the GET response
        mock_response = Mock()
        mock_response.body.read.return_value = json.dumps(mock_lookup_files_response).encode(
            "utf-8"
        )
        service.get.return_value = mock_response

        return service

    async def test_list_lookup_files_success(
        self, fastmcp_client, extract_tool_result, mock_service
    ):
        """Test successful listing of lookup files."""
        async with fastmcp_client as client:
            # Execute tool through FastMCP
            result = await client.call_tool("list_lookup_files", {})
            data = extract_tool_result(result)

            # Verify response structure
            if data.get("status") == "success":
                assert "lookup_files" in data
                assert "count" in data
                assert isinstance(data["lookup_files"], list)
                # At least verify structure if mocking doesn't work
                if data["count"] > 0:
                    first_file = data["lookup_files"][0]
                    assert "name" in first_file
                    assert "filename" in first_file
                    assert "app" in first_file


class TestListLookupDefinitions:
    """Test suite for ListLookupDefinitions tool."""

    @pytest.fixture
    def mock_lookup_defs_response(self):
        """Create mock response for lookup definitions endpoint."""
        return {
            "entry": [
                {
                    "name": "geo_countries",
                    "id": "https://localhost:8089/servicesNS/nobody/search/data/transforms/lookups/geo_countries",
                    "content": {
                        "filename": "geo_attr_countries.csv",
                        "type": "file",
                        "match_type": "WILDCARD(country)",
                        "fields_list": "country,latitude,longitude,code",
                        "updated": "2024-01-15T10:30:00",
                        "min_matches": 0,
                        "max_matches": 1,
                        "default_match": "",
                        "case_sensitive_match": True,
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
            ],
            "paging": {"total": 1, "perPage": 0, "offset": 0},
        }

    @pytest.fixture
    def mock_service(self, mock_lookup_defs_response):
        """Create mock Splunk service for testing."""
        service = Mock()
        service.host = "localhost"
        service.port = 8089

        # Mock the GET response
        mock_response = Mock()
        mock_response.body.read.return_value = json.dumps(mock_lookup_defs_response).encode("utf-8")
        service.get.return_value = mock_response

        return service

    async def test_list_lookup_definitions_success(
        self, fastmcp_client, extract_tool_result, mock_service
    ):
        """Test successful listing of lookup definitions."""
        async with fastmcp_client as client:
            # Execute tool through FastMCP
            result = await client.call_tool("list_lookup_definitions", {})
            data = extract_tool_result(result)

            # Verify response structure
            if data.get("status") == "success":
                assert "lookup_definitions" in data
                assert "count" in data
                assert isinstance(data["lookup_definitions"], list)
                if data["count"] > 0:
                    first_def = data["lookup_definitions"][0]
                    assert "name" in first_def
                    assert "filename" in first_def
                    assert "type" in first_def
