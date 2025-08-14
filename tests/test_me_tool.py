"""
Test for the Me tool.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest
from fastmcp import Context

from src.tools.admin.me import Me


class TestMeTool:
    """Test the Me tool functionality."""

    def test_tool_metadata(self):
        """Test that the tool metadata is correctly defined."""
        tool = Me("me", "test")

        assert tool.METADATA.name == "me"
        assert tool.METADATA.category == "admin"
        assert "user" in tool.METADATA.tags
        assert "authentication" in tool.METADATA.tags
        assert "current" in tool.METADATA.tags
        assert tool.METADATA.requires_connection is True
        assert "currently authenticated user" in tool.METADATA.description

    @pytest.mark.asyncio
    async def test_execute_success(self):
        """Test successful execution of the me tool."""
        tool = Me("me", "test")
        ctx = AsyncMock(spec=Context)

        # Mock the Splunk service and user objects
        mock_service = MagicMock()
        mock_service.username = "testuser"

        # Mock user object
        mock_user = MagicMock()
        mock_user.name = "testuser"
        mock_user.content = {
            "realname": "Test User",
            "email": "test@example.com",
            "roles": ["admin", "user"],
            "type": "Splunk",
            "defaultApp": "search",
            "force_change_pass": False,
            "locked_out": False,
            "restart_background_jobs": True,
            "tz": "UTC",
        }

        # Mock roles for capabilities
        mock_admin_role = MagicMock()
        mock_admin_role.content = {"capabilities": ["admin_all_objects", "edit_user"]}

        mock_user_role = MagicMock()
        mock_user_role.content = {"capabilities": ["search"]}

        # Set up service mocks
        mock_service.users = {"testuser": mock_user}
        mock_service.roles = {"admin": mock_admin_role, "user": mock_user_role}

        # Mock the check_splunk_available method
        tool.check_splunk_available = MagicMock(return_value=(True, mock_service, None))

        # Execute the tool
        result = await tool.execute(ctx)

        # Verify the result
        assert result["status"] == "success"
        assert "data" in result

        user_data = result["data"]
        assert user_data["username"] == "testuser"
        assert user_data["realname"] == "Test User"
        assert user_data["email"] == "test@example.com"
        assert user_data["roles"] == ["admin", "user"]
        assert user_data["type"] == "Splunk"
        assert user_data["defaultApp"] == "search"
        assert "capabilities" in user_data
        assert "admin_all_objects" in user_data["capabilities"]
        assert "edit_user" in user_data["capabilities"]
        assert "search" in user_data["capabilities"]

    @pytest.mark.asyncio
    async def test_execute_no_username(self):
        """Test execution when service.username is None."""
        tool = Me("me", "test")
        ctx = AsyncMock(spec=Context)

        # Mock service with no username
        mock_service = MagicMock()
        mock_service.username = None

        # Mock the check_splunk_available method
        tool.check_splunk_available = MagicMock(return_value=(True, mock_service, None))

        # Execute the tool
        result = await tool.execute(ctx)

        # Verify error response
        assert result["status"] == "error"
        assert "Unable to determine current username" in result["error"]

    @pytest.mark.asyncio
    async def test_execute_user_not_found(self):
        """Test execution when current user is not found in users collection."""
        tool = Me("me", "test")
        ctx = AsyncMock(spec=Context)

        # Mock service with username but user not in collection
        mock_service = MagicMock()
        mock_service.username = "testuser"
        mock_service.users = {}  # Empty users collection

        # Mock the check_splunk_available method
        tool.check_splunk_available = MagicMock(return_value=(True, mock_service, None))

        # Execute the tool
        result = await tool.execute(ctx)

        # Verify error response
        assert result["status"] == "error"
        assert "not found in users collection" in result["error"]

    @pytest.mark.asyncio
    async def test_execute_no_splunk_connection(self):
        """Test execution when Splunk is not available."""
        tool = Me("me", "test")
        ctx = AsyncMock(spec=Context)

        # Mock the check_splunk_available method to return unavailable
        tool.check_splunk_available = MagicMock(return_value=(False, None, "Connection failed"))

        # Execute the tool
        result = await tool.execute(ctx)

        # Verify error response
        assert result["status"] == "error"
        assert result["error"] == "Connection failed"

    @pytest.mark.asyncio
    async def test_execute_with_capabilities_error(self):
        """Test execution when there's an error getting capabilities."""
        tool = Me("me", "test")
        ctx = AsyncMock(spec=Context)

        # Mock the Splunk service and user objects
        mock_service = MagicMock()
        mock_service.username = "testuser"

        # Mock user object
        mock_user = MagicMock()
        mock_user.name = "testuser"
        mock_user.content = {
            "realname": "Test User",
            "email": "test@example.com",
            "roles": ["admin"],
            "type": "Splunk",
            "defaultApp": "search",
        }

        # Set up service mocks - simulate error accessing roles
        mock_service.users = {"testuser": mock_user}
        mock_service.roles = MagicMock()
        mock_service.roles.__contains__ = MagicMock(side_effect=Exception("Role access error"))

        # Mock the check_splunk_available method
        tool.check_splunk_available = MagicMock(return_value=(True, mock_service, None))

        # Execute the tool
        result = await tool.execute(ctx)

        # Verify the result - should still succeed but with empty capabilities
        assert result["status"] == "success"
        assert "data" in result

        user_data = result["data"]
        assert user_data["username"] == "testuser"
        assert user_data["capabilities"] == []

    @pytest.mark.asyncio
    async def test_execute_filters_none_values(self):
        """Test that None values are filtered out of the response."""
        tool = Me("me", "test")
        ctx = AsyncMock(spec=Context)

        # Mock the Splunk service and user objects
        mock_service = MagicMock()
        mock_service.username = "testuser"

        # Mock user object with some None values
        mock_user = MagicMock()
        mock_user.name = "testuser"
        mock_user.content = {
            "realname": None,  # This should be filtered out
            "email": "test@example.com",
            "roles": ["user"],
            "type": "Splunk",
            "defaultApp": None,  # This should be filtered out
            "tz": None,  # This should be filtered out
        }

        # Mock role for capabilities
        mock_user_role = MagicMock()
        mock_user_role.content = {"capabilities": ["search"]}

        # Set up service mocks
        mock_service.users = {"testuser": mock_user}
        mock_service.roles = {"user": mock_user_role}

        # Mock the check_splunk_available method
        tool.check_splunk_available = MagicMock(return_value=(True, mock_service, None))

        # Execute the tool
        result = await tool.execute(ctx)

        # Verify the result
        assert result["status"] == "success"
        user_data = result["data"]

        # Check that None values were filtered out
        assert "realname" not in user_data
        assert "defaultApp" not in user_data
        assert "tz" not in user_data

        # Check that non-None values are present
        assert user_data["username"] == "testuser"
        assert user_data["email"] == "test@example.com"
        assert user_data["roles"] == ["user"]
        assert user_data["type"] == "Splunk"
