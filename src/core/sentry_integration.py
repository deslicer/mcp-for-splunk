"""
Sentry Integration for MCP Server for Splunk.

Optional module - works without sentry-sdk installed.
Install with: pip install mcp-server-for-splunk[sentry]
"""

import functools
import logging
import os
from contextlib import contextmanager
from contextvars import ContextVar
from typing import Any, Callable, TypeVar

logger = logging.getLogger(__name__)

_sentry_sdk_available = False
try:
    import sentry_sdk
    _sentry_sdk_available = True
except ImportError:
    sentry_sdk = None  # type: ignore

_sentry_initialized = False

mcp_session_id: ContextVar[str | None] = ContextVar("mcp_session_id", default=None)
mcp_request_id: ContextVar[str | None] = ContextVar("mcp_request_id", default=None)
mcp_tool_name: ContextVar[str | None] = ContextVar("mcp_tool_name", default=None)

F = TypeVar("F", bound=Callable[..., Any])


def is_sentry_enabled() -> bool:
    """Check if Sentry is enabled via environment configuration and SDK is available."""
    if not _sentry_sdk_available:
        return False
    dsn = os.getenv("SENTRY_DSN", "").strip()
    return bool(dsn)


def init_sentry() -> bool:
    """Initialize Sentry SDK. Returns True if initialized successfully."""
    global _sentry_initialized
    
    if _sentry_initialized:
        return True
    
    if not _sentry_sdk_available:
        logger.info("sentry-sdk not installed")
        return False
    
    dsn = os.getenv("SENTRY_DSN", "").strip()
    if not dsn:
        logger.info("SENTRY_DSN not set, Sentry disabled")
        return False
    
    try:
        import sentry_sdk
        from sentry_sdk.integrations.asyncio import AsyncioIntegration
        from sentry_sdk.integrations.logging import LoggingIntegration
        from sentry_sdk.integrations.starlette import StarletteIntegration
        from sentry_sdk.integrations.httpx import HttpxIntegration
        
        try:
            from sentry_sdk.integrations.mcp import MCPIntegration
            _mcp_integration_available = True
        except ImportError:
            MCPIntegration = None  # type: ignore
            _mcp_integration_available = False
        
        environment = os.getenv("SENTRY_ENVIRONMENT", "development")
        release = os.getenv("SENTRY_RELEASE", "mcp-server-splunk@0.4.0")
        traces_sample_rate = float(os.getenv("SENTRY_TRACES_SAMPLE_RATE", "1.0"))
        profiles_sample_rate = float(os.getenv("SENTRY_PROFILES_SAMPLE_RATE", "0.1"))
        debug = os.getenv("SENTRY_DEBUG", "false").lower() == "true"
        enable_logs = os.getenv("SENTRY_ENABLE_LOGS", "true").lower() == "true"
        
        def traces_sampler(sampling_context: dict) -> float:
            """Custom sampler - always trace MCP/tool ops, lower rate for health checks."""
            ctx = sampling_context.get("transaction_context", {})
            name = ctx.get("name", "")
            op = ctx.get("op", "")
            
            if "mcp" in op.lower() or "mcp" in name.lower() or "tool" in op.lower():
                return 1.0
            if "/health" in name or "health" in op.lower():
                return 0.01
            return traces_sample_rate
        
        sentry_sdk.init(
            dsn=dsn,
            environment=environment,
            release=release,
            debug=debug,
            traces_sampler=traces_sampler,
            profiles_sample_rate=profiles_sample_rate,
            enable_logs=enable_logs,
            auto_session_tracking=True,
            send_default_pii=os.getenv("SENTRY_SEND_PII", "true").lower() == "true",
            integrations=[
                *([MCPIntegration()] if _mcp_integration_available else []),
                AsyncioIntegration(),
                StarletteIntegration(
                    transaction_style="endpoint",
                    failed_request_status_codes={400, 401, 403, 404, 500, 502, 503},
                ),
                HttpxIntegration(),
                LoggingIntegration(
                    sentry_logs_level=logging.INFO,
                    level=logging.INFO,
                    event_level=logging.ERROR,
                ),
            ],
            attach_stacktrace=True,
            max_breadcrumbs=100,
            before_send=_before_send_hook,
            before_send_transaction=_before_send_transaction_hook,
        )
        
        _sentry_initialized = True
        logger.info(
            "Sentry initialized (env=%s, release=%s, mcp=%s)",
            environment, release, "yes" if _mcp_integration_available else "no",
        )
        return True
        
    except ImportError as e:
        logger.warning("Sentry SDK import error: %s", e)
        return False
    except Exception as e:
        logger.error("Failed to initialize Sentry: %s", e)
        return False


def _before_send_hook(event: dict, hint: dict) -> dict | None:
    """
    Enrich error events with MCP context before sending to Sentry.
    """
    try:
        # Add MCP context tags
        session_id = mcp_session_id.get()
        request_id = mcp_request_id.get()
        tool_name = mcp_tool_name.get()
        
        if "tags" not in event:
            event["tags"] = {}
        
        if session_id:
            event["tags"]["mcp.session.id"] = session_id
        if request_id:
            event["tags"]["mcp.request.id"] = request_id
        if tool_name:
            event["tags"]["mcp.tool.name"] = tool_name
        
        # Add MCP context as extra data
        if "extra" not in event:
            event["extra"] = {}
        
        event["extra"]["mcp_context"] = {
            "session_id": session_id,
            "request_id": request_id,
            "tool_name": tool_name,
        }
        
    except Exception:
        pass  # Don't fail event sending if enrichment fails
    
    return event


