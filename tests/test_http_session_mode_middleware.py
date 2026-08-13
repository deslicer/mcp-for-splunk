"""Response headers advertise session mode on every HTTP response."""

from __future__ import annotations

from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.routing import Route
from starlette.testclient import TestClient

from src.core.http_session_mode import HttpSessionModeAdvertiser
from src.core.http_session_mode_middleware import HttpSessionModeHeaderMiddleware


async def _ok(_request):
    return JSONResponse({"ok": True})


def test_middleware_sets_discovery_headers_on_json_response():
    advertiser = HttpSessionModeAdvertiser(
        version="0.6.9-test",
        stateless_http=True,
        json_response=True,
    )
    app = Starlette(routes=[Route("/mcp", _ok, methods=["POST"])])
    app.add_middleware(HttpSessionModeHeaderMiddleware, advertiser=advertiser)
    client = TestClient(app)

    resp = client.post("/mcp", json={})

    assert resp.status_code == 200
    assert resp.headers["X-MCP-Server-Version"] == "0.6.9-test"
    assert resp.headers["X-MCP-Session-Mode"] == "sessionless"
