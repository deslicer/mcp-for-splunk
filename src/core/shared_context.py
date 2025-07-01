"""
Shared context variables for the MCP server.

This module contains context variables that need to be shared across modules
to avoid circular import issues.
"""

from contextvars import ContextVar

# Context variable to store HTTP headers for MCP middleware access
http_headers_context: ContextVar[dict] = ContextVar('http_headers', default={}) 