def _before_send_transaction_hook(event: dict, hint: dict) -> dict | None:
    """Enrich transaction events with MCP metadata."""
    try:
        session_id = mcp_session_id.get()
        if session_id:
            if "tags" not in event:
                event["tags"] = {}
            event["tags"]["mcp.session.id"] = session_id
    except Exception:
        pass
    
    return event


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
                
                # Set tool context for error enrichment
                token = mcp_tool_name.set(name)
                
                try:
                    with sentry_sdk.start_span(
                        op="mcp.tool",
                        name=f"tools/call {name}",
                        description=f"Execute MCP tool: {name}",
                    ) as span:
                        # Set tool metadata
                        span.set_data("mcp.tool.name", name)
                        span.set_data("mcp.method.name", "tools/call")
                        
                        # Extract session info from context if available
                        session_id = mcp_session_id.get()
                        if session_id:
                            span.set_data("mcp.session.id", session_id)
                        
                        # Track input parameters (sanitized)
                        sanitized_kwargs = _sanitize_kwargs(kwargs)
                        span.set_data("mcp.tool.arguments", sanitized_kwargs)
                        
                        try:
                            result = await func(*args, **kwargs)
                            
                            # Track success
                            span.set_data("mcp.tool.status", "success")
                            
                            # Track result metadata (not content)
                            if isinstance(result, dict):
                                span.set_data("mcp.tool.result_keys", list(result.keys()))
                            
                            return result
                            
                        except Exception as e:
                            # Track failure
                            span.set_data("mcp.tool.status", "error")
                            span.set_data("mcp.tool.error_type", type(e).__name__)
                            span.set_status("internal_error")
                            
                            # Capture exception with MCP context
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
        
        # Return appropriate wrapper based on function type
        if asyncio_iscoroutinefunction(func):
            return async_wrapper  # type: ignore
        return sync_wrapper  # type: ignore
    
    return decorator


def trace_mcp_resource(resource_uri: str | None = None):
    """
    Decorator to trace MCP resource access with Sentry spans.
    
    Args:
        resource_uri: Optional resource URI override
    
    Example:
        @trace_mcp_resource("splunk://config/apps")
        async def get_apps_config(ctx: Context) -> str:
            ...
    """
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
                        
                        # Track response size if string
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
        
        if asyncio_iscoroutinefunction(func):
            return async_wrapper  # type: ignore
        return sync_wrapper  # type: ignore
    
    return decorator


def trace_splunk_operation(operation: str):
    """
    Decorator to trace Splunk-specific operations.
    
    Creates spans for Splunk API calls, searches, and other operations.
    
    Args:
        operation: Operation name (e.g., "search", "get_indexes", "create_alert")
    
    Example:
        @trace_splunk_operation("search")
        async def execute_search(query: str) -> dict:
            ...
    """
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
                    
                    # Track query if provided (first positional arg or 'query' kwarg)
                    query = kwargs.get("query")
                    if not query and args:
                        # Check if first arg looks like a query
                        first_arg = args[0] if len(args) > 0 else None
                        if isinstance(first_arg, str) and ("search" in first_arg.lower() or 
                                                            first_arg.startswith("|") or
                                                            "index=" in first_arg.lower()):
                            query = first_arg
                    
                    if query and isinstance(query, str):
                        # Store truncated query for debugging
                        span.set_data("splunk.query_preview", query[:200] if len(query) > 200 else query)
                        span.set_data("splunk.query_length", len(query))
                    
                    try:
                        result = await func(*args, **kwargs)
                        span.set_data("splunk.status", "success")
                        
                        # Track result count if available
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
        
        if asyncio_iscoroutinefunction(func):
            return async_wrapper  # type: ignore
        return sync_wrapper  # type: ignore
    
    return decorator


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
    
    Args:
        session_id: MCP session identifier
        request_id: MCP request identifier  
        user_id: User identifier (if authenticated)
        extra: Additional context data
    """
    if not _sentry_initialized:
        return
    
    try:
        import sentry_sdk
        
        # Set context variables
        if session_id:
            mcp_session_id.set(session_id)
        if request_id:
            mcp_request_id.set(request_id)
        
        # Set Sentry scope
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
    
    Args:
        error: The exception to capture
        tool_name: Name of the tool that failed
        resource_uri: URI of the resource that failed
        extra: Additional context data
    """
    if not _sentry_initialized:
        return
    
    try:
        import sentry_sdk
        
        with sentry_sdk.push_scope() as scope:
            # Add MCP context
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
    
    Args:
        message: Breadcrumb message
        category: Category (e.g., "mcp.tool", "mcp.resource", "splunk")
        level: Severity level (info, warning, error)
        data: Additional data
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
    except Exception:
        pass


def _sanitize_kwargs(kwargs: dict) -> dict:
    """
    Sanitize keyword arguments for safe logging/tracing.
    
    Masks sensitive values like passwords, tokens, and secrets.
    """
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


def asyncio_iscoroutinefunction(func) -> bool:
    """Check if a function is a coroutine function."""
    import asyncio
    import inspect
    
    return asyncio.iscoroutinefunction(func) or inspect.iscoroutinefunction(func)


# Convenience functions for common MCP operations

def trace_tool_call(tool_name: str):
    """Convenience decorator alias for trace_mcp_tool."""
    return trace_mcp_tool(tool_name)


def trace_resource_read(resource_uri: str):
    """Convenience decorator alias for trace_mcp_resource."""
    return trace_mcp_resource(resource_uri)

