"""
Modular MCP Server for Splunk

This is the new modular version that uses the core framework for
automatic discovery and loading of tools, resources, and prompts.
"""

import argparse
import asyncio
import os
import sys
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastmcp import FastMCP

# Add the project root to the path for imports
project_root = os.path.dirname(os.path.dirname(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import logging

# Create logs directory if it doesn't exist
log_dir = os.path.join(os.path.dirname(__file__), 'logs')
os.makedirs(log_dir, exist_ok=True)

# Enhanced logging configuration
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(log_dir, 'mcp_splunk_server.log')),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Import the core framework components
from src.core.base import SplunkContext
from src.core.loader import ComponentLoader


@asynccontextmanager
async def splunk_lifespan(server: FastMCP) -> AsyncIterator[SplunkContext]:
    """Manage Splunk connection lifecycle"""
    logger.info("Initializing Splunk connection...")
    service = None
    is_connected = False

    try:
        # Import the safe version that doesn't raise exceptions
        from src.client.splunk_client import get_splunk_service_safe
        service = get_splunk_service_safe()

        if service:
            logger.info("Splunk connection established successfully")
            is_connected = True
        else:
            logger.warning("Splunk connection failed - running in degraded mode")
            logger.warning("Some tools will not be available until Splunk connection is restored")

        # Create the context
        context = SplunkContext(service=service, is_connected=is_connected)
        
        # Load all components using the modular framework
        logger.info("Loading MCP components...")
        component_loader = ComponentLoader(server)
        results = component_loader.load_all_components()
        
        logger.info(f"Successfully loaded components: {results}")
        
        yield context

    except Exception as e:
        logger.error(f"Unexpected error during server initialization: {str(e)}")
        logger.exception("Full traceback:")
        # Still yield a context with no service to allow MCP server to start
        yield SplunkContext(service=None, is_connected=False)
    finally:
        logger.info("Shutting down Splunk connection")


# Initialize FastMCP server with lifespan context
mcp = FastMCP(name="MCP Server for Splunk", lifespan=splunk_lifespan)


# Health check endpoint for Docker
@mcp.resource("health://status")
def health_check() -> str:
    """Health check endpoint for Docker and load balancers"""
    return "OK"


async def main():
    """Main function for running the MCP server"""
    # Get the port from environment variable, default to 8000
    port = int(os.environ.get("MCP_SERVER_PORT", 8000))
    host = os.environ.get("MCP_SERVER_HOST", "0.0.0.0")

    logger.info(f"Starting modular MCP server on {host}:{port}")

    # Use FastMCP's built-in run_async method for proper lifespan management
    await mcp.run_async(transport="http", host=host, port=port, path="/mcp/")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Modular MCP Server for Splunk")
    parser.add_argument(
        "--transport",
        choices=["stdio", "http"],
        default="http",
        help="Transport mode for MCP server"
    )
    parser.add_argument(
        "--host",
        default="0.0.0.0",
        help="Host to bind the HTTP server (only for http transport)"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Port to bind the HTTP server (only for http transport)"
    )
    
    args = parser.parse_args()
    
    logger.info("Starting Modular MCP Server for Splunk...")
    
    try:
        if args.transport == "stdio":
            logger.info("Running in stdio mode for direct MCP client communication")
            asyncio.run(mcp.run())
        else:
            # HTTP mode: use Streamable HTTP transport for web-based communication
            logger.info("Running in HTTP mode with Streamable HTTP transport")
            asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
    except Exception as e:
        logger.error(f"Fatal server error: {str(e)}", exc_info=True)
        sys.exit(1) 