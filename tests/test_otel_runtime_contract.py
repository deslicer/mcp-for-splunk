"""Exercise telemetry against the installed FastMCP and OTel implementations."""

import logging

import pytest
from fastmcp import Client, FastMCP

from src.core.otel import bootstrap
from src.core.otel.bootstrap import _instrument_logging
from src.core.otel.mcp_middleware import OtelToolSpanMiddleware

try:
    from opentelemetry import trace
    from opentelemetry.exporter.otlp.proto.common.trace_encoder import encode_spans
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


def test_bootstrap_export_drops_raw_exception_details(monkeypatch):
    monkeypatch.setenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://collector.invalid:4318")
    monkeypatch.setattr(trace, "set_tracer_provider", lambda provider: None)
    bootstrap._reset_for_tests()
    exporter = InMemorySpanExporter()
    provider = bootstrap.init_otel(span_exporter=exporter)
    assert provider is not None
    original_exporter = InMemorySpanExporter()
    provider.add_span_processor(SimpleSpanProcessor(original_exporter))
    try:
        try:
            with provider.get_tracer("httpx").start_as_current_span("GET") as active:
                active.set_attribute("http.request.method", "GET")
                active.add_event("retry", {"attempt": 1})
                raise ValueError("Authorization: Bearer transport-secret; private@example.test")
        except ValueError:
            pass  # The SDK has recorded the failure as the span context exits.
        span = exporter.get_finished_spans()[0]
        original = original_exporter.get_finished_spans()[0]
        assert span.status.status_code.name == "ERROR"
        assert span.events[1].attributes["exception.type"] == "ValueError"
        encoded = encode_spans([span])
        wire_span = encoded.resource_spans[0].scope_spans[0].spans[0]
        assert wire_span.trace_id.hex() == format(original.context.trace_id, "032x")
        assert wire_span.span_id.hex() == format(original.context.span_id, "016x")
        assert wire_span.start_time_unix_nano == original.start_time
        assert wire_span.end_time_unix_nano == original.end_time
        assert wire_span.events[0].name == "retry"
        assert wire_span.events[0].attributes[0].value.int_value == 1
        assert wire_span.attributes[0].value.string_value == "GET"
        assert encoded.resource_spans[0].scope_spans[0].scope.name == "httpx"
        assert "transport-secret" in original.to_json(), "The original span must not be mutated"
        evidence = span.to_json() + str(encoded) + str(span.status.description)
        assert "transport-secret" not in evidence
        assert "private@example.test" not in evidence
    finally:
        provider.shutdown()
        bootstrap._reset_for_tests()
