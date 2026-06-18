"""Tests for client/session disconnect detection and middleware."""

from unittest.mock import AsyncMock, Mock

import pytest

from src.core.session_disconnect import is_session_disconnect_error
from src.core.session_disconnect_middleware import SessionDisconnectMiddleware


class TestSessionDisconnectDetection:
    def test_detects_anyio_closed_resource_error(self):
        from anyio import ClosedResourceError

        assert is_session_disconnect_error(ClosedResourceError())

    def test_detects_starlette_client_disconnect(self):
        from starlette.requests import ClientDisconnect

        assert is_session_disconnect_error(ClientDisconnect())

    def test_ignores_unrelated_errors(self):
        assert not is_session_disconnect_error(RuntimeError("something else"))


class TestSessionDisconnectMiddleware:
    @pytest.mark.asyncio
    async def test_logs_and_reraises_disconnect_errors(self, caplog):
        from anyio import ClosedResourceError

        middleware = SessionDisconnectMiddleware()
        context = Mock(method="tools/call", session_id="sess-1")
        call_next = AsyncMock(side_effect=ClosedResourceError())

        with caplog.at_level("WARNING"):
            with pytest.raises(ClosedResourceError):
                await middleware.on_request(context, call_next)

        assert any("Client disconnected" in record.message for record in caplog.records)

    @pytest.mark.asyncio
    async def test_passes_through_other_errors(self):
        middleware = SessionDisconnectMiddleware()
        context = Mock(method="tools/call", session_id="sess-1")
        call_next = AsyncMock(side_effect=ValueError("bad input"))

        with pytest.raises(ValueError, match="bad input"):
            await middleware.on_request(context, call_next)
