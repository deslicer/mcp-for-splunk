"""Middleware for graceful handling of MCP client disconnects."""

from __future__ import annotations

import logging

from fastmcp.server.middleware import Middleware, MiddlewareContext

from src.core.session_disconnect import is_session_disconnect_error

logger = logging.getLogger(__name__)


class SessionDisconnectMiddleware(Middleware):
    """Log client disconnects at warning level instead of treating them as server errors."""

    async def on_request(self, context: MiddlewareContext, call_next):
        method = getattr(context, "method", "unknown")
        session_id = getattr(context, "session_id", None)

        try:
            return await call_next(context)
        except Exception as error:
            if not is_session_disconnect_error(error):
                raise

            logger.warning(
                "Client disconnected during MCP %s (session_id=%s): %s",
                method,
                session_id,
                error,
            )
            raise
