"""Unit tests for dual-era client config cache key resolution."""

from __future__ import annotations

import hashlib

from src.core.client_config_cache import (
    ClientConfigCache,
    ClientConfigCacheKeyResolver,
    extract_header,
    normalize_header_token,
)


def test_normalize_header_token_takes_first_comma_token() -> None:
    assert normalize_header_token("abc, abc") == "abc"
    assert normalize_header_token("  uuid-1 , uuid-1 ") == "uuid-1"
    assert normalize_header_token("") is None
    assert normalize_header_token(None) is None
    assert normalize_header_token("   ") is None


def test_extract_header_is_case_insensitive() -> None:
    headers = {"x-session-id": "sess-1", "X-Splunk-Host": "so1"}
    assert extract_header(headers, "X-Session-ID") == "sess-1"
    assert extract_header(headers, "x-splunk-host") == "so1"
    assert extract_header(headers, "missing") is None


def test_resolve_prefers_x_session_id_over_mcp_session_id() -> None:
    resolver = ClientConfigCacheKeyResolver()
    headers = {
        "X-Session-ID": "x-sess",
        "MCP-Session-ID": "mcp-sess",
        "X-Splunk-Host": "so1",
        "X-Splunk-Username": "admin",
    }
    assert resolver.resolve(headers, mcp_session_id="param-sess") == "x-sess"


def test_resolve_uses_mcp_session_id_header_when_no_x_session() -> None:
    resolver = ClientConfigCacheKeyResolver()
    headers = {"mcp-session-id": "legacy-sess, legacy-sess"}
    assert resolver.resolve(headers, mcp_session_id=None) == "legacy-sess"


def test_resolve_uses_mcp_session_id_param_when_headers_lack_session() -> None:
    resolver = ClientConfigCacheKeyResolver()
    headers = {"X-Splunk-Host": "so1"}
    assert resolver.resolve(headers, mcp_session_id="handshake-sess") == "handshake-sess"


def test_resolve_falls_back_to_identity_hash() -> None:
    resolver = ClientConfigCacheKeyResolver()
    headers = {
        "X-Splunk-Host": "so1",
        "X-Splunk-Username": "admin",
    }
    expected = "cfg_" + hashlib.sha256(b"so1:admin").hexdigest()[:16]
    assert resolver.resolve(headers, mcp_session_id=None) == expected


def test_resolve_returns_none_without_stable_identity() -> None:
    resolver = ClientConfigCacheKeyResolver()
    assert resolver.resolve({}, mcp_session_id=None) is None
    assert resolver.resolve({"X-Splunk-Host": "so1"}, mcp_session_id=None) is None


def test_client_config_cache_get_set_clear() -> None:
    cache = ClientConfigCache()
    cache.set("sess-a", {"splunk_host": "so1"})
    assert cache.get("sess-a") == {"splunk_host": "so1"}
    cache.clear("sess-a")
    assert cache.get("sess-a") is None


def test_client_config_cache_clear_all() -> None:
    cache = ClientConfigCache()
    cache.set("a", {"x": 1})
    cache.set("b", {"y": 2})
    cache.clear_all()
    assert cache.get("a") is None
    assert cache.get("b") is None
