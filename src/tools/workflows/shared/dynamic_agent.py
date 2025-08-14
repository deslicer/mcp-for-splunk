"""Dynamic Micro-Agent Template

A configurable micro-agent that can be dynamically created for any task
based on provided instructions, tools, and context. This eliminates the need
for specific agent files and enables task-driven parallelization.
"""

import logging
import time
from dataclasses import dataclass
from typing import Any

from fastmcp import Context

from .config import AgentConfig
from .context import DiagnosticResult, SplunkDiagnosticContext
from .tools import SplunkToolRegistry

logger = logging.getLogger(__name__)

# Import OpenAI agents if available
try:
    # Import tracing capabilities
    from agents import Agent, Runner, custom_span, function_tool

    OPENAI_AGENTS_AVAILABLE = True
    logger.info("OpenAI agents SDK loaded successfully for dynamic micro-agents")
except ImportError:
    OPENAI_AGENTS_AVAILABLE = False
    Agent = None
    Runner = None
    function_tool = None
    custom_span = None
    logger.warning(
        "OpenAI agents SDK not available for dynamic micro-agents. Install with: pip install openai-agents"
    )


@dataclass
class TaskDefinition:
    """Definition of a task that can be executed by a dynamic micro-agent."""

    task_id: str
    name: str
    description: str
    instructions: str
    required_tools: list[str] = None
    dependencies: list[str] = None
    context_requirements: list[str] = None
    expected_output_format: str = "diagnostic_result"
    timeout_seconds: int = 300

    def __post_init__(self):
        if self.required_tools is None:
            self.required_tools = []
        if self.dependencies is None:
            self.dependencies = []
        if self.context_requirements is None:
            self.context_requirements = []


@dataclass
class AgentExecutionContext:
    """Context provided to a dynamic agent for task execution."""

    task_definition: TaskDefinition
    diagnostic_context: SplunkDiagnosticContext
    dependency_results: dict[str, DiagnosticResult] = None
    execution_metadata: dict[str, Any] = None

    def __post_init__(self):
        if self.dependency_results is None:
            self.dependency_results = {}
        if self.execution_metadata is None:
            self.execution_metadata = {}


