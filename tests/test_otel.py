"""Tests for the optional OpenTelemetry tracing integration.

The integration is import-safe (works without the SDK) and only activates
at runtime when ``OTEL_EXPORTER_OTLP_ENDPOINT`` is set. These tests cover the
configuration parsing, the JSON log formatter (logs<->traces correlation +
credential deny-list), the bootstrap lifecycle, and the per-tool span
middleware that emits ``mcp.tool.{name}`` spans.
"""

import json
import logging

import pytest


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
class TestOtelSettings:
    def test_disabled_when_endpoint_missing(self, monkeypatch):
        from src.core.otel.config import OtelSettings, is_otel_enabled

        monkeypatch.delenv("OTEL_EXPORTER_OTLP_ENDPOINT", raising=False)
        settings = OtelSettings.from_env()

        assert settings.endpoint is None
        assert settings.enabled is False
        assert is_otel_enabled() is False

    def test_enabled_when_endpoint_set(self, monkeypatch):
        from src.core.otel.config import OtelSettings, _otel_sdk_available, is_otel_enabled

        monkeypatch.setenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://otel-collector:4318")
        settings = OtelSettings.from_env()

        assert settings.endpoint == "http://otel-collector:4318"
        assert settings.enabled is True
        # is_otel_enabled() additionally requires the optional [otel] SDK extra,
        # so it is only True when the SDK is actually installed.
        assert is_otel_enabled() is _otel_sdk_available

    def test_defaults_mirror_contract(self, monkeypatch):
        from src.core.otel.config import OtelSettings

        monkeypatch.setenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://otel-collector:4318")
        monkeypatch.delenv("OTEL_SERVICE_NAME", raising=False)
        monkeypatch.delenv("OTEL_EXPORTER_OTLP_PROTOCOL", raising=False)
        monkeypatch.delenv("OTEL_TRACES_SAMPLER", raising=False)
        settings = OtelSettings.from_env()

        assert settings.service_name == "splunk-mcp"
        assert settings.protocol == "http/protobuf"
        assert settings.sampler == "parentbased_always_on"

    def test_env_overrides_defaults(self, monkeypatch):
        from src.core.otel.config import OtelSettings

        monkeypatch.setenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://collector:4318")
        monkeypatch.setenv("OTEL_SERVICE_NAME", "custom-mcp")
        monkeypatch.setenv("DEPLOYMENT_ENVIRONMENT", "staging")
        settings = OtelSettings.from_env()

        assert settings.service_name == "custom-mcp"
        assert settings.deployment_environment == "staging"


# ---------------------------------------------------------------------------
# JSON logging (logs <-> traces correlation + credential deny-list)
# ---------------------------------------------------------------------------
class TestOtelJsonFormatter:
    def _record(self, msg: str) -> logging.LogRecord:
        return logging.LogRecord(
            name="test.logger",
            level=logging.INFO,
            pathname=__file__,
            lineno=1,
            msg=msg,
            args=(),
            exc_info=None,
        )

    def test_emits_json_with_trace_ids(self):
        from src.core.otel.logging import OtelJsonFormatter

        formatter = OtelJsonFormatter()
        record = self._record("hello world")
        # Simulate fields injected by the OTel logging instrumentation.
        record.otelTraceID = "abc123"
        record.otelSpanID = "def456"
        record.otelServiceName = "splunk-mcp"

        payload = json.loads(formatter.format(record))

        assert payload["message"] == "hello world"
        assert payload["level"] == "INFO"
        assert payload["otelTraceID"] == "abc123"
        assert payload["otelSpanID"] == "def456"

    def test_timestamp_is_iso8601_with_millis(self):
        from src.core.otel.logging import OtelJsonFormatter

        formatter = OtelJsonFormatter()
        payload = json.loads(formatter.format(self._record("tick")))

        ts = payload["timestamp"]
        # Must be a real timestamp, not a literal strftime token like ".fZ".
        assert "f" not in ts.replace("Z", "")
        assert ts.endswith("Z")
        assert ts[:4].isdigit()

    def test_trace_ids_default_when_absent(self):
        from src.core.otel.logging import OtelJsonFormatter

        formatter = OtelJsonFormatter()
        payload = json.loads(formatter.format(self._record("no span active")))

        assert payload["otelTraceID"] == "0"
        assert payload["otelSpanID"] == "0"

    def test_redacts_sensitive_values(self):
        from src.core.otel.logging import OtelJsonFormatter

        formatter = OtelJsonFormatter()
        record = self._record("connecting with X-Splunk-Token: super-secret-value")
        payload = json.loads(formatter.format(record))

        assert "super-secret-value" not in payload["message"]
        assert "***" in payload["message"]

    def test_redacts_sensitive_structured_extras(self):
        from src.core.otel.logging import OtelJsonFormatter

        formatter = OtelJsonFormatter()
        record = self._record("login")
        # Structured extras (e.g. logger.info(..., extra={...})) must not leak
        # even when the bare value has no `key: value` shape to pattern-match.
        record.splunk_token = "bare-secret-token"
        record.api_key = "another-secret"
        record.index = "main"

        payload = json.loads(formatter.format(record))

        assert payload["splunk_token"] == "***"
        assert payload["api_key"] == "***"
        assert payload["index"] == "main"


