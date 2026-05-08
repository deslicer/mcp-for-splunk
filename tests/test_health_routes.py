"""Verify the /health JSON endpoint surfaces loaded plugins and toolsets.

Operators rely on /health to confirm which plugins are active in a
running server, and clients can use ``available_toolsets`` to discover
the universe of values they may pass in ``X-MCP-Toolsets``.
"""

from __future__ import annotations

from fastmcp import FastMCP
from starlette.testclient import TestClient

from src.routes.health import setup_health_routes


def _build_app(mcp: FastMCP):
    """Return a Starlette/ASGI app that exposes the health routes for testing."""
    setup_health_routes(mcp)
    return mcp.http_app()


def test_health_api_includes_loaded_plugins_when_plugins_present():
    mcp = FastMCP(name="HealthTestWithPlugins")
    mcp._loaded_plugins = [{"name": "itsi"}, {"name": "auth"}]

    client = TestClient(_build_app(mcp))
    resp = client.get("/health")

    assert resp.status_code == 200
    body = resp.json()
    assert body.get("loaded_plugins") == [{"name": "itsi"}, {"name": "auth"}]


def test_health_api_available_toolsets_unions_splunk_with_plugins():
    mcp = FastMCP(name="HealthTestToolsets")
    mcp._loaded_plugins = [{"name": "itsi"}]

    client = TestClient(_build_app(mcp))
    resp = client.get("/health")

    assert resp.status_code == 200
    body = resp.json()
    assert set(body.get("available_toolsets", [])) == {"splunk", "itsi"}


def test_health_api_handles_missing_loaded_plugins_attribute():
    mcp = FastMCP(name="HealthTestNoPlugins")
    # Intentionally do NOT set _loaded_plugins to simulate a fresh server.

    client = TestClient(_build_app(mcp))
    resp = client.get("/health")

    assert resp.status_code == 200
    body = resp.json()
    assert body.get("loaded_plugins") == []
    assert body.get("available_toolsets") == ["splunk"]
