"""
Shared tool utilities for Splunk troubleshooting agents.
"""

import logging
import time
from collections.abc import Callable
from typing import Any

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
        self._current_context: Context | None = None
        self._tools: list[Callable] = []
        self._tool_name_map: dict[str, str] = {}

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

    def register_tool(self, tool_func: Callable, aliases: list[str] = None):
        """Register a tool function with optional aliases."""
        self._tools.append(tool_func)

        # Register aliases for tool name mapping
        if aliases:
            # Prefer explicit name attribute (FunctionTool provides .name)
            tool_name = (
                getattr(tool_func, "name", None)
                or getattr(tool_func, "__name__", None)
                or str(tool_func)
            )
            for alias in aliases:
                self._tool_name_map[alias] = tool_name
                logger.debug(f"Registered tool alias: {alias} -> {tool_name}")

        return tool_func

    def get_tools(self) -> list[Callable]:
        """Get all registered tools."""
        return self._tools.copy()

    def get_available_tools(self) -> list[str]:
        """Get list of available tool names including aliases."""
        tool_names = []

        # Add actual tool names
        for tool in self._tools:
            if hasattr(tool, "__name__"):
                tool_names.append(tool.__name__)
            elif hasattr(tool, "name"):
                tool_names.append(tool.name)
            else:
                tool_names.append(str(tool))

        # Add aliases
        tool_names.extend(self._tool_name_map.keys())

        return tool_names

    def _resolve_mcp_tool_name(self, requested_name: str) -> str:
        """Resolve a requested tool name or alias to an MCP tool name.

        This uses both the explicit alias map in this registry and a static
        mapping for common synonyms used in workflows.
        """
        # Handle common synonyms used in workflow JSON (map to MCP registry names)
        tool_name_mapping = {
            "get_current_user": "me",
            "get_current_user_info": "me",
            "list_splunk_indexes": "list_indexes",
            "list_indexes": "list_indexes",
            "run_oneshot_search": "run_oneshot_search",
            "run_splunk_search": "run_splunk_search",
            "get_splunk_health": "get_splunk_health",
        }

        # First resolve dynamic aliases registered via register_tool()
        # Example: "list_indexes" -> "list_splunk_indexes"
        resolved_name = self._tool_name_map.get(requested_name, requested_name)

        # Then translate any known synonyms/canonical names to MCP registry names
        # Example: "list_splunk_indexes" -> "list_indexes"
        return tool_name_mapping.get(resolved_name, resolved_name)

    def create_agent_tool(self, requested_name: str):
        """Create an OpenAI Agents function tool dynamically for a given MCP tool name.

        Returns the function tool or None if it cannot be created (e.g., Agents SDK not available
        or the tool is not found in the MCP registry).
        """
        if not OPENAI_AGENTS_AVAILABLE:
            return None

        try:
            # Import MCP tool registry for direct access
            try:
                from ....core.registry import tool_registry as mcp_tool_registry
            except ImportError:
                from src.core.registry import tool_registry as mcp_tool_registry

            # Resolve alias to canonical MCP name
            mcp_name = self._resolve_mcp_tool_name(requested_name)

            # Look up the MCP tool instance and metadata
            tool = mcp_tool_registry.get_tool(mcp_name)
            if not tool:
                logger.warning(f"Requested agent tool '{requested_name}' not found as MCP tool '{mcp_name}'")
                return None

            metadata = mcp_tool_registry.get_metadata(mcp_name)

            # Build a thin wrapper that matches the underlying tool's execute signature (minus ctx)
            import inspect

            execute_sig = inspect.signature(tool.execute)
            params: list[inspect.Parameter] = []
            for name, param in execute_sig.parameters.items():
                if name in ("self", "ctx"):
                    continue
                params.append(
                    inspect.Parameter(
                        name=name,
                        kind=inspect.Parameter.POSITIONAL_OR_KEYWORD,
                        default=param.default,
                        annotation=param.annotation,
                    )
                )

            wrapper_sig = inspect.Signature(params)

            async def dynamic_tool_wrapper(*args, **kwargs) -> str:
                # Ensure we have a context bound so tools can report progress
                ctx = self.get_context()
                # Keep context in registry for any nested calls
                self.set_context(ctx)

                try:
                    bound = wrapper_sig.bind(*args, **kwargs)
                    bound.apply_defaults()
                except TypeError:
                    # If binding fails due to signature mismatch, fall back to passing kwargs through
                    bound = None

                result = await tool.execute(ctx, **(bound.arguments if bound else kwargs))
                return str(result)

            # Apply an explicit signature and annotations before wrapping
            try:
                dynamic_tool_wrapper.__signature__ = wrapper_sig
                # Build annotations for strict schema generation
                annotations: dict[str, Any] = {"return": str}
                for p in wrapper_sig.parameters.values():
                    # Default to str if annotation is missing
                    ann = p.annotation if p.annotation is not inspect._empty else str
                    annotations[p.name] = ann
                dynamic_tool_wrapper.__annotations__ = annotations

                # Wrap as an Agents function tool with explicit name/description
                wrapped = function_tool(
                    dynamic_tool_wrapper,
                    name_override=mcp_name,
                    description_override=(metadata.description if metadata else mcp_name),
                )
                return wrapped
            except Exception as e:
                logger.error(
                    "Failed to finalize dynamic agent tool for '%s': %s", requested_name, e
                )
                return None

        except Exception as e:
            logger.error(f"Failed to create dynamic agent tool for '{requested_name}': {e}", exc_info=True)
            return None

    async def call_tool(self, tool_name: str, args: dict[str, Any] = None) -> dict[str, Any]:
        """Call a tool by name with arguments using the MCP tool registry."""
        if args is None:
            args = {}

        logger.debug(f"Calling MCP tool: {tool_name} with args: {args}")

        try:
            # Import MCP tool registry for direct access
            try:
                from ....core.registry import tool_registry as mcp_tool_registry
            except ImportError:
                from src.core.registry import tool_registry as mcp_tool_registry

            # Get current context
            ctx = self.get_context()

            # Resolve to MCP registry name (supports aliases)
            mcp_tool_name = self._resolve_mcp_tool_name(tool_name)

            # Get the tool from the MCP registry
            tool = mcp_tool_registry.get_tool(mcp_tool_name)
            if not tool:
                logger.error(f"Tool {mcp_tool_name} not found in MCP registry")
                return {
                    "success": False,
                    "error": f"Tool {mcp_tool_name} not found in MCP registry",
                }

            logger.debug(f"Executing MCP tool: {mcp_tool_name}")

            # Call the tool with appropriate arguments
            if mcp_tool_name == "run_oneshot_search":
                result = await tool.execute(
                    ctx,
                    query=args.get("query", ""),
                    earliest_time=args.get("earliest_time", "-15m"),
                    latest_time=args.get("latest_time", "now"),
                    max_results=args.get("max_results", 100),
                )
            elif mcp_tool_name == "run_splunk_search":
                result = await tool.execute(
                    ctx,
                    query=args.get("query", ""),
                    earliest_time=args.get("earliest_time", "-24h"),
                    latest_time=args.get("latest_time", "now"),
                )
            elif mcp_tool_name == "list_indexes":
                result = await tool.execute(ctx)
            elif mcp_tool_name == "list_sources":
                result = await tool.execute(ctx)
            elif mcp_tool_name == "list_sourcetypes":
                result = await tool.execute(ctx)
            elif mcp_tool_name == "list_apps":
                result = await tool.execute(ctx)
            elif mcp_tool_name == "list_users":
                result = await tool.execute(ctx)
            elif mcp_tool_name == "me":
                result = await tool.execute(ctx)
            elif mcp_tool_name == "get_splunk_health":
                result = await tool.execute(ctx)
            elif mcp_tool_name == "list_triggered_alerts":
                result = await tool.execute(
                    ctx,
                    count=args.get("count", 50),
                    earliest_time=args.get("earliest_time", "-24h@h"),
                    latest_time=args.get("latest_time", "now"),
                    search=args.get("search", ""),
                )
            else:
                # Generic call with all provided args
                result = await tool.execute(ctx, **args)

            logger.info(f"MCP tool {mcp_tool_name} executed successfully")

            # Return the result in a consistent format
            return {"success": True, "data": result, "tool_name": mcp_tool_name}

        except Exception as e:
            error_msg = f"Error calling MCP tool {tool_name}: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return {"success": False, "error": error_msg, "tool_name": tool_name}


