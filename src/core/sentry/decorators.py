"""Decorators for MCP and Splunk operation tracing."""

import asyncio
import functools
import inspect
import logging
from collections.abc import Callable
from typing import Any, TypeVar

from .config import _sentry_initialized, mcp_session_id, mcp_tool_name

logger = logging.getLogger(__name__)

F = TypeVar("F", bound=Callable[..., Any])


def _is_coroutine_function(func) -> bool:
    """Check if a function is a coroutine function."""
    return asyncio.iscoroutinefunction(func) or inspect.iscoroutinefunction(func)


def _sanitize_kwargs(kwargs: dict) -> dict:
    """Sanitize keyword arguments for safe logging/tracing."""
    sensitive_keys = {"password", "token", "secret", "authorization", "api_key", "apikey"}
    sanitized = {}

    for key, value in kwargs.items():
        key_lower = key.lower()
        if any(s in key_lower for s in sensitive_keys):
            sanitized[key] = "***REDACTED***"
        elif isinstance(value, str) and len(value) > 500:
            sanitized[key] = f"{value[:100]}...(truncated, {len(value)} chars)"
        else:
            sanitized[key] = value

    return sanitized


def trace_mcp_tool(tool_name: str | None = None):
    """Decorator to trace MCP tool executions with Sentry spans."""

    def decorator(func: F) -> F:
        name = tool_name or func.__name__

        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            if not _sentry_initialized:
                return await func(*args, **kwargs)

            try:
                import sentry_sdk

                token = mcp_tool_name.set(name)

                try:
                    with sentry_sdk.start_span(
                        op="mcp.tool",
                        name=f"tools/call {name}",
                        description=f"Execute MCP tool: {name}",
                    ) as span:
                        span.set_data("mcp.tool.name", name)
                        span.set_data("mcp.method.name", "tools/call")

                        session_id = mcp_session_id.get()
                        if session_id:
                            span.set_data("mcp.session.id", session_id)

                        sanitized_kwargs = _sanitize_kwargs(kwargs)
                        span.set_data("mcp.tool.arguments", sanitized_kwargs)

                        try:
                            result = await func(*args, **kwargs)
                            span.set_data("mcp.tool.status", "success")

                            if isinstance(result, dict):
                                span.set_data("mcp.tool.result_keys", list(result.keys()))

                            return result

                        except Exception as e:
                            span.set_data("mcp.tool.status", "error")
                            span.set_data("mcp.tool.error_type", type(e).__name__)
                            span.set_status("internal_error")
                            sentry_sdk.capture_exception(e)
                            raise

                finally:
                    mcp_tool_name.reset(token)

            except ImportError:
                return await func(*args, **kwargs)

        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            if not _sentry_initialized:
                return func(*args, **kwargs)

            try:
                import sentry_sdk

                token = mcp_tool_name.set(name)

                try:
                    with sentry_sdk.start_span(
                        op="mcp.tool",
                        name=f"tools/call {name}",
                    ) as span:
                        span.set_data("mcp.tool.name", name)

                        try:
                            result = func(*args, **kwargs)
                            span.set_data("mcp.tool.status", "success")
                            return result
                        except Exception as e:
                            span.set_data("mcp.tool.status", "error")
                            span.set_status("internal_error")
                            sentry_sdk.capture_exception(e)
                            raise
                finally:
                    mcp_tool_name.reset(token)

            except ImportError:
                return func(*args, **kwargs)

        if _is_coroutine_function(func):
            return async_wrapper  # type: ignore
        return sync_wrapper  # type: ignore

    return decorator