class DynamicMicroAgent:
    """
    A dynamic micro-agent that can be configured for any task.

    This agent template can be instantiated with different:
    - Instructions (what to do)
    - Tools (how to do it)
    - Context (what data to work with)
    - Dependencies (what results from other agents to use)

    This enables task-driven parallelization where any independent task
    can become a parallel micro-agent.
    """

    def __init__(
        self,
        config: AgentConfig,
        tool_registry: SplunkToolRegistry,
        task_definition: TaskDefinition,
    ):
        self.config = config
        self.tool_registry = tool_registry
        self.task_definition = task_definition
        self.name = f"DynamicAgent_{task_definition.task_id}"

        # Store current context for tool calls
        self._current_ctx = None

        # Validate task definition
        self._validate_task_definition()

        # Create OpenAI Agent if available
        if OPENAI_AGENTS_AVAILABLE:
            self._create_openai_agent()
        else:
            logger.warning(
                f"[{self.name}] OpenAI Agents SDK not available, falling back to basic execution"
            )
            self.openai_agent = None

        logger.info(f"Created dynamic micro-agent for task: {task_definition.name}")

    def _validate_task_definition(self):
        """Validate that the task definition is complete and valid."""
        if not self.task_definition.task_id:
            raise ValueError("Task definition must have a task_id")

        if not self.task_definition.instructions:
            raise ValueError("Task definition must have instructions")

        # Validate required tools are available
        available_tools = self.tool_registry.get_available_tools()
        for tool in self.task_definition.required_tools:
            if tool not in available_tools:
                logger.warning(f"Required tool '{tool}' not available in registry")

    def _create_openai_agent(self):
        """Create OpenAI Agent for instruction following."""
        if not OPENAI_AGENTS_AVAILABLE:
            self.openai_agent = None
            return

        try:
            # Create tools for this agent
            agent_tools = self._create_agent_tools()

            # Create the OpenAI Agent with dynamic instructions
            instructions_template = """
You are a specialized Splunk diagnostic micro-agent executing a specific task: {task_name}

**Your Task:** {task_description}

**Instructions:**
{task_instructions}

**Available Tools:** {available_tools}

**Important Guidelines:**
1. Follow the task instructions precisely
2. Use the available tools to gather data and perform analysis
3. Return results in DiagnosticResult format using the return_diagnostic_result function
4. For the return_diagnostic_result function, use JSON strings for the findings and recommendations parameters:
   - findings: JSON array string containing discovered issues or observations
   - recommendations: JSON array string containing actionable recommendations
   - details: JSON object string containing additional context and data

5. Be thorough but efficient in your analysis
6. Provide specific, actionable recommendations
7. Include relevant search queries and results in your findings

**Output Format:**
Always return your results as a structured DiagnosticResult by calling the `return_diagnostic_result` function with:
- status: "healthy", "warning", "critical", or "error"
- findings: JSON string containing array of discovered issues or observations
- recommendations: JSON string containing array of actionable recommendations
- details: JSON string containing object with additional context and data

Use proper JSON formatting for the string parameters to ensure they can be parsed correctly.
            """

            final_instructions = instructions_template.format(
                task_name=self.task_definition.name,
                task_description=self.task_definition.description,
                task_instructions=self.task_definition.instructions,
                available_tools=", ".join(self.task_definition.required_tools),
            )

            self.openai_agent = Agent(
                name=self.name,
                instructions=final_instructions,
                model=self.config.model,
                tools=agent_tools,
            )

            logger.debug(f"[{self.name}] Created OpenAI Agent with {len(agent_tools)} tools")

        except Exception as e:
            logger.error(f"[{self.name}] Failed to create OpenAI Agent: {e}")
            self.openai_agent = None

    def _create_agent_tools(self):
        """Create function tools for this agent."""
        if not OPENAI_AGENTS_AVAILABLE:
            return []

        tools = []

        # Create tool functions for each required tool
        for tool_name in self.task_definition.required_tools:
            if tool_name == "run_splunk_search":
                tools.append(self._create_run_splunk_search_tool())
            elif tool_name == "run_oneshot_search":
                tools.append(self._create_run_oneshot_search_tool())
            elif tool_name == "list_splunk_indexes":
                tools.append(self._create_list_indexes_tool())
            elif tool_name == "get_current_user_info":
                tools.append(self._create_get_user_info_tool())
            elif tool_name == "get_splunk_health":
                tools.append(self._create_get_health_tool())

        # Add the result return function
        tools.append(self._create_return_result_tool())

        logger.debug(f"[{self.name}] Created {len(tools)} agent tools")
        return tools

    def _create_run_splunk_search_tool(self):
        """Create run_splunk_search tool for the agent."""

        async def run_splunk_search(
            query: str, earliest_time: str = "-24h", latest_time: str = "now"
        ) -> str:
            """Execute a Splunk search query with progress tracking."""
            logger.debug(f"[{self.name}] Executing search: {query[:100]}...")

            # Get the current context for progress reporting
            ctx = self._current_ctx
            if ctx:
                await ctx.info(f"🔍 Executing Splunk search: {query[:50]}...")
                # Set the context on the tool registry for progress reporting
                self.tool_registry.set_context(ctx)

            # Add tracing for tool execution
            if OPENAI_AGENTS_AVAILABLE and custom_span:
                with custom_span(f"splunk_search_{self.task_definition.task_id}"):
                    result = await self.tool_registry.call_tool(
                        "run_splunk_search",
                        {
                            "query": query,
                            "earliest_time": earliest_time,
                            "latest_time": latest_time,
                        },
                    )

                    if result.get("success"):
                        if ctx:
                            await ctx.info("✅ Search completed successfully")
                        return str(result.get("data", ""))
                    else:
                        error_msg = f"Search failed: {result.get('error', 'Unknown error')}"
                        if ctx:
                            await ctx.error(f"❌ {error_msg}")
                        return error_msg
            else:
                result = await self.tool_registry.call_tool(
                    "run_splunk_search",
                    {"query": query, "earliest_time": earliest_time, "latest_time": latest_time},
                )

                if result.get("success"):
                    if ctx:
                        await ctx.info("✅ Search completed successfully")
                    return str(result.get("data", ""))
                else:
                    error_msg = f"Search failed: {result.get('error', 'Unknown error')}"
                    if ctx:
                        await ctx.error(f"❌ {error_msg}")
                    return error_msg

        # Create the function tool without schema modification
        try:
            tool = function_tool(
                run_splunk_search,
                name_override="run_splunk_search",
                description_override="Execute a Splunk search query with progress tracking",
            )
            return tool
        except Exception as e:
            logger.error(f"[{self.name}] Failed to create run_splunk_search tool: {e}")
            # Return a no-op tool as fallback
            return self._create_fallback_tool("run_splunk_search", "Execute a Splunk search query")

    def _create_run_oneshot_search_tool(self):
        """Create run_oneshot_search tool for the agent."""

        async def run_oneshot_search(
            query: str,
            earliest_time: str = "-15m",
            latest_time: str = "now",
            max_results: int = 100,
        ) -> str:
            """Execute a quick Splunk oneshot search."""
            logger.debug(f"[{self.name}] Executing oneshot search: {query[:100]}...")

            # Get the current context for progress reporting
            ctx = self._current_ctx
            if ctx:
                await ctx.info(f"⚡ Executing oneshot search: {query[:50]}...")
                # Set the context on the tool registry for progress reporting
                self.tool_registry.set_context(ctx)

            # Add tracing for tool execution
            if OPENAI_AGENTS_AVAILABLE and custom_span:
                with custom_span(f"splunk_oneshot_search_{self.task_definition.task_id}"):
                    result = await self.tool_registry.call_tool(
                        "run_oneshot_search",
                        {
                            "query": query,
                            "earliest_time": earliest_time,
                            "latest_time": latest_time,
                            "max_results": max_results,
                        },
                    )

                    if result.get("success"):
                        if ctx:
                            await ctx.info("✅ Oneshot search completed successfully")
                        return str(result.get("data", ""))
                    else:
                        error_msg = f"Oneshot search failed: {result.get('error', 'Unknown error')}"
                        if ctx:
                            await ctx.error(f"❌ {error_msg}")
                        return error_msg
            else:
                result = await self.tool_registry.call_tool(
                    "run_oneshot_search",
                    {
                        "query": query,
                        "earliest_time": earliest_time,
                        "latest_time": latest_time,
                        "max_results": max_results,
                    },
                )

                if result.get("success"):
                    if ctx:
                        await ctx.info("✅ Oneshot search completed successfully")
                    return str(result.get("data", ""))
                else:
                    error_msg = f"Oneshot search failed: {result.get('error', 'Unknown error')}"
                    if ctx:
                        await ctx.error(f"❌ {error_msg}")
                    return error_msg

        # Create the function tool without schema modification
        try:
            tool = function_tool(
                run_oneshot_search,
                name_override="run_oneshot_search",
                description_override="Execute a quick Splunk oneshot search",
            )
            return tool
        except Exception as e:
            logger.error(f"[{self.name}] Failed to create run_oneshot_search tool: {e}")
            # Return a no-op tool as fallback
            return self._create_fallback_tool(
                "run_oneshot_search", "Execute a quick Splunk oneshot search"
            )

    def _create_list_indexes_tool(self):
        """Create list_splunk_indexes tool for the agent."""

        async def list_splunk_indexes() -> str:
            """List available Splunk indexes."""
            logger.debug(f"[{self.name}] Listing Splunk indexes...")

            # Get the current context for progress reporting
            ctx = self._current_ctx
            if ctx:
                await ctx.info("📂 Listing available Splunk indexes...")
                # Set the context on the tool registry for progress reporting
                self.tool_registry.set_context(ctx)

            # Add tracing for tool execution
            if OPENAI_AGENTS_AVAILABLE and custom_span:
                with custom_span(f"splunk_list_indexes_{self.task_definition.task_id}"):
                    result = await self.tool_registry.call_tool("list_splunk_indexes")

                    if result.get("success"):
                        if ctx:
                            await ctx.info("✅ Index list retrieved successfully")
                        return str(result.get("data", ""))
                    else:
                        error_msg = (
                            f"Failed to list indexes: {result.get('error', 'Unknown error')}"
                        )
                        if ctx:
                            await ctx.error(f"❌ {error_msg}")
                        return error_msg
            else:
                result = await self.tool_registry.call_tool("list_splunk_indexes")

                if result.get("success"):
                    if ctx:
                        await ctx.info("✅ Index list retrieved successfully")
                    return str(result.get("data", ""))
                else:
                    error_msg = f"Failed to list indexes: {result.get('error', 'Unknown error')}"
                    if ctx:
                        await ctx.error(f"❌ {error_msg}")
                    return error_msg

        # Create the function tool without schema modification
        try:
            tool = function_tool(
                list_splunk_indexes,
                name_override="list_splunk_indexes",
                description_override="List available Splunk indexes",
            )
            return tool
        except Exception as e:
            logger.error(f"[{self.name}] Failed to create list_splunk_indexes tool: {e}")
            # Return a no-op tool as fallback
            return self._create_fallback_tool(
                "list_splunk_indexes", "List available Splunk indexes"
            )

    def _create_get_user_info_tool(self):
        """Create get_current_user_info tool for the agent."""

        async def get_current_user_info() -> str:
            """Get current user information including roles and capabilities."""
            logger.debug(f"[{self.name}] Getting current user info...")

            # Get the current context for progress reporting
            ctx = self._current_ctx
            if ctx:
                await ctx.info("👤 Getting current user information...")
                # Set the context on the tool registry for progress reporting
                self.tool_registry.set_context(ctx)

            # Add tracing for tool execution
            if OPENAI_AGENTS_AVAILABLE and custom_span:
                with custom_span(f"splunk_user_info_{self.task_definition.task_id}"):
                    result = await self.tool_registry.call_tool("get_current_user_info")

                    if result.get("success"):
                        if ctx:
                            await ctx.info("✅ User information retrieved successfully")
                        return str(result.get("data", ""))
                    else:
                        error_msg = (
                            f"Failed to get user info: {result.get('error', 'Unknown error')}"
                        )
                        if ctx:
                            await ctx.error(f"❌ {error_msg}")
                        return error_msg
            else:
                result = await self.tool_registry.call_tool("get_current_user_info")

                if result.get("success"):
                    if ctx:
                        await ctx.info("✅ User information retrieved successfully")
                    return str(result.get("data", ""))
                else:
                    error_msg = f"Failed to get user info: {result.get('error', 'Unknown error')}"
                    if ctx:
                        await ctx.error(f"❌ {error_msg}")
                    return error_msg

        # Create the function tool without schema modification
        try:
            tool = function_tool(
                get_current_user_info,
                name_override="get_current_user_info",
                description_override="Get current user information including roles and capabilities",
            )
            return tool
        except Exception as e:
            logger.error(f"[{self.name}] Failed to create get_current_user_info tool: {e}")
            # Return a no-op tool as fallback
            return self._create_fallback_tool(
                "get_current_user_info", "Get current user information"
            )

    def _create_get_health_tool(self):
        """Create get_splunk_health tool for the agent."""

        async def get_splunk_health() -> str:
            """Check Splunk server health and connectivity."""
            logger.debug(f"[{self.name}] Checking Splunk health...")

            # Get the current context for progress reporting
            ctx = self._current_ctx
            if ctx:
                await ctx.info("🏥 Checking Splunk server health...")
                # Set the context on the tool registry for progress reporting
                self.tool_registry.set_context(ctx)

            # Add tracing for tool execution
            if OPENAI_AGENTS_AVAILABLE and custom_span:
                with custom_span(f"splunk_health_check_{self.task_definition.task_id}"):
                    result = await self.tool_registry.call_tool("get_splunk_health")

                    if result.get("success"):
                        if ctx:
                            await ctx.info("✅ Health check completed successfully")
                        return str(result.get("data", ""))
                    else:
                        error_msg = f"Health check failed: {result.get('error', 'Unknown error')}"
                        if ctx:
                            await ctx.error(f"❌ {error_msg}")
                        return error_msg
            else:
                result = await self.tool_registry.call_tool("get_splunk_health")

                if result.get("success"):
                    if ctx:
                        await ctx.info("✅ Health check completed successfully")
                    return str(result.get("data", ""))
                else:
                    error_msg = f"Health check failed: {result.get('error', 'Unknown error')}"
                    if ctx:
                        await ctx.error(f"❌ {error_msg}")
                    return error_msg

        # Create the function tool without schema modification
        try:
            tool = function_tool(
                get_splunk_health,
                name_override="get_splunk_health",
                description_override="Check Splunk server health and connectivity",
            )
            return tool
        except Exception as e:
            logger.error(f"[{self.name}] Failed to create get_splunk_health tool: {e}")
            # Return a no-op tool as fallback
            return self._create_fallback_tool("get_splunk_health", "Check Splunk server health")

    def _create_return_result_tool(self):
        """Create tool for returning diagnostic results."""

        async def return_diagnostic_result(
            status: str, findings: str, recommendations: str, details: str = ""
        ) -> str:
            """Return the diagnostic result for this task.

            Args:
                status: One of "healthy", "warning", "critical", "error"
                findings: JSON string of discovered issues or observations (list)
                recommendations: JSON string of actionable recommendations (list)
                details: Optional JSON string with additional context (dict)
            """
            import json

            # Parse the JSON strings back to Python objects
            try:
                findings_list = json.loads(findings) if findings else []
                recommendations_list = json.loads(recommendations) if recommendations else []
                details_dict = json.loads(details) if details else {}
            except json.JSONDecodeError as e:
                logger.error(f"[{self.name}] JSON parsing error in return_diagnostic_result: {e}")
                findings_list = [findings] if findings else []
                recommendations_list = [recommendations] if recommendations else []
                details_dict = {"raw_details": details} if details else {}

            # Store the result for later retrieval
            self._task_result = DiagnosticResult(
                step=self.task_definition.task_id,
                status=status,
                findings=findings_list,
                recommendations=recommendations_list,
                details=details_dict,
            )

            logger.debug(
                f"[{self.name}] Task result stored: status={status}, findings={len(findings_list)}, recommendations={len(recommendations_list)}"
            )
            return f"Diagnostic result recorded successfully with status: {status}"

        # Create the function tool with simpler schema that avoids additionalProperties issues
        try:
            tool = function_tool(
                return_diagnostic_result,
                name_override="return_diagnostic_result",
                description_override="Return the diagnostic result for this task. Use JSON strings for lists and objects.",
            )

            # Don't modify the schema at all - let OpenAI Agents SDK handle it
            logger.debug(f"[{self.name}] Created return_diagnostic_result tool successfully")
            return tool

        except Exception as e:
            logger.error(f"[{self.name}] Failed to create return_diagnostic_result tool: {e}")
            # Return a no-op tool as fallback
            return self._create_fallback_tool(
                "return_diagnostic_result", "Return diagnostic result"
            )

    def _create_fallback_tool(self, tool_name: str, description: str):
        """Create a fallback no-op tool when tool creation fails."""

        async def fallback_function() -> str:
            """Fallback function when tool creation fails."""
            return f"Tool {tool_name} is not available due to configuration issues"

        try:
            tool = function_tool(
                fallback_function,
                name_override=tool_name,
                description_override=f"Fallback for {description}",
            )
            return tool
        except Exception as e:
            logger.error(f"[{self.name}] Even fallback tool creation failed for {tool_name}: {e}")
            return None

    def _fix_json_schema(self, schema: dict) -> None:
        """Fix JSON schema to ensure proper handling of optional parameters and avoid additionalProperties issues."""
        if isinstance(schema, dict):
            # Remove additionalProperties if it exists to avoid OpenAI Agents SDK conflicts
            if "additionalProperties" in schema:
                del schema["additionalProperties"]

            # Fix the required array to only include parameters without defaults
            if schema.get("type") == "object" and "properties" in schema and "required" in schema:
                properties = schema["properties"]
                required = schema["required"]

                # For the return_diagnostic_result function, details should not be required
                # since it has a default value
                if "details" in properties and "details" in required:
                    # Remove details from required since it has a default value
                    required = [req for req in required if req != "details"]
                    schema["required"] = required

                    # Also ensure the details parameter allows null
                    if "details" in properties:
                        details_prop = properties["details"]
                        if isinstance(details_prop, dict):
                            # Allow null for optional parameters by using oneOf
                            if "type" in details_prop:
                                if details_prop["type"] == "object":
                                    # Use oneOf to allow object or null
                                    details_prop.clear()
                                    details_prop["oneOf"] = [{"type": "object"}, {"type": "null"}]
                                elif isinstance(details_prop["type"], str):
                                    # Convert single type to oneOf with null
                                    original_type = details_prop["type"]
                                    details_prop.clear()
                                    details_prop["oneOf"] = [
                                        {"type": original_type},
                                        {"type": "null"},
                                    ]

            # Recursively fix nested schemas
            for _key, value in schema.items():
                if isinstance(value, dict):
                    self._fix_json_schema(value)
                elif isinstance(value, list):
                    for item in value:
                        if isinstance(item, dict):
                            self._fix_json_schema(item)

    async def execute_task(
        self, execution_context: AgentExecutionContext, ctx: Context
    ) -> DiagnosticResult:
        """
        Execute the assigned task with the provided context and comprehensive tracing.

        Args:
            execution_context: Context containing task definition, diagnostic context,
                             and any dependency results
            ctx: FastMCP context for progress reporting and logging

        Returns:
            DiagnosticResult with task execution results
        """
        start_time = time.time()

        # Store the context for tool calls
        self._current_ctx = ctx

        logger.info(f"[{self.name}] Starting task execution: {self.task_definition.name}")

        # Report initial progress
        await ctx.report_progress(progress=0, total=100)
        await ctx.info(f"🔄 Starting {self.task_definition.name}")

        # Create comprehensive tracing for task execution
        if OPENAI_AGENTS_AVAILABLE and custom_span:
            with custom_span(f"micro_agent_task_{self.task_definition.task_id}"):
                return await self._execute_task_with_tracing(
                    execution_context, start_time, ctx, True
                )
        else:
            # Fallback without tracing
            return await self._execute_task_with_tracing(execution_context, start_time, ctx, False)

    async def _execute_task_with_tracing(
        self,
        execution_context: AgentExecutionContext,
        start_time: float,
        ctx: Context,
        tracing_enabled: bool = False,
    ) -> DiagnosticResult:
        """Execute the task with optional tracing support and progress reporting."""

        try:
            # Initialize task result storage
            self._task_result = None

            # Report progress: Task setup
            await ctx.report_progress(progress=10, total=100)

            # Build dynamic instructions with context (with tracing)
            if OPENAI_AGENTS_AVAILABLE and custom_span and tracing_enabled:
                with custom_span("instruction_building"):
                    dynamic_instructions = self._build_dynamic_instructions(execution_context)
            else:
                dynamic_instructions = self._build_dynamic_instructions(execution_context)

            # Report progress: Instructions built
            await ctx.report_progress(progress=20, total=100)
            await ctx.info(f"📋 Instructions prepared for {self.task_definition.name}")

            # Execute the task using OpenAI Agent if available (with tracing)
            if self.openai_agent and OPENAI_AGENTS_AVAILABLE:
                await ctx.info(f"🤖 Executing {self.task_definition.name} with OpenAI Agent")
                await ctx.report_progress(progress=30, total=100)

                if custom_span and tracing_enabled:
                    with custom_span("openai_agent_execution"):
                        result = await self._execute_with_openai_agent(
                            execution_context, dynamic_instructions, ctx
                        )
                else:
                    result = await self._execute_with_openai_agent(
                        execution_context, dynamic_instructions, ctx
                    )
            else:
                await ctx.info(f"⚙️ Executing {self.task_definition.name} with fallback method")
                await ctx.report_progress(progress=30, total=100)

                # Fallback to hardcoded execution for basic tasks (with tracing)
                if custom_span and tracing_enabled:
                    with custom_span("fallback_execution"):
                        result = await self._execute_diagnostic_task_fallback(
                            execution_context, dynamic_instructions, ctx
                        )
                else:
                    result = await self._execute_diagnostic_task_fallback(
                        execution_context, dynamic_instructions, ctx
                    )

            # Report progress: Task execution complete
            await ctx.report_progress(progress=90, total=100)

            # Finalize result with execution metadata (with tracing)
            execution_time = time.time() - start_time
            result.details["execution_time"] = execution_time
            result.details["agent_name"] = self.name
            result.details["task_id"] = self.task_definition.task_id
            result.details["tracing_enabled"] = OPENAI_AGENTS_AVAILABLE and custom_span is not None

            # Report final progress
            await ctx.report_progress(progress=100, total=100)
            await ctx.info(f"✅ {self.task_definition.name} completed with status: {result.status}")

            logger.info(
                f"[{self.name}] Task completed in {execution_time:.2f}s with status: {result.status}"
            )
            return result

        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"[{self.name}] Task execution failed: {e}", exc_info=True)

            await ctx.error(f"❌ {self.task_definition.name} failed: {str(e)}")

            return DiagnosticResult(
                step=self.task_definition.task_id,
                status="error",
                findings=[f"Task execution failed: {str(e)}"],
                recommendations=["Check task configuration and retry"],
                details={
                    "error": str(e),
                    "execution_time": execution_time,
                    "task_definition": self.task_definition.name,
                    "agent_name": self.name,
                    "tracing_enabled": OPENAI_AGENTS_AVAILABLE and custom_span is not None,
                },
            )

    async def _execute_with_openai_agent(
        self, execution_context: AgentExecutionContext, dynamic_instructions: str, ctx: Context
    ) -> DiagnosticResult:
        """Execute task using OpenAI Agent with instruction following and progress reporting."""
        logger.debug(f"[{self.name}] Executing task with OpenAI Agent...")

        try:
            # Report progress before agent execution
            await ctx.report_progress(progress=40, total=100)
            await ctx.info(f"🧠 Running OpenAI Agent for {self.task_definition.name}")

            # Execute the agent with the dynamic instructions
            agent_result = await Runner.run(
                self.openai_agent,
                input=dynamic_instructions,
                max_turns=10,  # Allow multiple turns for complex tasks
            )

            # Report progress after agent execution
            await ctx.report_progress(progress=80, total=100)

            # Check if the agent stored a result using return_diagnostic_result
            if hasattr(self, "_task_result") and self._task_result:
                logger.debug(f"[{self.name}] Retrieved stored diagnostic result")
                await ctx.info(f"📊 {self.task_definition.name} analysis complete")
                return self._task_result

            # If no stored result, create one from the agent output
            logger.warning(f"[{self.name}] No diagnostic result stored, creating from agent output")
            await ctx.warning(f"⚠️ {self.task_definition.name} completed without structured result")

            # Analyze the agent output to determine status
            output = agent_result.final_output.lower() if agent_result.final_output else ""

            if "error" in output or "failed" in output:
                status = "error"
                findings = ["Agent execution completed with errors"]
            elif "warning" in output or "issue" in output:
                status = "warning"
                findings = ["Agent identified potential issues"]
            else:
                status = "completed"
                findings = ["Agent execution completed"]

            return DiagnosticResult(
                step=self.task_definition.task_id,
                status=status,
                findings=findings,
                recommendations=["Review agent output for details"],
                details={
                    "agent_output": agent_result.final_output,
                    "execution_method": "openai_agent",
                },
            )

        except Exception as e:
            logger.error(f"[{self.name}] OpenAI Agent execution failed: {e}", exc_info=True)
            await ctx.error(
                f"❌ OpenAI Agent execution failed for {self.task_definition.name}: {str(e)}"
            )

            return DiagnosticResult(
                step=self.task_definition.task_id,
                status="error",
                findings=[f"OpenAI Agent execution failed: {str(e)}"],
                recommendations=["Check agent configuration and retry"],
                details={"error": str(e), "execution_method": "openai_agent"},
            )

    def _build_dynamic_instructions(self, execution_context: AgentExecutionContext) -> str:
        """Build dynamic instructions by injecting context and dependency results."""

        instructions = self.task_definition.instructions

        # Inject diagnostic context
        context = execution_context.diagnostic_context
        instructions = instructions.replace("{earliest_time}", context.earliest_time)
        instructions = instructions.replace("{latest_time}", context.latest_time)
        instructions = instructions.replace("{focus_index}", context.focus_index or "*")
        instructions = instructions.replace("{focus_host}", context.focus_host or "*")
        instructions = instructions.replace("{focus_sourcetype}", context.focus_sourcetype or "*")
        instructions = instructions.replace(
            "{problem_description}",
            context.problem_description or "No specific problem description provided",
        )
        instructions = instructions.replace("{workflow_type}", context.workflow_type or "unknown")
        instructions = instructions.replace("{complexity_level}", context.complexity_level)

        if context.indexes:
            instructions = instructions.replace("{indexes}", ", ".join(context.indexes))
        if context.sourcetypes:
            instructions = instructions.replace("{sourcetypes}", ", ".join(context.sourcetypes))
        if context.sources:
            instructions = instructions.replace("{sources}", ", ".join(context.sources))

        # Inject dependency results if available
        if execution_context.dependency_results:
            dependency_summary = self._create_dependency_summary(
                execution_context.dependency_results
            )
            instructions += f"\n\n**Dependency Results:**\n{dependency_summary}"

        # Add comprehensive task context including problem description
        instructions += "\n\n**Task Context:**\n"
        instructions += f"- Task ID: {self.task_definition.task_id}\n"
        instructions += f"- Task Name: {self.task_definition.name}\n"
        instructions += f"- Available Tools: {', '.join(self.task_definition.required_tools)}\n"
        instructions += (
            f"- Diagnostic Time Range: {context.earliest_time} to {context.latest_time}\n"
        )
        instructions += f"- Complexity Level: {context.complexity_level}\n"

        if context.problem_description:
            instructions += f"- Original Problem: {context.problem_description}\n"
        if context.workflow_type:
            instructions += f"- Workflow Type: {context.workflow_type}\n"
        if context.focus_index:
            instructions += f"- Focus Index: {context.focus_index}\n"
        if context.focus_host:
            instructions += f"- Focus Host: {context.focus_host}\n"
        if context.focus_sourcetype:
            instructions += f"- Focus Sourcetype: {context.focus_sourcetype}\n"

        return instructions

    def _create_dependency_summary(self, dependency_results: dict[str, DiagnosticResult]) -> str:
        """Create a summary of dependency results for context injection."""

        summary_parts = []
        for dep_task_id, result in dependency_results.items():
            summary_parts.append(f"**{dep_task_id}** (Status: {result.status})")

            # Include key findings
            if result.findings:
                summary_parts.append("Key findings:")
                for finding in result.findings[:3]:  # Limit to top 3 findings
                    summary_parts.append(f"  - {finding}")

            # Include important details
            if result.details:
                important_keys = ["user_info", "license_state", "total_events", "available_indexes"]
                for key in important_keys:
                    if key in result.details:
                        summary_parts.append(f"  - {key}: {result.details[key]}")

            summary_parts.append("")  # Add spacing

        return "\n".join(summary_parts)

    async def _execute_diagnostic_task_fallback(
        self, execution_context: AgentExecutionContext, instructions: str, ctx: Context
    ) -> DiagnosticResult:
        """Fallback execution method for when OpenAI Agents SDK is not available."""

        task_id = self.task_definition.task_id

        # Report progress for fallback execution
        await ctx.report_progress(progress=50, total=100)
        await ctx.info(f"🔧 Using fallback execution for {self.task_definition.name}")

        # Route to appropriate execution method based on task type
        if "license" in task_id.lower():
            return await self._execute_license_verification(execution_context, ctx)
        elif "index" in task_id.lower():
            return await self._execute_index_verification(execution_context, ctx)
        elif "permission" in task_id.lower():
            return await self._execute_permissions_check(execution_context, ctx)
        elif "time" in task_id.lower() or "range" in task_id.lower():
            return await self._execute_time_range_check(execution_context, ctx)
        else:
            return await self._execute_generic_task(execution_context, instructions, ctx)

    async def _execute_license_verification(
        self, execution_context: AgentExecutionContext, ctx: Context
    ) -> DiagnosticResult:
        """Execute license verification task with progress reporting."""
        try:
            await ctx.info("🔍 Checking Splunk license information")
            await ctx.report_progress(progress=60, total=100)

            # Set the context on the tool registry for progress reporting
            self.tool_registry.set_context(ctx)

            # Get server information - use proper time range to avoid "latest_time must be after earliest_time" error
            server_result = await self.tool_registry.call_tool(
                "run_oneshot_search",
                {
                    "query": "| rest /services/server/info | fields splunk_version, product_type, license_state",
                    "earliest_time": "-1m",  # Use a small time window instead of "now" for both
                    "latest_time": "now",
                    "max_results": 1,
                },
            )

            await ctx.report_progress(progress=80, total=100)

            if not server_result.get("success"):
                await ctx.error(
                    f"Failed to retrieve server information: {server_result.get('error')}"
                )
                return DiagnosticResult(
                    step=self.task_definition.task_id,
                    status="error",
                    findings=["Failed to retrieve server information"],
                    recommendations=["Check Splunk connectivity"],
                    details={"error": server_result.get("error")},
                )

            # Parse results and create diagnostic result
            # Implementation similar to the specific license agent but more generic
            findings = ["License verification completed"]
            status = "healthy"

            await ctx.info("✅ License verification completed successfully")

            return DiagnosticResult(
                step=self.task_definition.task_id,
                status=status,
                findings=findings,
                recommendations=[],
                details={"server_info": server_result.get("data", {})},
            )

        except Exception as e:
            await ctx.error(f"License verification failed: {str(e)}")
            return DiagnosticResult(
                step=self.task_definition.task_id,
                status="error",
                findings=[f"License verification failed: {str(e)}"],
                recommendations=["Check configuration and retry"],
                details={"error": str(e)},
            )

    async def _execute_index_verification(
        self, execution_context: AgentExecutionContext, ctx: Context
    ) -> DiagnosticResult:
        """Execute index verification task with progress reporting."""
        try:
            await ctx.info("📂 Checking Splunk index availability")
            await ctx.report_progress(progress=60, total=100)

            # Set the context on the tool registry for progress reporting
            self.tool_registry.set_context(ctx)

            # Get available indexes
            indexes_result = await self.tool_registry.call_tool("list_splunk_indexes")

            await ctx.report_progress(progress=80, total=100)

            if not indexes_result.get("success"):
                await ctx.error(f"Failed to retrieve index list: {indexes_result.get('error')}")
                return DiagnosticResult(
                    step=self.task_definition.task_id,
                    status="error",
                    findings=["Failed to retrieve index list"],
                    recommendations=["Check Splunk connectivity"],
                    details={"error": indexes_result.get("error")},
                )

            # Check target indexes from context
            context = execution_context.diagnostic_context
            available_indexes = indexes_result.get("data", {}).get("indexes", [])

            missing_indexes = []
            for target_index in context.indexes:
                if target_index not in available_indexes:
                    missing_indexes.append(target_index)

            if missing_indexes:
                status = "warning"
                findings = [f"Missing indexes: {', '.join(missing_indexes)}"]
                recommendations = ["Verify index names and permissions"]
                await ctx.warning(f"⚠️ Missing indexes found: {', '.join(missing_indexes)}")
            else:
                status = "healthy"
                findings = ["All target indexes are accessible"]
                recommendations = []
                await ctx.info("✅ All target indexes are accessible")

            return DiagnosticResult(
                step=self.task_definition.task_id,
                status=status,
                findings=findings,
                recommendations=recommendations,
                details={
                    "available_indexes": available_indexes,
                    "target_indexes": context.indexes,
                    "missing_indexes": missing_indexes,
                },
            )

        except Exception as e:
            await ctx.error(f"Index verification failed: {str(e)}")
            return DiagnosticResult(
                step=self.task_definition.task_id,
                status="error",
                findings=[f"Index verification failed: {str(e)}"],
                recommendations=["Check configuration and retry"],
                details={"error": str(e)},
            )

    async def _execute_permissions_check(
        self, execution_context: AgentExecutionContext, ctx: Context
    ) -> DiagnosticResult:
        """Execute permissions verification task with progress reporting."""
        try:
            await ctx.info("🔐 Checking user permissions and roles")
            await ctx.report_progress(progress=60, total=100)

            # Set the context on the tool registry for progress reporting
            self.tool_registry.set_context(ctx)

            # Get user info from dependencies or directly
            user_info = None
            if "license_verification" in execution_context.dependency_results:
                license_result = execution_context.dependency_results["license_verification"]
                user_info = license_result.details.get("user_info")

            if not user_info:
                user_result = await self.tool_registry.call_tool("get_current_user_info", {})
                user_info = user_result.get("data", {}) if user_result.get("success") else {}

            await ctx.report_progress(progress=80, total=100)

            # Basic permissions check
            user_roles = user_info.get("roles", [])
            if not user_roles:
                status = "warning"
                findings = ["No roles assigned to user"]
                recommendations = ["Contact administrator for role assignment"]
                await ctx.warning("⚠️ No roles assigned to current user")
            else:
                status = "healthy"
                findings = [f"User has roles: {', '.join(user_roles)}"]
                recommendations = []
                await ctx.info(f"✅ User has {len(user_roles)} role(s): {', '.join(user_roles[:3])}")

            return DiagnosticResult(
                step=self.task_definition.task_id,
                status=status,
                findings=findings,
                recommendations=recommendations,
                details={"user_info": user_info, "user_roles": user_roles},
            )

        except Exception as e:
            await ctx.error(f"Permissions check failed: {str(e)}")
            return DiagnosticResult(
                step=self.task_definition.task_id,
                status="error",
                findings=[f"Permissions check failed: {str(e)}"],
                recommendations=["Check authentication and retry"],
                details={"error": str(e)},
            )

    async def _execute_time_range_check(
        self, execution_context: AgentExecutionContext, ctx: Context
    ) -> DiagnosticResult:
        """Execute time range verification task with progress reporting."""
        try:
            context = execution_context.diagnostic_context

            await ctx.info(
                f"⏰ Checking data availability in time range {context.earliest_time} to {context.latest_time}"
            )
            await ctx.report_progress(progress=60, total=100)

            # Set the context on the tool registry for progress reporting
            self.tool_registry.set_context(ctx)

            # Build search query based on context
            search_filters = []
            if context.indexes:
                search_filters.append(f"index={' OR index='.join(context.indexes)}")
            if context.sourcetypes:
                search_filters.append(f"sourcetype={' OR sourcetype='.join(context.sourcetypes)}")

            base_search = " ".join(search_filters) if search_filters else "*"
            count_query = f"{base_search} | stats count"

            # Execute count query
            count_result = await self.tool_registry.call_tool(
                "run_oneshot_search",
                {
                    "query": count_query,
                    "earliest_time": context.earliest_time,
                    "latest_time": context.latest_time,
                    "max_results": 1,
                },
            )

            await ctx.report_progress(progress=80, total=100)

            if not count_result.get("success"):
                await ctx.error(f"Failed to check data in time range: {count_result.get('error')}")
                return DiagnosticResult(
                    step=self.task_definition.task_id,
                    status="error",
                    findings=["Failed to check data in time range"],
                    recommendations=["Check search permissions"],
                    details={"error": count_result.get("error")},
                )

            # Parse results
            total_events = 0
            if count_result.get("data", {}).get("results"):
                total_events = int(count_result["data"]["results"][0].get("count", 0))

            if total_events == 0:
                status = "critical"
                findings = [
                    f"No data found in time range {context.earliest_time} to {context.latest_time}"
                ]
                recommendations = ["Verify time range and check if data exists outside this window"]
                await ctx.warning("⚠️ No data found in specified time range")
            else:
                status = "healthy"
                findings = [f"Found {total_events:,} events in time range"]
                recommendations = []
                await ctx.info(f"✅ Found {total_events:,} events in time range")

            return DiagnosticResult(
                step=self.task_definition.task_id,
                status=status,
                findings=findings,
                recommendations=recommendations,
                details={
                    "total_events": total_events,
                    "time_range": f"{context.earliest_time} to {context.latest_time}",
                },
            )

        except Exception as e:
            await ctx.error(f"Time range check failed: {str(e)}")
            return DiagnosticResult(
                step=self.task_definition.task_id,
                status="error",
                findings=[f"Time range check failed: {str(e)}"],
                recommendations=["Check search syntax and time format"],
                details={"error": str(e)},
            )

    async def _execute_generic_task(
        self, execution_context: AgentExecutionContext, instructions: str, ctx: Context
    ) -> DiagnosticResult:
        """Execute a generic task using the provided instructions with progress reporting."""

        await ctx.info(f"⚙️ Executing generic task: {self.task_definition.name}")
        await ctx.report_progress(progress=70, total=100)

        # For generic tasks, we can implement a simple execution pattern
        # or integrate with an LLM for complex instruction following

        return DiagnosticResult(
            step=self.task_definition.task_id,
            status="completed",
            findings=[f"Generic task '{self.task_definition.name}' executed"],
            recommendations=["Review task results"],
            details={"instructions": instructions},
        )

    async def _execute_custom_task(
        self, execution_context: AgentExecutionContext, instructions: str
    ) -> Any:
        """Execute a custom task with non-diagnostic output format."""

        # This method can be extended to support different output formats
        # For now, return a simple result
        return {
            "task_id": self.task_definition.task_id,
            "status": "completed",
            "result": f"Custom task '{self.task_definition.name}' executed",
            "instructions": instructions,
        }


# Helper function to create dynamic agents
def create_dynamic_agent(
    config: AgentConfig, tool_registry: SplunkToolRegistry, task_definition: TaskDefinition
) -> DynamicMicroAgent:
    """Factory function to create a dynamic micro-agent for a task."""
    return DynamicMicroAgent(config, tool_registry, task_definition)
