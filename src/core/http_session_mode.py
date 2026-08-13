"""Advertise MCP HTTP session mode to clients.

Deslicer AI (and other HTTP clients) probe ``GET /health`` before connecting.
Package version alone is not enough: published 0.6.8 is handshake-era, while
unreleased main also reports 0.6.8 after FastMCP 4. Clients must read the
explicit ``session_mode`` flag (and matching response headers).
"""

from __future__ import annotations

import os
from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as package_version
from pathlib import Path

try:  # Python 3.11+
    import tomllib  # type: ignore[attr-defined]
except ImportError:  # Python 3.10 fallback
    import tomli as tomllib  # type: ignore[no-redef]

SESSION_MODE_SESSIONLESS = "sessionless"
SESSION_MODE_SESSION = "session"
CLIENT_API_VERSION = 1
PACKAGE_DISTRIBUTION_NAME = "mcp-server-for-splunk"
HEADER_SERVER_VERSION = "X-MCP-Server-Version"
HEADER_SESSION_MODE = "X-MCP-Session-Mode"


def env_flag_is_true(name: str, default: bool = True) -> bool:
    """Return True when the named env var is the string ``true`` (case-insensitive)."""
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() == "true"


def resolve_package_version() -> str:
    """Return the installed package version, then pyproject.toml, then unknown."""
    try:
        return package_version(PACKAGE_DISTRIBUTION_NAME)
    except PackageNotFoundError:
        pass
    from_toml = _version_from_pyproject()
    return from_toml or "unknown"


def _version_from_pyproject() -> str | None:
    project_root = Path(__file__).resolve().parents[2]
    pyproject_path = project_root / "pyproject.toml"
    try:
        with pyproject_path.open("rb") as handle:
            data = tomllib.load(handle)
        version = data.get("project", {}).get("version")
        if isinstance(version, str) and version.strip():
            return version.strip()
    except Exception:
        return None
    return None


class HttpSessionModeAdvertiser:
    """Build the client-discovery payload and response headers for one process."""

    def __init__(
        self,
        *,
        version: str,
        stateless_http: bool,
        json_response: bool,
    ) -> None:
        self.version = version
        self.stateless_http = stateless_http
        self.json_response = json_response

    @classmethod
    def from_env(cls) -> HttpSessionModeAdvertiser:
        """Snapshot version and HTTP flags from the current process environment."""
        return cls(
            version=resolve_package_version(),
            stateless_http=env_flag_is_true("MCP_STATELESS_HTTP", True),
            json_response=env_flag_is_true("MCP_JSON_RESPONSE", True),
        )

    @property
    def session_mode(self) -> str:
        """Return ``sessionless`` when Streamable HTTP does not require sticky ids."""
        if self.stateless_http:
            return SESSION_MODE_SESSIONLESS
        return SESSION_MODE_SESSION

    def as_health_http_block(self) -> dict[str, object]:
        """Return the ``http`` object nested under ``GET /health``."""
        return {
            "stateless": self.stateless_http,
            "json_response": self.json_response,
            "session_mode": self.session_mode,
            "client_api": CLIENT_API_VERSION,
        }

    def as_response_headers(self) -> dict[str, str]:
        """Return headers clients can read without parsing the JSON body."""
        return {
            HEADER_SERVER_VERSION: self.version,
            HEADER_SESSION_MODE: self.session_mode,
        }

    def as_server_info_fields(self) -> dict[str, object]:
        """Return fields merged into the ``info://server`` resource."""
        return {
            "version": self.version,
            "session_mode": self.session_mode,
            "stateless_http": self.stateless_http,
            "json_response": self.json_response,
            "client_api": CLIENT_API_VERSION,
        }
