"""Context management utilities for MCP tracing."""

import logging
from contextlib import contextmanager
from typing import Any

from .config import (
    _sentry_initialized,
    mcp_request_id,
    mcp_session_id,
)

logger = logging.getLogger(__name__)


@contextmanager
def mcp_span(op: str, name: str, description: str | None = None, **attributes: Any):
    """Create an MCP-specific span for tracing operations."""
    if not _sentry_initialized:
        yield None
        return

    try:
        import sentry_sdk

        with sentry_sdk.start_span(op=op, name=name, description=description) as span:
            for key, value in attributes.items():
                if value:
                    span.set_data(f"mcp.{key}" if not key.startswith("mcp.") else key, value)
            yield span

    except Exception as e:
        logger.debug("Error creating Sentry span: %s", e)
        yield None


def set_mcp_context(
    session_id: str | None = None,
    request_id: str | None = None,
    user_id: str | None = None,
    extra: dict | None = None,
):
    """
    Set MCP context for the current request/session.

    Call this at the start of request processing to enrich all
    subsequent spans and error events with MCP context.
    """
    if not _sentry_initialized:
        return

    try:
        import sentry_sdk

        if session_id:
            mcp_session_id.set(session_id)
        if request_id:
            mcp_request_id.set(request_id)

        with sentry_sdk.configure_scope() as scope:
            if session_id:
                scope.set_tag("mcp.session.id", session_id)
            if request_id:
                scope.set_tag("mcp.request.id", request_id)
            if user_id:
                scope.set_user({"id": user_id})
            if extra:
                scope.set_context("mcp", extra)

    except Exception as e:
        logger.debug("Error setting MCP context: %s", e)


def capture_mcp_error(
    error: Exception,
    tool_name: str | None = None,
    resource_uri: str | None = None,
    extra: dict | None = None,
):
    """
    Capture an error with MCP context.

    Use this to manually capture exceptions with rich MCP metadata.
    """
    if not _sentry_initialized:
        return

    try:
        import sentry_sdk

        with sentry_sdk.push_scope() as scope:
            scope.set_tag("mcp.error.source", "manual")

            if tool_name:
                scope.set_tag("mcp.tool.name", tool_name)
            if resource_uri:
                scope.set_tag("mcp.resource.uri", resource_uri)

            session_id = mcp_session_id.get()
            request_id = mcp_request_id.get()

            if session_id:
                scope.set_tag("mcp.session.id", session_id)
            if request_id:
                scope.set_tag("mcp.request.id", request_id)

            if extra:
                scope.set_context("mcp_error_context", extra)

            sentry_sdk.capture_exception(error)

    except Exception as e:
        logger.debug("Error capturing MCP error: %s", e)


def add_breadcrumb(
    message: str,
    category: str = "mcp",
    level: str = "info",
    data: dict | None = None,
):
    """
    Add a breadcrumb for MCP operation tracking.

    Breadcrumbs appear in error reports and help understand
    the sequence of events leading to an error.
    """
    if not _sentry_initialized:
        return

    try:
        import sentry_sdk

        sentry_sdk.add_breadcrumb(
            message=message,
            category=category,
            level=level,
            data=data or {},
        )
    except Exception as e:
        logger.debug("Error adding breadcrumb: %s", e)

