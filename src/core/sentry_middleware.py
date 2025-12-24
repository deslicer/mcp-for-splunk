"""Sentry middleware for MCP Server - HTTP and MCP request tracing."""

import logging
import time
import uuid
from typing import Any, cast

from fastmcp.server.middleware import Middleware, MiddlewareContext
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from .sentry_integration import (
    _sentry_initialized,
    add_breadcrumb,
    mcp_request_id,
    mcp_session_id,
    set_mcp_context,
)

logger = logging.getLogger(__name__)


class SentryHTTPMiddleware(BaseHTTPMiddleware):
    """ASGI middleware for Sentry HTTP request tracing."""

    async def dispatch(self, request: Request, call_next) -> Response:
        """Process HTTP request with Sentry tracing."""
        if not _sentry_initialized:
            return cast(Response, await call_next(request))

        try:
            import sentry_sdk
        except ImportError:
            return cast(Response, await call_next(request))

        # Extract session ID from headers
        session_id = (
            request.headers.get("MCP-Session-ID")
            or request.headers.get("mcp-session-id")
            or request.headers.get("X-Session-ID")
            or request.headers.get("x-session-id")
        )

        # Normalize session ID (handle "id, id" format)
        if session_id and "," in session_id:
            session_id = session_id.split(",")[0].strip()

        # Generate request ID
        request_id = (
            request.headers.get("X-Request-ID")
            or request.headers.get("x-request-id")
            or str(uuid.uuid4())[:8]
        )

        # Set context for downstream use
        session_token = mcp_session_id.set(session_id)
        request_token = mcp_request_id.set(request_id)

        # Determine transaction name based on path
        path = request.url.path
        method = request.method

        # Create a meaningful transaction name
        if "/mcp" in path:
            transaction_name = f"MCP {method} {path}"
        else:
            transaction_name = f"{method} {path}"

        start_time = time.perf_counter()

        try:
            with sentry_sdk.start_transaction(
                op="http.server",
                name=transaction_name,
                source="route",
            ) as transaction:
                # Set MCP-specific tags
                transaction.set_tag("mcp.transport", "http")
                if session_id:
                    transaction.set_tag("mcp.session.id", session_id)
                transaction.set_tag("mcp.request.id", request_id)

                # Set request metadata
                transaction.set_data("http.method", method)
                transaction.set_data("http.url", str(request.url))
                transaction.set_data("http.path", path)

                # Add client info
                if request.client:
                    transaction.set_data("client.ip", request.client.host)

                # Add breadcrumb for request start
                add_breadcrumb(
                    message=f"HTTP {method} {path}",
                    category="http.request",
                    level="info",
                    data={
                        "method": method,
                        "path": path,
                        "session_id": session_id,
                    },
                )

                # Process request
                response = cast(Response, await call_next(request))

                # Record response info
                duration_ms = (time.perf_counter() - start_time) * 1000
                transaction.set_data("http.status_code", response.status_code)
                transaction.set_data("http.duration_ms", round(duration_ms, 2))

                # Set status based on response code
                if response.status_code >= 500:
                    transaction.set_status("internal_error")
                elif response.status_code >= 400:
                    transaction.set_status("invalid_argument")
                else:
                    transaction.set_status("ok")

                return response

        except Exception as e:
            # Capture exception with context
            sentry_sdk.capture_exception(e)
            raise

        finally:
            # Reset context
            try:
                mcp_session_id.reset(session_token)
                mcp_request_id.reset(request_token)
            except Exception as e:
                logger.debug("Error resetting context: %s", e)


