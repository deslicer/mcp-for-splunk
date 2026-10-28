"""Omit potentially sensitive exception text at the final span export boundary."""

from __future__ import annotations

import json
from collections.abc import Sequence
from typing import Any, cast

from opentelemetry.sdk.trace import ReadableSpan
from opentelemetry.sdk.trace.export import SpanExporter, SpanExportResult
from opentelemetry.trace import Status


class _ExceptionEventView:
    def __init__(self, event: Any) -> None:
        self._event = event
        self.attributes = {
            key: value
            for key, value in (event.attributes or {}).items()
            if key in {"exception.type", "exception.escaped"}
        }

    def __getattr__(self, name: str) -> Any:
        return getattr(self._event, name)


class _SpanView:
    """Read-only exporter view; never mutate spans shared by other processors.

    Exporters consume ReadableSpan's public fields. Delegate unchanged metadata,
    including resource, scope, links, timings and drop counts, to the original.
    The JSON method is overridden too for console/debug exporters.
    """

    def __init__(self, span: ReadableSpan) -> None:
        self._span = span
        self.events = tuple(
            _ExceptionEventView(event) if event.name == "exception" else event
            for event in span.events
        )
        self.status = Status(span.status.status_code)

    def __getattr__(self, name: str) -> Any:
        return getattr(self._span, name)

    def to_json(self, indent: int | None = 4) -> str:
        payload = json.loads(self._span.to_json())
        payload["status"].pop("description", None)
        for original, event in zip(payload["events"], self.events, strict=True):
            if event.name == "exception":
                original["attributes"] = dict(event.attributes)
        return json.dumps(payload, indent=indent)


class SafeSpanExporter(SpanExporter):
    """Retain error classes while dropping raw messages, stacks and status text.

    Third-party instrumentors can record errors before application handlers can
    redact them. Apply this to both OTLP and injected exporters so credentials
    or personal data in those exception details cannot leave the process.
    """

    def __init__(self, delegate: SpanExporter) -> None:
        self._delegate = delegate

    def export(self, spans: Sequence[ReadableSpan]) -> SpanExportResult:
        return self._delegate.export([cast(ReadableSpan, _SpanView(span)) for span in spans])

    def shutdown(self) -> None:
        self._delegate.shutdown()

    def force_flush(self, timeout_millis: int = 30000) -> bool:
        return bool(self._delegate.force_flush(timeout_millis))
