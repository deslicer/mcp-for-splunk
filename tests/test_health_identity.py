"""Health identity must belong to the requested connection, never a fallback."""
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

import pytest

from mcp_server_for_splunk.tools.health.status import GetSplunkHealth


@pytest.mark.asyncio
async def test_health_reports_instance_identity_from_client_headers():
    tool = GetSplunkHealth("get_splunk_health", "health")
    tool.get_client_config_from_context = AsyncMock(return_value={"splunk_host": "endpoint"})
    ctx = SimpleNamespace(info=AsyncMock(), error=AsyncMock())
    service = Mock()
    service.info = {"version": "10.2.8", "host": "os-host", "serverName": "retained-name", "guid": "instance-1"}
    with patch("mcp_server_for_splunk.tools.health.status.get_splunk_service", return_value=service):
        result = await tool.execute(ctx)
    assert result["server_name"] == "retained-name"
    assert result["hostname"] == "os-host"
    assert result["instance_guid"] == "instance-1"
    assert result["connection_source"] == "client_config"
    service.get.assert_not_called()


@pytest.mark.asyncio
async def test_failed_client_connection_never_reports_default_server_identity():
    tool = GetSplunkHealth("get_splunk_health", "health")
    tool.get_client_config_from_context = AsyncMock(return_value={"splunk_host": "endpoint"})
    tool.get_splunk_service = AsyncMock()
    ctx = SimpleNamespace(info=AsyncMock(), error=AsyncMock())
    with patch("mcp_server_for_splunk.tools.health.status.get_splunk_service", side_effect=RuntimeError("unreachable")):
        result = await tool.execute(ctx)
    assert result["status"] == "error"
    assert "instance_guid" not in result
    tool.get_splunk_service.assert_not_called()
