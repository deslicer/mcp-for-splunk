"""Structured JSON logging that correlates logs with traces.

The OTel logging instrumentation injects ``otelTraceID`` / ``otelSpanID`` /
``otelServiceName`` onto every :class:`logging.LogRecord` while a span is
active. This formatter renders records as JSON carrying those fields so logs can
be correlated with traces, and applies a credential deny-list
(Authorization / X-Splunk-Token / X-Splunk-Password / keys) to both the message
and any structured ``extra`` fields.
"""

from __future__ import annotations

import json
import logging
import re
from datetime import datetime, timezone

# Header / field names whose values must never be logged in clear text.
_SENSITIVE_KEYS = (
    "authorization",
    "x-splunk-token",
    "x-splunk-password",
    "splunk_password",
    "splunk_token",
    "password",
    "token",
    "api_key",
    "apikey",
    "secret",
)

# Matches `key: value`, `key=value`, and `"key": "value"` shapes, capturing the
# separator so we can preserve formatting while masking the value.
_SENSITIVE_PATTERN = re.compile(
    r"(?i)(?P<key>" + "|".join(re.escape(k) for k in _SENSITIVE_KEYS) + r")"
    r"(?P<sep>\"?\s*[:=]\s*\"?)"
    r"(?:bearer\s+)?(?P<val>[^\s,;\"']+)"
)

# Standard LogRecord attributes we never want to duplicate as JSON "extra".
_RESERVED_RECORD_ATTRS = frozenset(
    {
        "args",
        "asctime",
        "created",
        "exc_info",
        "exc_text",
        "filename",
        "funcName",
        "levelname",
        "levelno",
        "lineno",
        "module",
        "msecs",
        "message",
        "msg",
        "name",
        "pathname",
        "process",
        "processName",
        "relativeCreated",
        "stack_info",
        "taskName",
        "thread",
        "threadName",
        "otelTraceID",
        "otelSpanID",
        "otelServiceName",
        "otelTraceSampled",
    }
)


def redact_sensitive(text: str) -> str:
    """Mask values of deny-listed credential keys inside a free-form string."""
    if not text:
        return text

    def _mask(match: re.Match[str]) -> str:
        return f"{match.group('key')}{match.group('sep')}***"

    return _SENSITIVE_PATTERN.sub(_mask, text)


def is_sensitive_key(key: str) -> bool:
    """True when a log/extra field name matches a deny-listed credential key."""
    lowered = key.lower()
    return any(sensitive in lowered for sensitive in _SENSITIVE_KEYS)


class OtelJsonFormatter(logging.Formatter):
    """Render log records as single-line JSON with trace correlation fields."""

    def __init__(self, include_extra: bool = True) -> None:
        super().__init__()
        self._include_extra = include_extra

    def format(self, record: logging.LogRecord) -> str:
        message = redact_sensitive(record.getMessage())

        payload: dict[str, object] = {
            "timestamp": _iso_timestamp(record.created),
            "level": record.levelname,
            "logger": record.name,
            "message": message,
            "otelTraceID": getattr(record, "otelTraceID", "0"),
            "otelSpanID": getattr(record, "otelSpanID", "0"),
            "otelServiceName": getattr(record, "otelServiceName", ""),
        }

        session = getattr(record, "session", None)
        if session and session != "-":
            payload["session"] = session

        if record.exc_info:
            payload["exception"] = redact_sensitive(self.formatException(record.exc_info))

        if self._include_extra:
            for key, value in record.__dict__.items():
                if key in _RESERVED_RECORD_ATTRS or key in payload or key == "session":
                    continue
                if key.startswith("_"):
                    continue
                payload[key] = _coerce(key, value)

        return json.dumps(payload, default=str, ensure_ascii=False)


def _iso_timestamp(created: float) -> str:
    """UTC ISO-8601 timestamp with millisecond precision and trailing ``Z``."""
    dt = datetime.fromtimestamp(created, tz=timezone.utc)
    return dt.strftime("%Y-%m-%dT%H:%M:%S.") + f"{dt.microsecond // 1000:03d}Z"


def _coerce(key: str, value: object) -> object:
    """Make an extra JSON-serializable; fully mask deny-listed keys, redact strings."""
    if is_sensitive_key(key):
        return "***"
    if isinstance(value, str):
        return redact_sensitive(value)
    if isinstance(value, (int, float, bool)) or value is None:
        return value
    return redact_sensitive(str(value))
