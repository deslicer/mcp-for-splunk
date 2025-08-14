"""
Shared context variables for the MCP server.

This module contains context variables that need to be shared across modules
to avoid circular import issues.
"""

from contextvars import ContextVar

# Context variable to store HTTP headers for MCP middleware access
# Avoid mutable default for ContextVar (ruff B039)
http_headers_context: ContextVar[dict | None] = ContextVar("http_headers", default=None)
