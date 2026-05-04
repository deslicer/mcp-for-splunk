"""Response shaping helpers shared by every ITSI tool/resource."""

from __future__ import annotations

from typing import Any


def success_response(**data: Any) -> dict[str, Any]:
    """Return a uniform success payload."""
    return {"status": "success", **data}


def error_response(error: str, **extra: Any) -> dict[str, Any]:
    """Return a uniform error payload (never raises)."""
    return {"status": "error", "error": error, **extra}
