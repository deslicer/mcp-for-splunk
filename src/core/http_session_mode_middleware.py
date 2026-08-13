"""Attach session-mode discovery headers to every HTTP response."""

from __future__ import annotations

from typing import cast

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from src.core.http_session_mode import HttpSessionModeAdvertiser


class HttpSessionModeHeaderMiddleware(BaseHTTPMiddleware):
    """Add ``X-MCP-Server-Version`` and ``X-MCP-Session-Mode`` on responses."""

    def __init__(
        self,
        app,
        advertiser: HttpSessionModeAdvertiser | None = None,
    ) -> None:
        super().__init__(app)
        self._advertiser = advertiser or HttpSessionModeAdvertiser.from_env()

    async def dispatch(self, request: Request, call_next) -> Response:
        response = cast(Response, await call_next(request))
        for header_name, header_value in self._advertiser.as_response_headers().items():
            response.headers[header_name] = header_value
        return response
