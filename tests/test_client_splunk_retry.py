"""Tests for Splunk connection retry with exponential backoff."""

import errno
import os
from unittest.mock import Mock, patch

import pytest

from src.client.splunk_client import _connect_with_retry, get_splunk_service


class TestSplunkConnectRetry:
    def test_empty_retry_plan_raises_explicit_error(self, monkeypatch):
        monkeypatch.setattr("src.client.splunk_client._get_connect_retry_settings", lambda: (0, 0))
        connect = Mock()
        monkeypatch.setattr("src.client.splunk_client.client.connect", connect)

        with pytest.raises(RuntimeError, match="No Splunk connection attempts were made"):
            _connect_with_retry({}, "basic")

        connect.assert_not_called()

    @pytest.mark.parametrize("retry_count", ["0", "-1"])
    def test_nonpositive_retry_count_still_preserves_connection_error(
        self, monkeypatch, retry_count
    ):
        error = OSError("connection reset")
        connect = Mock(side_effect=error)
        monkeypatch.setattr("src.client.splunk_client.client.connect", connect)
        monkeypatch.setenv("SPLUNK_CONNECT_RETRY_COUNT", retry_count)

        with pytest.raises(OSError) as raised:
            _connect_with_retry({}, "basic")

        assert raised.value is error
        connect.assert_called_once()

    @patch("src.client.splunk_client.time.sleep")
    @patch("src.client.splunk_client.client.connect")
    def test_retries_transient_failures(self, mock_connect, mock_sleep):
        mock_service = Mock()
        mock_connect.side_effect = [OSError("Connection reset by peer"), mock_service]

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
    def test_does_not_retry_network_unreachable(self, mock_connect, mock_sleep):
        mock_connect.side_effect = OSError(errno.ENETUNREACH, "Network is unreachable")

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
            with pytest.raises(OSError, match="Network is unreachable"):
                get_splunk_service()

        assert mock_connect.call_count == 1
        mock_sleep.assert_not_called()

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
