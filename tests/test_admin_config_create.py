"""
Tests for the CreateConfig admin tool.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest
from fastmcp import Context

from src.tools.admin.config import CreateConfig


class TestCreateConfigTool:
    @pytest.mark.asyncio
    async def test_create_new_stanza_rest(self, mock_splunk_service):
        tool = CreateConfig("create_config", "test")
        ctx = AsyncMock(spec=Context)

        # Ensure default owner fallback triggers 'nobody' namespace path
        if hasattr(mock_splunk_service, "username"):
            delattr(mock_splunk_service, "username")

        # Mock availability
        tool.check_splunk_available = MagicMock(return_value=(True, mock_splunk_service, ""))

        result = await tool.execute(
            ctx,
            conf_file="props",
            stanza="myweblogs",
            settings={"CHARSET": "UTF-8", "SHOULD_LINEMERGE": "false"},
        )

        assert result["status"] == "success"
        assert result["action"] == "created"
        assert set(result["added_keys"]) == {"CHARSET", "SHOULD_LINEMERGE"}

        # Verify reading back via REST GET handler returns content
        # Stanza should now exist in mocked service
        resp = mock_splunk_service.get(
            "/services/configs/conf-props/myweblogs",
            owner="nobody",
            app="search",
            output_mode="json",
        )
        payload = resp.body.read().decode("utf-8")
        assert "myweblogs" in payload
        assert "CHARSET" in payload

    @pytest.mark.asyncio
    async def test_update_add_only_new_keys_overwrite_false(self, mock_splunk_service):
        tool = CreateConfig("create_config", "test")
        ctx = AsyncMock(spec=Context)

        # Precreate stanza - use a stanza that doesn't exist in initial mock configs
        tool.check_splunk_available = MagicMock(return_value=(True, mock_splunk_service, ""))
        await tool.execute(
            ctx,
            conf_file="transforms",
            stanza="test_lookup",  # Use different stanza name to avoid initial mock config
            settings={"external_cmd": "test_lookup.py"},
        )

        # Attempt to add an existing key with a different value without overwrite
        result = await tool.execute(
            ctx,
            conf_file="transforms",
            stanza="test_lookup",  # Use same stanza name
            settings={"external_cmd": "test_lookup_v2.py", "fields_list": "clientip"},
            overwrite=False,
        )

        assert result["status"] == "success"
        # Only new key should be added; existing differing key should be skipped
        assert result["action"] == "updated"
        assert result["added_keys"] == ["fields_list"]
        assert result["changed_keys"] == []

    @pytest.mark.asyncio
    async def test_update_change_values_with_overwrite_true(self, mock_splunk_service):
        tool = CreateConfig("create_config", "test")
        ctx = AsyncMock(spec=Context)

        # Create stanza with an initial value - use a stanza that doesn't exist in initial mock configs
        tool.check_splunk_available = MagicMock(return_value=(True, mock_splunk_service, ""))
        await tool.execute(
            ctx,
            conf_file="web",
            stanza="test_settings",  # Use different stanza name to avoid initial mock config
            settings={"httpport": "8000"},
        )

        # Change existing value with overwrite=True
        result = await tool.execute(
            ctx,
            conf_file="web",
            stanza="test_settings",  # Use same stanza name
            settings={"httpport": "8001", "mgmtHostPort": "127.0.0.1:8089"},
            overwrite=True,
        )

        assert result["status"] == "success"
        assert result["action"] == "updated"
        # One changed existing key and one newly added key
        assert set(result["changed_keys"]) == {"httpport"}
        assert set(result["added_keys"]) == {"mgmtHostPort"}

    @pytest.mark.asyncio
    async def test_skip_when_no_changes(self, mock_splunk_service):
        tool = CreateConfig("create_config", "test")
        ctx = AsyncMock(spec=Context)

        tool.check_splunk_available = MagicMock(return_value=(True, mock_splunk_service, ""))

        # Create once
        await tool.execute(
            ctx,
            conf_file="server",
            stanza="general",
            settings={"serverName": "splunk-server"},
        )

        # No-op update (same value, overwrite=False)
        result = await tool.execute(
            ctx,
            conf_file="server",
            stanza="general",
            settings={"serverName": "splunk-server"},
            overwrite=False,
        )

        assert result["status"] == "success"
        assert result["action"] == "skipped"
