"""FastMCP middleware that emits a span per tool call.

Creates a ``mcp.tool.{name}`` span (attribute ``mcp.tool.name``) as a child of
the ambient HTTP server span produced by the Starlette instrumentation, so each
tool's latency is visible in any OTel backend. Tool arguments are intentionally
NOT attached to spans to honor the credential deny-list.
"""

from __future__ import annotations

import logging
from typing import Any

from fastmcp.server.middleware import Middleware, MiddlewareContext

logger = logging.getLogger(__name__)

_TRACER_NAME = "mcp-for-splunk"


class OtelToolSpanMiddleware(Middleware):
    """Wrap ``tools/call`` invocations in an OpenTelemetry span."""

    def __init__(self, tracer_provider: Any | None = None) -> None:
        super().__init__()
        self._tracer_provider = tracer_provider
        logger.info("OtelToolSpanMiddleware initialized")

    def _get_tracer(self) -> Any:
        from opentelemetry import trace

        if self._tracer_provider is not None:
            return self._tracer_provider.get_tracer(_TRACER_NAME)
        return trace.get_tracer(_TRACER_NAME)

    async def on_request(self, context: MiddlewareContext, call_next):
        """Create a tool span for ``tools/call``; pass through other methods."""
        method = getattr(context, "method", None)
        if method != "tools/call":
            return await call_next(context)

        tool_name = self._tool_name(context)
        session_id = getattr(context, "session_id", None)

        try:
            from opentelemetry.trace import SpanKind, Status, StatusCode
        except ImportError:
            return await call_next(context)

        tracer = self._get_tracer()
        with tracer.start_as_current_span(
            f"mcp.tool.{tool_name}", kind=SpanKind.INTERNAL
        ) as span:
            span.set_attribute("mcp.tool.name", tool_name)
            if session_id:
                span.set_attribute("mcp.session.id", str(session_id))

            try:
                result = await call_next(context)
                span.set_status(Status(StatusCode.OK))
                return result
            except Exception as exc:
                span.record_exception(exc)
                span.set_status(Status(StatusCode.ERROR, str(exc)[:200]))
                raise

    @staticmethod
    def _tool_name(context: MiddlewareContext) -> str:
        params = getattr(context, "params", None)
        if isinstance(params, dict):
            name = params.get("name")
            if name:
                return str(name)
        return "unknown"
