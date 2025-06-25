import argparse
import asyncio
import os
import sys
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import Any
from urllib.parse import quote

from fastmcp import Context, FastMCP
from splunklib import client
from splunklib.results import ResultsReader

sys.path.append(os.path.dirname(os.path.dirname(__file__)))
import logging
import time

# Create logs directory if it doesn't exist
log_dir = os.path.join(os.path.dirname(__file__), 'logs')
os.makedirs(log_dir, exist_ok=True)

# Enhanced logging configuration
logging.basicConfig(
    level=logging.DEBUG,  # Changed to DEBUG for more detailed logs
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_dir + '/mcp_splunk_server.log'),
        logging.StreamHandler()  # Also log to console
    ]
)
logger = logging.getLogger(__name__)

@dataclass
class SplunkContext:
    service: client.Service | None
    is_connected: bool

@asynccontextmanager
async def splunk_lifespan(server: FastMCP) -> AsyncIterator[SplunkContext]:
    """Manage Splunk connection lifecycle"""
    logger.info("Initializing Splunk connection...")
    service = None
    is_connected = False

    try:
        # Import the safe version that doesn't raise exceptions
        from src.splunk_client import get_splunk_service_safe
        service = get_splunk_service_safe()

        if service:
            logger.info("Splunk connection established successfully")
            is_connected = True
        else:
            logger.warning("Splunk connection failed - running in degraded mode")
            logger.warning("Some tools will not be available until Splunk connection is restored")

        yield SplunkContext(service=service, is_connected=is_connected)

    except Exception as e:
        logger.error(f"Unexpected error during Splunk connection: {str(e)}")
        # Still yield a context with no service to allow MCP server to start
        yield SplunkContext(service=None, is_connected=False)
    finally:
        logger.info("Closing Splunk connection")

# Initialize FastMCP server with lifespan context
mcp = FastMCP(name="MCP Server for Splunk", lifespan=splunk_lifespan)

mcp.dependencies = [
    "splunk-mcp-server"
]

def check_splunk_available(ctx: Context) -> tuple[bool, client.Service | None, str]:
    """
    Check if Splunk is available and return status
    
    Returns:
        Tuple of (is_available, service, error_message)
    """
    splunk_ctx = ctx.request_context.lifespan_context

    if not splunk_ctx.is_connected or not splunk_ctx.service:
        return False, None, "Splunk service is not available. MCP server is running in degraded mode."

    return True, splunk_ctx.service, ""

# Health check endpoint for Docker
@mcp.resource("health://status")
def health_check() -> str:
    """Health check endpoint for Docker and load balancers"""
    return "OK"

@mcp.tool()
def get_splunk_health(ctx: Context) -> dict[str, Any]:
    """
    Get Splunk connection health status
    
    Returns:
        Dict containing Splunk connection status and version information
    """
    logger.info("Checking Splunk health status...")
    splunk_ctx = ctx.request_context.lifespan_context

    if not splunk_ctx.is_connected or not splunk_ctx.service:
        return {
            "status": "disconnected",
            "error": "Splunk service is not available",
            "message": "MCP server is running in degraded mode"
        }

    try:
        service = splunk_ctx.service
        info = {
            "status": "connected",
            "version": service.info["version"],
            "server_name": service.info.get("host", "unknown")
        }
        logger.info(f"Health check successful: {info}")
        return info
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return {
            "status": "error",
            "error": str(e)
        }

@mcp.tool()
def list_indexes(ctx: Context) -> dict[str, Any]:
    """
    Retrieves a list of all accessible indexes from the configured Splunk instance.
    
    Returns:
        Dict containing list of indexes and count
    """
    is_available, service, error_msg = check_splunk_available(ctx)

    if not is_available:
        return {
            "status": "error",
            "error": error_msg,
            "indexes": [],
            "count": 0
        }

    try:
        indexes = [index.name for index in service.indexes]
        return {
            "status": "success",
            "indexes": sorted(indexes),
            "count": len(indexes)
        }
    except Exception as e:
        logger.error(f"Failed to list indexes: {str(e)}")
        return {
            "status": "error",
            "error": str(e),
            "indexes": [],
            "count": 0
        }

