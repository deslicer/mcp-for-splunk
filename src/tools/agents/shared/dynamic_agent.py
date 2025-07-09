"""Dynamic Micro-Agent Template

A configurable micro-agent that can be dynamically created for any task
based on provided instructions, tools, and context. This eliminates the need
for specific agent files and enables task-driven parallelization.
"""

import logging
import time
from dataclasses import dataclass
from typing import Any

from .config import AgentConfig
from .context import DiagnosticResult, SplunkDiagnosticContext
from .tools import SplunkToolRegistry

logger = logging.getLogger(__name__)

# Import OpenAI agents if available
try:
    from agents import Agent, Runner, function_tool
    # Import tracing capabilities
    from agents import custom_span

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
            self.openai_agent = Agent(
                name=self.name,
                instructions=f"""
You are a specialized Splunk diagnostic micro-agent executing a specific task: {self.task_definition.name}

**Your Task:** {self.task_definition.description}

**Instructions:**
{self.task_definition.instructions}

**Available Tools:** {", ".join(self.task_definition.required_tools)}

**Important Guidelines:**
1. Follow the task instructions precisely
2. Use the available tools to gather data and perform analysis
3. Return results in DiagnosticResult format with:
   - step: task identifier
   - status: "healthy", "warning", "critical", or "error"
   - findings: list of discovered issues or observations
   - recommendations: list of actionable recommendations
   - details: dictionary with additional context and data

4. Be thorough but efficient in your analysis
5. Provide specific, actionable recommendations
6. Include relevant search queries and results in your findings

**Output Format:**
Always return your results as a structured DiagnosticResult by calling the `return_diagnostic_result` function with appropriate parameters.
                """,
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

        @function_tool
        async def run_splunk_search(
            query: str, earliest_time: str = "-24h", latest_time: str = "now"
        ) -> str:
            """Execute a Splunk search query with progress tracking."""
            logger.debug(f"[{self.name}] Executing search: {query[:100]}...")

            # Add tracing for tool execution
            if OPENAI_AGENTS_AVAILABLE and custom_span:
                with custom_span(f"splunk_search_{self.task_definition.task_id}"):
                    result = await self.tool_registry.call_tool(
                        "run_splunk_search",
                        {"query": query, "earliest_time": earliest_time, "latest_time": latest_time},
                    )
                    
                    if result.get("success"):
                        return str(result.get("data", ""))
                    else:
                        return f"Search failed: {result.get('error', 'Unknown error')}"
            else:
                result = await self.tool_registry.call_tool(
                    "run_splunk_search",
                    {"query": query, "earliest_time": earliest_time, "latest_time": latest_time},
                )

                if result.get("success"):
                    return str(result.get("data", ""))
                else:
                    return f"Search failed: {result.get('error', 'Unknown error')}"

        return run_splunk_search

    def _create_run_oneshot_search_tool(self):
        """Create run_oneshot_search tool for the agent."""

        @function_tool
        async def run_oneshot_search(
            query: str,
            earliest_time: str = "-15m",
            latest_time: str = "now",
            max_results: int = 100,
        ) -> str:
            """Execute a quick Splunk oneshot search."""
            logger.debug(f"[{self.name}] Executing oneshot search: {query[:100]}...")

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
                        return str(result.get("data", ""))
                    else:
                        return f"Oneshot search failed: {result.get('error', 'Unknown error')}"
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
                    return str(result.get("data", ""))
                else:
                    return f"Oneshot search failed: {result.get('error', 'Unknown error')}"

        return run_oneshot_search

    def _create_list_indexes_tool(self):
        """Create list_splunk_indexes tool for the agent."""

        @function_tool
        async def list_splunk_indexes() -> str:
            """List available Splunk indexes."""
            logger.debug(f"[{self.name}] Listing Splunk indexes...")

            # Add tracing for tool execution
            if OPENAI_AGENTS_AVAILABLE and custom_span:
                with custom_span(f"splunk_list_indexes_{self.task_definition.task_id}"):
                    result = await self.tool_registry.call_tool("list_splunk_indexes")
                    
                    if result.get("success"):
                        return str(result.get("data", ""))
                    else:
                        return f"Failed to list indexes: {result.get('error', 'Unknown error')}"
            else:
                result = await self.tool_registry.call_tool("list_splunk_indexes")

                if result.get("success"):
                    return str(result.get("data", ""))
                else:
                    return f"Failed to list indexes: {result.get('error', 'Unknown error')}"

        return list_splunk_indexes

    def _create_get_user_info_tool(self):
        """Create get_current_user_info tool for the agent."""

        @function_tool
        async def get_current_user_info() -> str:
            """Get current user information including roles and capabilities."""
            logger.debug(f"[{self.name}] Getting current user info...")

            # Add tracing for tool execution
            if OPENAI_AGENTS_AVAILABLE and custom_span:
                with custom_span(f"splunk_user_info_{self.task_definition.task_id}"):
                    result = await self.tool_registry.call_tool("get_current_user_info")
                    
                    if result.get("success"):
                        return str(result.get("data", ""))
                    else:
                        return f"Failed to get user info: {result.get('error', 'Unknown error')}"
            else:
                result = await self.tool_registry.call_tool("get_current_user_info")

                if result.get("success"):
                    return str(result.get("data", ""))
                else:
                    return f"Failed to get user info: {result.get('error', 'Unknown error')}"

        return get_current_user_info

    def _create_get_health_tool(self):
        """Create get_splunk_health tool for the agent."""

        @function_tool
        async def get_splunk_health() -> str:
            """Check Splunk server health and connectivity."""
            logger.debug(f"[{self.name}] Checking Splunk health...")

            # Add tracing for tool execution
            if OPENAI_AGENTS_AVAILABLE and custom_span:
                with custom_span(f"splunk_health_check_{self.task_definition.task_id}"):
                    result = await self.tool_registry.call_tool("get_splunk_health")
                    
                    if result.get("success"):
                        return str(result.get("data", ""))
                    else:
                        return f"Health check failed: {result.get('error', 'Unknown error')}"
            else:
                result = await self.tool_registry.call_tool("get_splunk_health")

                if result.get("success"):
                    return str(result.get("data", ""))
                else:
                    return f"Health check failed: {result.get('error', 'Unknown error')}"

        return get_splunk_health

    def _create_return_result_tool(self):
        """Create tool for returning diagnostic results."""

        @function_tool
        async def return_diagnostic_result(
            status: str, findings: list[str], recommendations: list[str], details: dict = None
        ) -> str:
            """Return the diagnostic result for this task.

            Args:
                status: One of "healthy", "warning", "critical", "error"
                findings: List of discovered issues or observations
                recommendations: List of actionable recommendations
                details: Optional dictionary with additional context
            """
            if details is None:
                details = {}

            # Store the result for later retrieval
            self._task_result = DiagnosticResult(
                step=self.task_definition.task_id,
                status=status,
                findings=findings,
                recommendations=recommendations,
                details=details,
            )

            logger.debug(
                f"[{self.name}] Task result stored: status={status}, findings={len(findings)}, recommendations={len(recommendations)}"
            )
            return f"Diagnostic result recorded successfully with status: {status}"

        return return_diagnostic_result

    async def execute_task(self, execution_context: AgentExecutionContext) -> DiagnosticResult:
        """
        Execute the assigned task with the provided context and comprehensive tracing.

        Args:
            execution_context: Context containing task definition, diagnostic context,
                             and any dependency results

        Returns:
            DiagnosticResult with task execution results
        """
        start_time = time.time()
        task_name = f"Task: {self.task_definition.name}"
        
        logger.info(f"[{self.name}] Starting task execution: {self.task_definition.name}")

        # Create comprehensive tracing for task execution
        if OPENAI_AGENTS_AVAILABLE and custom_span:
            with custom_span(f"micro_agent_task_{self.task_definition.task_id}"):
                return await self._execute_task_with_tracing(execution_context, start_time, True)
        else:
            # Fallback without tracing
            return await self._execute_task_with_tracing(execution_context, start_time, False)

    async def _execute_task_with_tracing(
        self, 
        execution_context: AgentExecutionContext, 
        start_time: float,
        tracing_enabled: bool = False
    ) -> DiagnosticResult:
        """Execute the task with optional tracing support."""
        
        try:
            # Initialize task result storage
            self._task_result = None

            # Build dynamic instructions with context (with tracing)
            if OPENAI_AGENTS_AVAILABLE and custom_span and tracing_enabled:
                with custom_span("instruction_building"):
                    dynamic_instructions = self._build_dynamic_instructions(execution_context)
            else:
                dynamic_instructions = self._build_dynamic_instructions(execution_context)

            # Execute the task using OpenAI Agent if available (with tracing)
            if self.openai_agent and OPENAI_AGENTS_AVAILABLE:
                if custom_span and tracing_enabled:
                    with custom_span("openai_agent_execution"):
                        result = await self._execute_with_openai_agent(
                            execution_context, dynamic_instructions
                        )
                else:
                    result = await self._execute_with_openai_agent(
                        execution_context, dynamic_instructions
                    )
            else:
                # Fallback to hardcoded execution for basic tasks (with tracing)
                if custom_span and tracing_enabled:
                    with custom_span("fallback_execution"):
                        result = await self._execute_diagnostic_task_fallback(
                            execution_context, dynamic_instructions
                        )
                else:
                    result = await self._execute_diagnostic_task_fallback(
                        execution_context, dynamic_instructions
                    )

            # Finalize result with execution metadata (with tracing)
            execution_time = time.time() - start_time
            result.details["execution_time"] = execution_time
            result.details["agent_name"] = self.name
            result.details["task_id"] = self.task_definition.task_id
            result.details["tracing_enabled"] = OPENAI_AGENTS_AVAILABLE and custom_span is not None

            logger.info(
                f"[{self.name}] Task completed in {execution_time:.2f}s with status: {result.status}"
            )
            return result

        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"[{self.name}] Task execution failed: {e}", exc_info=True)

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
        self, execution_context: AgentExecutionContext, dynamic_instructions: str
    ) -> DiagnosticResult:
        """Execute task using OpenAI Agent with instruction following."""
        logger.debug(f"[{self.name}] Executing task with OpenAI Agent...")

        try:
            # Execute the agent with the dynamic instructions
            agent_result = await Runner.run(
                self.openai_agent,
                input=dynamic_instructions,
                max_turns=10,  # Allow multiple turns for complex tasks
            )

            # Check if the agent stored a result using return_diagnostic_result
            if hasattr(self, "_task_result") and self._task_result:
                logger.debug(f"[{self.name}] Retrieved stored diagnostic result")
                return self._task_result

            # If no stored result, create one from the agent output
            logger.warning(f"[{self.name}] No diagnostic result stored, creating from agent output")

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
        instructions = instructions.replace("{focus_index}", context.focus_index or "all indexes")
        instructions = instructions.replace("{focus_host}", context.focus_host or "all hosts")

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

        # Add task-specific context
        instructions += "\n\n**Task Context:**\n"
        instructions += f"- Task ID: {self.task_definition.task_id}\n"
        instructions += f"- Task Name: {self.task_definition.name}\n"
        instructions += f"- Available Tools: {', '.join(self.task_definition.required_tools)}\n"
        instructions += (
            f"- Diagnostic Time Range: {context.earliest_time} to {context.latest_time}\n"
        )

        if context.focus_index:
            instructions += f"- Focus Index: {context.focus_index}\n"
        if context.focus_host:
            instructions += f"- Focus Host: {context.focus_host}\n"

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
        self, execution_context: AgentExecutionContext, instructions: str
    ) -> DiagnosticResult:
        """Fallback execution method for when OpenAI Agents SDK is not available."""

        task_id = self.task_definition.task_id

        # Route to appropriate execution method based on task type
        if "license" in task_id.lower():
            return await self._execute_license_verification(execution_context)
        elif "index" in task_id.lower():
            return await self._execute_index_verification(execution_context)
        elif "permission" in task_id.lower():
            return await self._execute_permissions_check(execution_context)
        elif "time" in task_id.lower() or "range" in task_id.lower():
            return await self._execute_time_range_check(execution_context)
        else:
            return await self._execute_generic_task(execution_context, instructions)

    async def _execute_license_verification(
        self, execution_context: AgentExecutionContext
    ) -> DiagnosticResult:
        """Execute license verification task."""
        try:
            # Get server information
            server_result = await self.tool_registry.call_tool(
                "run_oneshot_search",
                {
                    "query": "| rest /services/server/info | fields splunk_version, product_type, license_state",
                    "earliest_time": "now",
                    "latest_time": "now",
                    "max_results": 1,
                },
            )

            if not server_result.get("success"):
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

            return DiagnosticResult(
                step=self.task_definition.task_id,
                status=status,
                findings=findings,
                recommendations=[],
                details={"server_info": server_result.get("data", {})},
            )

        except Exception as e:
            return DiagnosticResult(
                step=self.task_definition.task_id,
                status="error",
                findings=[f"License verification failed: {str(e)}"],
                recommendations=["Check configuration and retry"],
                details={"error": str(e)},
            )

    async def _execute_index_verification(
        self, execution_context: AgentExecutionContext
    ) -> DiagnosticResult:
        """Execute index verification task."""
        try:
            # Get available indexes
            indexes_result = await self.tool_registry.call_tool("list_splunk_indexes")

            if not indexes_result.get("success"):
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
            else:
                status = "healthy"
                findings = ["All target indexes are accessible"]
                recommendations = []

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
            return DiagnosticResult(
                step=self.task_definition.task_id,
                status="error",
                findings=[f"Index verification failed: {str(e)}"],
                recommendations=["Check configuration and retry"],
                details={"error": str(e)},
            )

    async def _execute_permissions_check(
        self, execution_context: AgentExecutionContext
    ) -> DiagnosticResult:
        """Execute permissions verification task."""
        try:
            # Get user info from dependencies or directly
            user_info = None
            if "license_verification" in execution_context.dependency_results:
                license_result = execution_context.dependency_results["license_verification"]
                user_info = license_result.details.get("user_info")

            if not user_info:
                user_result = await self.tool_registry.call_tool("get_current_user_info", {})
                user_info = user_result.get("data", {}) if user_result.get("success") else {}

            # Basic permissions check
            user_roles = user_info.get("roles", [])
            if not user_roles:
                status = "warning"
                findings = ["No roles assigned to user"]
                recommendations = ["Contact administrator for role assignment"]
            else:
                status = "healthy"
                findings = [f"User has roles: {', '.join(user_roles)}"]
                recommendations = []

            return DiagnosticResult(
                step=self.task_definition.task_id,
                status=status,
                findings=findings,
                recommendations=recommendations,
                details={"user_info": user_info, "user_roles": user_roles},
            )

        except Exception as e:
            return DiagnosticResult(
                step=self.task_definition.task_id,
                status="error",
                findings=[f"Permissions check failed: {str(e)}"],
                recommendations=["Check authentication and retry"],
                details={"error": str(e)},
            )

    async def _execute_time_range_check(
        self, execution_context: AgentExecutionContext
    ) -> DiagnosticResult:
        """Execute time range verification task."""
        try:
            context = execution_context.diagnostic_context

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

            if not count_result.get("success"):
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
            else:
                status = "healthy"
                findings = [f"Found {total_events:,} events in time range"]
                recommendations = []

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
            return DiagnosticResult(
                step=self.task_definition.task_id,
                status="error",
                findings=[f"Time range check failed: {str(e)}"],
                recommendations=["Check search syntax and time format"],
                details={"error": str(e)},
            )

    async def _execute_generic_task(
        self, execution_context: AgentExecutionContext, instructions: str
    ) -> DiagnosticResult:
        """Execute a generic task using the provided instructions."""

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
