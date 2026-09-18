"""Operator-controlled TLS verification policy for Splunk requests."""

from __future__ import annotations


class TLSVerificationPolicy:
    """Prevent request headers from weakening the operator's TLS policy."""

    _ENABLED_VALUES = frozenset({"1", "true", "yes", "y", "on"})

    def __init__(self, operator_verification_enabled: bool) -> None:
        self._operator_verification_enabled = operator_verification_enabled

    def resolve(self, request_header: str | None) -> bool:
        """Return the effective TLS verification setting."""
        if self._operator_verification_enabled:
            return True
        if request_header is None:
            return False
        return request_header.strip().lower() in self._ENABLED_VALUES
