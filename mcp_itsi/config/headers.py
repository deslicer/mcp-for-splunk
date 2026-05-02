"""Per-request configuration extracted from MCP HTTP headers.

The ITSI MCP server intentionally re-uses the same ``X-Splunk-*`` headers used
by the parent ``mcp-for-splunk`` server so AI clients can talk to both
servers with a single set of credentials. Optional ``X-ITSI-*`` overrides let
clients target a non-default ITSI app namespace or API version per request.
"""

from __future__ import annotations

import logging
from collections.abc import Mapping
from dataclasses import dataclass, field

from mcp_itsi.config.settings import ITSIServerSettings

logger = logging.getLogger(__name__)

HEADER_PREFIX_SPLUNK = "X-Splunk-"
HEADER_PREFIX_ITSI = "X-ITSI-"


@dataclass
class ITSIRequestConfig:
    """Effective configuration for a single MCP request."""

    splunk_host: str
    splunk_port: int = 8089
    splunk_scheme: str = "https"
    splunk_username: str | None = None
    splunk_password: str | None = None
    splunk_token: str | None = None
    verify_ssl: bool = False

    itsi_app: str = "SA-ITOA"
    user_ns: str = "nobody"
    api_version: str = "vLatest"

    extra_headers: dict[str, str] = field(default_factory=dict)

    @property
    def base_url(self) -> str:
        return f"{self.splunk_scheme}://{self.splunk_host}:{self.splunk_port}"

    @property
    def itsi_namespace(self) -> str:
        return f"/servicesNS/{self.user_ns}/{self.itsi_app}"

    def has_credentials(self) -> bool:
        return bool(self.splunk_token) or bool(self.splunk_username and self.splunk_password)


def _ci_get(headers: Mapping[str, str], name: str) -> str | None:
    """Case-insensitive header lookup."""
    if name in headers:
        return headers[name]
    lower = name.lower()
    for key, value in headers.items():
        if key.lower() == lower:
            return value
    return None


def _bool_header(value: str | None, default: bool) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


def _int_header(value: str | None, default: int) -> int:
    if value is None or not value.strip():
        return default
    try:
        return int(value)
    except ValueError:
        return default


def extract_request_config(
    headers: Mapping[str, str] | None,
    settings: ITSIServerSettings,
) -> ITSIRequestConfig:
    """Build an :class:`ITSIRequestConfig` from the incoming request headers.

    Defaults fall back to the server-level settings when a header is missing.
    """

    headers = headers or {}

    host = _ci_get(headers, "X-Splunk-Host") or settings.default_splunk_host
    if not host:
        raise ValueError(
            "No Splunk host provided. Send X-Splunk-Host or set SPLUNK_HOST in the env."
        )

    cfg = ITSIRequestConfig(
        splunk_host=host,
        splunk_port=_int_header(_ci_get(headers, "X-Splunk-Port"), settings.default_splunk_port),
        splunk_scheme=_ci_get(headers, "X-Splunk-Scheme") or settings.default_splunk_scheme,
        splunk_username=_ci_get(headers, "X-Splunk-Username") or settings.default_splunk_username,
        splunk_password=_ci_get(headers, "X-Splunk-Password") or settings.default_splunk_password,
        splunk_token=_ci_get(headers, "X-Splunk-Token") or settings.default_splunk_token,
        verify_ssl=_bool_header(
            _ci_get(headers, "X-Splunk-Verify-SSL"), settings.default_splunk_verify_ssl
        ),
        itsi_app=_ci_get(headers, "X-ITSI-App") or settings.default_itsi_app,
        user_ns=_ci_get(headers, "X-ITSI-User-NS") or settings.default_itsi_user_ns,
        api_version=_ci_get(headers, "X-ITSI-API-Version") or settings.default_itsi_version,
    )

    if not cfg.has_credentials():
        raise ValueError(
            "No Splunk credentials provided. Send X-Splunk-Token, or "
            "X-Splunk-Username and X-Splunk-Password headers."
        )

    return cfg
