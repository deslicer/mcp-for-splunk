"""Helpers for resolving an :class:`ITSIRequestConfig` from an MCP request."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from mcp_itsi.client.http_client import ITSIClient
from mcp_itsi.config.headers import ITSIRequestConfig, extract_request_config
from mcp_itsi.config.settings import ITSIServerSettings, load_settings

logger = logging.getLogger(__name__)


@dataclass
class ITSICallContext:
    """Wraps a :class:`ITSIRequestConfig` with helpers for tools.

    Tools should never construct :class:`ITSIClient` directly; instead, do::

        async with ctx.client() as itsi:
            ...
    """

    request_config: ITSIRequestConfig
    settings: ITSIServerSettings

    def client(self) -> ITSIClient:
        return ITSIClient(self.request_config, timeout=self.settings.request_timeout_seconds)


def _request_headers_from_mcp_context(mcp_ctx: Any) -> dict[str, str]:
    """Best-effort extraction of HTTP headers from a FastMCP context.

    The function is defensive: when run in stdio mode there is no HTTP
    request, so it falls back to an empty mapping.
    """
    try:
        from fastmcp.server.dependencies import get_http_headers

        headers = get_http_headers(include_all=True) or {}
        if headers:
            return dict(headers)
    except Exception:  # pragma: no cover - dependency absent or no http req
        pass

    try:
        request = getattr(getattr(mcp_ctx, "request_context", None), "request", None)
        if request is not None and hasattr(request, "headers"):
            return dict(request.headers)
    except Exception:  # pragma: no cover - depends on framework internals
        pass

    return {}


def build_call_context(
    mcp_ctx: Any,
    settings: ITSIServerSettings | None = None,
) -> ITSICallContext:
    """Resolve a per-request :class:`ITSICallContext`.

    Raises :class:`ValueError` when no Splunk host/credentials are available.
    """
    settings = settings or load_settings()
    headers = _request_headers_from_mcp_context(mcp_ctx)
    cfg = extract_request_config(headers, settings)
    return ITSICallContext(request_config=cfg, settings=settings)
