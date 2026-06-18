"""Detect client/session disconnect errors from MCP transport layers."""

from __future__ import annotations

_DISCONNECT_EXCEPTION_TYPES: tuple[type[BaseException], ...]


def _load_disconnect_exception_types() -> tuple[type[BaseException], ...]:
    types: list[type[BaseException]] = []

    try:
        from anyio import BrokenResourceError, ClosedResourceError, EndOfStream

        types.extend([ClosedResourceError, BrokenResourceError, EndOfStream])
    except ImportError:
        pass

    try:
        from starlette.requests import ClientDisconnect

        types.append(ClientDisconnect)
    except ImportError:
        pass

    return tuple(types)


_DISCONNECT_EXCEPTION_TYPES = _load_disconnect_exception_types()


def is_session_disconnect_error(error: BaseException) -> bool:
    """Return True when the client disconnected before the response completed."""
    if isinstance(error, _DISCONNECT_EXCEPTION_TYPES):
        return True

    message = str(error).lower()
    disconnect_markers = (
        "closedresourceerror",
        "brokenresourceerror",
        "client disconnected",
        "connection reset",
        "end of stream",
    )
    return any(marker in message for marker in disconnect_markers)
