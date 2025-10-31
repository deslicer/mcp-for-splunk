import os

from fastmcp.server.middleware import Middleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse


def _authorized(headers: dict) -> bool:
    expected = os.getenv("PREMIUM_API_KEY")
    provided = headers.get("x-api-key")
    return bool(expected) and provided == expected


class AuthHTTPMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        if not _authorized(dict(request.headers)):
            return JSONResponse({"detail": "Unauthorized"}, status_code=401)
        return await call_next(request)


class AuthMCPMiddleware(Middleware):
    async def on_request(self, context, call_next):
        headers = getattr(context, "http_headers", None) or {}
        if not isinstance(headers, dict):
            headers = {}
        if not _authorized(headers):
            return {"status": "error", "error": "Unauthorized"}
        return await call_next(context)


def setup(mcp, root_app=None):
    """Entry point for the premium plugin."""
    mcp.add_middleware(AuthMCPMiddleware())
    if root_app is not None:
        root_app.add_middleware(AuthHTTPMiddleware)

