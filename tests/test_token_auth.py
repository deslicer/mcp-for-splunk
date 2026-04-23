"""
Tests for Splunk token / bearer authentication support.

Covers the modular client (`src/client/splunk_client.py`), the HTTP header
extraction utility (`src/core/utils.py`), the enhanced extractor
(`src/core/enhanced_config_extractor.py`), and the security validation in
`src/core/client_identity.py`.
"""

import os
from unittest.mock import patch

import pytest


# ---------------------------------------------------------------------------
# src/client/splunk_client.py
# ---------------------------------------------------------------------------
class TestModularClientTokenAuth:
    """Verify the modular Splunk client honours bearer / session tokens."""

    def test_get_splunk_config_maps_splunk_token_to_bearer_kwarg(self):
        from src.client.splunk_client import get_splunk_config

        with patch.dict(os.environ, {}, clear=True):
            cfg = get_splunk_config({
                "splunk_host": "splunk.example.com",
                "splunk_token": "tok-abc",
            })

        assert cfg["host"] == "splunk.example.com"
        assert cfg["splunkToken"] == "tok-abc"

    def test_get_splunk_config_maps_session_token_to_token(self):
        from src.client.splunk_client import get_splunk_config

        with patch.dict(os.environ, {}, clear=True):
            cfg = get_splunk_config({
                "splunk_host": "splunk.example.com",
                "splunk_session_token": "session-xyz",
            })

        assert cfg["token"] == "session-xyz"

    def test_get_splunk_config_picks_up_env_token(self):
        from src.client.splunk_client import get_splunk_config

        with patch.dict(os.environ, {"SPLUNK_TOKEN": "env-bearer"}, clear=True):
            cfg = get_splunk_config(None)

        assert cfg["splunkToken"] == "env-bearer"

    @patch("src.client.splunk_client.client.connect")
    def test_get_splunk_service_drops_password_when_token_present(self, mock_connect):
        from src.client.splunk_client import get_splunk_service

        with patch.dict(os.environ, {}, clear=True):
            get_splunk_service({
                "splunk_host": "splunk.example.com",
                "splunk_username": "admin",
                "splunk_password": "ignored",
                "splunk_token": "tok-abc",
            })

        kwargs = mock_connect.call_args[1]
        assert kwargs["splunkToken"] == "tok-abc"
        assert "password" not in kwargs
        assert "username" not in kwargs

    def test_get_splunk_service_requires_some_credential(self):
        from src.client.splunk_client import get_splunk_service

        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValueError, match="No Splunk credentials provided"):
                get_splunk_service({"splunk_host": "splunk.example.com"})


# ---------------------------------------------------------------------------
# src/core/utils.py
# ---------------------------------------------------------------------------
class TestHeaderExtractionForTokens:
    def test_x_splunk_token_header_extracted(self):
        from src.core.utils import extract_client_config_from_headers

        cfg = extract_client_config_from_headers({
            "X-Splunk-Host": "splunk.example.com",
            "X-Splunk-Token": "header-token",
        })

        assert cfg is not None
        assert cfg["splunk_token"] == "header-token"
        assert "splunk_password" not in cfg

    def test_x_splunk_session_token_header_extracted(self):
        from src.core.utils import extract_client_config_from_headers

        cfg = extract_client_config_from_headers({
            "X-Splunk-Host": "splunk.example.com",
            "X-Splunk-Session-Token": "session-token",
        })

        assert cfg is not None
        assert cfg["splunk_session_token"] == "session-token"

    def test_authorization_bearer_used_when_mcp_auth_disabled(self):
        from src.core.utils import extract_client_config_from_headers

        with patch.dict(os.environ, {"MCP_AUTH_DISABLED": "true"}, clear=False):
            cfg = extract_client_config_from_headers({
                "X-Splunk-Host": "splunk.example.com",
                "Authorization": "Bearer abc.def.ghi",
            })

        assert cfg is not None
        assert cfg["splunk_token"] == "abc.def.ghi"

    def test_authorization_bearer_ignored_when_mcp_auth_enabled(self):
        from src.core.utils import extract_client_config_from_headers

        with patch.dict(os.environ, {"MCP_AUTH_DISABLED": "false"}, clear=False):
            cfg = extract_client_config_from_headers({
                "X-Splunk-Host": "splunk.example.com",
                "Authorization": "Bearer abc.def.ghi",
            })

        assert cfg is not None
        assert "splunk_token" not in cfg

    def test_explicit_splunk_token_header_wins_over_authorization(self):
        from src.core.utils import extract_client_config_from_headers

        with patch.dict(os.environ, {"MCP_AUTH_DISABLED": "true"}, clear=False):
            cfg = extract_client_config_from_headers({
                "X-Splunk-Host": "splunk.example.com",
                "X-Splunk-Token": "preferred",
                "Authorization": "Bearer fallback",
            })

        assert cfg["splunk_token"] == "preferred"


