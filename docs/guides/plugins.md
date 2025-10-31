# Plugins via entry points

This guide explains how to ship extensions in a separate package and have the server auto-load them at runtime.

## How it works

- Plugins are discovered via the entry-point group `mcp_splunk.plugins`.
- Each plugin exports `setup(mcp, root_app=None)`.
- Inside `setup` you can:
  - Add MCP middleware: `mcp.add_middleware(...)`
  - Register tools/resources/prompts: `@mcp.tool`, `@mcp.resource`, `@mcp.prompt`
  - Add HTTP middleware/routes when `root_app` is provided: `root_app.add_middleware(...)`
- Control via env vars:
  - `MCP_DISABLE_PLUGINS=true` to disable loading
  - `MCP_PLUGIN_GROUP` to override the group name

## Example plugin skeleton

```toml
# pyproject.toml
[project]
name = "mcp-splunk-auth-plugin"
version = "0.1.0"
requires-python = ">=3.10"
dependencies = ["mcp-server-for-splunk>=0.2.1", "starlette>=0.37", "fastmcp>=2.11.3"]

[project.entry-points."mcp_splunk.plugins"]
auth = "auth_plugin.plugins:setup"
```

```python
# src/auth_plugin/plugins.py
import os
import secrets
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
from fastmcp.server.middleware import Middleware


def _authorized(headers: dict) -> bool:
    expected = os.getenv("PLUGIN_API_KEY") or ""
    provided = headers.get("x-api-key") or ""
    # Use constant-time comparison to avoid timing attacks
    return bool(expected) and secrets.compare_digest(provided, expected)

class AuthHTTPMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        if not _authorized(dict(request.headers)):
            return JSONResponse({"detail": "Unauthorized"}, status_code=401)
        return await call_next(request)

class AuthMCPMiddleware(Middleware):
    async def on_request(self, context, call_next):
        headers = getattr(context, "http_headers", None) or {}
        if not _authorized(headers):
            return {"status": "error", "error": "Unauthorized"}
        return await call_next(context)

def setup(mcp, root_app=None):
    mcp.add_middleware(AuthMCPMiddleware())
    if root_app is not None:
        root_app.add_middleware(AuthHTTPMiddleware)
```

> Security: Use `secrets.compare_digest` for API key checks to prevent timing attacks.

## Local run

```bash
pip install -e /path/to/mcp-for-splunk
pip install -e .
export PLUGIN_API_KEY=dev-key
mcp-server
```

- Without `x-api-key: dev-key`, requests are rejected.
- Disable plugins in CI: `MCP_DISABLE_PLUGINS=true`.

## Versioning

- Use SemVer.
- In the plugin, depend on a compatible OSS range (e.g., `>=0.3,<0.4`).

## Docker

```dockerfile
FROM yourorg/mcp-splunk:oss
COPY dist/mcp_splunk_auth_plugin-0.1.0-py3-none-any.whl /tmp/
RUN pip install /tmp/mcp_splunk_auth_plugin-0.1.0-py3-none-any.whl
ENV PLUGIN_API_KEY=...  # set via secrets
```
