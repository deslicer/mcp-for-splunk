"""Tests for FastMCP Context helpers on alert tools."""

from unittest.mock import AsyncMock, Mock

import pytest

from src.core.base import BaseTool
from src.tools.alerts.alert_tool_context import AlertContextMixin
from src.tools.alerts.update_alert import UpdateAlert


class _StubAlertTool(AlertContextMixin, BaseTool):
    async def execute(self, ctx, **kwargs):  # pragma: no cover - not used
        return {}


@pytest.mark.asyncio
async def test_fail_sends_ctx_error_and_structured_dict() -> None:
    tool = _StubAlertTool("stub", "stub")
    ctx = AsyncMock()
    result = await tool.fail(ctx, "bad request", name="x", created=False)
    ctx.error.assert_awaited_once_with("bad request")
    assert result["status"] == "error"
    assert result["error"] == "bad request"
    assert result["created"] is False


@pytest.mark.asyncio
async def test_notify_progress_uses_fastmcp_report_progress() -> None:
    tool = _StubAlertTool("stub", "stub")
    ctx = AsyncMock()
    await tool.notify_progress(ctx, 50, 100, "halfway")
    ctx.report_progress.assert_awaited_once_with(
        progress=50, total=100, message="halfway"
    )


@pytest.mark.asyncio
async def test_unknown_actions_fails_closed_when_catalog_errors() -> None:
    tool = _StubAlertTool("stub", "stub")
    ctx = AsyncMock()
    service = Mock()
    service.get.side_effect = RuntimeError("catalog down")
    message = await tool.unknown_actions_message(
        ctx, service, [{"name": "email", "params": {}, "enabled": True}]
    )
    assert message is not None
    assert "Could not validate alert actions" in message
    ctx.warning.assert_not_called()


@pytest.mark.asyncio
async def test_update_alert_rejects_empty_override_actions() -> None:
    tool = UpdateAlert("update_alert", "update")
    tool.check_splunk_available = lambda ctx: (True, Mock(), "")  # type: ignore[method-assign]
    ctx = AsyncMock()
    result = await tool.execute(ctx, name="x", actions_mode="override", actions=[])
    assert result["status"] == "error"
    assert "non-empty actions list" in result["error"]
    ctx.error.assert_awaited()
