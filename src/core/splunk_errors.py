"""Safe connection diagnostics, independent of search execution state."""

import errno
import re
import socket
import ssl
from dataclasses import dataclass
from typing import Any

from splunklib.binding import AuthenticationError, HTTPError

# Unquoted credentials may contain spaces or punctuation. Consume the rest of
# that line rather than expose a suffix whose boundary cannot be determined.
_CREDENTIAL = re.compile(
    r"(?i)(?P<key>\b(?:authorization|x-splunk-token|x-splunk-password|"
    r"splunk_session_token|splunk_token|splunk_password|splunkToken|"
    r"password|token|api_key|apikey|secret))"
    r"(?P<sep>[\"']?\s*[:=,]\s*)"
    r"(?:\"(?:\\.|[^\"\\])*\"|'(?:\\.|[^'\\])*'|"
    r"[^\r\n]+)"
)
_URL_CREDENTIAL = re.compile(r"(?i)(https?://)[^\s/@]+@")


def safe_error_message(error: object) -> str:
    """Mask credential fields/headers and URL userinfo in diagnostic prose."""
    text = _CREDENTIAL.sub(lambda m: f"{m['key']}{m['sep']}[REDACTED]", str(error))
    return _URL_CREDENTIAL.sub(r"\1[REDACTED]@", text)


def classify_splunk_error(error: BaseException | None, *, default: str) -> str:
    """Classify typed causes, including urllib and explicitly chained failures.

    Classification never decides whether a search was dispatched. Avoid matching
    arbitrary HTTP response prose, which can mention TLS for unrelated reasons.
    """
    seen: set[int] = set()
    current = error
    fallback = default
    while current is not None and id(current) not in seen:
        seen.add(id(current))
        if isinstance(current, ssl.SSLCertVerificationError):
            return "certificate_verify_failed"
        if isinstance(current, socket.gaierror):
            return "dns_resolution_failed"
        if isinstance(current, AuthenticationError):
            return "authentication_failed"
        if isinstance(current, HTTPError):
            if current.status == 401:
                return "authentication_failed"
            if current.status == 403:
                return "permission_denied"
        if isinstance(current, ConnectionRefusedError):
            return "connection_refused"
        if isinstance(current, TimeoutError):
            return "connection_timeout"
        if isinstance(current, OSError) and current.errno in (
            errno.ENETUNREACH,
            errno.EHOSTUNREACH,
        ):
            return "network_unreachable"
        if isinstance(current, ssl.SSLError):
            fallback = "tls_error"
        reason = getattr(current, "reason", None)
        current = (
            current.__cause__
            or (reason if isinstance(reason, BaseException) else None)
            or (current.__context__ if not current.__suppress_context__ else None)
        )
    return fallback


@dataclass(frozen=True)
class SplunkAvailability:
    available: bool
    service: Any = None
    error: str = ""
    error_code: str = ""
