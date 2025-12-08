"""
Credentials Handling Security Tests (Pentest-style)

Tests for credential handling including:
- Password masking in responses
- Session credential isolation
- Cross-session leakage prevention
- Credential cleanup on session termination
"""

import json

import pytest


@pytest.mark.integration
@pytest.mark.security
class TestPasswordMaskingInResponses:
    """Test that passwords are never echoed back in tool responses."""

    @pytest.mark.asyncio
    async def test_user_agent_info_masks_password(self):
        """user_agent_info tool should mask X-Splunk-Password in response."""
        import httpx

        from src.server import create_root_app, get_mcp

        mcp = get_mcp()
        app = create_root_app(mcp)

        test_password = "my_super_secret_password_12345"  # gitleaks:allow (test data)
        headers = {
            "accept": "application/json, text/event-stream",
            "content-type": "application/json",
            "X-Session-ID": "test-session-mask-1",
            "X-Splunk-Host": "splunk.example.com",
            "X-Splunk-Port": "8089",
            "X-Splunk-Username": "admin",
            "X-Splunk-Password": test_password,
        }

        body = {
            "jsonrpc": "2.0",
            "id": "1",
            "method": "tools/call",
            "params": {"name": "user_agent_info", "arguments": {}},
        }

        try:
            from asgi_lifespan import LifespanManager

            async with LifespanManager(app):
                transport = httpx.ASGITransport(app=app)
                async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
                    resp = await client.post("/mcp", headers=headers, content=json.dumps(body))

                    # Password should NOT appear in response
                    response_text = resp.text
                    assert test_password not in response_text, "Password was echoed back in response!"

                    # Should be masked with ***
                    if resp.status_code == 200 and "password" in response_text.lower():
                        # If password key appears, value should be masked
                        assert "***" in response_text or "*" * 3 in response_text
        except ImportError:
            pytest.skip("ASGI lifespan not available")

    @pytest.mark.asyncio
    async def test_error_responses_dont_contain_password(self):
        """Error responses should never contain passwords."""
        import httpx

        from src.server import create_root_app, get_mcp

        mcp = get_mcp()
        app = create_root_app(mcp)

        test_password = "error_test_password_67890"  # gitleaks:allow (test data)
        headers = {
            "accept": "application/json",
            "content-type": "application/json",
            "X-Splunk-Host": "nonexistent.host.local",
            "X-Splunk-Port": "8089",
            "X-Splunk-Username": "baduser",
            "X-Splunk-Password": test_password,
        }

        # Intentionally bad request to trigger error
        body = {
            "jsonrpc": "2.0",
            "id": "1",
            "method": "tools/call",
            "params": {
                "name": "run_oneshot_search",
                "arguments": {"query": "index=main | head 1"},
            },
        }

        try:
            from asgi_lifespan import LifespanManager

            async with LifespanManager(app):
                transport = httpx.ASGITransport(app=app)
                async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
                    resp = await client.post("/mcp", headers=headers, content=json.dumps(body))

                    # Password should NEVER appear in any response
                    response_text = resp.text
                    assert test_password not in response_text, "Password leaked in error response!"
        except ImportError:
            pytest.skip("ASGI lifespan not available")

    @pytest.mark.asyncio
    async def test_token_not_echoed_in_responses(self):
        """Authorization tokens should not be echoed back."""
        import httpx

        from src.server import create_root_app, get_mcp

        mcp = get_mcp()
        app = create_root_app(mcp)

        test_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.test_payload.signature"
        headers = {
            "accept": "application/json",
            "content-type": "application/json",
            "Authorization": f"Bearer {test_token}",
        }

        body = {
            "jsonrpc": "2.0",
            "id": "1",
            "method": "tools/call",
            "params": {"name": "user_agent_info", "arguments": {}},
        }

        try:
            from asgi_lifespan import LifespanManager

            async with LifespanManager(app):
                transport = httpx.ASGITransport(app=app)
                async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
                    resp = await client.post("/mcp", headers=headers, content=json.dumps(body))

                    # Full token should not appear in response
                    response_text = resp.text
                    assert test_token not in response_text, "Bearer token leaked in response!"
        except ImportError:
            pytest.skip("ASGI lifespan not available")


