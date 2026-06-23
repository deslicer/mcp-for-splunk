"""OpenTelemetry bootstrap: provider setup + instrumentation entry points.

Public API (referenced from ``src/server.py``):

* :func:`init_otel` — build a ``TracerProvider`` (resource + sampler + OTLP
  ``BatchSpanProcessor``) from the environment and register it globally.
* :func:`instrument_starlette` — wrap the ASGI app so incoming requests extract
  the W3C ``traceparent`` and emit a server span.
* :func:`instrument_httpx` — emit client child spans for outbound HTTP calls.

Everything is import-safe and a no-op unless the ``[otel]`` extra is installed
and ``OTEL_EXPORTER_OTLP_ENDPOINT`` is set.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from .config import OtelSettings, _otel_sdk_available

if TYPE_CHECKING:  # pragma: no cover - typing only
    from opentelemetry.sdk.trace import TracerProvider

logger = logging.getLogger(__name__)


class _BootstrapState:
    """Holds the bootstrap provider + idempotency guard for this module."""

    def __init__(self) -> None:
        self.initialized = False
        self.provider: Any | None = None

    def reset(self) -> None:
        self.initialized = False
        self.provider = None


_state = _BootstrapState()


def _reset_for_tests() -> None:
    """Reset module state so the bootstrap can run again (tests only)."""
    _state.reset()


def init_otel(
    settings: OtelSettings | None = None,
    *,
    span_exporter: Any | None = None,
) -> TracerProvider | None:
    """Initialize the global tracer provider. Returns the provider or ``None``.

    Returns ``None`` (and registers nothing) when the SDK is missing, no
    endpoint is configured, or no span processor could be attached — so callers
    can treat a non-``None`` result as "tracing is actually exporting".

    Args:
        settings: Pre-resolved settings; defaults to :meth:`OtelSettings.from_env`.
        span_exporter: Optional exporter override (tests inject an in-memory one).
    """
    if _state.initialized:
        return _state.provider

    if not _otel_sdk_available:
        logger.info("opentelemetry SDK not installed; tracing disabled")
        return None

    settings = settings or OtelSettings.from_env()
    if not settings.enabled:
        logger.info("OTEL_EXPORTER_OTLP_ENDPOINT not set; tracing disabled")
        return None

    try:
        from opentelemetry import trace
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor, SimpleSpanProcessor

        resource = Resource.create(
            {
                "service.name": settings.service_name,
                "service.version": settings.service_version,
                "deployment.environment": settings.deployment_environment,
            }
        )

        provider = TracerProvider(resource=resource, sampler=_build_sampler(settings.sampler))

        if span_exporter is not None:
            provider.add_span_processor(SimpleSpanProcessor(span_exporter))
        else:
            exporter = _build_otlp_exporter()
            if exporter is None:
                logger.error(
                    "OTLP exporter unavailable; OpenTelemetry not enabled "
                    "(no span processor registered, nothing would be exported)"
                )
                return None
            provider.add_span_processor(BatchSpanProcessor(exporter))

        trace.set_tracer_provider(provider)
        _instrument_logging()

        _state.provider = provider
        _state.initialized = True
        logger.info(
            "OpenTelemetry initialized (service=%s, env=%s, endpoint=%s)",
            settings.service_name,
            settings.deployment_environment,
            settings.endpoint,
        )
        return provider

    except Exception as exc:  # pragma: no cover - defensive
        logger.error("Failed to initialize OpenTelemetry: %s", exc)
        return None


def _build_sampler(sampler_name: str) -> Any:
    """Map the configured sampler name to an SDK sampler (default AlwaysOn root)."""
    from opentelemetry.sdk.trace.sampling import (
        ALWAYS_OFF,
        ALWAYS_ON,
        ParentBased,
        TraceIdRatioBased,
    )

    name = (sampler_name or "").lower()
    if name == "parentbased_always_on":
        return ParentBased(ALWAYS_ON)
    if name == "parentbased_always_off":
        return ParentBased(ALWAYS_OFF)
    if name == "always_on":
        return ALWAYS_ON
    if name == "always_off":
        return ALWAYS_OFF
    if name.startswith("parentbased_traceidratio") or name == "traceidratio":
        import os

        try:
            ratio = float(os.getenv("OTEL_TRACES_SAMPLER_ARG", "1.0"))
        except ValueError:
            ratio = 1.0
        base = TraceIdRatioBased(ratio)
        return ParentBased(base) if name.startswith("parentbased") else base
    return ParentBased(ALWAYS_ON)


def _build_otlp_exporter() -> Any | None:
    """Create the OTLP/HTTP span exporter (reads endpoint/headers from env)."""
    try:
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter

        return OTLPSpanExporter()
    except Exception as exc:  # pragma: no cover - defensive
        logger.warning("OTLP exporter unavailable: %s", exc)
        return None


def _instrument_logging() -> None:
    """Inject otelTraceID/otelSpanID onto log records (formatter renders them)."""
    try:
        from opentelemetry.instrumentation.logging import LoggingInstrumentor

        LoggingInstrumentor().instrument(set_logging_format=False)
    except Exception as exc:  # pragma: no cover - defensive
        logger.debug("Logging instrumentation unavailable: %s", exc)


def instrument_starlette(app: Any) -> None:
    """Instrument a Starlette app to extract W3C context and emit server spans."""
    if not _otel_sdk_available:
        return
    try:
        from opentelemetry.instrumentation.starlette import StarletteInstrumentor

        StarletteInstrumentor.instrument_app(app)
        logger.info("Starlette OTel instrumentation enabled")
    except Exception as exc:  # pragma: no cover - defensive
        logger.warning("Failed to instrument Starlette for OTel: %s", exc)


def instrument_httpx() -> None:
    """Instrument httpx so outbound REST calls become client child spans."""
    if not _otel_sdk_available:
        return
    try:
        from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor

        HTTPXClientInstrumentor().instrument()
        logger.info("httpx OTel instrumentation enabled")
    except Exception as exc:  # pragma: no cover - defensive
        logger.warning("Failed to instrument httpx for OTel: %s", exc)