@mcp.tool()
def list_sourcetypes(ctx: Context) -> dict[str, Any]:
    """
    List all available sourcetypes from the configured Splunk instance using metadata command.
    This tool returns a comprehensive list of sourcetypes present in your Splunk environment.
    
    Returns:
        Dict containing list of sourcetypes and count
    """
    service = ctx.request_context.lifespan_context.service
    logger.info("Retrieving list of sourcetypes...")

    try:
        # Use metadata command to retrieve sourcetypes
        job = service.jobs.oneshot("| metadata type=sourcetypes | table sourcetype")

        sourcetypes = []
        for result in ResultsReader(job):
            if isinstance(result, dict) and "sourcetype" in result:
                sourcetypes.append(result["sourcetype"])

        logger.info(f"Retrieved {len(sourcetypes)} sourcetypes")
        return {
            "sourcetypes": sorted(sourcetypes),
            "count": len(sourcetypes)
        }
    except Exception as e:
        logger.error(f"Failed to retrieve sourcetypes: {str(e)}")
        raise

@mcp.tool()
def list_sources(ctx: Context) -> dict[str, Any]:
    """
    List all available data sources from the configured Splunk instance using metadata command.
    This tool provides a comprehensive inventory of data sources in your Splunk environment.

    Returns:
        Dict containing list of sources and count
    """
    service = ctx.request_context.lifespan_context.service
    logger.info("Retrieving list of sources...")

    try:
        # Use metadata command to retrieve sources
        job = service.jobs.oneshot("| metadata type=sources | table source")

        sources = []
        for result in ResultsReader(job):
            if isinstance(result, dict) and "source" in result:
                sources.append(result["source"])

        logger.info(f"Retrieved {len(sources)} sources")
        return {
            "sources": sorted(sources),
            "count": len(sources)
        }
    except Exception as e:
        logger.error(f"Failed to retrieve sources: {str(e)}")
        raise

@mcp.tool()
def run_oneshot_search(
    ctx: Context,
    query: str,
    earliest_time: str = "-15m",
    latest_time: str = "now",
    max_results: int = 100
) -> dict[str, Any]:
    """
    Execute a one-shot Splunk search that returns results immediately. Use this tool for quick,
    simple searches where you need immediate results and don't need to track job progress.
    Best for simple searches that return quickly.
    
    Args:
        query: The Splunk search query (SPL) to execute. The 'search' command will be automatically
            added if not present (e.g., "index=main" becomes "search index=main")
        earliest_time: Search start time (default: "-15m")
        latest_time: Search end time (default: "now")
        max_results: Maximum number of results to return (default: 100)
    
    Returns:
        Dict containing:
            - results: List of search results as dictionaries
            - results_count: Number of results returned
            - query_executed: The actual query that was executed
    
    Example:
        run_oneshot_search(
            query="index=_internal | stats count by log_level",
            earliest_time="-1h",
            max_results=10
        )
    """
    is_available, service, error_msg = check_splunk_available(ctx)

    if not is_available:
        return {
            "status": "error",
            "error": error_msg,
            "results": [],
            "results_count": 0,
            "query_executed": query
        }

    # Add 'search' command if not present and query doesn't start with a pipe
    if not query.strip().lower().startswith(('search ', '| ')):
        query = f"search {query}"

    logger.info(f"Executing one-shot search: {query}")

    try:
        kwargs = {
            "earliest_time": earliest_time,
            "latest_time": latest_time,
            "count": max_results
        }

        start_time = time.time()
        job = service.jobs.oneshot(query, **kwargs)

        # Process results
        results = []
        result_count = 0

        for result in ResultsReader(job):
            if isinstance(result, dict):
                results.append(result)
                result_count += 1
                if result_count >= max_results:
                    break

        duration = time.time() - start_time

        return {
            "status": "success",
            "results": results,
            "results_count": result_count,
            "query_executed": query,
            "duration": round(duration, 3)
        }
    except Exception as e:
        logger.error(f"One-shot search failed: {str(e)}")
        return {
            "status": "error",
            "error": str(e),
            "results": [],
            "results_count": 0,
            "query_executed": query
        }

