"""
Sentry Integration for MCP Server for Splunk.

Optional module - works without sentry-sdk installed.
Install with: pip install mcp-server-for-splunk[sentry]
"""

from .config import (
    _sentry_initialized,
    _sentry_sdk_available,
    init_sentry,
    is_sentry_enabled,
    mcp_request_id,
    mcp_session_id,
    mcp_tool_name,
)
from .context import (
    add_breadcrumb,
    capture_mcp_error,
    mcp_span,
    set_mcp_context,
)
from .decorators import (
    trace_mcp_resource,
    trace_mcp_tool,
    trace_resource_read,
    trace_splunk_operation,
    trace_tool_call,
)
from .http_middleware import SentryHTTPMiddleware
from .mcp_middleware import SentryMCPMiddleware, create_sentry_middlewares

__all__ = [
    # Config
    "_sentry_sdk_available",
    "_sentry_initialized",
    "init_sentry",
    "is_sentry_enabled",
    "mcp_session_id",
    "mcp_request_id",
    "mcp_tool_name",
    # Context
    "mcp_span",
    "set_mcp_context",
    "capture_mcp_error",
    "add_breadcrumb",
    # Decorators
    "trace_mcp_tool",
    "trace_mcp_resource",
    "trace_splunk_operation",
    "trace_tool_call",
    "trace_resource_read",
    # Middleware
    "SentryHTTPMiddleware",
    "SentryMCPMiddleware",
    "create_sentry_middlewares",
]

