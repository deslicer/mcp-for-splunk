"""Turn tool status:error payloads into MCP errors, preserving search metadata."""

from typing import Any

from fastmcp.exceptions import ToolError
from fastmcp.tools import ToolResult


def raise_on_tool_error_status(result: Any) -> Any:
    """Keep errors marked as failures, including structured search diagnostics."""
    if isinstance(result, dict) and result.get("status") == "error":
        message = str(result.get("error") or "Tool failed")
        if {"error_code", "execution_stage", "search_started"} <= result.keys():
            return ToolResult(content=message, structured_content=result, is_error=True)
        raise ToolError(message)
    return result


def wrap_unexpected_tool_failure(exc: BaseException) -> ToolError:
    """Convert unexpected tool exceptions into an agent-visible ToolError."""
    if isinstance(exc, ToolError):
        return exc
    return ToolError(str(exc))


def is_tool_error_result(result: Any) -> bool:
    """Recognize MCP error results even when no exception was raised."""
    return getattr(result, "is_error", False) is True or (
        isinstance(result, dict) and result.get("isError") is True
    )