class TestRedaction:
    def test_redacts_authorization_bearer(self):
        from src.core.otel.logging import redact_sensitive

        out = redact_sensitive("Authorization: Bearer eyJhbGciOi.secrettoken")
        assert "secrettoken" not in out
        assert "***" in out

    def test_passes_through_clean_text(self):
        from src.core.otel.logging import redact_sensitive

        assert redact_sensitive("searching index=main") == "searching index=main"


# ---------------------------------------------------------------------------
# Bootstrap lifecycle
# ---------------------------------------------------------------------------
class TestInitOtel:
    def test_returns_none_when_disabled(self, monkeypatch):
        from src.core.otel import bootstrap

        monkeypatch.delenv("OTEL_EXPORTER_OTLP_ENDPOINT", raising=False)
        bootstrap._reset_for_tests()

        assert bootstrap.init_otel() is None

    def test_initializes_and_is_idempotent(self, monkeypatch):
        pytest.importorskip("opentelemetry.sdk")
        from opentelemetry.sdk.trace.export.in_memory_span_exporter import (
            InMemorySpanExporter,
        )

        from src.core.otel import bootstrap

        monkeypatch.setenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://collector:4318")
        bootstrap._reset_for_tests()

        exporter = InMemorySpanExporter()
        provider = bootstrap.init_otel(span_exporter=exporter)
        assert provider is not None

        # Second call must not create a new provider.
        provider2 = bootstrap.init_otel(span_exporter=exporter)
        assert provider2 is provider


# ---------------------------------------------------------------------------
# Per-tool span middleware
# ---------------------------------------------------------------------------
class TestOtelToolSpanMiddleware:
    @pytest.mark.asyncio
    async def test_creates_tool_span_with_attribute(self, monkeypatch):
        pytest.importorskip("opentelemetry.sdk")
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import SimpleSpanProcessor
        from opentelemetry.sdk.trace.export.in_memory_span_exporter import (
            InMemorySpanExporter,
        )

        from src.core.otel.mcp_middleware import OtelToolSpanMiddleware

        exporter = InMemorySpanExporter()
        provider = TracerProvider()
        provider.add_span_processor(SimpleSpanProcessor(exporter))

        middleware = OtelToolSpanMiddleware(tracer_provider=provider)

        class FakeContext:
            method = "tools/call"
            params = {"name": "get_indexes", "arguments": {}}
            session_id = "sess-1"

        async def call_next(_ctx):
            return {"ok": True}

        result = await middleware.on_request(FakeContext(), call_next)

        assert result == {"ok": True}
        spans = exporter.get_finished_spans()
        assert len(spans) == 1
        assert spans[0].name == "mcp.tool.get_indexes"
        assert spans[0].attributes.get("mcp.tool.name") == "get_indexes"

    @pytest.mark.asyncio
    async def test_exception_event_is_redacted(self):
        pytest.importorskip("opentelemetry.sdk")
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import SimpleSpanProcessor
        from opentelemetry.sdk.trace.export.in_memory_span_exporter import (
            InMemorySpanExporter,
        )

        from src.core.otel.mcp_middleware import OtelToolSpanMiddleware

        exporter = InMemorySpanExporter()
        provider = TracerProvider()
        provider.add_span_processor(SimpleSpanProcessor(exporter))
        middleware = OtelToolSpanMiddleware(tracer_provider=provider)

        class FakeContext:
            method = "tools/call"
            params = {"name": "do_thing", "arguments": {}}
            session_id = None

        async def call_next(_ctx):
            raise ValueError("X-Splunk-Token: super-secret-value")

        with pytest.raises(ValueError):
            await middleware.on_request(FakeContext(), call_next)

        spans = exporter.get_finished_spans()
        assert len(spans) == 1
        span = spans[0]

        # Status description must not carry the raw secret.
        assert "super-secret-value" not in (span.status.description or "")
        assert "***" in (span.status.description or "")

        # Exception event message + stacktrace must be redacted.
        blob = json.dumps(
            {event.name: dict(event.attributes) for event in span.events}
        )
        assert "exception" in blob
        assert "super-secret-value" not in blob
        assert "***" in blob

    @pytest.mark.asyncio
    async def test_non_tool_method_is_passthrough(self):
        pytest.importorskip("opentelemetry.sdk")
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import SimpleSpanProcessor
        from opentelemetry.sdk.trace.export.in_memory_span_exporter import (
            InMemorySpanExporter,
        )

        from src.core.otel.mcp_middleware import OtelToolSpanMiddleware

        exporter = InMemorySpanExporter()
        provider = TracerProvider()
        provider.add_span_processor(SimpleSpanProcessor(exporter))
        middleware = OtelToolSpanMiddleware(tracer_provider=provider)

        class FakeContext:
            method = "resources/read"
            params = {"uri": "health://status"}
            session_id = None

        async def call_next(_ctx):
            return "OK"

        result = await middleware.on_request(FakeContext(), call_next)

        assert result == "OK"
        # No tool span should be created for non tool calls.
        assert exporter.get_finished_spans() == ()
