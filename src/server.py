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

from fastmcp import FastMCP
from fastmcp.server.middleware import Middleware, MiddlewareContext
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


# ASGI Middleware to capture HTTP headers
class HeaderCaptureMiddleware(BaseHTTPMiddleware):
    """
    ASGI middleware that captures HTTP headers and stores them in a context variable
    so they can be accessed by MCP middleware downstream.
    """

    async def dispatch(self, request: Request, call_next):
        """Capture headers and store in context variable before processing request."""
        logger.info(f"HeaderCaptureMiddleware: Processing request to {request.url.path}")

        try:
            # Convert headers to dict (case-insensitive)
            headers = dict(request.headers)

            # Store headers in context variable
            http_headers_context.set(headers)
            logger.debug(f"Captured headers: {list(headers.keys())}")

            # Log header extraction for debugging
            splunk_headers = {k: v for k, v in headers.items() if k.lower().startswith("x-splunk-")}
            if splunk_headers:
                logger.info(f"Captured Splunk headers: {list(splunk_headers.keys())}")
            else:
                logger.debug(f"No Splunk headers found. Available headers: {list(headers.keys())}")

            # Extract and attach client config to the Starlette request state for tools to use
            try:
                client_config = extract_client_config_from_headers(headers)
                if client_config:
                    # Attach to request.state so BaseTool can retrieve it
                    request.state.client_config = client_config
                    logger.debug("Attached client_config to request.state for downstream access")
            except Exception as e:
                logger.warning(f"Failed to attach client_config to request.state: {e}")

        except Exception as e:
            logger.error(f"Error capturing HTTP headers: {e}")
            # Set empty dict as fallback
            http_headers_context.set({})

        # Continue processing the request
        response = await call_next(request)
        return response


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
        logger.debug(f"Processing request: {context.method}")

        client_config = None

        # Try to access HTTP headers from context variable (set by ASGI middleware)
        try:
            headers = http_headers_context.get({})

            # Derive a stable per-session cache key
            session_key = getattr(context, "session_id", None) or headers.get("x-session-id")

            if headers:
                logger.debug(f"Found HTTP headers from context: {list(headers.keys())}")

                # Extract client config from headers
                client_config = extract_client_config_from_headers(headers)

                if client_config:
                    logger.info("Successfully extracted MCP client configuration from HTTP headers")
                    logger.info(f"Client config extracted: {list(client_config.keys())}")

                    # Cache the config for this session (avoid cross-session leakage)
                    if session_key:
                        self.client_config_cache[session_key] = client_config
                else:
                    logger.debug("No Splunk headers found in HTTP request")
            else:
                logger.debug("No HTTP headers found in context variable")

            # If we didn't extract config from headers, check if we have cached config
            if not client_config and session_key:
                client_config = self.client_config_cache.get(session_key)
                if client_config:
                    logger.debug(f"Using cached client config for session {session_key}")

        except Exception as e:
            logger.error(f"Error extracting client config from headers: {e}")
            logger.exception("Full traceback:")

        # Store client config in the context for tools to access
        if client_config:
            # Update the lifespan context if available (non-intrusive)
            try:
                if (
                    hasattr(context, "fastmcp_context")
                    and context.fastmcp_context
                    and hasattr(context.fastmcp_context, "lifespan_context")
                ):
                    lifespan_ctx = context.fastmcp_context.lifespan_context
                    if hasattr(lifespan_ctx, "client_config"):
                        lifespan_ctx.client_config = client_config
                        logger.debug("Updated lifespan context with client config")
            except Exception as e:
                logger.warning(f"Failed to update lifespan context with client config: {e}")

        # If this request is a session termination, clean up cached credentials
        try:
            if isinstance(getattr(context, "method", None), str):
                if context.method in ("session/terminate", "session/end", "session/close"):
                    headers = headers if isinstance(headers, dict) else {}
                    session_key = getattr(context, "session_id", None) or headers.get("x-session-id")
                    if session_key and session_key in self.client_config_cache:
                        self.client_config_cache.pop(session_key, None)
                        logger.debug(f"Cleared cached client config for session {session_key}")
        except Exception:
            pass

        # Continue with the request
        result = await call_next(context)

        return result


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


async def main():
    """Main function for running the MCP server"""
    # Get the port from environment variable, default to 8001 (to avoid conflict with Splunk Web UI on 8000)
    port = int(os.environ.get("MCP_SERVER_PORT", 8001))
    host = os.environ.get("MCP_SERVER_HOST", "0.0.0.0")

    logger.info(f"Starting modular MCP server on {host}:{port}")

    # Ensure components are loaded at server startup for health endpoints
    await ensure_components_loaded(mcp)

    # Create custom ASGI middleware list to capture HTTP headers
    from starlette.middleware import Middleware as StarletteMiddleware

    custom_middleware = [
        StarletteMiddleware(HeaderCaptureMiddleware),
    ]

    # Create the FastMCP ASGI app with proper middleware and transport
    # Use the recommended Streamable HTTP transport (default for 'http')
    app = mcp.http_app(
        path="/mcp/",
        middleware=custom_middleware,
        transport="http",  # Explicitly use Streamable HTTP transport
    )

    # Use uvicorn to run the server
    try:
        import uvicorn

        config = uvicorn.Config(app, host=host, port=port, log_level=UVICORN_LOG_LEVEL)
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
