"""Build per-client Splunk headers for the CLI connection test."""

from __future__ import annotations

import os


class SplunkTestHeaderManager:
    """Create FastMCP transport headers from the local environment."""

    @staticmethod
    def build_from_env() -> dict[str, str]:
        headers = {
            "X-Splunk-Host": os.getenv("SPLUNK_HOST", "").strip() or "localhost",
            "X-Splunk-Port": os.getenv("SPLUNK_PORT", "8089").strip(),
            "X-Splunk-Username": os.getenv("SPLUNK_USERNAME", "admin").strip(),
            "X-Splunk-Password": os.getenv("SPLUNK_PASSWORD", "changeme"),
            "X-Splunk-Scheme": os.getenv("SPLUNK_SCHEME", "https").strip(),
            "X-Splunk-Verify-SSL": (
                os.getenv("SPLUNK_VERIFY_SSL", "false").strip() or "false"
            ),
            "Accept": "application/json, text/event-stream",
        }
        bearer_credential = os.getenv("SPLUNK_TOKEN", "").strip()
        if bearer_credential:
            headers["X-Splunk-Token"] = bearer_credential
        return headers
