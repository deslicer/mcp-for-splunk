"""Tests for BaseTool.check_splunk_available header-based config resolution."""

from unittest.mock import MagicMock, patch

import pytest
from fastmcp import Context

from src.core.base import BaseTool, SplunkContext


class _TestTool(BaseTool):
    """Minimal concrete tool for testing BaseTool helpers."""

    async def execute(self, ctx: Context, *args, **kwargs):
        return {"status": "success"}


@pytest.fixture
def tool():
    return _TestTool("test", "test tool")


@pytest.fixture
def ctx():
    mock_ctx = MagicMock(spec=Context)
    mock_request = MagicMock()
    mock_request.state.client_config = None
    mock_ctx.request_context.request = mock_request
    mock_ctx.request_context.lifespan_context = SplunkContext(
        service=None,
        is_connected=False,
        client_config={},
    )
    return mock_ctx


class TestCheckSplunkAvailable:
    """Verify check_splunk_available resolves header-based client config."""

    @patch("src.client.splunk_client.get_splunk_service")
    @patch("src.core.base.get_http_headers")
    def test_uses_http_headers_when_request_state_empty(
        self, mock_get_http_headers, mock_get_splunk_service, tool, ctx
    ):
        """Header config should be used when request.state has no client_config."""
        mock_get_http_headers.return_value = {
            "X-Splunk-Host": "splunk.example.com",
            "X-Splunk-Port": "8089",
            "X-Splunk-Token": "test-token",
        }
        mock_service = MagicMock()
        mock_get_splunk_service.return_value = mock_service

        is_available, service, error = tool.check_splunk_available(ctx)

        assert is_available is True
        assert service is mock_service
        assert error == ""
        mock_get_splunk_service.assert_called_once_with(
            {
                "splunk_host": "splunk.example.com",
                "splunk_port": 8089,
                "splunk_token": "test-token",
            }
        )

    @patch("src.client.splunk_client.get_splunk_service")
    @patch("src.core.base.get_http_headers")
    def test_prefers_request_state_over_headers(
        self, mock_get_http_headers, mock_get_splunk_service, tool, ctx
    ):
        """Request state client_config takes priority over HTTP headers."""
        ctx.request_context.request.state.client_config = {
            "splunk_host": "state.example.com",
            "splunk_port": 8089,
        }
        mock_get_http_headers.return_value = {
            "X-Splunk-Host": "header.example.com",
            "X-Splunk-Port": "8089",
        }
        mock_service = MagicMock()
        mock_get_splunk_service.return_value = mock_service

        is_available, service, error = tool.check_splunk_available(ctx)

        assert is_available is True
        assert service is mock_service
        assert error == ""
        mock_get_splunk_service.assert_called_once_with(
            {
                "splunk_host": "state.example.com",
                "splunk_port": 8089,
            }
        )

    @patch("src.client.splunk_client.get_splunk_service")
    @patch("src.core.base.get_http_headers")
    def test_falls_back_to_degraded_mode_when_no_client_config(
        self, mock_get_http_headers, mock_get_splunk_service, tool, ctx
    ):
        """Without client config, degraded lifespan connection is reported unavailable."""
        mock_get_http_headers.return_value = {}

        is_available, service, error = tool.check_splunk_available(ctx)

        assert is_available is False
        assert service is None
        assert "degraded mode" in error
        mock_get_splunk_service.assert_not_called()

    @patch("src.client.splunk_client.get_splunk_service")
    @patch("src.core.base.get_http_headers")
    def test_falls_back_to_lifespan_when_headers_fail(
        self, mock_get_http_headers, mock_get_splunk_service, tool, ctx
    ):
        """When header connection fails, fall back to lifespan default service."""
        mock_get_http_headers.return_value = {
            "X-Splunk-Host": "bad.example.com",
            "X-Splunk-Port": "8089",
        }
        mock_get_splunk_service.side_effect = Exception("connection refused")

        lifespan_service = MagicMock()
        ctx.request_context.lifespan_context = SplunkContext(
            service=lifespan_service,
            is_connected=True,
            client_config={},
        )

        is_available, service, error = tool.check_splunk_available(ctx)

        assert is_available is True
        assert service is lifespan_service
        assert error == ""