def trace_mcp_resource(resource_uri: str | None = None):
    """Decorator to trace MCP resource access with Sentry spans."""

    def decorator(func: F) -> F:
        uri = resource_uri or f"resource://{func.__name__}"

        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            if not _sentry_initialized:
                return await func(*args, **kwargs)

            try:
                import sentry_sdk

                with sentry_sdk.start_span(
                    op="mcp.resource",
                    name=f"resources/read {uri}",
                    description=f"Read MCP resource: {uri}",
                ) as span:
                    span.set_data("mcp.resource.uri", uri)
                    span.set_data("mcp.method.name", "resources/read")

                    try:
                        result = await func(*args, **kwargs)
                        span.set_data("mcp.resource.status", "success")

                        if isinstance(result, str):
                            span.set_data("mcp.resource.size_bytes", len(result.encode()))

                        return result
                    except Exception as e:
                        span.set_data("mcp.resource.status", "error")
                        span.set_status("internal_error")
                        sentry_sdk.capture_exception(e)
                        raise

            except ImportError:
                return await func(*args, **kwargs)

        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            if not _sentry_initialized:
                return func(*args, **kwargs)

            try:
                import sentry_sdk

                with sentry_sdk.start_span(
                    op="mcp.resource",
                    name=f"resources/read {uri}",
                ) as span:
                    span.set_data("mcp.resource.uri", uri)

                    try:
                        result = func(*args, **kwargs)
                        span.set_data("mcp.resource.status", "success")
                        return result
                    except Exception as e:
                        span.set_data("mcp.resource.status", "error")
                        sentry_sdk.capture_exception(e)
                        raise

            except ImportError:
                return func(*args, **kwargs)

        if _is_coroutine_function(func):
            return async_wrapper  # type: ignore
        return sync_wrapper  # type: ignore

    return decorator


def trace_splunk_operation(operation: str):
    """Decorator to trace Splunk-specific operations."""

    def decorator(func: F) -> F:
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            if not _sentry_initialized:
                return await func(*args, **kwargs)

            try:
                import sentry_sdk

                with sentry_sdk.start_span(
                    op="splunk.api",
                    name=f"splunk/{operation}",
                    description=f"Splunk operation: {operation}",
                ) as span:
                    span.set_data("splunk.operation", operation)

                    query = kwargs.get("query")
                    if not query and args:
                        first_arg = args[0] if len(args) > 0 else None
                        if isinstance(first_arg, str) and (
                            "search" in first_arg.lower()
                            or first_arg.startswith("|")
                            or "index=" in first_arg.lower()
                        ):
                            query = first_arg

                    if query and isinstance(query, str):
                        span.set_data(
                            "splunk.query_preview", query[:200] if len(query) > 200 else query
                        )
                        span.set_data("splunk.query_length", len(query))

                    try:
                        result = await func(*args, **kwargs)
                        span.set_data("splunk.status", "success")

                        if isinstance(result, dict):
                            if "results" in result and isinstance(result["results"], list):
                                span.set_data("splunk.result_count", len(result["results"]))
                            elif "count" in result:
                                span.set_data("splunk.result_count", result["count"])

                        return result

                    except Exception as e:
                        span.set_data("splunk.status", "error")
                        span.set_data("splunk.error_type", type(e).__name__)
                        span.set_status("internal_error")
                        sentry_sdk.capture_exception(e)
                        raise

            except ImportError:
                return await func(*args, **kwargs)

        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            if not _sentry_initialized:
                return func(*args, **kwargs)

            try:
                import sentry_sdk

                with sentry_sdk.start_span(
                    op="splunk.api",
                    name=f"splunk/{operation}",
                ) as span:
                    span.set_data("splunk.operation", operation)

                    try:
                        result = func(*args, **kwargs)
                        span.set_data("splunk.status", "success")
                        return result
                    except Exception as e:
                        span.set_data("splunk.status", "error")
                        sentry_sdk.capture_exception(e)
                        raise

            except ImportError:
                return func(*args, **kwargs)

        if _is_coroutine_function(func):
            return async_wrapper  # type: ignore
        return sync_wrapper  # type: ignore

    return decorator


# Convenience aliases
def trace_tool_call(tool_name: str):
    """Convenience decorator alias for trace_mcp_tool."""
    return trace_mcp_tool(tool_name)


def trace_resource_read(resource_uri: str):
    """Convenience decorator alias for trace_mcp_resource."""
    return trace_mcp_resource(resource_uri)

