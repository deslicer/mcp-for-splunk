"""Turn tool status:error payloads into MCP ToolError results."""

from typing import Any

from fastmcp.exceptions import ToolError


def raise_on_tool_error_status(result: Any) -> Any:
    """Raise ToolError when a tool returned a successful-looking error dict."""
    if isinstance(result, dict) and result.get("status") == "error":
        raise ToolError(str(result.get("error") or "Tool failed"))
    return result


def wrap_unexpected_tool_failure(exc: BaseException) -> ToolError:
    """Convert unexpected tool exceptions into an agent-visible ToolError."""
    if isinstance(exc, ToolError):
        return exc
    return ToolError(str(exc))
