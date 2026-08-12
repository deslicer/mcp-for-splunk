"""Dual-era MCP client config caching.

Modern MCP (2026-07-28) no longer exposes MCP-Session-ID after handshake.
Prefer X-Session-ID or a per-request Splunk identity hash. Legacy clients
still send MCP-Session-ID; honor it when X-Session-ID is absent.

When no stable key is available, return None so callers skip cross-request
caching.
"""

from __future__ import annotations

import hashlib


def normalize_header_token(value: str | None) -> str | None:
    """Return the first non-empty token when value is comma-duplicated."""
    if value is None:
        return None
    stripped = value.strip()
    if not stripped:
        return None
    if "," not in stripped:
        return stripped
    for token in stripped.split(","):
        candidate = token.strip()
        if candidate:
            return candidate
    return None


def extract_header(headers: dict, *names: str) -> str | None:
    """Case-insensitive header lookup for any of the given names."""
    if not headers or not names:
        return None
    lowered: dict[str, object] = {str(key).lower(): val for key, val in headers.items()}
    for name in names:
        raw = lowered.get(name.lower())
        if raw is None:
            continue
        text = str(raw).strip()
        if text:
            return text
    return None


class ClientConfigCacheKeyResolver:
    """Resolve a stable cache key from session or Splunk identity headers."""

    def resolve(self, headers: dict, mcp_session_id: str | None) -> str | None:
        """Return a cache key, or None when the caller must not cache."""
        x_session = normalize_header_token(
            extract_header(headers, "X-Session-ID", "x-session-id")
        )
        if x_session:
            return x_session

        mcp_from_headers = normalize_header_token(
            extract_header(headers, "MCP-Session-ID", "mcp-session-id")
        )
        if mcp_from_headers:
            return mcp_from_headers

        mcp_param = normalize_header_token(mcp_session_id)
        if mcp_param:
            return mcp_param

        return self._identity_hash_key(headers)

    def _identity_hash_key(self, headers: dict) -> str | None:
        """Hash host + credential fingerprint; skip cache without auth material.

        Host+username alone is unsafe: two callers sharing the same user with
        different passwords/tokens would collide and reuse cached secrets.
        """
        host = extract_header(headers, "X-Splunk-Host", "x-splunk-host")
        if not host:
            return None

        username = extract_header(headers, "X-Splunk-Username", "x-splunk-username")
        password = extract_header(
            headers,
            "X-Splunk-Password",
            "x-splunk-password",
            "X-Splunk-Password-Base64",
            "x-splunk-password-base64",
        )
        bearer = extract_header(headers, "X-Splunk-Token", "x-splunk-token")
        session = extract_header(
            headers, "X-Splunk-Session-Token", "x-splunk-session-token"
        )
        if not (password or bearer or session):
            return None

        parts = [f"host:{host.lower()}"]
        port = extract_header(headers, "X-Splunk-Port", "x-splunk-port")
        if port:
            parts.append(f"port:{port}")
        scheme = extract_header(headers, "X-Splunk-Scheme", "x-splunk-scheme")
        if scheme:
            parts.append(f"scheme:{scheme.lower()}")
        if username:
            parts.append(f"user:{username.lower()}")
        if bearer:
            parts.append(
                "bearer:" + hashlib.sha256(bearer.encode()).hexdigest()[:16]
            )
        elif session:
            parts.append(
                "session:" + hashlib.sha256(session.encode()).hexdigest()[:16]
            )
        else:
            parts.append(
                "basic:" + hashlib.sha256(password.encode()).hexdigest()[:16]
            )

        digest = hashlib.sha256("|".join(sorted(parts)).encode()).hexdigest()
        return f"cfg_{digest[:16]}"


class ClientConfigCache:
    """In-memory client config store keyed by resolved session identity."""

    def __init__(self) -> None:
        self._store: dict[str, dict] = {}

    def get(self, key: str, default: dict | None = None) -> dict | None:
        """Return the cached config for key, or default if missing."""
        return self._store.get(key, default)

    def set(self, key: str, config: dict) -> None:
        """Store config under key."""
        self._store[key] = config

    def __setitem__(self, key: str, config: dict) -> None:
        """Dict-style assignment used by older call sites and tests."""
        self.set(key, config)

    def clear(self, key: str) -> None:
        """Remove a single cache entry if present."""
        self._store.pop(key, None)

    def pop(self, key: str, default: dict | None = None) -> dict | None:
        """Remove and return a cache entry (dict-style)."""
        return self._store.pop(key, default)

    def clear_all(self) -> None:
        """Remove every cache entry."""
        self._store.clear()

    def items(self):
        """Iterate ``(key, config)`` pairs."""
        return self._store.items()

    def __contains__(self, key: object) -> bool:
        return key in self._store