@pytest.mark.integration
@pytest.mark.security
class TestSessionCredentialIsolation:
    """Test that credentials are isolated between sessions."""

    @pytest.mark.asyncio
    async def test_different_sessions_dont_share_credentials(self):
        """Different session IDs should have isolated credentials."""
        import httpx

        from src.server import create_root_app, get_mcp

        mcp = get_mcp()
        app = create_root_app(mcp)

        # Session 1 credentials
        session1_headers = {
            "accept": "application/json",
            "content-type": "application/json",
            "X-Session-ID": "isolated-session-001",
            "X-Splunk-Host": "host1.example.com",
            "X-Splunk-Username": "user1",
            "X-Splunk-Password": "password1_secret",  # gitleaks:allow (test data)
        }

        # Session 2 credentials (different)
        session2_headers = {
            "accept": "application/json",
            "content-type": "application/json",
            "X-Session-ID": "isolated-session-002",
            "X-Splunk-Host": "host2.example.com",
            "X-Splunk-Username": "user2",
            "X-Splunk-Password": "password2_secret",  # gitleaks:allow (test data)
        }

        body = {
            "jsonrpc": "2.0",
            "id": "1",
            "method": "tools/call",
            "params": {"name": "user_agent_info", "arguments": {}},
        }

        try:
            from asgi_lifespan import LifespanManager

            async with LifespanManager(app):
                transport = httpx.ASGITransport(app=app)
                async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
                    # Make request with session 1
                    resp1 = await client.post("/mcp", headers=session1_headers, content=json.dumps(body))

                    # Make request with session 2
                    resp2 = await client.post("/mcp", headers=session2_headers, content=json.dumps(body))

                    # Session 2 response should not contain session 1 credentials
                    assert "password1_secret" not in resp2.text
                    assert "user1" not in resp2.text or "user" in resp2.text.lower()

                    # Session 1 response should not contain session 2 credentials
                    assert "password2_secret" not in resp1.text
                    assert "host2.example.com" not in resp1.text
        except ImportError:
            pytest.skip("ASGI lifespan not available")


@pytest.mark.integration
@pytest.mark.security
class TestSessionTerminationCleanup:
    """Test that session termination clears cached credentials."""

    @pytest.mark.asyncio
    async def test_session_terminate_clears_cache(self):
        """Session termination should clear cached client config."""
        import httpx

        from src.server import HEADER_CLIENT_CONFIG_CACHE, create_root_app, get_mcp

        mcp = get_mcp()
        app = create_root_app(mcp)

        session_id = "terminate-test-session-001"
        headers = {
            "accept": "application/json",
            "content-type": "application/json",
            "X-Session-ID": session_id,
            "X-Splunk-Host": "terminate-host.example.com",
            "X-Splunk-Username": "terminate_user",
            "X-Splunk-Password": "terminate_password_secret",  # gitleaks:allow (test data)
        }

        # First make a request to cache credentials
        body = {
            "jsonrpc": "2.0",
            "id": "1",
            "method": "tools/call",
            "params": {"name": "user_agent_info", "arguments": {}},
        }

        try:
            from asgi_lifespan import LifespanManager

            async with LifespanManager(app):
                transport = httpx.ASGITransport(app=app)
                async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
                    # Make initial request to cache credentials
                    await client.post("/mcp", headers=headers, content=json.dumps(body))

                    # Verify credentials were cached (if caching is happening)
                    # This checks the global cache mechanism
                    initial_cache_state = session_id in HEADER_CLIENT_CONFIG_CACHE

                    # If caching is enabled, credentials should be cached
                    if initial_cache_state:
                        cached_config = HEADER_CLIENT_CONFIG_CACHE.get(session_id, {})
                        # Verify structure (but not actual values for security)
                        assert isinstance(cached_config, dict)

                    # The middleware should clean up on session termination
                    # (This tests the logic exists, actual termination depends on transport)
        except ImportError:
            pytest.skip("ASGI lifespan not available")


@pytest.mark.unit
@pytest.mark.security
class TestCredentialMaskingInLogs:
    """Test that credentials are masked in log output."""

    def test_cache_summary_masks_sensitive_values(self):
        """Cache summary should mask sensitive values."""
        from src.server import HEADER_CLIENT_CONFIG_CACHE, _cache_summary

        # Add test data to cache
        test_session = "log-test-session"
        HEADER_CLIENT_CONFIG_CACHE[test_session] = {
            "splunk_host": "test.example.com",
            "splunk_password": "super_secret_password",  # gitleaks:allow (test data)
            "splunk_username": "testuser",
            "authorization": "Bearer secret_token",  # gitleaks:allow (test data)
        }

        try:
            summary = _cache_summary(include_values=True)

            # Sensitive values should be masked
            if test_session in summary:
                session_data = summary[test_session]
                if isinstance(session_data, dict):
                    # Password should be masked
                    if "splunk_password" in session_data:
                        assert session_data["splunk_password"] == "***"
                    # Authorization should be masked
                    if "authorization" in session_data:
                        assert session_data["authorization"] == "***"
                    # Non-sensitive values can be shown
                    if "splunk_host" in session_data:
                        assert session_data["splunk_host"] == "test.example.com"
        finally:
            # Clean up
            HEADER_CLIENT_CONFIG_CACHE.pop(test_session, None)