@mcp.tool()
def run_splunk_search(
    ctx: Context,
    query: str,
    earliest_time: str = "-24h",
    latest_time: str = "now"
) -> dict[str, Any]:
    """
    Execute a normal Splunk search job with progress tracking. Use this tool for complex or
    long-running searches where you need to track progress and get detailed job information.
    Best for complex searches that might take longer to complete.
    
    Args:
        query: The Splunk search query (SPL) to execute. The 'search' command will be automatically
            added if not present (e.g., "index=main" becomes "search index=main")
        earliest_time: Search start time (default: "-24h")
        latest_time: Search end time (default: "now")
    
    Returns:
        Dict containing:
            - job_id: Search job ID (sid)
            - is_done: Whether the search is complete
            - scan_count: Number of events scanned
            - event_count: Number of events matched
            - results: List of search results as dictionaries
            - results_count: Number of results returned
            - query_executed: The actual query that was executed
            - duration: Search duration in seconds
            - status: Search status information
    
    Example:
        run_splunk_search(
            query="index=* | stats count by source",
            earliest_time="-7d"
        )
    """
    # Add 'search' command if not present and query doesn't start with a pipe
    if not query.strip().lower().startswith(('search ', '| ')):
        query = f"search {query}"

    logger.info(f"Starting normal search with query: {query}")
    service = ctx.request_context.lifespan_context.service

    try:
        start_time = time.time()

        # Create the search job
        job = service.jobs.create(
            query,
            earliest_time=earliest_time,
            latest_time=latest_time
        )

        # Poll for completion
        while not job.is_done():
            stats = job.content
            progress = {
                "done": stats.get('isDone', '0') == '1',
                "progress": float(stats.get('doneProgress', 0)) * 100,
                "scan_progress": float(stats.get('scanCount', 0)),
                "event_progress": float(stats.get('eventCount', 0))
            }
            logger.info(
                f"Search job {job.sid} in progress... "
                f"Progress: {progress['progress']:.1f}%, "
                f"Scanned: {progress['scan_progress']} events, "
                f"Matched: {progress['event_progress']} events"
            )
            time.sleep(2)

        # Get the results using ResultsReader for consistent parsing
        results = []
        result_count = 0
        for result in ResultsReader(job.results()):
            if isinstance(result, dict):
                results.append(result)
                result_count += 1

        # Get final job stats
        stats = job.content
        duration = time.time() - start_time

        return {
            "job_id": job.sid,
            "is_done": True,
            "scan_count": int(float(stats.get('scanCount', 0))),
            "event_count": int(float(stats.get('eventCount', 0))),
            "results": results,
            "earliest_time": stats.get('earliestTime', ''),
            "latest_time": stats.get('latestTime', ''),
            "results_count": result_count,
            "query_executed": query,
            "duration": round(duration, 3),
            "status": {
                "progress": 100,
                "is_finalized": stats.get('isFinalized', '0') == '1',
                "is_failed": stats.get('isFailed', '0') == '1'
            }
        }
    except Exception as e:
        logger.error(f"Search failed: {str(e)}")
        raise

@mcp.tool()
def list_apps(ctx: Context) -> dict[str, Any]:
    """
    List all installed Splunk apps.
    
    Returns:
        Dict containing list of apps and their properties
    """
    logger.info("Retrieving list of Splunk apps")
    service = ctx.request_context.lifespan_context.service

    try:
        apps = []
        for app in service.apps:
            apps.append({
                "name": app.name,
                "label": app.content.get("label"),
                "version": app.content.get("version"),
                "description": app.content.get("description"),
                "author": app.content.get("author"),
                "visible": app.content.get("visible")
            })

        return {
            "count": len(apps),
            "apps": apps
        }
    except Exception as e:
        logger.error(f"Failed to list apps: {str(e)}")
        raise

@mcp.tool()
def list_users(ctx: Context) -> dict[str, Any]:
    """
    List all Splunk users.
    
    Returns:
        Dict containing list of users and their properties
    """
    logger.info("Retrieving list of Splunk users")
    service = ctx.request_context.lifespan_context.service

    try:
        users = []
        for user in service.users:
            users.append({
                "username": user.name,
                "realname": user.content.get("realname"),
                "email": user.content.get("email"),
                "roles": user.content.get("roles", []),
                "type": user.content.get("type"),
                "defaultApp": user.content.get("defaultApp")
            })

        return {
            "count": len(users),
            "users": users
        }
    except Exception as e:
        logger.error(f"Failed to list users: {str(e)}")
        raise