def create_splunk_tools(splunk_tool_registry: SplunkToolRegistry) -> list[Callable]:
    """Create function tools that wrap MCP server tools for agent execution."""

    if not OPENAI_AGENTS_AVAILABLE:
        raise ImportError("OpenAI agents support required. Ensure openai-agents is installed.")

    logger.debug("Setting up direct tool registry access for agent execution...")

    # Import MCP tool registry for direct access
    try:
        from ....core.registry import tool_registry as mcp_tool_registry
    except ImportError:
        from src.core.registry import tool_registry as mcp_tool_registry

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
        "me",
    ]

    logger.info(
        f"Direct tool registry configured with filter for {len(allowed_tools)} allowed tools"
    )

    @function_tool
    async def run_splunk_search(
        query: str, earliest_time: str = "-24h", latest_time: str = "now"
    ) -> str:
        """Execute a Splunk search query via direct tool registry with progress tracking for long-running searches."""
        logger.debug(
            f"Executing job-based search: {query[:100]}... (time: {earliest_time} to {latest_time})"
        )

        try:
            # Get current context
            ctx = splunk_tool_registry.get_context()

            # Report search execution start
            if hasattr(ctx, "info"):
                await ctx.info(f"🔍 Starting job-based search: {query[:50]}...")

            # Get the job search tool directly from registry
            tool = mcp_tool_registry.get_tool("run_splunk_search")
            if not tool:
                raise RuntimeError("run_splunk_search tool not found in registry")

            logger.debug("Calling tool registry: run_splunk_search (job-based)")

            search_start_time = time.time()

            # Call the job search tool directly
            result = await tool.execute(
                ctx, query=query, earliest_time=earliest_time, latest_time=latest_time
            )

            search_duration = time.time() - search_start_time

            # Process the job search result
            if isinstance(result, dict):
                if result.get("status") == "success":
                    results = result.get("results", [])
                    result_count = result.get("results_count", len(results))
                    scan_count = result.get("scan_count", 0)
                    event_count = result.get("event_count", 0)
                    job_id = result.get("job_id", "unknown")

                    # Report completion with detailed stats
                    if hasattr(ctx, "info"):
                        await ctx.info(f"✅ Search job {job_id} completed in {search_duration:.1f}s")
                        await ctx.info(
                            f"📊 Results: {result_count} events, scanned {scan_count:,} events, matched {event_count:,} events"
                        )

                    logger.info(
                        f"Job search completed successfully - Job ID: {job_id}, Duration: {search_duration:.1f}s, Results: {result_count}"
                    )

                    # Format results for agent consumption
                    if results:
                        formatted_results = []
                        for i, res in enumerate(
                            results[:50]
                        ):  # Limit to first 50 results for readability
                            if isinstance(res, dict):
                                result_str = f"Result {i + 1}:"
                                for key, value in res.items():
                                    if key.startswith("_") and key not in ["_time", "_raw"]:
                                        continue  # Skip internal fields except _time and _raw
                                    result_str += f"\n  {key}: {value}"
                                formatted_results.append(result_str)
                            else:
                                formatted_results.append(f"Result {i + 1}: {str(res)}")

                        return (
                            f"Search completed successfully.\n\nJob Statistics:\n- Job ID: {job_id}\n- Results Count: {result_count}\n- Events Scanned: {scan_count:,}\n- Events Matched: {event_count:,}\n- Duration: {search_duration:.1f}s\n\nResults:\n"
                            + "\n\n".join(formatted_results)
                        )
                    else:
                        return f"Search completed successfully but returned no results.\n\nJob Statistics:\n- Job ID: {job_id}\n- Results Count: 0\n- Events Scanned: {scan_count:,}\n- Events Matched: {event_count:,}\n- Duration: {search_duration:.1f}s"
                else:
                    error_msg = result.get("error", "Unknown error")
                    logger.error(f"Job search failed: {error_msg}")
                    if hasattr(ctx, "error"):
                        await ctx.error(f"Search failed: {error_msg}")
                    return f"Search failed: {error_msg}"
            else:
                logger.warning(f"Unexpected result format from job search: {type(result)}")
                return f"Search completed with unexpected result format: {str(result)}"

        except Exception as e:
            logger.error(f"Error executing job-based search: {e}", exc_info=True)
            ctx = splunk_tool_registry.get_context()
            if hasattr(ctx, "error"):
                await ctx.error(f"Search failed: {str(e)}")
            return f"Error executing job-based search: {str(e)}"

    @function_tool
    async def run_oneshot_search(
        query: str, earliest_time: str = "-15m", latest_time: str = "now", max_results: int = 100
    ) -> str:
        """Execute a Splunk oneshot search query via direct tool registry for quick results."""
        logger.debug(
            f"Executing oneshot search: {query[:100]}... (time: {earliest_time} to {latest_time})"
        )

        try:
            ctx = splunk_tool_registry.get_context()

            if hasattr(ctx, "info"):
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
                max_results=max_results,
            )

            if hasattr(ctx, "info"):
                await ctx.info("✅ Oneshot search completed")

            logger.info(f"Oneshot search completed successfully, result length: {len(str(result))}")
            return str(result)

        except Exception as e:
            logger.error(f"Error executing oneshot search: {e}", exc_info=True)
            ctx = splunk_tool_registry.get_context()
            if hasattr(ctx, "error"):
                await ctx.error(f"Oneshot search failed: {str(e)}")
            return f"Error executing oneshot search: {str(e)}"

    @function_tool
    async def list_splunk_indexes() -> str:
        """List available Splunk indexes via direct tool registry."""
        logger.debug("Listing Splunk indexes via direct registry...")

        try:
            ctx = splunk_tool_registry.get_context()

            if hasattr(ctx, "info"):
                await ctx.info("📋 Retrieving available Splunk indexes...")

            tool = mcp_tool_registry.get_tool("list_indexes")
            if not tool:
                raise RuntimeError("list_indexes tool not found in registry")

            logger.debug("Calling tool registry: list_indexes")

            result = await tool.execute(ctx, random_string="dummy")

            if hasattr(ctx, "info"):
                index_count = str(result).count("index:") if "index:" in str(result) else "unknown"
                await ctx.info(f"✅ Retrieved {index_count} indexes")

            logger.info(f"Direct indexes listed successfully, result length: {len(str(result))}")
            return str(result)

        except Exception as e:
            logger.error(f"Error listing indexes via direct registry: {e}", exc_info=True)
            ctx = splunk_tool_registry.get_context()
            if hasattr(ctx, "error"):
                await ctx.error(f"Failed to list indexes: {str(e)}")
            return f"Error listing indexes via direct registry: {str(e)}"

    @function_tool
    async def get_splunk_health() -> str:
        """Check Splunk server health via direct tool registry."""
        logger.debug("Checking Splunk health via direct registry...")

        try:
            ctx = splunk_tool_registry.get_context()

            if hasattr(ctx, "info"):
                await ctx.info("🏥 Checking Splunk server health...")

            tool = mcp_tool_registry.get_tool("get_splunk_health")
            if not tool:
                raise RuntimeError("get_splunk_health tool not found in registry")

            logger.debug("Calling tool registry: get_splunk_health")

            result = await tool.execute(ctx)

            if hasattr(ctx, "info"):
                status = "healthy" if "connected" in str(result) else "issues detected"
                await ctx.info(f"✅ Health check complete - Status: {status}")

            logger.info(
                f"Direct health check completed successfully, result length: {len(str(result))}"
            )
            return str(result)

        except Exception as e:
            logger.error(f"Error checking health via direct registry: {e}", exc_info=True)
            ctx = splunk_tool_registry.get_context()
            if hasattr(ctx, "error"):
                await ctx.error(f"Health check failed: {str(e)}")
            return f"Error checking health via direct registry: {str(e)}"

    @function_tool
    async def get_current_user_info() -> str:
        """Get current authenticated user information including roles and capabilities via direct tool registry."""
        logger.debug("Getting current user information via direct registry...")

        try:
            ctx = splunk_tool_registry.get_context()

            if hasattr(ctx, "info"):
                await ctx.info("👤 Retrieving current user information...")

            tool = mcp_tool_registry.get_tool("me")
            if not tool:
                raise RuntimeError("me tool not found in registry")

            logger.debug("Calling tool registry: me")

            result = await tool.execute(ctx)

            if hasattr(ctx, "info"):
                if isinstance(result, dict) and result.get("status") == "success":
                    user_data = result.get("data", {}).get("data", {})
                    username = user_data.get("username", "unknown")
                    roles = user_data.get("roles", [])
                    await ctx.info(
                        f"✅ Retrieved user info for: {username} (roles: {', '.join(roles)})"
                    )
                else:
                    await ctx.info("✅ User information request completed")

            logger.info(
                f"Direct user info retrieved successfully, result length: {len(str(result))}"
            )
            return str(result)

        except Exception as e:
            logger.error(f"Error getting user info via direct registry: {e}", exc_info=True)
            ctx = splunk_tool_registry.get_context()
            if hasattr(ctx, "error"):
                await ctx.error(f"Failed to get user information: {str(e)}")
            return f"Error getting user info via direct registry: {str(e)}"

    # Register tools with aliases for expected names
    tools = [
        run_splunk_search,
        run_oneshot_search,
        list_splunk_indexes,
        get_splunk_health,
        get_current_user_info,
    ]

    # Register each tool with its aliases
    splunk_tool_registry.register_tool(run_splunk_search)
    splunk_tool_registry.register_tool(run_oneshot_search)
    splunk_tool_registry.register_tool(list_splunk_indexes, aliases=["list_indexes"])
    splunk_tool_registry.register_tool(get_splunk_health)
    splunk_tool_registry.register_tool(get_current_user_info, aliases=["get_current_user", "me"])

    logger.info(f"Created {len(tools)} direct registry tool wrappers for agent execution")
    logger.info(f"Available tool names: {splunk_tool_registry.get_available_tools()}")

    return tools
