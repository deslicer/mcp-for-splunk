"""Sentry MCP middleware for method-level tracing."""

import json
import logging
import time
from typing import Any

from fastmcp.server.middleware import Middleware, MiddlewareContext

from .config import _sentry_initialized
from .context import add_breadcrumb, set_mcp_context

logger = logging.getLogger(__name__)


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

        method = getattr(context, "method", "unknown")
        session_id = getattr(context, "session_id", None)

        set_mcp_context(session_id=session_id)

        span_op = self._get_span_op(method)
        span_name = self._get_span_name(context)

        start_time = time.perf_counter()

        try:
            with sentry_sdk.start_span(
                op=span_op,
                name=span_name,
                description=f"MCP method: {method}",
            ) as span:
                span.set_data("mcp.method.name", method)
                if session_id:
                    span.set_data("mcp.session.id", session_id)

                self._set_method_specific_data(span, context)

                add_breadcrumb(
                    message=f"MCP {method}",
                    category=f"mcp.{method.split('/')[0] if '/' in method else 'method'}",
                    level="info",
                    data={"method": method, "session_id": session_id},
                )

                try:
                    result = await call_next(context)

                    duration_ms = (time.perf_counter() - start_time) * 1000
                    span.set_data("mcp.duration_ms", round(duration_ms, 2))
                    span.set_data("mcp.status", "success")
                    span.set_status("ok")

                    self._set_result_metadata(span, result)

                    return result

                except Exception as e:
                    duration_ms = (time.perf_counter() - start_time) * 1000
                    span.set_data("mcp.duration_ms", round(duration_ms, 2))
                    span.set_data("mcp.status", "error")
                    span.set_data("mcp.error.type", type(e).__name__)
                    span.set_data("mcp.error.message", str(e)[:500])
                    span.set_status("internal_error")

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

        try:
            if hasattr(context, "params") and context.params:
                params = context.params

                if method == "tools/call" and "name" in params:
                    return f"tools/call {params['name']}"
                elif method == "resources/read" and "uri" in params:
                    uri = params["uri"]
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
        try:
            params = None

            if hasattr(context, "params") and context.params:
                params = context.params
            elif hasattr(context, "message") and context.message:
                message = context.message
                if isinstance(message, dict):
                    params = message.get("params", message)
                elif hasattr(message, "params"):
                    params = message.params
                elif hasattr(message, "__dict__"):
                    params = {k: v for k, v in message.__dict__.items() if not k.startswith("_")}

            if not params:
                span.set_data("request.params", None)
                return

            method = getattr(context, "method", "")

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

                if "arguments" in params:
                    args = params["arguments"]
                    if isinstance(args, dict):
                        sanitized = self._sanitize_params(args)
                        span.set_data("mcp.tool.arguments", sanitized)
                        try:
                            request_body = json.dumps(sanitized, default=str)[:2000]
                            span.set_data("request.body", request_body)
                        except Exception:
                            span.set_data("request.body", str(sanitized)[:2000])
                    else:
                        span.set_data("mcp.tool.arguments", str(args)[:500])
                        span.set_data("request.body", str(args)[:2000])
                else:
                    span.set_data("mcp.tool.arguments", "{}")
                    span.set_data("request.body", "{}")

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
        try:
            if result is None:
                span.set_data("mcp.result.type", "null")
                span.set_data("response.body", "null")
                span.set_data("response.status", "success")
                return

            span.set_data("mcp.result.type", type(result).__name__)
            span.set_data("response.status", "success")

            if isinstance(result, dict):
                span.set_data("mcp.result.keys", list(result.keys())[:20])

                if "error" in result:
                    span.set_data("mcp.result.has_error", True)
                    span.set_data("response.status", "error")
                if "content" in result:
                    content = result["content"]
                    if isinstance(content, list):
                        span.set_data("mcp.result.content_count", len(content))
                        if content and len(content) > 0:
                            first_item = content[0]
                            if isinstance(first_item, dict) and "text" in first_item:
                                text = first_item["text"]
                                if isinstance(text, str):
                                    span.set_data("response.content_preview", text[:1000])
                    elif isinstance(content, str):
                        span.set_data("mcp.result.content_length", len(content))
                        span.set_data("response.content_preview", content[:1000])

                try:
                    sanitized_result = self._sanitize_result(result)
                    response_json = json.dumps(sanitized_result, default=str)
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
                try:
                    if hasattr(result, "__dict__"):
                        result_dict = {
                            k: v for k, v in result.__dict__.items() if not k.startswith("_")
                        }
                        sanitized = self._sanitize_result(result_dict)
                        response_json = json.dumps(sanitized, default=str)[:4000]
                        span.set_data("response.body", response_json)
                    else:
                        span.set_data("response.body", str(result)[:2000])
                except Exception:
                    span.set_data("response.body", str(result)[:2000])

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

    from .http_middleware import SentryHTTPMiddleware

    return SentryHTTPMiddleware, SentryMCPMiddleware()

