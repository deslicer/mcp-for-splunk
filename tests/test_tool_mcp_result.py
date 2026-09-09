from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from fastmcp.exceptions import ToolError

from src.core.base import BaseTool
from src.core.loader import ToolLoader
from src.core.tool_mcp_result import raise_on_tool_error_status, wrap_unexpected_tool_failure


def test_raise_on_tool_error_status_surfaces_message() -> None:
    with pytest.raises(ToolError, match="count must be between 1 and 200"):
        raise_on_tool_error_status(
            {"status": "error", "error": "count must be between 1 and 200", "indexes": []}
        )


def test_raise_on_tool_error_status_passes_success_through() -> None:
    payload = {"status": "success", "indexes": ["main"]}
    assert raise_on_tool_error_status(payload) is payload


def test_wrap_unexpected_tool_failure_is_tool_error() -> None:
    with pytest.raises(ToolError, match="boom"):
        raise wrap_unexpected_tool_failure(RuntimeError("boom"))


@pytest.mark.asyncio
async def test_tool_wrapper_raises_status_error(monkeypatch: pytest.MonkeyPatch) -> None:
    class _ErrorTool(BaseTool):
        async def execute(self, ctx, **kwargs):
            return {
                "status": "error",
                "error": "count must be between 1 and 200",
                "indexes": [],
            }

    monkeypatch.setattr("src.core.loader.get_context", lambda: SimpleNamespace())
    wrapper = ToolLoader(Mock())._create_tool_wrapper(_ErrorTool, "list_indexes")
    with pytest.raises(ToolError, match="count must be between 1 and 200"):
        await wrapper()
