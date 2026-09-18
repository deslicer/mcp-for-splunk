"""Regression tests for local CLI Splunk authentication handling."""

from src.cli.splunk_auth_configuration import SplunkAuthConfiguration
from src.cli.splunk_test_headers import SplunkTestHeaderManager
from src.cli.test_mcp_server import _build_server_url_from_env


class TestSplunkAuthConfiguration:
    def test_accepts_host_with_bearer_credential(self):
        configuration = SplunkAuthConfiguration.from_env_values(
            {
                "SPLUNK_HOST": "splunk.example.com",
                "SPLUNK_TOKEN": "test-bearer-value",
            }
        )

        assert configuration.is_complete()

    def test_rejects_host_without_complete_authentication(self):
        configuration = SplunkAuthConfiguration.from_env_values(
            {
                "SPLUNK_HOST": "splunk.example.com",
                "SPLUNK_USERNAME": "admin",
            }
        )

        assert not configuration.is_complete()


class TestSplunkTestHeaderManager:
    def test_forwards_bearer_credential(self, monkeypatch):
        monkeypatch.setenv("SPLUNK_TOKEN", "test-bearer-value")

        headers = SplunkTestHeaderManager.build_from_env()

        assert headers["X-Splunk-Token"] == "test-bearer-value"


class TestMCPServerUrl:
    def test_defaults_to_local_server_port(self, monkeypatch):
        monkeypatch.delenv("MCP_SERVER_HOST", raising=False)
        monkeypatch.delenv("MCP_SERVER_PORT", raising=False)

        assert _build_server_url_from_env() == "http://localhost:8003/mcp/"
