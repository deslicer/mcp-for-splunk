"""
Tests for Splunk client connection functionality.
"""
import os
from unittest.mock import Mock, patch

import pytest

from src.splunk_client import get_splunk_service


class TestSplunkClientConnection:
    """Test Splunk client connection functionality"""

    @patch('src.splunk_client.client.Service')
    def test_successful_connection(self, mock_service_class):
        """Test successful Splunk connection with mocked client"""
        # Mock the service instance
        mock_service = Mock()
        mock_service.login = Mock()
        mock_service.info = {"version": "9.0.0"}
        mock_service_class.return_value = mock_service

        # Test the connection
        with patch.dict(os.environ, {
            'SPLUNK_USERNAME': 'admin',
            'SPLUNK_PASSWORD': 'password'
        }):
            service = get_splunk_service()

        # Verify the service was returned and login called
        assert service == mock_service
        mock_service.login.assert_called()
        mock_service_class.assert_called_once()

    @patch('src.splunk_client.client.Service')
    def test_connection_failure(self, mock_service_class):
        """Test connection failure handling"""
        mock_service = Mock()
        mock_service.login.side_effect = Exception("Connection failed")
        mock_service_class.return_value = mock_service

        with patch.dict(os.environ, {
            'SPLUNK_USERNAME': 'admin',
            'SPLUNK_PASSWORD': 'password'
        }):
            with pytest.raises(ValueError, match="Failed to connect to Splunk"):
                get_splunk_service()

    def test_missing_credentials(self):
        """Test error when no credentials provided"""
        # Clear all Splunk environment variables
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValueError, match="Either SPLUNK_TOKEN or SPLUNK_USERNAME/SPLUNK_PASSWORD must be provided"):
                get_splunk_service()

    @patch('src.splunk_client.client.Service')
    def test_port_conversion_success(self, mock_service_class):
        """Test successful port conversion"""
        mock_service = Mock()
        mock_service.login = Mock()
        mock_service.info = {"version": "9.0.0"}
        mock_service_class.return_value = mock_service

        with patch.dict(os.environ, {
            'SPLUNK_HOST': 'localhost',
            'SPLUNK_PORT': '9999',
            'SPLUNK_USERNAME': 'admin',
            'SPLUNK_PASSWORD': 'password'
        }):
            get_splunk_service()

            # Verify port was converted to integer and passed correctly
            call_args = mock_service_class.call_args[1]
            assert call_args['port'] == 9999
            assert isinstance(call_args['port'], int)

    def test_invalid_port_value(self):
        """Test invalid port value handling"""
        with patch.dict(os.environ, {
            'SPLUNK_HOST': 'localhost',
            'SPLUNK_PORT': 'invalid',
            'SPLUNK_USERNAME': 'admin',
            'SPLUNK_PASSWORD': 'password'
        }):
            # This should raise ValueError during int() conversion
            with pytest.raises(ValueError):
                get_splunk_service()


class TestEnvironmentVariableHandling:
    """Test environment variable handling"""

    @patch('src.splunk_client.client.Service')
    def test_default_values(self, mock_service_class):
        """Test default values when environment variables not set"""
        mock_service = Mock()
        mock_service.login = Mock()
        mock_service.info = {"version": "9.0.0"}
        mock_service_class.return_value = mock_service

        with patch.dict(os.environ, {
            'SPLUNK_USERNAME': 'admin',
            'SPLUNK_PASSWORD': 'password'
        }, clear=True):
            get_splunk_service()

            call_args = mock_service_class.call_args[1]
            assert call_args['host'] == 'localhost'  # Default host
            assert call_args['port'] == 8089        # Default port
            assert call_args['verify'] is False     # Default SSL verification
