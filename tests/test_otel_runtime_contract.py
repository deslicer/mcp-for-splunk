"""Exercise telemetry against the installed FastMCP and OTel implementations."""

import logging

import pytest
from fastmcp import Client, FastMCP

from src.core.otel.bootstrap import _instrument_logging
from src.core.otel.mcp_middleware import OtelToolSpanMiddleware

try:
    from opentelemetry.instrumentation.logging import LoggingInstrumentor
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import SimpleSpanProcessor
    from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
except ImportError:
    pytest.skip("OpenTelemetry extra is not installed", allow_module_level=True)


def test_logging_injects_context_without_changing_format(caplog):
    instrumentor = LoggingInstrumentor()
    was_instrumented = instrumentor.is_instrumented_by_opentelemetry
    if was_instrumented:
        instrumentor.uninstrument()
    provider = TracerProvider()
    try:
        _instrument_logging()
        with provider.get_tracer(__name__).start_as_current_span("probe") as span:
            with caplog.at_level(logging.INFO):
                logging.getLogger(__name__).info("correlated operation")
            record = caplog.records[-1]
            assert record.otelTraceID == format(span.get_span_context().trace_id, "032x")
            assert record.otelSpanID == format(span.get_span_context().span_id, "016x")
    finally:
        instrumentor.uninstrument()
        provider.shutdown()
        if was_instrumented:
            _instrument_logging()


async def test_real_mcp_call_uses_operation_name_and_ambient_trace():
    exporter = InMemorySpanExporter()
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    server = FastMCP("OTel contract")
    server.add_middleware(OtelToolSpanMiddleware(tracer_provider=provider))

    @server.tool
    def trace_probe(secret: str) -> str:
        return "ok"

    try:
        with provider.get_tracer(__name__).start_as_current_span("request") as parent:
            async with Client(server) as client:
                result = await client.call_tool("trace_probe", {"secret": "not-for-telemetry"})
            assert not result.is_error
        spans = [s for s in exporter.get_finished_spans() if s.name.startswith("mcp.tool.")]
        assert len(spans) == 1
        assert spans[0].name == "mcp.tool.trace_probe"
        assert spans[0].attributes["mcp.tool.name"] == "trace_probe"
        assert spans[0].context.trace_id == parent.get_span_context().trace_id
        assert "not-for-telemetry" not in spans[0].to_json()
    finally:
        provider.shutdown()
