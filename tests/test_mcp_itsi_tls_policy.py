"""Tests for operator-controlled ITSI TLS verification."""

from mcp_itsi.config.headers import extract_request_config
from mcp_itsi.config.settings import ITSIServerSettings
from mcp_itsi.config.tls_policy import TLSVerificationPolicy


class TestTLSVerificationPolicy:
    def test_secure_operator_default_rejects_header_downgrade(self):
        policy = TLSVerificationPolicy(operator_verification_enabled=True)

        assert policy.resolve("false") is True

    def test_secure_operator_default_accepts_verified_request(self):
        policy = TLSVerificationPolicy(operator_verification_enabled=True)

        assert policy.resolve("true") is True

    def test_explicit_lab_default_allows_insecure_transport(self):
        policy = TLSVerificationPolicy(operator_verification_enabled=False)

        assert policy.resolve(None) is False

    def test_lab_default_allows_request_to_restore_verification(self):
        policy = TLSVerificationPolicy(operator_verification_enabled=False)

        assert policy.resolve("true") is True


class TestITSIRequestTLSConfiguration:
    def test_request_cannot_downgrade_secure_operator_default(self):
        settings = ITSIServerSettings(
            default_splunk_host="splunk.example.com",
            default_splunk_verify_ssl=True,
        )

        configuration = extract_request_config(
            {
                "X-Splunk-Token": "abc",
                "X-Splunk-Verify-SSL": "false",
            },
            settings,
        )

        assert configuration.verify_ssl is True
