"""Sentry HTTP middleware for request tracing."""

import logging
import time
import uuid
from typing import cast

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from .config import _sentry_initialized, mcp_request_id, mcp_session_id
from .context import add_breadcrumb

logger = logging.getLogger(__name__)


class SentryHTTPMiddleware(BaseHTTPMiddleware):
    """ASGI middleware for Sentry HTTP request tracing."""

    async def dispatch(self, request: Request, call_next) -> Response:
        """Process HTTP request with Sentry tracing."""
        if not _sentry_initialized:
            return cast(Response, await call_next(request))

        try:
            import sentry_sdk
        except ImportError:
            return cast(Response, await call_next(request))

        # Extract session ID from headers
        session_id = (
            request.headers.get("MCP-Session-ID")
            or request.headers.get("mcp-session-id")
            or request.headers.get("X-Session-ID")
            or request.headers.get("x-session-id")
        )

        # Normalize session ID (handle "id, id" format)
        if session_id and "," in session_id:
            session_id = session_id.split(",")[0].strip()

        # Generate request ID
        request_id = (
            request.headers.get("X-Request-ID")
            or request.headers.get("x-request-id")
            or str(uuid.uuid4())[:8]
        )

        # Set context for downstream use
        session_token = mcp_session_id.set(session_id)
        request_token = mcp_request_id.set(request_id)

        # Determine transaction name based on path
        path = request.url.path
        method = request.method

        if "/mcp" in path:
            transaction_name = f"MCP {method} {path}"
        else:
            transaction_name = f"{method} {path}"

        start_time = time.perf_counter()

        try:
            with sentry_sdk.start_transaction(
                op="http.server",
                name=transaction_name,
                source="route",
            ) as transaction:
                transaction.set_tag("mcp.transport", "http")
                if session_id:
                    transaction.set_tag("mcp.session.id", session_id)
                transaction.set_tag("mcp.request.id", request_id)

                transaction.set_data("http.method", method)
                transaction.set_data("http.url", str(request.url))
                transaction.set_data("http.path", path)

                if request.client:
                    transaction.set_data("client.ip", request.client.host)

                add_breadcrumb(
                    message=f"HTTP {method} {path}",
                    category="http.request",
                    level="info",
                    data={"method": method, "path": path, "session_id": session_id},
                )

                response = cast(Response, await call_next(request))

                duration_ms = (time.perf_counter() - start_time) * 1000
                transaction.set_data("http.status_code", response.status_code)
                transaction.set_data("http.duration_ms", round(duration_ms, 2))

                if response.status_code >= 500:
                    transaction.set_status("internal_error")
                elif response.status_code >= 400:
                    transaction.set_status("invalid_argument")
                else:
                    transaction.set_status("ok")

                return response

        except Exception as e:
            sentry_sdk.capture_exception(e)
            raise

        finally:
            try:
                mcp_session_id.reset(session_token)
                mcp_request_id.reset(request_token)
            except Exception as e:
                logger.debug("Error resetting context: %s", e)