@mcp.tool()
def list_kvstore_collections(
    ctx: Context,
    app: str | None = None
) -> dict[str, Any]:
    """
    List all KV Store collections in Splunk. Use this tool to discover available KV Store collections
    either across all apps or within a specific app.
    
    Args:
        app: Optional app name (e.g., 'search', 'myapp'). If provided, lists collections only from 
            that specific app. If not provided, lists collections from all accessible apps.
    
    Returns:
        Dict containing:
            - count: Total number of collections found
            - collections: List of collections with their properties:
                - name: Collection name
                - fields: Field definitions
                - accelerated_fields: Indexed fields
                - replicated: Whether collection is replicated
    
    Example:
        To list collections in 'search' app:
        list_kvstore_collections(app='search')
        
        To list all collections:
        list_kvstore_collections()
    """
    logger.info(f"Retrieving KV Store collections for app: {app if app else 'all apps'}")
    service = ctx.request_context.lifespan_context.service

    try:
        collections = []
        kvstore = service.kvstore

        if app:
            kvstore = service.kvstore[app]

        for collection in kvstore:
            collections.append({
                "name": collection.name,
                "fields": collection.content.get("fields", []),
                "accelerated_fields": collection.content.get("accelerated_fields", {}),
                "replicated": collection.content.get("replicated", False)
            })

        return {
            "count": len(collections),
            "collections": collections
        }
    except Exception as e:
        logger.error(f"Failed to list KV Store collections: {str(e)}")
        raise

@mcp.tool()
def get_kvstore_data(
    ctx: Context,
    collection: str,
    app: str | None = None,
    query: dict | None = None
) -> dict[str, Any]:
    """
    Retrieve data from a specific KV Store collection. Use this tool when you need to fetch
    documents from a KV Store collection, with optional filtering capabilities.
    
    Args:
        collection: Name of the collection to retrieve data from
        app: Optional app name where the collection resides. If not provided, searches in
            default app context
        query: Optional MongoDB-style query filter (e.g., {"field": "value"}) to filter
            the documents to retrieve
    
    Returns:
        Dict containing:
            - count: Number of documents retrieved
            - documents: List of documents from the collection
    
    Example:
        To get all documents:
        get_collection_data(collection="mycollection", app="myapp")
        
        To get filtered documents:
        get_collection_data(collection="mycollection", app="myapp", 
                          query={"status": "active"})
    """
    logger.info(f"Retrieving data from KV Store collection: {collection}")
    service = ctx.request_context.lifespan_context.service

    try:
        if app:
            collection = service.kvstore[app][collection]
        else:
            collection = service.kvstore[collection]

        documents = collection.data.query(query) if query else collection.data.query()

        return {
            "count": len(documents),
            "documents": documents
        }
    except Exception as e:
        logger.error(f"Failed to get KV store data: {str(e)}")
        raise

@mcp.tool()
def create_kvstore_collection(
    ctx: Context,
    app: str,
    collection: str,
    fields: list[dict[str, Any]] | None = None,
    accelerated_fields: dict[str, list[list[str]]] | None = None,
    replicated: bool = True
) -> dict[str, Any]:
    """
    Create a new KV Store collection in a specified Splunk app. Use this tool when you need
    to create a new collection for storing custom data in Splunk.
    
    Args:
        app: Name of the app where the collection should be created (e.g., 'search', 'myapp').
             The app must exist and you must have permissions to create collections.
        collection: Name for the new collection. Must be unique within the app and contain only
                   alphanumeric characters and underscores.
        fields: Optional list of field definitions to structure the collection data. Each field
            definition should be a dict with:
            - name: Field name
            - type: Field type (string, number, boolean)
            - required: Whether the field is required (optional)
        accelerated_fields: Optional dict defining indexed fields for better query performance
        replicated: Whether the collection should be replicated across search heads (default: True)
    
    Returns:
        Dict containing:
            - status: Operation status
            - collection: Details of the created collection
    
    Example:
        # Create a simple collection
        create_kvstore_collection(
            app="search",
            collection="mycollection"
        )
        
        # Create a structured collection
        create_kvstore_collection(
            app="search",
            collection="users",
            fields=[
                {"name": "username", "type": "string", "required": True},
                {"name": "age", "type": "number"}
            ],
            accelerated_fields={"username_idx": [["username"]]}
        )
    """
    logger.info(f"Creating new KV Store collection: {collection} in app: {app}")
    service = ctx.request_context.lifespan_context.service

    try:
        # Validate app name
        if not app:
            raise ValueError("App name is required")

        # Validate collection name
        if not collection.isalnum() and '_' not in collection:
            raise ValueError("Collection name must contain only alphanumeric characters and underscores")

        # URL encode the app name to handle special characters
        encoded_app = quote(app, safe='')

        # Prepare collection configuration
        collection_config = {
            "name": collection,
            "replicated": replicated
        }

        if fields:
            collection_config["field"] = fields

        if accelerated_fields:
            collection_config["accelerated_fields"] = accelerated_fields

        # Create the collection
        kvstore = service.kvstore[encoded_app]
        new_collection = kvstore.create(
            name=collection,
            **collection_config
        )

        return {
            "status": "success",
            "collection": {
                "name": new_collection.name,
                "fields": new_collection.content.get("fields", []),
                "accelerated_fields": new_collection.content.get("accelerated_fields", {}),
                "replicated": new_collection.content.get("replicated", False)
            }
        }

    except Exception as e:
        logger.error(f"Failed to create KV Store collection: {str(e)}")
        raise ValueError(f"Failed to create collection: {str(e)}")

