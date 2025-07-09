"""
Shared tool utilities for Splunk troubleshooting agents.
"""

import logging
import time
from typing import Any, Callable, Dict, List, Optional

from fastmcp import Context

logger = logging.getLogger(__name__)

# Import OpenAI agents if available
try:
    from agents import function_tool
    OPENAI_AGENTS_AVAILABLE = True
except ImportError:
    OPENAI_AGENTS_AVAILABLE = False
    function_tool = None


class SplunkToolRegistry:
    """Registry for Splunk tools with shared context management."""
    
    def __init__(self):
        self._current_context: Optional[Context] = None
        self._tools: List[Callable] = []
    
    def set_context(self, ctx: Context):
        """Set the current context for tool calls."""
        self._current_context = ctx
    
    def get_context(self) -> Context:
        """Get the current context or create a mock one."""
        if self._current_context:
            return self._current_context
        
        # Create mock context as fallback
        class MockContext:
            async def info(self, message): 
                logger.info(f"[Agent Tool] {message}")
            async def error(self, message): 
                logger.error(f"[Agent Tool] {message}")
        
        return MockContext()
    
    def register_tool(self, tool_func: Callable):
        """Register a tool function."""
        self._tools.append(tool_func)
        return tool_func
    
    def get_tools(self) -> List[Callable]:
        """Get all registered tools."""
        return self._tools.copy()
    
    def get_available_tools(self) -> List[str]:
        """Get list of available tool names."""
        tool_names = []
        for tool in self._tools:
            if hasattr(tool, '__name__'):
                tool_names.append(tool.__name__)
            elif hasattr(tool, 'name'):
                tool_names.append(tool.name)
            else:
                tool_names.append(str(tool))
        return tool_names
    
    async def call_tool(self, tool_name: str, args: Dict[str, Any]) -> Dict[str, Any]:
        """Call a tool by name with arguments - mock implementation for testing."""
        logger.info(f"Mock tool call: {tool_name} with args: {args}")
        
        # Mock responses for testing
        if tool_name == "run_oneshot_search":
            return {
                "success": True,
                "data": {
                    "results": [{"count": "1000", "license_state": "OK", "product_type": "enterprise"}]
                }
            }
        elif tool_name == "list_indexes":
            return {
                "success": True,
                "data": {
                    "indexes": ["main", "security", "_internal", "_audit"]
                }
            }
        elif tool_name == "get_current_user":
            return {
                "success": True,
                "data": {
                    "name": "admin",
                    "roles": ["admin", "user"]
                }
            }
        else:
            return {"success": False, "error": f"Tool {tool_name} not found"}


