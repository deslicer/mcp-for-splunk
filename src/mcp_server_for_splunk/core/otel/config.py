"""OpenTelemetry configuration resolved from environment variables.

Vendor-neutral defaults: a stable service name (``splunk-mcp`` by default),
W3C context propagation, a ``parentbased_always_on`` sampler, and a
``deployment.environment`` resource attribute. The integration only activates
when ``OTEL_EXPORTER_OTLP_ENDPOINT`` is set, keeping OTel fully optional.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# OTel API ships transitively; the SDK + exporters arrive via the [otel] extra.
# Import a concrete SDK symbol so this acts as a real availability probe.
try:
    from opentelemetry.sdk.trace import TracerProvider as _SdkTracerProvider

    _otel_sdk_available = _SdkTracerProvider is not None
except ImportError:
    _otel_sdk_available = False


DEFAULT_SERVICE_NAME = "splunk-mcp"
DEFAULT_PROTOCOL = "http/protobuf"
DEFAULT_ENDPOINT = "http://otel-collector:4318"
DEFAULT_SAMPLER = "parentbased_always_on"


@dataclass(frozen=True)
class OtelSettings:
    """Immutable snapshot of the OTel environment configuration."""

    endpoint: str | None
    service_name: str
    service_version: str
    protocol: str
    sampler: str
    deployment_environment: str

    @property
    def enabled(self) -> bool:
        """OTel is enabled only when an OTLP endpoint is configured."""
        return bool(self.endpoint)

    @classmethod
    def from_env(cls) -> OtelSettings:
        """Build settings from the process environment."""
        endpoint = (os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT") or "").strip() or None
        deployment_environment = (
            os.getenv("DEPLOYMENT_ENVIRONMENT")
            or os.getenv("DEPLOYMENT_ENV")
            or os.getenv("SENTRY_ENVIRONMENT")
            or "development"
        ).strip()
        return cls(
            endpoint=endpoint,
            service_name=(os.getenv("OTEL_SERVICE_NAME") or DEFAULT_SERVICE_NAME).strip(),
            service_version=(
                os.getenv("OTEL_SERVICE_VERSION") or _resolve_service_version()
            ).strip(),
            protocol=(os.getenv("OTEL_EXPORTER_OTLP_PROTOCOL") or DEFAULT_PROTOCOL).strip(),
            sampler=(os.getenv("OTEL_TRACES_SAMPLER") or DEFAULT_SAMPLER).strip(),
            deployment_environment=deployment_environment,
        )


def _resolve_service_version() -> str:
    """Best-effort package version for the ``service.version`` resource attr."""
    try:
        from importlib.metadata import version

        return version("mcp-server-for-splunk")
    except Exception:
        return "0.0.0"


def is_otel_enabled() -> bool:
    """Return True when the SDK is installed and an OTLP endpoint is configured."""
    if not _otel_sdk_available:
        return False
    return OtelSettings.from_env().enabled
