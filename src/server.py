"""
Modular MCP Server for Splunk

This is the new modular version that uses the core framework for
automatic discovery and loading of tools, resources, and prompts.
"""

import argparse
import asyncio

# Add import for Starlette responses at the top
import logging
import os
import sys
import time
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from contextvars import ContextVar

from fastmcp import Context, FastMCP
from fastmcp.server.dependencies import get_context, get_http_headers, get_http_request
from fastmcp.server.middleware import Middleware, MiddlewareContext
from starlette.applications import Starlette
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from src.core.base import SplunkContext
from src.core.loader import ComponentLoader
from src.core.shared_context import http_headers_context
from src.routes import setup_health_routes

# Add the project root to the path for imports
project_root = os.path.dirname(os.path.dirname(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Create logs directory if it doesn't exist
log_dir = os.path.join(os.path.dirname(__file__), "logs")
os.makedirs(log_dir, exist_ok=True)

# Enhanced logging configuration (configurable via MCP_LOG_LEVEL)
# Resolve log level from environment with safe defaults
LOG_LEVEL_NAME = os.getenv("MCP_LOG_LEVEL", "INFO").upper()
LOG_LEVEL = getattr(logging, LOG_LEVEL_NAME, logging.INFO)

logging.basicConfig(
    level=LOG_LEVEL,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(os.path.join(log_dir, "mcp_splunk_server.log")),
        logging.StreamHandler(),
    ],
)

# Map Python logging level to uvicorn's expected string level
_UVICORN_LEVEL_MAP = {
    logging.DEBUG: "debug",
    logging.INFO: "info",
    logging.WARNING: "warning",
    logging.ERROR: "error",
    logging.CRITICAL: "critical",
}
UVICORN_LOG_LEVEL = _UVICORN_LEVEL_MAP.get(LOG_LEVEL, "info")
logger = logging.getLogger(__name__)

# Global cache to persist client config per session across Streamable HTTP requests
# Keyed by a caller-provided "X-Session-ID" header value
HEADER_CLIENT_CONFIG_CACHE: dict[str, dict] = {}

# Session correlation for logs
current_session_id: ContextVar[str] = ContextVar("current_session_id", default="-")

# Ensure every LogRecord has a 'session' attribute to avoid formatting errors
_old_record_factory = logging.getLogRecordFactory()


def _record_factory(*args, **kwargs):
    record = _old_record_factory(*args, **kwargs)
    if not hasattr(record, "session"):
        # Prefer session id from MCP ctx state if available
        try:
            ctx = get_context()
            try:
                sess = ctx.get_state("session_id")  # type: ignore[attr-defined]
            except Exception:
                sess = None
            if isinstance(sess, str) and sess:
                record.session = sess
            else:
                record.session = current_session_id.get()
        except Exception:
            # Fallback to ContextVar or '-'
            try:
                record.session = current_session_id.get()
            except Exception:
                record.session = "-"
    return record


logging.setLogRecordFactory(_record_factory)


def _cache_summary(include_values: bool = True) -> dict:
    """Return a sanitized summary of the header client-config cache.

    When include_values=True, includes key/value pairs with sensitive values masked.
    Sensitive keys: '*password*', 'authorization', 'token'.
    """
    try:
        summary: dict[str, dict | list[str]] = {}
        for session_key, cfg in HEADER_CLIENT_CONFIG_CACHE.items():
            if not include_values:
                summary[session_key] = list(cfg.keys())
                continue

            sanitized: dict[str, object] = {}
            for k, v in cfg.items():
                k_lower = k.lower()
                if any(s in k_lower for s in ["password", "authorization", "token"]):
                    sanitized[k] = "***"
                else:
                    sanitized[k] = v
            summary[session_key] = sanitized
        return summary
    except Exception:
        return {"error": "unavailable"}


# ASGI Middleware to capture HTTP headers
class HeaderCaptureMiddleware(BaseHTTPMiddleware):
    """
    ASGI middleware that captures HTTP headers and stores them in a context variable
    so they can be accessed by MCP middleware downstream.
    """

    async def dispatch(self, request: Request, call_next):
        """Capture headers and store in context variable before processing request."""
        token = None
        try:
            # Convert headers to dict (case-insensitive)
            headers = dict(request.headers)

            # Set session correlation id as early as possible for all downstream logs
            session_key = headers.get("X-Session-ID") or headers.get("x-session-id") or "-"
            token = current_session_id.set(session_key)

            logger.info("HeaderCaptureMiddleware: Processing request to %s", request.url.path)

            # Store headers in context variable
            http_headers_context.set(headers)
            logger.debug(f"Captured headers: {list(headers.keys())}")

            # Log header extraction for debugging
            splunk_headers = {k: v for k, v in headers.items() if k.lower().startswith("x-splunk-")}
            if splunk_headers:
                logger.debug("Captured Splunk headers: %s", list(splunk_headers.keys()))
            else:
                logger.debug("No Splunk headers found. Available headers: %s", list(headers.keys()))

            # Extract and attach client config to the Starlette request state for tools to use
            try:
                client_config = extract_client_config_from_headers(headers)
                if client_config:
                    # Attach to request.state so BaseTool can retrieve it
                    request.state.client_config = client_config
                    logger.debug(
                        "HeaderCaptureMiddleware: attached client_config to request.state (keys=%s)",
                        list(client_config.keys()),
                    )

                    # Persist per-session for subsequent Streamable HTTP requests
                    session_key = headers.get("X-Session-ID") or headers.get("x-session-id")
                    # Always cache under provided session id if available
                    if session_key:
                        HEADER_CLIENT_CONFIG_CACHE[session_key] = client_config
                        logger.debug(
                            "HeaderCaptureMiddleware: cached client_config for session %s (keys=%s)",
                            session_key,
                            list(client_config.keys()),
                        )
            except Exception as e:
                logger.warning(f"Failed to attach client_config to request.state: {e}")

        except Exception as e:
            logger.error(f"Error capturing HTTP headers: {e}")
            # Set empty dict as fallback
            http_headers_context.set({})

        # Continue processing the request
        try:
            response = await call_next(request)
            return response
        finally:
            # Reset session correlation id for this request
            if token is not None:
                try:
                    current_session_id.reset(token)
                except Exception:
                    pass


def extract_client_config_from_headers(headers: dict) -> dict | None:
    """
    Extract Splunk configuration from HTTP headers.

    Headers should be prefixed with 'X-Splunk-' for security.

    Args:
        headers: HTTP request headers

    Returns:
        Dict with Splunk configuration or None
    """
    client_config = {}

    # Mapping of header names to config keys
    header_mapping = {
        "X-Splunk-Host": "splunk_host",
        "X-Splunk-Port": "splunk_port",
        "X-Splunk-Username": "splunk_username",
        "X-Splunk-Password": "splunk_password",
        "X-Splunk-Scheme": "splunk_scheme",
        "X-Splunk-Verify-SSL": "splunk_verify_ssl",
    }

    for header_name, config_key in header_mapping.items():
        header_value = headers.get(header_name) or headers.get(header_name.lower())
        if header_value:
            # Handle type conversions
            if config_key == "splunk_port":
                client_config[config_key] = int(header_value)
            elif config_key == "splunk_verify_ssl":
                client_config[config_key] = header_value.lower() == "true"
            else:
                client_config[config_key] = header_value

    return client_config if client_config else None


def extract_client_config_from_env() -> dict | None:
    """
    Extract Splunk configuration from MCP client environment variables.

    These are separate from server environment variables and allow
    MCP clients to provide their own Splunk connection settings.

    Returns:
        Dict with Splunk configuration from client environment
    """
    client_config = {}

    # Check for MCP client-specific environment variables
    env_mapping = {
        "MCP_SPLUNK_HOST": "splunk_host",
        "MCP_SPLUNK_PORT": "splunk_port",
        "MCP_SPLUNK_USERNAME": "splunk_username",
        "MCP_SPLUNK_PASSWORD": "splunk_password",
        "MCP_SPLUNK_SCHEME": "splunk_scheme",
        "MCP_SPLUNK_VERIFY_SSL": "splunk_verify_ssl",
    }

    for env_var, config_key in env_mapping.items():
        env_value = os.getenv(env_var)
        if env_value:
            # Handle type conversions
            if config_key == "splunk_port":
                client_config[config_key] = int(env_value)
            elif config_key == "splunk_verify_ssl":
                client_config[config_key] = env_value.lower() == "true"
            else:
                client_config[config_key] = env_value

    return client_config if client_config else None


@asynccontextmanager
async def splunk_lifespan(server: FastMCP) -> AsyncIterator[SplunkContext]:
    """Manage Splunk connection lifecycle with client configuration support"""
    logger.info("Initializing Splunk connection with client configuration support...")
    service = None
    is_connected = False
    client_config = None

    try:
        # Check for MCP client configuration from environment (for stdio transport)
        client_config = extract_client_config_from_env()

        if client_config:
            logger.info("Found MCP client configuration in environment variables")
            logger.info(f"Client config keys: {list(client_config.keys())}")

        # Import the safe version that doesn't raise exceptions
        from src.client.splunk_client import get_splunk_service_safe

        service = get_splunk_service_safe(client_config)

        if service:
            config_source = "client environment" if client_config else "server environment"
            logger.info(f"Splunk connection established successfully using {config_source}")
            is_connected = True
        else:
            logger.warning("Splunk connection failed - running in degraded mode")
            logger.warning("Some tools will not be available until Splunk connection is restored")

        # Create the context with client configuration
        context = SplunkContext(
            service=service, is_connected=is_connected, client_config=client_config
        )

        # Load all components using the modular framework
        logger.info("Loading MCP components...")
        component_loader = ComponentLoader(server)
        results = component_loader.load_all_components()

        logger.info(f"Successfully loaded components: {results}")

        # Store component loading results on the MCP server instance globally for health endpoints to access
        # This ensures health endpoints can access the data even when called outside the lifespan context
        server._component_loading_results = results
        server._splunk_context = context

        yield context

    except Exception as e:
        logger.error(f"Unexpected error during server initialization: {str(e)}")
        logger.exception("Full traceback:")
        # Still yield a context with no service to allow MCP server to start
        yield SplunkContext(service=None, is_connected=False, client_config=client_config)
    finally:
        logger.info("Shutting down Splunk connection")


async def ensure_components_loaded(server: FastMCP) -> None:
    """Ensure components are loaded at server startup, not just during MCP lifespan"""
    logger.info("Ensuring components are loaded at server startup...")

    try:
        # Check if components are already loaded
        if hasattr(server, "_component_loading_results") and server._component_loading_results:
            logger.info("Components already loaded, skipping startup loading")
            return

        # Initialize Splunk context for component loading
        client_config = extract_client_config_from_env()

        # Import the safe version that doesn't raise exceptions
        from src.client.splunk_client import get_splunk_service_safe

        service = get_splunk_service_safe(client_config)
        is_connected = service is not None

        if service:
            config_source = "client environment" if client_config else "server environment"
            logger.info(f"Splunk connection established for startup loading using {config_source}")
        else:
            logger.warning("Splunk connection failed during startup - components will still load")

        # Create context for component loading
        context = SplunkContext(
            service=service, is_connected=is_connected, client_config=client_config
        )

        # Load components at startup
        logger.info("Loading MCP components at server startup...")
        component_loader = ComponentLoader(server)
        results = component_loader.load_all_components()

        # Store results for health endpoints
        server._component_loading_results = results
        server._splunk_context = context

        logger.info(f"Successfully loaded components at startup: {results}")

    except Exception as e:
        logger.error(f"Error during startup component loading: {str(e)}")
        logger.exception("Full traceback:")
        # Set default values so health endpoints don't crash
        server._component_loading_results = {"tools": 0, "resources": 0, "prompts": 0}
        server._splunk_context = SplunkContext(service=None, is_connected=False, client_config=None)


# Initialize FastMCP server with lifespan context
mcp = FastMCP(name="MCP Server for Splunk", lifespan=splunk_lifespan)

# Import and setup health routes
setup_health_routes(mcp)


# Middleware to extract client configuration from HTTP headers
class ClientConfigMiddleware(Middleware):
    """
    Middleware to extract client configuration from HTTP headers for tools to use.

    This middleware allows MCP clients to provide Splunk configuration
    via HTTP headers instead of environment variables.
    """

    def __init__(self):
        super().__init__()
        self.client_config_cache = {}
        logger.info("ClientConfigMiddleware initialized")

    async def on_request(self, context: MiddlewareContext, call_next):
        """Handle all MCP requests and extract client configuration from headers if available."""

        # Log context information for debugging
        session_id_val = getattr(context, "session_id", None)
        logger.info("ClientConfigMiddleware: processing %s (session_id=%s)", context.method, session_id_val)
        # Set session correlation id for downstream logs (including splunklib binding)
        # Prefer explicit session id; otherwise try X-Session-ID header; else '-'
        headers = {}
        try:
            headers = http_headers_context.get({})
        except Exception:
            headers = {}
        derived_session = session_id_val or headers.get("x-session-id") or "-"
        token = current_session_id.set(derived_session)

        client_config = None

        # Try to access HTTP headers from context variable (set by ASGI middleware)
        try:
            headers = http_headers_context.get({})

            # Derive a stable per-session cache key
            session_key = getattr(context, "session_id", None) or headers.get("x-session-id")

            if headers:
                logger.info(
                    "ClientConfigMiddleware: found HTTP headers (keys=%s)",
                    list(headers.keys()),
                )

                # Extract client config from headers
                client_config = extract_client_config_from_headers(headers)

                if client_config:
                    logger.info(
                        "ClientConfigMiddleware: extracted client_config from headers (keys=%s, session_key=%s)",
                        list(client_config.keys()),
                        session_key,
                    )

                    # Cache the config for this session (avoid cross-session leakage)
                    if session_key:
                        self.client_config_cache[session_key] = client_config
                else:
                    logger.debug("No Splunk headers found in HTTP request")
            else:
                logger.debug("No HTTP headers found in context variable")

            # If we didn't extract config from headers, check per-session cache only (no global fallback)
            if not client_config and session_key:
                client_config = self.client_config_cache.get(session_key) or HEADER_CLIENT_CONFIG_CACHE.get(
                    session_key
                )
                if client_config:
                    logger.info("ClientConfigMiddleware: using cached client_config for session %s", session_key)

            # Write per-request config and session into context state for tools
            try:
                if client_config and hasattr(context, "fastmcp_context") and context.fastmcp_context:
                    effective_session = session_key or derived_session
                    context.fastmcp_context.set_state("client_config", client_config)
                    if effective_session:
                        context.fastmcp_context.set_state("session_id", effective_session)
                    logger.info(
                        "ClientConfigMiddleware: wrote client_config to context state (keys=%s, session=%s)",
                        list(client_config.keys()),
                        effective_session,
                    )
            except Exception as e:
                logger.warning(f"ClientConfigMiddleware: failed to set context state: {e}")

        except Exception as e:
            logger.error(f"Error extracting client config from headers: {e}")
            logger.exception("Full traceback:")

        # Do not write per-request client_config into global lifespan context to avoid cross-session leakage

        # If this request is a session termination, clean up cached credentials
        try:
            if isinstance(getattr(context, "method", None), str):
                if context.method in ("session/terminate", "session/end", "session/close"):
                    headers = headers if isinstance(headers, dict) else {}
                    session_key = getattr(context, "session_id", None) or headers.get("x-session-id")
                    if session_key and session_key in self.client_config_cache:
                        self.client_config_cache.pop(session_key, None)
                        logger.info("ClientConfigMiddleware: cleared cached client_config for session %s", session_key)
                    if session_key and session_key in HEADER_CLIENT_CONFIG_CACHE:
                        HEADER_CLIENT_CONFIG_CACHE.pop(session_key, None)
                        logger.info("ClientConfigMiddleware: cleared global cached client_config for session %s", session_key)
        except Exception:
            pass

        # Continue with the request
        try:
            result = await call_next(context)
            return result
        finally:
            # Clear session correlation after request completes
            try:
                current_session_id.reset(token)
            except Exception:
                pass


# Add the middleware to the server
mcp.add_middleware(ClientConfigMiddleware())


# Health check endpoint for Docker using custom route (recommended pattern)
@mcp.custom_route("/health", methods=["GET"])
async def health_check(request) -> JSONResponse:
    """Health check endpoint for Docker and load balancers"""
    return JSONResponse({"status": "OK", "service": "MCP for Splunk"})


# Legacy health check resource for MCP Inspector compatibility
@mcp.resource("health://status")
def health_check_resource() -> str:
    """Health check endpoint for Docker and load balancers"""
    return "OK"


# Add more test resources for MCP Inspector testing
@mcp.resource("info://server")
def server_info() -> dict:
    """Server information and capabilities"""
    return {
        "name": "MCP Server for Splunk",
        "version": "2.0.0",
        "transport": "http",
        "capabilities": ["tools", "resources", "prompts"],
        "description": "Modular MCP Server providing Splunk integration",
        "status": "running",
    }


# Hot reload endpoint for development
@mcp.resource("debug://reload")
def hot_reload() -> dict:
    """Hot reload components for development (only works when MCP_HOT_RELOAD=true)"""
    if os.environ.get("MCP_HOT_RELOAD", "false").lower() != "true":
        return {"status": "error", "message": "Hot reload is disabled (MCP_HOT_RELOAD != true)"}

    try:
        # Get the component loader from the server context
        # This is a simple approach - in production you'd want proper context management
        logger.info("Triggering hot reload of MCP components...")

        # Create a new component loader and reload
        component_loader = ComponentLoader(mcp)
        results = component_loader.reload_all_components()

        return {
            "status": "success",
            "message": "Components hot reloaded successfully",
            "results": results,
            "timestamp": time.time(),
        }
    except Exception as e:
        logger.error(f"Hot reload failed: {e}")
        return {"status": "error", "message": f"Hot reload failed: {str(e)}"}


@mcp.resource("test://greeting/{name}")
def personalized_greeting(name: str) -> str:
    """Generate a personalized greeting message"""
    return f"Hello, {name}! Welcome to the MCP Server for Splunk."





@mcp.tool
async def user_agent_info(ctx: Context) -> dict:
    """Return request headers and context details for debugging.

    Includes all HTTP headers (with sensitive values masked) and core context metadata.
    """
    request: Request = get_http_request()
    headers = get_http_headers(include_all=True)

    def mask_sensitive(data: dict) -> dict:
        masked: dict[str, object] = {}
        for k, v in (data or {}).items():
            kl = str(k).lower()
            if any(s in kl for s in ["password", "authorization", "token"]):
                masked[k] = "***"
            else:
                masked[k] = v
        return masked

    # Known context state keys we may set in middleware
    state: dict[str, object] = {}
    try:
        sess = ctx.get_state("session_id")  # type: ignore[attr-defined]
        if sess:
            state["session_id"] = sess
    except Exception:
        pass
    try:
        cfg = ctx.get_state("client_config")  # type: ignore[attr-defined]
        if isinstance(cfg, dict):
            state["client_config"] = mask_sensitive(cfg)
    except Exception:
        pass

    return {
        "request": {
            "method": request.method,
            "path": request.url.path,
            "url": str(request.url),
            "client_ip": request.client.host if request.client else "Unknown",
        },
        "headers": mask_sensitive(headers),
        "context": {
            "request_id": getattr(ctx, "request_id", None),
            "client_id": getattr(ctx, "client_id", None),
            "session_id": getattr(ctx, "session_id", None),
            "server": {"name": getattr(getattr(ctx, "fastmcp", None), "name", None)},
            "state": state,
        },
    }


async def main():
    """Main function for running the MCP server"""
    # Get the port from environment variable, default to 8001 (to avoid conflict with Splunk Web UI on 8000)
    port = int(os.environ.get("MCP_SERVER_PORT", 8001))
    host = os.environ.get("MCP_SERVER_HOST", "0.0.0.0")

    logger.info(f"Starting modular MCP server on {host}:{port}")

    # Ensure components are loaded at server startup for health endpoints
    await ensure_components_loaded(mcp)

    # Build the MCP Starlette app and mount it under /mcp in a root Starlette app
    # Use internal path "/" to avoid double-prefixing when mounting at /mcp
    mcp_app = mcp.http_app(
        path="/",
        transport="http",
    )

    # Parent Starlette application that applies middleware to the initial HTTP handshake
    # IMPORTANT: pass the FastMCP app lifespan so Streamable HTTP session manager initializes
    root_app = Starlette(lifespan=mcp_app.lifespan)
    root_app.add_middleware(HeaderCaptureMiddleware)
    root_app.mount("/mcp", mcp_app)
    # Use uvicorn to run the server
    try:
        import uvicorn
        # Serve the root Starlette app so the MCP app is available under "/mcp"
        # and the HeaderCaptureMiddleware is applied to incoming HTTP requests
        config = uvicorn.Config(root_app, host=host, port=port, log_level=UVICORN_LOG_LEVEL)

        server = uvicorn.Server(config)
        await server.serve()
    except ImportError:
        logger.error("uvicorn is required for HTTP transport. Install with: pip install uvicorn")
        raise


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Modular MCP Server for Splunk")
    parser.add_argument(
        "--transport",
        choices=["stdio", "http"],
        default="http",
        help="Transport mode for MCP server",
    )
    parser.add_argument(
        "--host", default="0.0.0.0", help="Host to bind the HTTP server (only for http transport)"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8001,
        help="Port to bind the HTTP server (only for http transport, default 8001 to avoid conflict with Splunk)",
    )

    args = parser.parse_args()

    logger.info("Starting Modular MCP Server for Splunk...")

    try:
        if args.transport == "stdio":
            logger.info("Running in stdio mode for direct MCP client communication")
            # Use FastMCP's built-in run method for stdio
            mcp.run(transport="stdio")
        else:
            # HTTP mode: Use FastMCP's recommended approach for HTTP transport
            logger.info("Running in HTTP mode with Streamable HTTP transport")

            # Option 1: Use FastMCP's built-in HTTP server (recommended for simple cases)
            # mcp.run(transport="http", host=args.host, port=args.port, path="/mcp/")

            # Option 2: Use custom uvicorn setup for advanced middleware (current approach)
            asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
    except Exception as e:
        logger.error(f"Fatal server error: {str(e)}", exc_info=True)
        sys.exit(1)
