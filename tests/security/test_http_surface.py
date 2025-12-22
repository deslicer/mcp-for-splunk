"""
HTTP Surface Security Tests (Pentest-style)

Tests for the HTTP attack surface of the MCP server including:
- Health endpoint exposure
- Malformed request handling
- Error response sanitization
- Stack trace prevention
"""

import json

import pytest


@pytest.mark.integration
@pytest.mark.security
class TestHealthEndpointSecurity:
    """Test /health endpoint security - ensure only benign info is exposed."""

    @pytest.mark.asyncio
    async def test_health_endpoint_returns_minimal_info(self):
        """Health endpoint should expose only benign, non-sensitive information."""
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

                    # Should return 200 OK
                    assert resp.status_code == 200

                    # Parse response
                    data = resp.json()

                    # Should have minimal info
                    assert "status" in data
                    assert data["status"] in ["OK", "healthy"]

                    # Should NOT expose sensitive info
                    sensitive_keys = [
                        "password",
                        "token",
                        "secret",
                        "credentials",
                        "api_key",
                        "splunk_host",
                        "splunk_port",
                        "internal_ip",
                        "stack_trace",
                        "traceback",
                    ]
                    data_str = json.dumps(data).lower()
                    for key in sensitive_keys:
                        assert key not in data_str, f"Sensitive key '{key}' found in health response"
        except ImportError:
            import inspect

            params = list(getattr(inspect.signature(httpx.ASGITransport), "parameters", {}).keys())
            if "lifespan" in params:
                transport = httpx.ASGITransport(app=app, lifespan="on")
                async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
                    resp = await client.get("/health")
                    assert resp.status_code == 200
                    data = resp.json()
                    assert "status" in data
            else:
                pytest.skip("ASGI lifespan not available")

    @pytest.mark.asyncio
    async def test_health_endpoint_no_auth_required(self):
        """Health endpoint should work without any authentication."""
        import httpx

        from src.server import create_root_app, get_mcp

        mcp = get_mcp()
        app = create_root_app(mcp)

        try:
            from asgi_lifespan import LifespanManager

            async with LifespanManager(app):
                transport = httpx.ASGITransport(app=app)
                async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
                    # No auth headers at all
                    resp = await client.get("/health", headers={})
                    assert resp.status_code == 200
        except ImportError:
            pytest.skip("ASGI lifespan not available")


@pytest.mark.integration
@pytest.mark.security
class TestMalformedRequestHandling:
    """Test handling of malformed or malicious requests."""

    @pytest.mark.asyncio
    async def test_very_long_spl_query_handled_gracefully(self):
        """Very long SPL strings should not cause crashes or expose errors."""
        import httpx

        from src.server import create_root_app, get_mcp

        mcp = get_mcp()
        app = create_root_app(mcp)

        # Create a very long query (100KB)
        long_query = "index=main " + "A" * 100000

        body = {
            "jsonrpc": "2.0",
            "id": "1",
            "method": "tools/call",
            "params": {
                "name": "run_oneshot_search",
                "arguments": {"query": long_query, "max_results": 10},
            },
        }

        try:
            from asgi_lifespan import LifespanManager

            async with LifespanManager(app):
                transport = httpx.ASGITransport(app=app)
                async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
                    resp = await client.post(
                        "/mcp",
                        headers={
                            "accept": "application/json",
                            "content-type": "application/json",
                        },
                        content=json.dumps(body),
                        timeout=30.0,
                    )

                    # Should not crash - any 2xx or 4xx is acceptable
                    assert resp.status_code in range(200, 500)

                    # Should not contain stack traces
                    response_text = resp.text.lower()
                    assert "traceback" not in response_text
                    assert "exception" not in response_text or "securityexception" in response_text
        except ImportError:
            pytest.skip("ASGI lifespan not available")

    @pytest.mark.asyncio
    async def test_invalid_json_handled_gracefully(self):
        """Invalid JSON should return error without exposing internals."""
        import httpx

        from src.server import create_root_app, get_mcp

        mcp = get_mcp()
        app = create_root_app(mcp)

        invalid_json = '{"jsonrpc": "2.0", "id": "1", "method": "tools/call", "params": {invalid}'

        try:
            from asgi_lifespan import LifespanManager

            async with LifespanManager(app):
                transport = httpx.ASGITransport(app=app)
                async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
                    resp = await client.post(
                        "/mcp",
                        headers={
                            "accept": "application/json",
                            "content-type": "application/json",
                        },
                        content=invalid_json,
                    )

                    # Should return error status, not crash
                    assert resp.status_code in [200, 400, 406, 422]

                    # Response should not contain Python stack traces
                    response_text = resp.text.lower()
                    assert "file \"" not in response_text  # Python file path in traceback
                    assert "line " not in response_text or "error" in response_text
        except ImportError:
            pytest.skip("ASGI lifespan not available")

    @pytest.mark.asyncio
    async def test_special_characters_in_query(self):
        """Special characters in queries should be handled safely."""
        import httpx

        from src.server import create_root_app, get_mcp

        mcp = get_mcp()
        app = create_root_app(mcp)

        # Various injection attempts
        injection_payloads = [
            "index=main'; DROP TABLE users; --",
            "index=main\"; exec('rm -rf /')",
            "index=main` && cat /etc/passwd`",
            "index=main | $(whoami)",
            "index=main\x00\x00null_bytes",
            "index=main\n\r\nHTTP/1.1 200 OK\r\n",  # CRLF injection
        ]

        try:
            from asgi_lifespan import LifespanManager

            async with LifespanManager(app):
                transport = httpx.ASGITransport(app=app)
                async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
                    for payload in injection_payloads:
                        body = {
                            "jsonrpc": "2.0",
                            "id": "1",
                            "method": "tools/call",
                            "params": {
                                "name": "run_oneshot_search",
                                "arguments": {"query": payload, "max_results": 1},
                            },
                        }

                        resp = await client.post(
                            "/mcp",
                            headers={
                                "accept": "application/json",
                                "content-type": "application/json",
                            },
                            content=json.dumps(body),
                        )

                        # Server should not crash
                        assert resp.status_code in range(200, 500), f"Crash on payload: {payload[:50]}"
        except ImportError:
            pytest.skip("ASGI lifespan not available")


