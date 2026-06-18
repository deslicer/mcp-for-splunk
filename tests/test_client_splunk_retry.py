"""Tests for Splunk connection retry with exponential backoff."""

import os
from unittest.mock import Mock, patch

import pytest

from src.client.splunk_client import get_splunk_service


class TestSplunkConnectRetry:
    @patch("src.client.splunk_client.time.sleep")
    @patch("src.client.splunk_client.client.connect")
    def test_retries_transient_failures(self, mock_connect, mock_sleep):
        mock_service = Mock()
        mock_connect.side_effect = [OSError("Network unreachable"), mock_service]

        with patch.dict(
            os.environ,
            {
                "SPLUNK_USERNAME": "admin",
                "SPLUNK_PASSWORD": "password",
                "SPLUNK_CONNECT_RETRY_COUNT": "3",
                "SPLUNK_CONNECT_RETRY_BASE_DELAY": "2",
            },
            clear=True,
        ):
            service = get_splunk_service()

        assert service is mock_service
        assert mock_connect.call_count == 2
        mock_sleep.assert_called_once_with(2.0)

    @patch("src.client.splunk_client.time.sleep")
    @patch("src.client.splunk_client.client.connect")
    def test_raises_after_exhausting_retries(self, mock_connect, mock_sleep):
        mock_connect.side_effect = OSError("Name or service not known")

        with patch.dict(
            os.environ,
            {
                "SPLUNK_USERNAME": "admin",
                "SPLUNK_PASSWORD": "password",
                "SPLUNK_CONNECT_RETRY_COUNT": "2",
                "SPLUNK_CONNECT_RETRY_BASE_DELAY": "1",
            },
            clear=True,
        ):
            with pytest.raises(OSError, match="Name or service not known"):
                get_splunk_service()

        assert mock_connect.call_count == 2
        mock_sleep.assert_called_once_with(1.0)

    @patch("src.client.splunk_client.client.connect")
    def test_success_on_first_attempt_skips_sleep(self, mock_connect):
        mock_service = Mock()
        mock_connect.return_value = mock_service

        with patch.dict(
            os.environ,
            {
                "SPLUNK_USERNAME": "admin",
                "SPLUNK_PASSWORD": "password",
            },
            clear=True,
        ):
            service = get_splunk_service()

        assert service is mock_service
        mock_connect.assert_called_once()