def create_splunk_tools(splunk_tool_registry: SplunkToolRegistry) -> List[Callable]:
    """Create function tools that wrap MCP server tools for agent execution."""
    
    if not OPENAI_AGENTS_AVAILABLE:
        raise ImportError("OpenAI agents support required. Ensure openai-agents is installed.")
    
    logger.debug("Setting up direct tool registry access for agent execution...")
    
    # Import MCP tool registry for direct access
    from ....core.registry import tool_registry as mcp_tool_registry
    
    # Define allowed tools
    allowed_tools = [
        "list_indexes",
        "list_sources",
        "list_sourcetypes", 
        "list_apps",
        "list_users",
        "run_splunk_search",
        "run_oneshot_search",
        "get_splunk_health",
        "list_triggered_alerts",
        "me"
    ]
    
    logger.info(f"Direct tool registry configured with filter for {len(allowed_tools)} allowed tools")
    
    @function_tool
    async def run_splunk_search(query: str, earliest_time: str = "-24h", latest_time: str = "now") -> str:
        """Execute a Splunk search query via direct tool registry with progress tracking for long-running searches."""
        logger.debug(f"Executing job-based search: {query[:100]}... (time: {earliest_time} to {latest_time})")
        
        try:
            # Get current context
            ctx = splunk_tool_registry.get_context()
            
            # Report search execution start
            if hasattr(ctx, 'info'):
                await ctx.info(f"🔍 Starting job-based search: {query[:50]}...")
            
            # Get the job search tool directly from registry
            tool = mcp_tool_registry.get_tool("run_splunk_search")
            if not tool:
                raise RuntimeError("run_splunk_search tool not found in registry")
            
            logger.debug("Calling tool registry: run_splunk_search (job-based)")
            
            search_start_time = time.time()
            
            # Call the job search tool directly
            result = await tool.execute(
                ctx,
                query=query,
                earliest_time=earliest_time,
                latest_time=latest_time
            )
            
            search_duration = time.time() - search_start_time
            
            # Process the job search result
            if isinstance(result, dict):
                if result.get('status') == 'success':
                    results = result.get('results', [])
                    result_count = result.get('results_count', len(results))
                    scan_count = result.get('scan_count', 0)
                    event_count = result.get('event_count', 0)
                    job_id = result.get('job_id', 'unknown')
                    
                    # Report completion with detailed stats
                    if hasattr(ctx, 'info'):
                        await ctx.info(f"✅ Search job {job_id} completed in {search_duration:.1f}s")
                        await ctx.info(f"📊 Results: {result_count} events, scanned {scan_count:,} events, matched {event_count:,} events")
                    
                    logger.info(f"Job search completed successfully - Job ID: {job_id}, Duration: {search_duration:.1f}s, Results: {result_count}")
                    
                    # Format results for agent consumption
                    if results:
                        formatted_results = []
                        for i, res in enumerate(results[:50]):  # Limit to first 50 results for readability
                            if isinstance(res, dict):
                                result_str = f"Result {i+1}:"
                                for key, value in res.items():
                                    if key.startswith('_') and key not in ['_time', '_raw']:
                                        continue  # Skip internal fields except _time and _raw
                                    result_str += f"\n  {key}: {value}"
                                formatted_results.append(result_str)
                            else:
                                formatted_results.append(f"Result {i+1}: {str(res)}")
                        
                        return f"Search completed successfully.\n\nJob Statistics:\n- Job ID: {job_id}\n- Results Count: {result_count}\n- Events Scanned: {scan_count:,}\n- Events Matched: {event_count:,}\n- Duration: {search_duration:.1f}s\n\nResults:\n" + "\n\n".join(formatted_results)
                    else:
                        return f"Search completed successfully but returned no results.\n\nJob Statistics:\n- Job ID: {job_id}\n- Results Count: 0\n- Events Scanned: {scan_count:,}\n- Events Matched: {event_count:,}\n- Duration: {search_duration:.1f}s"
                else:
                    error_msg = result.get('error', 'Unknown error')
                    logger.error(f"Job search failed: {error_msg}")
                    if hasattr(ctx, 'error'):
                        await ctx.error(f"Search failed: {error_msg}")
                    return f"Search failed: {error_msg}"
            else:
                logger.warning(f"Unexpected result format from job search: {type(result)}")
                return f"Search completed with unexpected result format: {str(result)}"
        
        except Exception as e:
            logger.error(f"Error executing job-based search: {e}", exc_info=True)
            ctx = splunk_tool_registry.get_context()
            if hasattr(ctx, 'error'):
                await ctx.error(f"Search failed: {str(e)}")
            return f"Error executing job-based search: {str(e)}"
    
    @function_tool
    async def run_oneshot_search(query: str, earliest_time: str = "-15m", latest_time: str = "now", max_results: int = 100) -> str:
        """Execute a Splunk oneshot search query via direct tool registry for quick results."""
        logger.debug(f"Executing oneshot search: {query[:100]}... (time: {earliest_time} to {latest_time})")
        
        try:
            ctx = splunk_tool_registry.get_context()
            
            if hasattr(ctx, 'info'):
                await ctx.info(f"🔍 Starting oneshot search: {query[:50]}...")
            
            tool = mcp_tool_registry.get_tool("run_oneshot_search")
            if not tool:
                raise RuntimeError("run_oneshot_search tool not found in registry")
            
            logger.debug("Calling tool registry: run_oneshot_search")
            
            result = await tool.execute(
                ctx,
                query=query,
                earliest_time=earliest_time,
                latest_time=latest_time,
                max_results=max_results
            )
            
            if hasattr(ctx, 'info'):
                await ctx.info(f"✅ Oneshot search completed")
            
            logger.info(f"Oneshot search completed successfully, result length: {len(str(result))}")
            return str(result)
        
        except Exception as e:
            logger.error(f"Error executing oneshot search: {e}", exc_info=True)
            ctx = splunk_tool_registry.get_context()
            if hasattr(ctx, 'error'):
                await ctx.error(f"Oneshot search failed: {str(e)}")
            return f"Error executing oneshot search: {str(e)}"
    
    @function_tool
    async def list_splunk_indexes() -> str:
        """List available Splunk indexes via direct tool registry."""
        logger.debug("Listing Splunk indexes via direct registry...")
        
        try:
            ctx = splunk_tool_registry.get_context()
            
            if hasattr(ctx, 'info'):
                await ctx.info("📋 Retrieving available Splunk indexes...")
            
            tool = mcp_tool_registry.get_tool("list_indexes")
            if not tool:
                raise RuntimeError("list_indexes tool not found in registry")
            
            logger.debug("Calling tool registry: list_indexes")
            
            result = await tool.execute(ctx, random_string="check")
            
            if hasattr(ctx, 'info'):
                index_count = str(result).count('index:') if 'index:' in str(result) else 'unknown'
                await ctx.info(f"✅ Retrieved {index_count} indexes")
            
            logger.info(f"Direct indexes listed successfully, result length: {len(str(result))}")
            return str(result)
        
        except Exception as e:
            logger.error(f"Error listing indexes via direct registry: {e}", exc_info=True)
            ctx = splunk_tool_registry.get_context()
            if hasattr(ctx, 'error'):
                await ctx.error(f"Failed to list indexes: {str(e)}")
            return f"Error listing indexes via direct registry: {str(e)}"
    
    @function_tool
    async def get_splunk_health() -> str:
        """Check Splunk server health via direct tool registry."""
        logger.debug("Checking Splunk health via direct registry...")
        
        try:
            ctx = splunk_tool_registry.get_context()
            
            if hasattr(ctx, 'info'):
                await ctx.info("🏥 Checking Splunk server health...")
            
            tool = mcp_tool_registry.get_tool("get_splunk_health")
            if not tool:
                raise RuntimeError("get_splunk_health tool not found in registry")
            
            logger.debug("Calling tool registry: get_splunk_health")
            
            result = await tool.execute(ctx)
            
            if hasattr(ctx, 'info'):
                status = 'healthy' if 'connected' in str(result) else 'issues detected'
                await ctx.info(f"✅ Health check complete - Status: {status}")
            
            logger.info(f"Direct health check completed successfully, result length: {len(str(result))}")
            return str(result)
        
        except Exception as e:
            logger.error(f"Error checking health via direct registry: {e}", exc_info=True)
            ctx = splunk_tool_registry.get_context()
            if hasattr(ctx, 'error'):
                await ctx.error(f"Health check failed: {str(e)}")
            return f"Error checking health via direct registry: {str(e)}"
    
    @function_tool
    async def get_current_user_info() -> str:
        """Get current authenticated user information including roles and capabilities via direct tool registry."""
        logger.debug("Getting current user information via direct registry...")
        
        try:
            ctx = splunk_tool_registry.get_context()
            
            if hasattr(ctx, 'info'):
                await ctx.info("👤 Retrieving current user information...")
            
            tool = mcp_tool_registry.get_tool("me")
            if not tool:
                raise RuntimeError("me tool not found in registry")
            
            logger.debug("Calling tool registry: me")
            
            result = await tool.execute(ctx)
            
            if hasattr(ctx, 'info'):
                if isinstance(result, dict) and result.get('status') == 'success':
                    user_data = result.get('data', {}).get('data', {})
                    username = user_data.get('username', 'unknown')
                    roles = user_data.get('roles', [])
                    await ctx.info(f"✅ Retrieved user info for: {username} (roles: {', '.join(roles)})")
                else:
                    await ctx.info("✅ User information request completed")
            
            logger.info(f"Direct user info retrieved successfully, result length: {len(str(result))}")
            return str(result)
        
        except Exception as e:
            logger.error(f"Error getting user info via direct registry: {e}", exc_info=True)
            ctx = splunk_tool_registry.get_context()
            if hasattr(ctx, 'error'):
                await ctx.error(f"Failed to get user information: {str(e)}")
            return f"Error getting user info via direct registry: {str(e)}"
    
    # Register tools
    tools = [
        run_splunk_search,
        run_oneshot_search,
        list_splunk_indexes, 
        get_splunk_health,
        get_current_user_info
    ]
    
    for tool in tools:
        splunk_tool_registry.register_tool(tool)
    
    logger.info(f"Created {len(tools)} direct registry tool wrappers for agent execution")
    return tools 