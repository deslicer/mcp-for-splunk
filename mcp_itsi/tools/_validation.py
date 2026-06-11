"""Write-path pre-flight validation for ITSI mutating operations.

Hard validation errors raise :class:`PayloadValidationError` (converted to an
error response by :class:`~mcp_itsi.core.base.BaseITSITool`). Non-fatal warnings
are pushed onto a request-scoped buffer and merged into the success response by
the same base class, so every create/update tool surfaces warnings inline with
no per-tool code.
"""

from __future__ import annotations

from contextvars import ContextVar
from typing import Any

from mcp_itsi.knowledge.schema import PayloadValidator, registry
from mcp_itsi.knowledge.schema.validator import ValidationResult

_pending_warnings: ContextVar[list[dict[str, str]] | None] = ContextVar(
    "itsi_validation_warnings", default=None
)


class PayloadValidationError(Exception):
    """Raised when a payload fails hard pre-flight validation."""

    def __init__(self, object_type: str, result: ValidationResult) -> None:
        self.object_type = object_type
        self.result = result
        count = len(result.errors)
        super().__init__(
            f"Payload for '{object_type}' failed validation with {count} error(s)."
        )


def reset_warnings() -> None:
    """Clear the request-scoped warnings buffer (call at request start)."""
    _pending_warnings.set([])


def drain_warnings() -> list[dict[str, str]]:
    """Return and clear any accumulated warnings."""
    warnings = _pending_warnings.get() or []
    _pending_warnings.set([])
    return warnings


def preflight(object_type: str, payload: Any, *, is_partial: bool) -> None:
    """Validate a payload before a write.

    Raises :class:`PayloadValidationError` on hard errors. Records warnings on
    the request-scoped buffer. Unknown object types are skipped (no schema to
    validate against), preserving forward compatibility.
    """
    if registry.get(object_type) is None or not isinstance(payload, dict):
        return
    result = PayloadValidator().validate(object_type, payload, is_partial=is_partial)
    if result.warnings:
        buffer = list(_pending_warnings.get() or [])
        buffer.extend(w.to_dict() for w in result.warnings)
        _pending_warnings.set(buffer)
    if not result.ok:
        raise PayloadValidationError(object_type, result)
