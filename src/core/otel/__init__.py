"""OpenTelemetry distributed tracing for MCP Server for Splunk.

Optional module - works without the OTel SDK installed. Install with:
``pip install mcp-server-for-splunk[otel]`` and set
``OTEL_EXPORTER_OTLP_ENDPOINT`` to activate. Exports OTLP spans to any
OpenTelemetry-compatible backend; the default service name is ``splunk-mcp``.
"""

from .bootstrap import (
    init_otel,
    instrument_httpx,
    instrument_starlette,
)
from .config import OtelSettings, is_otel_enabled
from .logging import OtelJsonFormatter, redact_sensitive
from .mcp_middleware import OtelToolSpanMiddleware

__all__ = [
    # Config
    "OtelSettings",
    "is_otel_enabled",
    # Bootstrap
    "init_otel",
    "instrument_starlette",
    "instrument_httpx",
    # Logging
    "OtelJsonFormatter",
    "redact_sensitive",
    # Middleware
    "OtelToolSpanMiddleware",
]
