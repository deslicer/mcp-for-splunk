"""Structured MCP errors must remain failures in telemetry."""

import sys
from contextlib import nullcontext
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest
from fastmcp.tools import ToolResult

from src.core.otel.mcp_middleware import OtelToolSpanMiddleware
from src.core.sentry.mcp_middleware import SentryMCPMiddleware


@pytest.fixture(params=[True, False], ids=["error", "success"])
def tool_result(request):
    return ToolResult(content="Search response", is_error=request.param)


async def test_otel_records_structured_error_status(tool_result):
    sdk = pytest.importorskip("opentelemetry.sdk.trace")
    export = pytest.importorskip("opentelemetry.sdk.trace.export")
    memory = pytest.importorskip("opentelemetry.sdk.trace.export.in_memory_span_exporter")
    provider = sdk.TracerProvider()
    exporter = memory.InMemorySpanExporter()
    provider.add_span_processor(export.SimpleSpanProcessor(exporter))
    middleware = OtelToolSpanMiddleware(tracer_provider=provider)
    context = SimpleNamespace(method="tools/call", params={"name": "run_splunk_search"})
    result = await middleware.on_request(context, AsyncMock(return_value=tool_result))
    assert result is tool_result
    span = exporter.get_finished_spans()[0]
    assert span.status.status_code.name == ("ERROR" if tool_result.is_error else "OK")
    provider.shutdown()


async def test_sentry_records_structured_error_status(tool_result, monkeypatch):
    monkeypatch.setattr("src.core.sentry.mcp_middleware._sentry_initialized", True)
    monkeypatch.setattr("src.core.sentry.mcp_middleware.set_mcp_context", Mock())
    monkeypatch.setattr("src.core.sentry.mcp_middleware.add_breadcrumb", Mock())
    span = Mock()
    sentry = SimpleNamespace(start_span=lambda **kwargs: nullcontext(span))
    monkeypatch.setitem(sys.modules, "sentry_sdk", sentry)
    middleware = SentryMCPMiddleware()
    context = SimpleNamespace(method="tools/call", params={"name": "run_splunk_search"})
    monkeypatch.setattr(middleware, "_set_method_specific_data", Mock())
    result = await middleware.on_request(context, AsyncMock(return_value=tool_result))
    assert result is tool_result
    span.set_status.assert_called_with("internal_error" if tool_result.is_error else "ok")
    values = {call.args[0]: call.args[1] for call in span.set_data.call_args_list}
    assert values["mcp.status"] == ("error" if tool_result.is_error else "success")
    assert values["response.status"] == ("error" if tool_result.is_error else "success")
