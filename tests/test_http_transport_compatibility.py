"""Exercise real MCP HTTP messages through the production app factory."""

import json

import pytest
from fastmcp import Context, FastMCP
from mcp_types import (
    CLIENT_CAPABILITIES_META_KEY,
    CLIENT_INFO_META_KEY,
    PROTOCOL_VERSION_META_KEY,
)
from starlette.testclient import TestClient

from mcp_server_for_splunk import server
from mcp_server_for_splunk.core.http_session_mode import HttpSessionModeAdvertiser


@pytest.mark.parametrize("stateless", [True, False], ids=["sessionless", "session"])
@pytest.mark.parametrize("json_response", [True, False], ids=["json", "sse"])
@pytest.mark.parametrize("protocol", ["2025-11-25", "2026-07-28"])
def test_http_discovery_and_tool_calls(monkeypatch, stateless, json_response, protocol):
    """Legacy sessions and modern discovery must both survive framework upgrades."""
    probe = FastMCP("HTTP compatibility probe")

    @probe.tool(tags={"splunk"})
    async def echo(message: str, ctx: Context) -> str:
        await ctx.report_progress(progress=1, total=1)
        return message

    advertiser = HttpSessionModeAdvertiser(
        version="test", stateless_http=stateless, json_response=json_response
    )
    monkeypatch.setattr(server, "STATELESS_HTTP", stateless)
    monkeypatch.setattr(server, "JSON_RESPONSE", json_response)
    monkeypatch.setattr(server, "HTTP_SESSION_MODE", advertiser)
    monkeypatch.setattr(server, "HOST_ORIGIN_PROTECTION", True)
    monkeypatch.setattr(server, "_otel_enabled", False)
    monkeypatch.setattr(server, "_sentry_enabled", False)
    monkeypatch.setattr(server, "load_plugins", lambda *args: None)
    headers = {
        "Accept": "application/json, text/event-stream",
        "Mcp-Protocol-Version": protocol,
        "X-MCP-Toolsets": "splunk",
    }
    modern = protocol == "2026-07-28"
    client_info = {"name": "http-compatibility-test", "version": "1"}

    with TestClient(server.create_root_app(probe), base_url="http://localhost") as client:

        def request(method, params, request_id):
            if modern:
                params = {
                    **params,
                    "_meta": {
                        **params.get("_meta", {}),
                        PROTOCOL_VERSION_META_KEY: protocol,
                        CLIENT_CAPABILITIES_META_KEY: {},
                        CLIENT_INFO_META_KEY: client_info,
                    },
                }
            request_headers = {**headers, "Mcp-Method": method}
            if modern and "name" in params:
                request_headers["Mcp-Name"] = params["name"]
            response = client.post(
                "/mcp",
                headers=request_headers,
                json={"jsonrpc": "2.0", "id": request_id, "method": method, "params": params},
            )
            assert response.status_code == 200, response.text
            assert response.headers["X-MCP-Session-Mode"] == advertiser.session_mode
            content_type = response.headers["content-type"].split(";")[0]
            if json_response:
                assert content_type == "application/json"
            elif not modern or method == "tools/call":
                # Modern HTTP defers SSE until the tool emits progress. Its
                # immediate discovery/list responses may still use JSON.
                assert content_type == "text/event-stream"
            else:
                assert content_type in {"application/json", "text/event-stream"}
            if response.headers["content-type"].startswith("application/json"):
                message = response.json()
            else:
                messages = [
                    json.loads(line[6:])
                    for line in response.text.splitlines()
                    if line.startswith("data: ") and line[6:].strip()
                ]
                message = next(item for item in messages if item.get("id") == request_id)
            assert message["id"] == request_id
            assert "error" not in message, message
            return response, message["result"]

        if modern:
            response, discovery = request("server/discover", {}, 1)
            assert "tools" in discovery["capabilities"]
        else:
            response, initialized = request(
                "initialize",
                {"protocolVersion": protocol, "capabilities": {}, "clientInfo": client_info},
                1,
            )
            assert initialized["protocolVersion"] == protocol

        session_id = response.headers.get("mcp-session-id")
        assert bool(session_id) == (not stateless and not modern)
        if session_id:
            headers["Mcp-Session-Id"] = session_id
        if not modern:
            notification = client.post(
                "/mcp",
                headers=headers,
                json={"jsonrpc": "2.0", "method": "notifications/initialized"},
            )
            assert notification.status_code == 202

        _, listing = request("tools/list", {}, 2)
        assert [tool["name"] for tool in listing["tools"]] == ["echo"]
        for request_id, value in [(3, "first call"), (4, "repeated call")]:
            _, result = request(
                "tools/call",
                {
                    "name": "echo",
                    "arguments": {"message": value},
                    "_meta": {"progressToken": request_id},
                },
                request_id,
            )
            assert not result.get("isError", False)
            assert result["content"] == [{"type": "text", "text": value}]

        if session_id:
            headers.pop("Mcp-Session-Id")
            missing_session = client.post(
                "/mcp",
                headers=headers,
                json={"jsonrpc": "2.0", "id": 5, "method": "tools/list", "params": {}},
            )
            assert missing_session.status_code == 400
