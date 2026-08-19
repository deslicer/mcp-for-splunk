"""Tests for alert create/update/delete and list_alert_actions tools."""

import pytest


class TestAlertToolAvailability:
    """Verify the new alert management tools are registered."""

    async def test_alert_tools_are_registered(self, fastmcp_client):
        async with fastmcp_client as client:
            tools = await client.list_tools()
            names = {tool.name for tool in tools}
            assert "list_alert_actions" in names
            assert "create_alert" in names
            assert "update_alert" in names
            assert "delete_alert" in names

    async def test_update_alert_describes_patch_and_override(self, fastmcp_client):
        async with fastmcp_client as client:
            tools = await client.list_tools()
            update_alert = next(tool for tool in tools if tool.name == "update_alert")
            description = (update_alert.description or "").lower()
            assert "patch" in description
            assert "override" in description
            assert update_alert.inputSchema is not None

    async def test_delete_alert_requires_confirm_in_schema(self, fastmcp_client):
        async with fastmcp_client as client:
            tools = await client.list_tools()
            delete_alert = next(tool for tool in tools if tool.name == "delete_alert")
            properties = (delete_alert.inputSchema or {}).get("properties") or {}
            assert "confirm" in properties

    async def test_create_alert_without_splunk_returns_error(
        self, fastmcp_client, extract_tool_result
    ):
        async with fastmcp_client as client:
            result = await client.call_tool(
                "create_alert",
                {
                    "name": "unit_test_alert",
                    "search": "index=_internal | head 1",
                    "cron_schedule": "0 0 1 1 *",
                },
            )
            data = extract_tool_result(result)
            assert isinstance(data, dict)
            assert "status" in data
            if data.get("status") == "error":
                assert "error" in data
            else:
                pytest.skip("Live Splunk available in this test environment")