# ---------------------------------------------------------------------------
# src/core/enhanced_config_extractor.py
# ---------------------------------------------------------------------------
class TestEnhancedConfigExtractorTokenNormalization:
    def test_normalize_keeps_token_distinct_from_password(self):
        from src.core.enhanced_config_extractor import EnhancedConfigExtractor

        extractor = EnhancedConfigExtractor()
        normalized = extractor._normalize_config(
            {
                "host": "splunk.example.com",
                "token": "abc.def.ghi",
            }
        )

        assert normalized["splunk_host"] == "splunk.example.com"
        assert normalized["splunk_token"] == "abc.def.ghi"
        assert "splunk_password" not in normalized

    def test_normalize_session_token_alias(self):
        from src.core.enhanced_config_extractor import EnhancedConfigExtractor

        extractor = EnhancedConfigExtractor()
        normalized = extractor._normalize_config(
            {"session_token": "session-value"}
        )

        assert normalized["splunk_session_token"] == "session-value"

    def test_server_default_config_picks_up_splunk_token_env(self):
        from src.core.enhanced_config_extractor import EnhancedConfigExtractor

        extractor = EnhancedConfigExtractor()
        with patch.dict(
            os.environ,
            {"SPLUNK_HOST": "splunk.example.com", "SPLUNK_TOKEN": "env-token"},
            clear=False,
        ):
            cfg = extractor._get_server_default_config()

        assert cfg["splunk_token"] == "env-token"


# ---------------------------------------------------------------------------
# src/core/client_identity.py
# ---------------------------------------------------------------------------
class TestClientIdentityTokenValidation:
    def test_validate_accepts_token_only_config(self):
        from src.core.client_identity import ClientConnectionManager

        mgr = ClientConnectionManager()
        # Should not raise
        mgr._validate_client_config({
            "splunk_host": "splunk.example.com",
            "splunk_token": "abc",
        })

    def test_validate_accepts_username_password_config(self):
        from src.core.client_identity import ClientConnectionManager

        mgr = ClientConnectionManager()
        mgr._validate_client_config({
            "splunk_host": "splunk.example.com",
            "splunk_username": "admin",
            "splunk_password": "p",
        })

    def test_validate_rejects_when_no_auth_provided(self):
        from src.core.client_identity import ClientConnectionManager, SecurityError

        mgr = ClientConnectionManager()
        with pytest.raises(SecurityError, match="authentication missing"):
            mgr._validate_client_config({"splunk_host": "splunk.example.com"})

    def test_token_fingerprint_changes_identity_hash(self):
        """Different bearer tokens should produce different identity hashes."""
        from src.core.client_identity import ClientConnectionManager

        mgr = ClientConnectionManager()
        h1 = mgr._normalize_config_for_hash({
            "splunk_host": "splunk.example.com",
            "splunk_token": "token-A",
        })
        h2 = mgr._normalize_config_for_hash({
            "splunk_host": "splunk.example.com",
            "splunk_token": "token-B",
        })
        assert h1 != h2
        # Raw token must not appear in the hash input
        assert "token-A" not in h1
        assert "token-B" not in h2