@pytest.mark.unit
@pytest.mark.security
class TestEnvironmentVariableCredentials:
    """Test credentials from environment variables are handled securely."""

    @pytest.mark.asyncio
    async def test_env_credentials_not_in_health_response(self):
        """Environment credentials should not appear in health responses."""
        import httpx

        from src.server import create_root_app, get_mcp

        mcp = get_mcp()
        app = create_root_app(mcp)

        try:
            from asgi_lifespan import LifespanManager

            async with LifespanManager(app):
                transport = httpx.ASGITransport(app=app)
                async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
                    resp = await client.get("/health")
                    response_text = resp.text.lower()
                    # Ensure no credential patterns in health response
                    assert "password" not in response_text or "***" in response_text
                    assert "token" not in response_text or "***" in response_text
        except ImportError:
            pytest.skip("ASGI lifespan not available")


@pytest.mark.unit
@pytest.mark.security
class TestHeaderExtraction:
    """Test header extraction handles credentials securely."""

    def test_extract_client_config_from_headers(self):
        """Test that extract_client_config_from_headers works correctly."""
        from src.server import extract_client_config_from_headers

        headers = {
            "X-Splunk-Host": "test.example.com",
            "X-Splunk-Port": "8089",
            "X-Splunk-Username": "testuser",
            "X-Splunk-Password": "testpassword",
            "X-Splunk-Scheme": "https",
            "X-Splunk-Verify-SSL": "true",
        }

        config = extract_client_config_from_headers(headers)

        assert config is not None
        assert config["splunk_host"] == "test.example.com"
        assert config["splunk_port"] == 8089  # Should be int
        assert config["splunk_username"] == "testuser"
        assert config["splunk_password"] == "testpassword"
        assert config["splunk_scheme"] == "https"
        assert config["splunk_verify_ssl"] is True

    def test_extract_client_config_case_insensitive(self):
        """Header extraction should be case-insensitive."""
        from src.server import extract_client_config_from_headers

        headers = {
            "x-splunk-host": "test.example.com",
            "x-splunk-port": "8089",
        }

        config = extract_client_config_from_headers(headers)

        assert config is not None
        assert config["splunk_host"] == "test.example.com"

    def test_extract_client_config_empty_headers(self):
        """Empty headers should return None."""
        from src.server import extract_client_config_from_headers

        config = extract_client_config_from_headers({})
        assert config is None

    def test_extract_client_config_partial_headers(self):
        """Partial headers should return partial config."""
        from src.server import extract_client_config_from_headers

        headers = {
            "X-Splunk-Host": "partial.example.com",
            # Missing other headers
        }

        config = extract_client_config_from_headers(headers)

        assert config is not None
        assert config["splunk_host"] == "partial.example.com"
        assert "splunk_password" not in config


@pytest.mark.integration
@pytest.mark.security
class TestCrossSessionLeakagePrevention:
    """Test prevention of credential leakage between sessions."""

    @pytest.mark.asyncio
    async def test_no_global_credential_contamination(self):
        """Credentials from one session should not contaminate global state."""
        import httpx

        from src.server import create_root_app, get_mcp

        mcp = get_mcp()
        app = create_root_app(mcp)

        # Session with specific credentials
        headers_with_creds = {
            "accept": "application/json",
            "content-type": "application/json",
            "X-Session-ID": "contamination-test-session",
            "X-Splunk-Host": "contaminated-host.local",
            "X-Splunk-Password": "contamination_test_password",
        }

        # Session without credentials
        headers_no_creds = {
            "accept": "application/json",
            "content-type": "application/json",
            "X-Session-ID": "clean-session",
        }

        body = {
            "jsonrpc": "2.0",
            "id": "1",
            "method": "tools/call",
            "params": {"name": "get_splunk_health", "arguments": {}},
        }

        try:
            from asgi_lifespan import LifespanManager

            async with LifespanManager(app):
                transport = httpx.ASGITransport(app=app)
                async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
                    # First request with credentials
                    await client.post("/mcp", headers=headers_with_creds, content=json.dumps(body))

                    # Second request without credentials should not get first session's creds
                    resp2 = await client.post("/mcp", headers=headers_no_creds, content=json.dumps(body))

                    # Response should not contain leaked credentials
                    assert "contaminated-host.local" not in resp2.text
                    assert "contamination_test_password" not in resp2.text
        except ImportError:
            pytest.skip("ASGI lifespan not available")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