class SentryMCPMiddleware(Middleware):
    """MCP middleware for Sentry method-level tracing."""

    def __init__(self):
        super().__init__()
        logger.info("SentryMCPMiddleware initialized")

    async def on_request(self, context: MiddlewareContext, call_next):
        """Process MCP request with Sentry tracing."""
        if not _sentry_initialized:
            return await call_next(context)

        try:
            import sentry_sdk
        except ImportError:
            return await call_next(context)

        # Extract method and session info
        method = getattr(context, "method", "unknown")
        session_id = getattr(context, "session_id", None)

        # Set session context
        set_mcp_context(session_id=session_id)

        # Create span name based on MCP method
        span_op = self._get_span_op(method)
        span_name = self._get_span_name(context)

        start_time = time.perf_counter()

        try:
            with sentry_sdk.start_span(
                op=span_op,
                name=span_name,
                description=f"MCP method: {method}",
            ) as span:
                # Set MCP method metadata
                span.set_data("mcp.method.name", method)
                if session_id:
                    span.set_data("mcp.session.id", session_id)

                # Extract tool/resource-specific data
                self._set_method_specific_data(span, context)

                # Add breadcrumb
                add_breadcrumb(
                    message=f"MCP {method}",
                    category=f"mcp.{method.split('/')[0] if '/' in method else 'method'}",
                    level="info",
                    data={"method": method, "session_id": session_id},
                )

                try:
                    # Execute the actual MCP method
                    result = await call_next(context)

                    # Record success
                    duration_ms = (time.perf_counter() - start_time) * 1000
                    span.set_data("mcp.duration_ms", round(duration_ms, 2))
                    span.set_data("mcp.status", "success")
                    span.set_status("ok")

                    # Record result metadata
                    self._set_result_metadata(span, result)

                    return result

                except Exception as e:
                    # Record failure
                    duration_ms = (time.perf_counter() - start_time) * 1000
                    span.set_data("mcp.duration_ms", round(duration_ms, 2))
                    span.set_data("mcp.status", "error")
                    span.set_data("mcp.error.type", type(e).__name__)
                    span.set_data("mcp.error.message", str(e)[:500])
                    span.set_status("internal_error")

                    # Capture exception
                    sentry_sdk.capture_exception(e)
                    raise

        except ImportError:
            return await call_next(context)

    def _get_span_op(self, method: str) -> str:
        """Get the span operation type for an MCP method."""
        if method.startswith("tools/"):
            return "mcp.tool"
        elif method.startswith("resources/"):
            return "mcp.resource"
        elif method.startswith("prompts/"):
            return "mcp.prompt"
        elif method.startswith("session/"):
            return "mcp.session"
        else:
            return "mcp.method"

    def _get_span_name(self, context: MiddlewareContext) -> str:
        """Generate a descriptive span name for the MCP method."""
        method = getattr(context, "method", "unknown")

        # Try to extract tool/resource name for more specific naming
        try:
            if hasattr(context, "params") and context.params:
                params = context.params

                if method == "tools/call" and "name" in params:
                    return f"tools/call {params['name']}"
                elif method == "resources/read" and "uri" in params:
                    uri = params["uri"]
                    # Truncate long URIs
                    if len(uri) > 50:
                        uri = uri[:47] + "..."
                    return f"resources/read {uri}"
                elif method == "prompts/get" and "name" in params:
                    return f"prompts/get {params['name']}"
        except Exception as e:
            logger.debug("Error generating span name: %s", e)

        return method

    def _set_method_specific_data(self, span, context: MiddlewareContext):
        """Set method-specific data on the span."""
        import json

        try:
            # Extract params from context - FastMCP stores them in context.message
            params = None

            # First try context.params
            if hasattr(context, "params") and context.params:
                params = context.params
                logger.debug(f"Found params in context.params: {type(params).__name__}")
            # Then try context.message (FastMCP middleware context structure)
            elif hasattr(context, "message") and context.message:
                message = context.message
                if isinstance(message, dict):
                    # Message might contain params directly or as a nested key
                    params = message.get("params", message)
                    logger.debug(
                        f"Found params in context.message: {type(params).__name__}, keys: {list(params.keys()) if isinstance(params, dict) else 'N/A'}"
                    )
                elif hasattr(message, "params"):
                    params = message.params
                    logger.debug(f"Found params in context.message.params: {type(params).__name__}")
                elif hasattr(message, "__dict__"):
                    params = {k: v for k, v in message.__dict__.items() if not k.startswith("_")}
                    logger.debug(f"Extracted params from message object: {list(params.keys())}")

            if not params:
                logger.debug("No params found in context")
                span.set_data("request.params", None)
                return

            logger.debug(
                f"Params extracted: {type(params).__name__} with keys: {list(params.keys()) if isinstance(params, dict) else 'N/A'}"
            )

            # Get method from context (don't overwrite params!)
            method = getattr(context, "method", "")

            # Always capture raw params summary for debugging
            try:
                params_summary = {
                    "keys": list(params.keys()) if isinstance(params, dict) else [],
                    "type": type(params).__name__,
                }
                span.set_data("request.params_summary", params_summary)
            except Exception as e:
                logger.debug("Error setting params summary: %s", e)

            if method == "tools/call":
                tool_name = params.get("name", "unknown")
                span.set_data("mcp.tool.name", tool_name)
                logger.debug(f"Setting request data for tool: {tool_name}")

                if "arguments" in params:
                    # Sanitize and capture arguments as request body
                    args = params["arguments"]
                    if isinstance(args, dict):
                        sanitized = self._sanitize_params(args)
                        span.set_data("mcp.tool.arguments", sanitized)
                        # Also set as request.body for Sentry UI visibility
                        try:
                            request_body = json.dumps(sanitized, default=str)[:2000]
                            span.set_data("request.body", request_body)
                            logger.debug(f"Set request.body: {request_body[:100]}...")
                        except Exception:
                            span.set_data("request.body", str(sanitized)[:2000])
                            logger.debug(f"Set request.body (fallback): {str(sanitized)[:100]}...")
                    else:
                        span.set_data("mcp.tool.arguments", str(args)[:500])
                        span.set_data("request.body", str(args)[:2000])
                        logger.debug(f"Set request.body (non-dict): {str(args)[:100]}...")
                else:
                    span.set_data("mcp.tool.arguments", "{}")
                    span.set_data("request.body", "{}")
                    logger.debug("No arguments in params, set empty request.body")

            elif method == "resources/read":
                if "uri" in params:
                    span.set_data("mcp.resource.uri", params["uri"])
                    span.set_data("request.uri", params["uri"])

            elif method == "prompts/get":
                if "name" in params:
                    span.set_data("mcp.prompt.name", params["name"])
                if "arguments" in params:
                    sanitized = self._sanitize_params(params.get("arguments", {}))
                    span.set_data("mcp.prompt.arguments", sanitized)
                    try:
                        span.set_data("request.body", json.dumps(sanitized, default=str)[:2000])
                    except Exception as e:
                        logger.debug("Error setting prompt request.body: %s", e)

            # Capture full params as JSON for debugging
            try:
                sanitized_params = self._sanitize_params(params) if isinstance(params, dict) else {}
                span.set_data(
                    "request.full_params", json.dumps(sanitized_params, default=str)[:4000]
                )
            except Exception as e:
                logger.debug("Error setting full_params: %s", e)

        except Exception as e:
            logger.debug("Error setting method-specific data: %s", e)
            span.set_data("request.error", str(e)[:200])

    def _set_result_metadata(self, span, result: Any):
        """Set result metadata on the span with response body preview."""
        import json

        logger.debug(f"Setting result metadata for type: {type(result).__name__}")

        try:
            if result is None:
                span.set_data("mcp.result.type", "null")
                span.set_data("response.body", "null")
                span.set_data("response.status", "success")
                logger.debug("Set response.body: null")
                return

            span.set_data("mcp.result.type", type(result).__name__)
            span.set_data("response.status", "success")

            if isinstance(result, dict):
                span.set_data("mcp.result.keys", list(result.keys())[:20])

                # Track specific result indicators
                if "error" in result:
                    span.set_data("mcp.result.has_error", True)
                    span.set_data("response.status", "error")
                if "content" in result:
                    content = result["content"]
                    if isinstance(content, list):
                        span.set_data("mcp.result.content_count", len(content))
                        # Capture first content item preview
                        if content and len(content) > 0:
                            first_item = content[0]
                            if isinstance(first_item, dict) and "text" in first_item:
                                text = first_item["text"]
                                # Truncate large text responses
                                if isinstance(text, str):
                                    span.set_data("response.content_preview", text[:1000])
                    elif isinstance(content, str):
                        span.set_data("mcp.result.content_length", len(content))
                        span.set_data("response.content_preview", content[:1000])

                # Capture sanitized response body
                try:
                    sanitized_result = self._sanitize_result(result)
                    response_json = json.dumps(sanitized_result, default=str)
                    # Truncate large responses
                    span.set_data("response.body", response_json[:4000])
                    span.set_data("response.body_size", len(response_json))
                except Exception:
                    span.set_data("response.body", str(result)[:2000])

            elif isinstance(result, list):
                span.set_data("mcp.result.length", len(result))
                try:
                    span.set_data("response.body", json.dumps(result, default=str)[:2000])
                except Exception:
                    span.set_data("response.body", f"[list with {len(result)} items]")

            elif isinstance(result, str):
                span.set_data("mcp.result.length", len(result))
                span.set_data("response.body", result[:2000])

            else:
                # Handle other types (like MCP result objects e.g. ToolResult)
                try:
                    if hasattr(result, "__dict__"):
                        result_dict = {
                            k: v for k, v in result.__dict__.items() if not k.startswith("_")
                        }
                        sanitized = self._sanitize_result(result_dict)
                        response_json = json.dumps(sanitized, default=str)[:4000]
                        span.set_data("response.body", response_json)
                        logger.debug(f"Set response.body from object: {response_json[:100]}...")
                    else:
                        response_str = str(result)[:2000]
                        span.set_data("response.body", response_str)
                        logger.debug(f"Set response.body from str: {response_str[:100]}...")
                except Exception:
                    span.set_data("response.body", str(result)[:2000])
                    logger.debug(f"Set response.body fallback: {str(result)[:100]}...")

        except Exception as e:
            span.set_data("response.error", str(e)[:200])

    def _sanitize_params(self, params: dict) -> dict[str, Any]:
        """Sanitize parameters to remove sensitive values."""
        if not isinstance(params, dict):
            return {}

        sensitive_keys = {"password", "token", "secret", "authorization", "api_key", "apikey"}
        sanitized: dict[str, Any] = {}

        for key, value in params.items():
            key_lower = key.lower()
            if any(s in key_lower for s in sensitive_keys):
                sanitized[key] = "***REDACTED***"
            elif isinstance(value, str) and len(value) > 200:
                sanitized[key] = f"[{len(value)} chars]"
            elif isinstance(value, dict):
                sanitized[key] = self._sanitize_params(value)
            else:
                sanitized[key] = value

        return sanitized

    def _sanitize_result(self, result: Any, max_depth: int = 3) -> Any:
        """Sanitize result data for Sentry, truncating large values."""
        if not isinstance(result, dict) or max_depth <= 0:
            return (
                result
                if not isinstance(result, str) or len(result) <= 500
                else f"[{len(result)} chars]"
            )

        sensitive_keys = {
            "password",
            "token",
            "secret",
            "authorization",
            "api_key",
            "apikey",
            "dsn",
        }
        sanitized: dict[str, Any] = {}

        for key, value in result.items():
            key_lower = key.lower() if isinstance(key, str) else str(key)

            if any(s in key_lower for s in sensitive_keys):
                sanitized[key] = "***REDACTED***"
            elif isinstance(value, str):
                # Truncate long strings
                if len(value) > 500:
                    sanitized[key] = f"{value[:500]}... [{len(value)} chars total]"
                else:
                    sanitized[key] = value
            elif isinstance(value, dict):
                sanitized[key] = self._sanitize_result(value, max_depth - 1)
            elif isinstance(value, list):
                if len(value) > 10:
                    sanitized[key] = f"[list with {len(value)} items]"
                else:
                    sanitized[key] = [
                        self._sanitize_result(item, max_depth - 1)
                        if isinstance(item, dict)
                        else (
                            item
                            if not isinstance(item, str) or len(item) <= 200
                            else f"[{len(item)} chars]"
                        )
                        for item in value[:10]
                    ]
            else:
                sanitized[key] = value

        return sanitized


def create_sentry_middlewares():
    """Factory function to create Sentry middleware instances."""
    if not _sentry_initialized:
        logger.debug("Sentry not initialized, skipping middleware creation")
        return None, None

    return SentryHTTPMiddleware, SentryMCPMiddleware()
