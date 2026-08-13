"""FastMCP middleware that emits a span per tool call.

Creates a ``mcp.tool.{name}`` span (attribute ``mcp.tool.name``) as a child of
the ambient HTTP server span produced by the Starlette instrumentation, so each
tool's latency is visible in any OTel backend. Tool arguments are intentionally
NOT attached to spans to honor the credential deny-list.
"""

from __future__ import annotations

import logging as stdlib_logging
import traceback
from typing import Any

from fastmcp.server.middleware import Middleware, MiddlewareContext

from .logging import redact_sensitive

logger = stdlib_logging.getLogger(__name__)

_MAX_EXC_MESSAGE = 500
_MAX_EXC_STACKTRACE = 8000

_TRACER_NAME = "mcp-for-splunk"


class OtelToolSpanMiddleware(Middleware):
    """Wrap ``tools/call`` invocations in an OpenTelemetry span."""

    def __init__(self, tracer_provider: Any | None = None) -> None:
        super().__init__()
        self._tracer_provider = tracer_provider
        logger.info("OtelToolSpanMiddleware initialized")

    def _get_tracer(self) -> Any:
        from opentelemetry.trace import get_tracer

        if self._tracer_provider is not None:
            return self._tracer_provider.get_tracer(_TRACER_NAME)
        return get_tracer(_TRACER_NAME)

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
        # Disable the SDK's automatic exception recording: it would attach the
        # raw, unredacted message + stacktrace on context-manager exit. We record
        # a credential-masked exception event ourselves instead.
        with tracer.start_as_current_span(
            f"mcp.tool.{tool_name}",
            kind=SpanKind.INTERNAL,
            record_exception=False,
            set_status_on_exception=False,
        ) as span:
            span.set_attribute("mcp.tool.name", tool_name)
            if session_id:
                span.set_attribute("mcp.session.id", str(session_id))

            try:
                result = await call_next(context)
                span.set_status(Status(StatusCode.OK))
                return result
            except Exception as exc:
                _record_redacted_exception(span, exc)
                span.set_status(
                    Status(StatusCode.ERROR, redact_sensitive(str(exc))[:200])
                )
                raise

    @staticmethod
    def _tool_name(context: MiddlewareContext) -> str:
        params = getattr(context, "params", None)
        if isinstance(params, dict):
            name = params.get("name")
            if name:
                return str(name)
        return "unknown"


def _record_redacted_exception(span: Any, exc: BaseException) -> None:
    """Record an exception event on the span with credentials masked.

    Mirrors the JSON-log credential deny-list so exception messages and stack
    traces exported to the OTLP backend cannot leak tokens/passwords. We emit a
    sanitized ``exception`` event instead of ``span.record_exception`` (which
    would attach the raw message + traceback verbatim).
    """
    stacktrace = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
    span.add_event(
        "exception",
        attributes={
            "exception.type": type(exc).__qualname__,
            "exception.message": redact_sensitive(str(exc))[:_MAX_EXC_MESSAGE],
            "exception.stacktrace": redact_sensitive(stacktrace)[:_MAX_EXC_STACKTRACE],
        },
    )
