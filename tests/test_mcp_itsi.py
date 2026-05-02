"""Tests for the ITSI MCP server package.

These tests focus on the parts of ``mcp_itsi`` that don't require a live
Splunk instance: configuration parsing, base tool dispatch, registration,
the knowledge bundle, and the FastMCP wiring.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest

from mcp_itsi.client.http_client import ITSIClient, ITSIError, ITSINotFoundError
from mcp_itsi.config.headers import extract_request_config
from mcp_itsi.config.settings import ITSIServerSettings, load_settings
from mcp_itsi.core.base import BaseITSITool, ToolMetadata
from mcp_itsi.core.responses import error_response, success_response
from mcp_itsi.knowledge import catalog
from mcp_itsi.server import build_server

# ---------------------------------------------------------------------------
# Configuration / headers
# ---------------------------------------------------------------------------


def test_load_settings_returns_defaults(monkeypatch):
    for key in (
        "MCP_ITSI_SERVER_HOST",
        "MCP_ITSI_SERVER_PORT",
        "MCP_ITSI_PORT",
        "MCP_ITSI_TRANSPORT",
        "MCP_TRANSPORT",
        "SPLUNK_HOST",
        "SPLUNK_USERNAME",
        "SPLUNK_PASSWORD",
        "SPLUNK_TOKEN",
        "ITSI_APP",
        "ITSI_USER_NS",
        "ITSI_API_VERSION",
        "MCP_STATELESS_HTTP",
        "MCP_JSON_RESPONSE",
    ):
        monkeypatch.delenv(key, raising=False)
    s = load_settings()
    assert s.server_port == 8004
    assert s.transport == "http"
    assert s.default_itsi_app == "SA-ITOA"
    assert s.default_itsi_user_ns == "nobody"


def test_extract_request_config_uses_headers():
    settings = ITSIServerSettings()
    headers = {
        "X-Splunk-Host": "so1",
        "X-Splunk-Port": "8089",
        "X-Splunk-Username": "admin",
        "X-Splunk-Password": "Chang3d!",
        "X-Splunk-Scheme": "https",
        "X-Splunk-Verify-SSL": "false",
        "X-ITSI-App": "MyApp",
    }
    cfg = extract_request_config(headers, settings)
    assert cfg.splunk_host == "so1"
    assert cfg.splunk_port == 8089
    assert cfg.splunk_username == "admin"
    assert cfg.itsi_app == "MyApp"
    assert cfg.base_url == "https://so1:8089"
    assert cfg.itsi_namespace == "/servicesNS/nobody/MyApp"
    assert cfg.has_credentials() is True


def test_extract_request_config_token_auth():
    settings = ITSIServerSettings(default_splunk_host="so1")
    cfg = extract_request_config({"X-Splunk-Token": "abc"}, settings)
    assert cfg.splunk_token == "abc"
    assert cfg.has_credentials() is True


def test_extract_request_config_requires_host():
    settings = ITSIServerSettings()
    with pytest.raises(ValueError, match="No Splunk host"):
        extract_request_config({"X-Splunk-Token": "abc"}, settings)


def test_extract_request_config_requires_credentials():
    settings = ITSIServerSettings(default_splunk_host="so1")
    with pytest.raises(ValueError, match="No Splunk credentials"):
        extract_request_config({}, settings)


# ---------------------------------------------------------------------------
# Knowledge bundle
# ---------------------------------------------------------------------------


def test_knowledge_catalog_lists_all_docs():
    docs = catalog.list_docs()
    slugs = {d.slug for d in docs}
    expected = {
        "overview",
        "api/reference",
        "api/schema",
        "service-insights",
        "entity-integrations",
        "event-analytics",
        "modules",
        "best-practices",
        "cookbook/header-auth",
    }
    assert expected.issubset(slugs)


def test_knowledge_get_doc_round_trip():
    entry = catalog.get_doc("api/reference")
    assert entry is not None
    assert entry.uri == "itsi://docs/api/reference"
    text = entry.read()
    assert "ITSI REST API reference" in text
    assert "itoa_interface" in text


def test_knowledge_search_returns_matches():
    hits = catalog.search("KPI")
    assert hits, "expected at least one doc to match 'KPI'"
    slugs = [h[0].slug for h in hits]
    assert "service-insights" in slugs or "best-practices" in slugs


# ---------------------------------------------------------------------------
# Base tool dispatch
# ---------------------------------------------------------------------------


class _PingTool(BaseITSITool):
    METADATA = ToolMetadata(
        name="itsi_ping",
        description="No-op tool used in unit tests.",
        category="test",
        requires_connection=False,
    )

    async def execute(self, mcp_ctx, ctx, message: str = "pong") -> dict[str, Any]:
        return success_response(message=message)


@pytest.mark.asyncio
async def test_base_tool_no_connection_required():
    tool = _PingTool()
    result = await tool(MagicMock(), message="hi")
    assert result == {"status": "success", "message": "hi"}


class _BoomTool(BaseITSITool):
    METADATA = ToolMetadata(
        name="itsi_boom",
        description="Tool that always raises.",
        category="test",
        requires_connection=False,
    )

    async def execute(self, mcp_ctx, ctx) -> dict[str, Any]:
        raise RuntimeError("kaboom")


@pytest.mark.asyncio
async def test_base_tool_handles_exceptions():
    tool = _BoomTool()
    result = await tool(MagicMock())
    assert result["status"] == "error"
    assert "kaboom" in result["error"]


# ---------------------------------------------------------------------------
# HTTP client error mapping
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_itsi_client_maps_404_to_not_found():
    cfg = MagicMock()
    cfg.base_url = "https://example.invalid:8089"
    cfg.verify_ssl = False
    cfg.splunk_token = None
    cfg.splunk_username = None
    cfg.splunk_password = None
    cfg.itsi_namespace = "/servicesNS/nobody/SA-ITOA"

    client = ITSIClient(cfg, timeout=1.0)
    client._client = MagicMock()
    response = httpx.Response(
        404,
        request=httpx.Request("GET", "https://example.invalid:8089/foo"),
        json={"messages": [{"text": "not found"}]},
    )
    client._client.request = AsyncMock(return_value=response)
    with pytest.raises(ITSINotFoundError):
        await client.get_json("/itoa_interface/service/missing")


@pytest.mark.asyncio
async def test_itsi_client_maps_500_to_error():
    cfg = MagicMock()
    cfg.base_url = "https://example.invalid:8089"
    cfg.verify_ssl = False
    cfg.splunk_token = None
    cfg.splunk_username = None
    cfg.splunk_password = None
    cfg.itsi_namespace = "/servicesNS/nobody/SA-ITOA"

    client = ITSIClient(cfg, timeout=1.0)
    client._client = MagicMock()
    response = httpx.Response(
        500,
        request=httpx.Request("GET", "https://example.invalid:8089/foo"),
        text="boom",
    )
    client._client.request = AsyncMock(return_value=response)
    with pytest.raises(ITSIError):
        await client.get_json("/itoa_interface/service")


# ---------------------------------------------------------------------------
# FastMCP wiring (the canary test)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_build_server_registers_everything():
    mcp, _ = build_server()
    tools = await mcp.list_tools()
    resources = await mcp.list_resources()
    prompts = await mcp.list_prompts()

    tool_names = {getattr(t, "name", "") for t in tools}
    assert "itsi_list_services" in tool_names
    assert "itsi_list_notable_events" in tool_names
    assert "itsi_read_doc" in tool_names

    resource_uris = {str(getattr(r, "uri", "")) for r in resources}
    assert "itsi://docs/api/reference" in resource_uris

    prompt_names = {getattr(p, "name", "") for p in prompts}
    assert "itsi_service_onboarding" in prompt_names


def test_error_response_helpers():
    assert success_response(a=1) == {"status": "success", "a": 1}
    assert error_response("boom", b=2) == {"status": "error", "error": "boom", "b": 2}