@mcp.tool()
def get_configurations(
    ctx: Context,
    conf_file: str,
    stanza: str | None = None
) -> dict[str, Any]:
    """
    Get Splunk configurations.
    
    Args:
        conf_file: Configuration file name (e.g., 'props', 'transforms', 'inputs')
        stanza: Optional stanza name to get specific configuration
    
    Returns:
        Dict containing configuration settings
    """
    logger.info(f"Retrieving configurations from {conf_file}")
    service = ctx.request_context.lifespan_context.service

    try:
        confs = service.confs[conf_file]

        if stanza:
            stanza_obj = confs[stanza]
            return {
                "stanza": stanza,
                "settings": dict(stanza_obj.content)
            }

        all_stanzas = {}
        for stanza_obj in confs:
            all_stanzas[stanza_obj.name] = dict(stanza_obj.content)

        return {
            "file": conf_file,
            "stanzas": all_stanzas
        }
    except Exception as e:
        logger.error(f"Failed to get configurations: {str(e)}")
        raise

async def main():
    """Main function for running the MCP server with transport selection"""
    parser = argparse.ArgumentParser(
        description='MCP Server for Splunk',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run locally with stdio (default)
  python src/server.py
  python src/server.py --transport stdio

  # Run with HTTP transport
  python src/server.py --transport streamable-http
  python src/server.py --transport streamable-http --host 0.0.0.0 --port 8000

  # Environment variables (useful for Docker)
  export MCP_TRANSPORT=streamable-http
  export MCP_HOST=0.0.0.0
  export MCP_PORT=8000
  python src/server.py
        """
    )

    parser.add_argument(
        '--transport',
        choices=['stdio', 'streamable-http'],
        default=os.environ.get('MCP_TRANSPORT', 'stdio'),
        help='Transport method: stdio (local) or streamable-http (remote)'
    )
    parser.add_argument(
        '--host',
        default=os.environ.get('MCP_HOST', 'localhost'),
        help='Host for HTTP transport (default: localhost)'
    )
    parser.add_argument(
        '--port',
        type=int,
        default=int(os.environ.get('MCP_PORT', 8000)),
        help='Port for HTTP transport (default: 8000)'
    )
    parser.add_argument(
        '--path',
        default=os.environ.get('MCP_PATH', '/mcp/'),
        help='Path for HTTP transport (default: /mcp/)'
    )

    # Parse arguments, but don't fail if none provided (for Docker compatibility)
    if len(sys.argv) == 1:
        # No arguments provided, use environment variables or defaults
        args = argparse.Namespace(
            transport=os.environ.get('MCP_TRANSPORT', 'stdio'),
            host=os.environ.get('MCP_HOST', 'localhost'),
            port=int(os.environ.get('MCP_PORT', 8000)),
            path=os.environ.get('MCP_PATH', '/mcp/'),

        )
    else:
        args = parser.parse_args()

    logger.info("🚀 Starting MCP Server for Splunk")
    logger.info(f"📡 Transport: {args.transport}")

    if args.transport == "stdio":
        logger.info("🔌 Running with STDIO transport (local mode)")
        await mcp.run_async(transport="stdio")
    elif args.transport == "streamable-http":
        logger.info(f"🌐 Running with HTTP transport on {args.host}:{args.port}{args.path}")
        await mcp.run_async(
            transport="streamable-http",
            host=args.host,
            port=args.port,
            path=args.path
        )

if __name__ == "__main__":
    logger.info("Starting MCP Server for Splunk...")
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("👋 Server stopped by user")
    except Exception as e:
        logger.error(f"❌ Fatal server error: {str(e)}", exc_info=True)
        sys.exit(1)