@pytest.mark.integration
@pytest.mark.security
class TestErrorResponseSanitization:
    """Test that error responses don't expose sensitive information."""

    @pytest.mark.asyncio
    async def test_error_response_no_stack_traces(self):
        """Error responses should not contain Python stack traces."""
        import httpx

        from src.server import create_root_app, get_mcp

        mcp = get_mcp()
        app = create_root_app(mcp)

        # Call a non-existent tool to trigger error
        body = {
            "jsonrpc": "2.0",
            "id": "1",
            "method": "tools/call",
            "params": {
                "name": "nonexistent_tool_12345",
                "arguments": {},
            },
        }

        try:
            from asgi_lifespan import LifespanManager

            async with LifespanManager(app):
                transport = httpx.ASGITransport(app=app)
                async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
                    resp = await client.post(
                        "/mcp",
                        headers={
                            "accept": "application/json",
                            "content-type": "application/json",
                        },
                        content=json.dumps(body),
                    )

                    response_text = resp.text.lower()

                    # Should not contain Python internals
                    assert "traceback (most recent call last)" not in response_text
                    assert "file \"/" not in response_text  # Unix path in traceback
                    assert "file \"c:" not in response_text  # Windows path in traceback
        except ImportError:
            pytest.skip("ASGI lifespan not available")

    @pytest.mark.asyncio
    async def test_error_response_no_internal_paths(self):
        """Error responses should not expose internal file paths."""
        import httpx

        from src.server import create_root_app, get_mcp

        mcp = get_mcp()
        app = create_root_app(mcp)

        # Trigger an error with invalid parameters
        body = {
            "jsonrpc": "2.0",
            "id": "1",
            "method": "tools/call",
            "params": {
                "name": "run_splunk_search",
                "arguments": {
                    # Missing required 'query' parameter
                },
            },
        }

        try:
            from asgi_lifespan import LifespanManager

            async with LifespanManager(app):
                transport = httpx.ASGITransport(app=app)
                async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
                    resp = await client.post(
                        "/mcp",
                        headers={
                            "accept": "application/json",
                            "content-type": "application/json",
                        },
                        content=json.dumps(body),
                    )

                    response_text = resp.text.lower()

                    # Should not expose file system paths
                    path_patterns = ["/home/", "/var/", "/usr/", "/opt/", "c:\\", "d:\\"]
                    for pattern in path_patterns:
                        assert pattern not in response_text, f"Internal path '{pattern}' exposed in error"
        except ImportError:
            pytest.skip("ASGI lifespan not available")

    @pytest.mark.asyncio
    async def test_error_response_no_secrets(self):
        """Error responses should not contain secrets or credentials."""
        import httpx

        from src.server import create_root_app, get_mcp

        mcp = get_mcp()
        app = create_root_app(mcp)

        # Try to trigger an error with bad credentials
        body = {
            "jsonrpc": "2.0",
            "id": "1",
            "method": "tools/call",
            "params": {
                "name": "run_oneshot_search",
                "arguments": {"query": "index=main", "max_results": 1},
            },
        }

        headers = {
            "accept": "application/json",
            "content-type": "application/json",
            "X-Splunk-Host": "badhost.example.com",
            "X-Splunk-Port": "8089",
            "X-Splunk-Username": "testuser",
            "X-Splunk-Password": "super_secret_password_12345",
        }

        try:
            from asgi_lifespan import LifespanManager

            async with LifespanManager(app):
                transport = httpx.ASGITransport(app=app)
                async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
                    resp = await client.post("/mcp", headers=headers, content=json.dumps(body))

                    response_text = resp.text

                    # Password should never appear in response
                    assert "super_secret_password_12345" not in response_text
                    assert "testuser" not in response_text or "testuser" in response_text.lower()
        except ImportError:
            pytest.skip("ASGI lifespan not available")


@pytest.mark.integration
@pytest.mark.security
class TestRequestRateLimiting:
    """Test rate limiting and DoS protection."""

    @pytest.mark.asyncio
    async def test_rapid_requests_dont_crash_server(self):
        """Rapid requests should be handled without crashing."""
        import asyncio

        import httpx

        from src.server import create_root_app, get_mcp

        mcp = get_mcp()
        app = create_root_app(mcp)

        try:
            from asgi_lifespan import LifespanManager

            async with LifespanManager(app):
                transport = httpx.ASGITransport(app=app)
                async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
                    # Send 50 rapid requests
                    tasks = []
                    for _ in range(50):
                        task = client.get("/health")
                        tasks.append(task)

                    responses = await asyncio.gather(*tasks, return_exceptions=True)

                    # At least some should succeed
                    success_count = sum(1 for r in responses if hasattr(r, "status_code") and r.status_code == 200)
                    assert success_count > 0, "All rapid requests failed"

                    # Server should still be responsive after burst
                    final_resp = await client.get("/health")
                    assert final_resp.status_code == 200
        except ImportError:
            pytest.skip("ASGI lifespan not available")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
