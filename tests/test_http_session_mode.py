"""Client-discovery payload for sessionless vs session-scoped HTTP."""

from __future__ import annotations

from src.core.http_session_mode import (
    CLIENT_API_VERSION,
    HEADER_SERVER_VERSION,
    HEADER_SESSION_MODE,
    SESSION_MODE_SESSION,
    SESSION_MODE_SESSIONLESS,
    HttpSessionModeAdvertiser,
    env_flag_is_true,
)


def test_env_flag_is_true_defaults_and_parses_true_false(monkeypatch) -> None:
    monkeypatch.delenv("MCP_STATELESS_HTTP", raising=False)
    assert env_flag_is_true("MCP_STATELESS_HTTP", True) is True
    monkeypatch.setenv("MCP_STATELESS_HTTP", "false")
    assert env_flag_is_true("MCP_STATELESS_HTTP", True) is False
    monkeypatch.setenv("MCP_STATELESS_HTTP", "TRUE")
    assert env_flag_is_true("MCP_STATELESS_HTTP", True) is True


def test_advertiser_defaults_to_sessionless() -> None:
    advertiser = HttpSessionModeAdvertiser(
        version="0.6.9",
        stateless_http=True,
        json_response=True,
    )
    assert advertiser.session_mode == SESSION_MODE_SESSIONLESS
    assert advertiser.as_health_http_block() == {
        "stateless": True,
        "json_response": True,
        "session_mode": SESSION_MODE_SESSIONLESS,
        "client_api": CLIENT_API_VERSION,
    }
    headers = advertiser.as_response_headers()
    assert headers[HEADER_SERVER_VERSION] == "0.6.9"
    assert headers[HEADER_SESSION_MODE] == SESSION_MODE_SESSIONLESS


def test_advertiser_session_mode_when_stateless_disabled() -> None:
    advertiser = HttpSessionModeAdvertiser(
        version="0.6.9",
        stateless_http=False,
        json_response=False,
    )
    assert advertiser.session_mode == SESSION_MODE_SESSION
    block = advertiser.as_health_http_block()
    assert block["stateless"] is False
    assert block["session_mode"] == SESSION_MODE_SESSION
    assert advertiser.as_response_headers()[HEADER_SESSION_MODE] == SESSION_MODE_SESSION


def test_from_env_reads_stateless_flag(monkeypatch) -> None:
    monkeypatch.setenv("MCP_STATELESS_HTTP", "false")
    monkeypatch.setenv("MCP_JSON_RESPONSE", "false")
    advertiser = HttpSessionModeAdvertiser.from_env()
    assert advertiser.stateless_http is False
    assert advertiser.json_response is False
    assert advertiser.session_mode == SESSION_MODE_SESSION
    assert advertiser.version
    assert advertiser.version != "unknown"
