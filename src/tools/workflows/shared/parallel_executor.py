"""
Parallel Workflow Executor for Dynamic Micro-Agents

This module provides dependency-aware parallel execution of workflow tasks using asyncio.gather.
It respects task dependencies while maximizing concurrent execution within each phase.
"""

import asyncio
import logging
import time
from dataclasses import dataclass
from typing import Any

from fastmcp import Context

from .config import AgentConfig
from .context import DiagnosticResult, SplunkDiagnosticContext
from .tools import SplunkToolRegistry
from .workflow_manager import TaskDefinition, WorkflowDefinition, WorkflowResult

logger = logging.getLogger(__name__)

# Import OpenAI agents if available
try:
    from agents import Agent, Runner, custom_span, function_tool

    OPENAI_AGENTS_AVAILABLE = True
    logger.info("OpenAI agents SDK loaded successfully for parallel execution")
except ImportError:
    OPENAI_AGENTS_AVAILABLE = False
    Agent = None
    Runner = None
    function_tool = None
    custom_span = None
    logger.warning(
        "OpenAI agents SDK not available for parallel execution. Install with: pip install openai-agents"
    )


@dataclass
class ParallelExecutionMetrics:
    """Metrics for parallel execution performance."""

    total_execution_time: float
    phase_execution_times: list[float]
    tasks_per_phase: list[int]
    parallel_efficiency: float
    total_tasks: int
    total_phases: int
    successful_tasks: int
    failed_tasks: int


class ParallelWorkflowExecutor:
    """
    Executes workflow tasks in dependency-aware parallel phases using asyncio.gather.

    This executor:
    1. Analyzes task dependencies to create execution phases
    2. Runs independent tasks in parallel within each phase
    3. Passes dependency results to dependent tasks
    4. Provides comprehensive error handling and progress reporting
    5. Maintains full tracing and observability
    """

    def __init__(self, config: AgentConfig, tool_registry: SplunkToolRegistry):
        self.config = config
        self.tool_registry = tool_registry

        logger.info("Initializing ParallelWorkflowExecutor...")
        logger.debug(f"Config: model={self.config.model}, temperature={self.config.temperature}")
        logger.debug(f"Tool registry available tools: {self.tool_registry.get_available_tools()}")

        if not OPENAI_AGENTS_AVAILABLE:
            logger.error("OpenAI agents SDK is required for parallel execution")
            raise ImportError(
                "OpenAI agents SDK is required for parallel execution. "
                "Install with: pip install openai-agents"
            )

        logger.info("ParallelWorkflowExecutor initialized successfully")

    async def execute_workflow(
        self,
        workflow: WorkflowDefinition,
        diagnostic_context: SplunkDiagnosticContext,
        ctx: Context,
        execution_metadata: dict[str, Any] = None,
    ) -> WorkflowResult:
        """
        Execute a workflow by running tasks in dependency-aware parallel phases.

        Args:
            workflow: The workflow definition containing tasks to execute
            diagnostic_context: Context for diagnostic execution
            ctx: FastMCP context for progress reporting and logging
            execution_metadata: Optional metadata for execution tracking

        Returns:
            WorkflowResult containing execution results and performance metrics
        """
        start_time = time.time()

        if execution_metadata is None:
            execution_metadata = {}

        logger.info("=" * 80)
        logger.info(f"STARTING PARALLEL WORKFLOW EXECUTION: {workflow.workflow_id}")
        logger.info("=" * 80)

        # Add comprehensive tracing for workflow execution
        if OPENAI_AGENTS_AVAILABLE and custom_span:
            # Create unique trace name to avoid conflicts
            trace_timestamp = int(time.time() * 1000)

            with custom_span(f"parallel_workflow_{workflow.workflow_id}_{trace_timestamp}"):
                return await self._execute_workflow_core(
                    workflow, diagnostic_context, ctx, execution_metadata, start_time
                )
        else:
            # Fallback execution without tracing
            logger.warning("OpenAI Agents tracing not available, executing without traces")
            return await self._execute_workflow_core(
                workflow, diagnostic_context, ctx, execution_metadata, start_time
            )

    async def _execute_workflow_core(
        self,
        workflow: WorkflowDefinition,
        diagnostic_context: SplunkDiagnosticContext,
        ctx: Context,
        execution_metadata: dict[str, Any],
        start_time: float,
    ) -> WorkflowResult:
        """Core workflow execution with parallel phases and comprehensive tracing."""

        try:
            # Report initial progress
            await ctx.report_progress(progress=0, total=100)
            await ctx.info(f"🚀 Starting parallel execution: {workflow.name}")

            logger.info(f"Workflow: {workflow.name} with {len(workflow.tasks)} tasks")

            # Build dependency graph and execution phases
            if OPENAI_AGENTS_AVAILABLE and custom_span:
                with custom_span("dependency_analysis"):
                    dependency_graph = self._build_dependency_graph(workflow.tasks)
                    execution_phases = self._create_execution_phases(
                        workflow.tasks, dependency_graph
                    )
            else:
                dependency_graph = self._build_dependency_graph(workflow.tasks)
                execution_phases = self._create_execution_phases(workflow.tasks, dependency_graph)

            logger.info("Dependency analysis complete:")
            logger.info(f"  - Total tasks: {len(workflow.tasks)}")
            logger.info(f"  - Execution phases: {len(execution_phases)}")
            logger.info(f"  - Dependency graph: {dependency_graph}")

            # Report progress: Dependencies analyzed
            await ctx.report_progress(progress=10, total=100)
            await ctx.info(
                f"📊 Analysis complete: {len(execution_phases)} phases, max {max(len(phase) for phase in execution_phases)} parallel tasks"
            )

            # Execute tasks in phases with comprehensive tracking
            all_task_results: dict[str, DiagnosticResult] = {}
            phase_execution_times: list[float] = []
            tasks_per_phase: list[int] = []

            phase_progress_step = 80 / len(execution_phases)  # 80% of progress for task execution

            for phase_idx, phase_tasks in enumerate(execution_phases):
                phase_start_time = time.time()
                phase_name = f"execution_phase_{phase_idx + 1}"

                logger.info(
                    f"Executing phase {phase_idx + 1}/{len(execution_phases)}: {len(phase_tasks)} parallel tasks"
                )
                logger.info(
                    f"Phase {phase_idx + 1} tasks: {[task.task_id for task in phase_tasks]}"
                )

                # Report progress for this phase
                phase_progress = 10 + (phase_idx * phase_progress_step)
                await ctx.report_progress(
                    progress=phase_progress,
                    total=100,
                    message=f"Starting phase {phase_idx + 1}/{len(execution_phases)}",
                )
                await ctx.info(
                    f"⚡ Phase {phase_idx + 1}/{len(execution_phases)}: {len(phase_tasks)} parallel tasks"
                )
                await ctx.info(f"📋 Phase tasks: {[task.task_id for task in phase_tasks]}")

                if OPENAI_AGENTS_AVAILABLE and custom_span:
                    with custom_span(phase_name):
                        phase_results = await self._execute_phase(
                            phase_tasks, all_task_results, diagnostic_context, ctx
                        )
                else:
                    phase_results = await self._execute_phase(
                        phase_tasks, all_task_results, diagnostic_context, ctx
                    )

                # Update task results
                all_task_results.update(phase_results)

                # Track phase metrics
                phase_execution_time = time.time() - phase_start_time
                phase_execution_times.append(phase_execution_time)
                tasks_per_phase.append(len(phase_tasks))

                # Log phase completion
                successful_tasks = [
                    task_id
                    for task_id, result in phase_results.items()
                    if result.status in ["healthy", "warning"]
                ]
                failed_tasks = [
                    task_id for task_id, result in phase_results.items() if result.status == "error"
                ]

                logger.info(
                    f"Phase {phase_idx + 1} completed in {phase_execution_time:.2f}s: {len(successful_tasks)} successful, {len(failed_tasks)} failed"
                )
                await ctx.info(
                    f"✅ Phase {phase_idx + 1} complete: {len(successful_tasks)} successful, {len(failed_tasks)} failed ({phase_execution_time:.1f}s)"
                )

                # Report progress after phase completion
                phase_completion_progress = 10 + ((phase_idx + 1) * phase_progress_step)
                await ctx.report_progress(
                    progress=phase_completion_progress,
                    total=100,
                    message=f"Completed phase {phase_idx + 1}/{len(execution_phases)}",
                )

            # Report progress: Task execution complete
            await ctx.report_progress(progress=90, total=100)
            await ctx.info("🔄 All phases completed, finalizing results...")

            # Create execution metrics
            total_execution_time = time.time() - start_time
            execution_metrics = ParallelExecutionMetrics(
                total_execution_time=total_execution_time,
                phase_execution_times=phase_execution_times,
                tasks_per_phase=tasks_per_phase,
                parallel_efficiency=self._calculate_parallel_efficiency(
                    workflow.tasks, execution_phases
                ),
                total_tasks=len(workflow.tasks),
                total_phases=len(execution_phases),
                successful_tasks=len(
                    [r for r in all_task_results.values() if r.status in ["healthy", "warning"]]
                ),
                failed_tasks=len([r for r in all_task_results.values() if r.status == "error"]),
            )

            # Finalize workflow result
            if OPENAI_AGENTS_AVAILABLE and custom_span:
                with custom_span("workflow_result_finalization"):
                    workflow_result = await self._finalize_workflow_result(
                        workflow, all_task_results, execution_phases, execution_metrics, start_time
                    )
            else:
                workflow_result = await self._finalize_workflow_result(
                    workflow, all_task_results, execution_phases, execution_metrics, start_time
                )

            # Report final progress
            await ctx.report_progress(progress=100, total=100)
            await ctx.info(
                f"✅ Parallel execution completed: {workflow_result.status} ({total_execution_time:.1f}s)"
            )

            logger.info("=" * 80)
            logger.info("PARALLEL WORKFLOW EXECUTION COMPLETED SUCCESSFULLY")
            logger.info(f"Total execution time: {total_execution_time:.2f}s")
            logger.info(f"Execution phases: {len(execution_phases)}")
            logger.info(f"Parallel efficiency: {execution_metrics.parallel_efficiency:.1%}")
            logger.info(f"Status: {workflow_result.status}")
            logger.info(
                f"Successful tasks: {execution_metrics.successful_tasks}/{execution_metrics.total_tasks}"
            )
            logger.info("=" * 80)

            return workflow_result

        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"Parallel workflow execution failed: {e}", exc_info=True)
            await ctx.error(f"❌ Parallel execution failed: {str(e)}")

            # Create error result
            return WorkflowResult(
                workflow_id=workflow.workflow_id,
                status="error",
                execution_time=execution_time,
                task_results={},
                dependency_graph={},
                execution_order=[],
                summary={
                    "error": str(e),
                    "execution_time": execution_time,
                    "execution_method": "parallel_phases",
                    "tasks_completed": 0,
                    "successful_tasks": 0,
                    "failed_tasks": 0,
                },
            )

    async def _execute_phase(
        self,
        phase_tasks: list[TaskDefinition],
        completed_results: dict[str, DiagnosticResult],
        diagnostic_context: SplunkDiagnosticContext,
        ctx: Context,
    ) -> dict[str, DiagnosticResult]:
        """Execute a phase of tasks in parallel using asyncio.gather."""

        phase_results = {}

        # Report phase start
        await ctx.info(f"⚡ Starting phase with {len(phase_tasks)} parallel tasks")
        await ctx.info(f"📋 Phase tasks: {[task.task_id for task in phase_tasks]}")

        # Create async tasks for parallel execution
        async_tasks = []
        task_definitions = []

        for task_def in phase_tasks:
            logger.debug(f"Creating agent for task: {task_def.task_id}")
            await ctx.info(f"🔧 Preparing task: {task_def.task_id} ({task_def.name})")

            # Create agent from task definition
            agent = self._create_agent_from_task(task_def)

            # Create async task for execution
            async_task = self._execute_agent_with_dependencies(
                agent, task_def, completed_results, diagnostic_context, ctx
            )

            async_tasks.append(async_task)
            task_definitions.append(task_def)

        # Execute all tasks in parallel
        if async_tasks:
            logger.info(f"Executing {len(async_tasks)} tasks in parallel...")
            await ctx.info(f"🚀 Executing {len(async_tasks)} tasks in parallel...")

            # Report progress at start of parallel execution
            await ctx.report_progress(
                progress=0,
                total=len(async_tasks),
                message=f"Starting parallel execution of {len(async_tasks)} tasks",
            )

            # Use return_exceptions=True to handle individual task failures gracefully
            results = await asyncio.gather(*async_tasks, return_exceptions=True)

            # Process results
            successful_tasks = 0
            failed_tasks = 0

            for i, result in enumerate(results):
                task_def = task_definitions[i]
                task_id = task_def.task_id

                # Report progress for each completed task
                await ctx.report_progress(
                    progress=i + 1,
                    total=len(async_tasks),
                    message=f"Completed task {task_id} ({task_def.name})",
                )

                if isinstance(result, Exception):
                    logger.error(f"Task {task_id} failed with exception: {result}")
                    await ctx.error(f"❌ Task {task_id} failed: {str(result)}")
                    failed_tasks += 1

                    # Create error diagnostic result
                    phase_results[task_id] = DiagnosticResult(
                        step=task_id,
                        status="error",
                        findings=[f"Task execution failed: {str(result)}"],
                        recommendations=["Check task configuration and retry"],
                        details={"error": str(result), "task_name": task_def.name},
                    )
                else:
                    phase_results[task_id] = result
                    successful_tasks += 1
                    logger.debug(f"Task {task_id} completed with status: {result.status}")
                    await ctx.info(f"✅ Task {task_id} completed: {result.status}")

            # Report phase completion
            await ctx.info(
                f"🎯 Phase completed: {successful_tasks} successful, {failed_tasks} failed"
            )
            await ctx.report_progress(
                progress=len(async_tasks),
                total=len(async_tasks),
                message=f"Phase completed: {successful_tasks} successful, {failed_tasks} failed",
            )

        return phase_results

    def _create_agent_from_task(self, task: TaskDefinition) -> Agent:
        """Convert a TaskDefinition into an OpenAI Agent."""

        logger.debug(f"Creating agent from task: {task.task_id}")

        # Create tools based on required_tools (dynamic resolution via registry)
        agent_tools = []
        for tool_name in task.required_tools:
            # Prefer dynamic factory for flexibility and alias support
            dynamic_tool = self.tool_registry.create_agent_tool(tool_name)
            if dynamic_tool is not None:
                agent_tools.append(dynamic_tool)
                continue

            # Fallback to built-in wrappers for backwards compatibility
            if tool_name == "run_splunk_search":
                agent_tools.append(self._create_splunk_search_tool())
            elif tool_name == "run_oneshot_search":
                agent_tools.append(self._create_oneshot_search_tool())
            elif tool_name == "list_splunk_indexes":
                agent_tools.append(self._create_list_indexes_tool())
            elif tool_name in ("get_current_user_info", "get_current_user", "me"):
                agent_tools.append(self._create_user_info_tool())
            elif tool_name == "get_splunk_health":
                agent_tools.append(self._create_health_tool())

        # Create the agent
        agent = Agent(
            name=task.name,
            instructions=task.instructions,
            model=self.config.model,
            tools=agent_tools,
        )

        logger.debug(f"Created agent '{task.name}' with {len(agent_tools)} tools")
        return agent

    async def _execute_agent_with_dependencies(
        self,
        agent: Agent,
        task: TaskDefinition,
        completed_results: dict[str, DiagnosticResult],
        diagnostic_context: SplunkDiagnosticContext,
        ctx: Context,
    ) -> DiagnosticResult:
        """Execute a single agent with dependency context injection."""

        logger.debug(f"Executing agent for task: {task.task_id}")
        await ctx.info(f"🎯 Executing task: {task.task_id} ({task.name})")

        try:
            # Inject dependency results and context into instructions
            enhanced_instructions = self._inject_dependency_context(
                task.instructions, task.dependencies, completed_results, diagnostic_context
            )

            # Update agent instructions with enhanced context
            agent_with_context = agent.clone(instructions=enhanced_instructions)

            # Report task start with dependencies info
            if task.dependencies:
                await ctx.info(f"📋 Task {task.task_id} dependencies: {task.dependencies}")
            else:
                await ctx.info(f"📋 Task {task.task_id} has no dependencies")

            # Report agent execution start
            await ctx.report_progress(
                progress=0, total=1, message=f"Starting agent execution for {task.task_id}"
            )

            # Execute the agent
            if OPENAI_AGENTS_AVAILABLE and custom_span:
                with custom_span(f"agent_execution_{task.task_id}"):
                    await ctx.info(f"🤖 Starting agent execution for {task.task_id}...")
                    result = await Runner.run(agent_with_context, enhanced_instructions)
            else:
                await ctx.info(f"🤖 Starting agent execution for {task.task_id}...")
                result = await Runner.run(agent_with_context, enhanced_instructions)

            # Convert agent result to DiagnosticResult
            diagnostic_result = self._parse_agent_result_to_diagnostic(result, task)

            logger.debug(f"Agent {task.task_id} completed with status: {diagnostic_result.status}")
            await ctx.info(f"✅ Task {task.task_id} completed: {diagnostic_result.status}")

            # Report agent execution completion
            await ctx.report_progress(
                progress=1, total=1, message=f"Completed agent execution for {task.task_id}"
            )

            # Report key findings if any
            if diagnostic_result.findings:
                key_findings = diagnostic_result.findings[:2]  # Show first 2 findings
                await ctx.info(f"🔍 Key findings for {task.task_id}: {key_findings}")

            return diagnostic_result

        except Exception as e:
            logger.error(f"Agent execution failed for task {task.task_id}: {e}", exc_info=True)
            await ctx.error(f"❌ Task {task.task_id} execution failed: {str(e)}")
            await ctx.report_progress(
                progress=1, total=1, message=f"Failed agent execution for {task.task_id}"
            )
            raise

    def _inject_dependency_context(
        self,
        base_instructions: str,
        dependencies: list[str],
        completed_results: dict[str, DiagnosticResult],
        diagnostic_context: SplunkDiagnosticContext,
    ) -> str:
        """Inject dependency results and diagnostic context into agent instructions."""

        enhanced_instructions = base_instructions

        # Inject diagnostic context variables
        enhanced_instructions = enhanced_instructions.replace(
            "{earliest_time}", diagnostic_context.earliest_time
        )
        enhanced_instructions = enhanced_instructions.replace(
            "{latest_time}", diagnostic_context.latest_time
        )
        enhanced_instructions = enhanced_instructions.replace(
            "{focus_index}", diagnostic_context.focus_index or "all indexes"
        )
        enhanced_instructions = enhanced_instructions.replace(
            "{focus_host}", diagnostic_context.focus_host or "all hosts"
        )
        enhanced_instructions = enhanced_instructions.replace(
            "{focus_sourcetype}", diagnostic_context.focus_sourcetype or "all sourcetypes"
        )
        enhanced_instructions = enhanced_instructions.replace(
            "{problem_description}",
            diagnostic_context.problem_description or "No specific problem description provided",
        )
        enhanced_instructions = enhanced_instructions.replace(
            "{workflow_type}", diagnostic_context.workflow_type or "unknown"
        )
        enhanced_instructions = enhanced_instructions.replace(
            "{complexity_level}", diagnostic_context.complexity_level
        )

        if diagnostic_context.indexes:
            enhanced_instructions = enhanced_instructions.replace(
                "{indexes}", ", ".join(diagnostic_context.indexes)
            )
        if diagnostic_context.sourcetypes:
            enhanced_instructions = enhanced_instructions.replace(
                "{sourcetypes}", ", ".join(diagnostic_context.sourcetypes)
            )
        if diagnostic_context.sources:
            enhanced_instructions = enhanced_instructions.replace(
                "{sources}", ", ".join(diagnostic_context.sources)
            )

        # Inject dependency results if available
        if dependencies and completed_results:
            dependency_context = "\n\n**Dependency Results:**\n"

            for dep_id in dependencies:
                if dep_id in completed_results:
                    dep_result = completed_results[dep_id]
                    dependency_context += f"\n**{dep_id}** (Status: {dep_result.status})\n"

                    # Include key findings
                    if dep_result.findings:
                        dependency_context += "Key findings:\n"
                        for finding in dep_result.findings[:3]:  # Limit to top 3 findings
                            dependency_context += f"  - {finding}\n"

                    # Include important details
                    if dep_result.details:
                        important_keys = [
                            "user_info",
                            "license_state",
                            "total_events",
                            "available_indexes",
                            "server_info",
                        ]
                        for key in important_keys:
                            if key in dep_result.details:
                                dependency_context += f"  - {key}: {dep_result.details[key]}\n"

                    dependency_context += "\n"

            enhanced_instructions += dependency_context

        # Add comprehensive execution context including problem description
        enhanced_instructions += "\n\n**Execution Context:**\n"
        enhanced_instructions += f"- Time Range: {diagnostic_context.earliest_time} to {diagnostic_context.latest_time}\n"
        enhanced_instructions += f"- Complexity Level: {diagnostic_context.complexity_level}\n"

        if diagnostic_context.problem_description:
            enhanced_instructions += (
                f"- Original Problem: {diagnostic_context.problem_description}\n"
            )
        if diagnostic_context.workflow_type:
            enhanced_instructions += f"- Workflow Type: {diagnostic_context.workflow_type}\n"
        if diagnostic_context.focus_index:
            enhanced_instructions += f"- Focus Index: {diagnostic_context.focus_index}\n"
        if diagnostic_context.focus_host:
            enhanced_instructions += f"- Focus Host: {diagnostic_context.focus_host}\n"
        if diagnostic_context.focus_sourcetype:
            enhanced_instructions += f"- Focus Sourcetype: {diagnostic_context.focus_sourcetype}\n"

        return enhanced_instructions

    def _parse_agent_result_to_diagnostic(
        self, agent_result: Any, task: TaskDefinition
    ) -> DiagnosticResult:
        """Convert agent execution result to DiagnosticResult format."""

        # Extract output from agent result
        output = (
            agent_result.final_output
            if hasattr(agent_result, "final_output")
            else str(agent_result)
        )

        # Parse the output to extract structured information
        # This is a simplified parser - in practice, you might want more sophisticated parsing
        findings = []
        recommendations = []
        status = "completed"

        # Simple heuristic-based parsing
        lines = output.split("\n")
        current_section = None

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # Detect sections
            if "finding" in line.lower() or "issue" in line.lower():
                current_section = "findings"
                if line.startswith("-") or line.startswith("•"):
                    findings.append(line[1:].strip())
            elif "recommend" in line.lower() or "action" in line.lower():
                current_section = "recommendations"
                if line.startswith("-") or line.startswith("•"):
                    recommendations.append(line[1:].strip())
            elif current_section == "findings" and (line.startswith("-") or line.startswith("•")):
                findings.append(line[1:].strip())
            elif current_section == "recommendations" and (
                line.startswith("-") or line.startswith("•")
            ):
                recommendations.append(line[1:].strip())

        # Determine status based on output content - improved logic to reduce false positives
        output_lower = output.lower()

        # Check for actual error indicators (more specific patterns)
        error_patterns = [
            "fatal error",
            "execution failed",
            "search failed",
            "connection failed",
            "authentication failed",
            "permission denied",
            "access denied",
            "critical error",
            "severe error",
            "exception:",
            "traceback",
        ]

        # Check for warning indicators (more specific patterns)
        warning_patterns = [
            "warning:",
            "potential issue",
            "configuration issue",
            "performance issue",
            "deprecated",
            "missing configuration",
            "timeout occurred",
            "partial failure",
        ]

        # Check for successful completion indicators
        success_patterns = [
            "analysis completed",
            "check completed",
            "verification completed",
            "successfully",
            "no issues found",
            "working properly",
            "healthy",
        ]

        # Determine status based on specific patterns rather than broad keywords
        if any(pattern in output_lower for pattern in error_patterns):
            status = "critical"
        elif any(pattern in output_lower for pattern in warning_patterns):
            status = "warning"
        elif any(pattern in output_lower for pattern in success_patterns):
            status = "healthy"
        else:
            # Default to healthy for neutral/informational outputs
            # Only mark as warning if there are actual actionable issues mentioned
            if (
                "no data found" in output_lower
                or "zero results" in output_lower
                or "missing" in output_lower
                and "configuration" in output_lower
            ):
                status = "warning"
            else:
                status = "healthy"

        # Fallback if no structured findings found
        if not findings:
            findings = [f"Analysis completed for {task.name}"]
        if not recommendations:
            recommendations = ["Review analysis results for further actions"]

        return DiagnosticResult(
            step=task.task_id,
            status=status,
            findings=findings,
            recommendations=recommendations,
            details={
                "agent_output": output,
                "task_name": task.name,
                "execution_method": "parallel_agent",
            },
        )

    # Tool creation methods (similar to the existing dynamic_agent.py approach)
    def _create_splunk_search_tool(self):
        """Create run_splunk_search tool for agents."""
        if not OPENAI_AGENTS_AVAILABLE:
            return None

        @function_tool
        async def run_splunk_search(
            query: str, earliest_time: str = "-24h", latest_time: str = "now"
        ) -> str:
            """Execute a Splunk search query."""
            try:
                result = await self.tool_registry.call_tool(
                    "run_splunk_search",
                    {"query": query, "earliest_time": earliest_time, "latest_time": latest_time},
                )
                if result.get("success"):
                    return str(result.get("data", ""))
                else:
                    return f"Search failed: {result.get('error', 'Unknown error')}"
            except Exception as e:
                return f"Search execution failed: {str(e)}"

        return run_splunk_search

    def _create_oneshot_search_tool(self):
        """Create run_oneshot_search tool for agents."""
        if not OPENAI_AGENTS_AVAILABLE:
            return None

        @function_tool
        async def run_oneshot_search(
            query: str,
            earliest_time: str = "-15m",
            latest_time: str = "now",
            max_results: int = 100,
        ) -> str:
            """Execute a quick Splunk oneshot search."""
            try:
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
            except Exception as e:
                return f"Oneshot search execution failed: {str(e)}"

        return run_oneshot_search

    def _create_list_indexes_tool(self):
        """Create list_splunk_indexes tool for agents."""
        if not OPENAI_AGENTS_AVAILABLE:
            return None

        @function_tool
        async def list_splunk_indexes() -> str:
            """List available Splunk indexes."""
            try:
                result = await self.tool_registry.call_tool("list_splunk_indexes")
                if result.get("success"):
                    return str(result.get("data", ""))
                else:
                    return f"Failed to list indexes: {result.get('error', 'Unknown error')}"
            except Exception as e:
                return f"Index listing failed: {str(e)}"

        return list_splunk_indexes

    def _create_user_info_tool(self):
        """Create get_current_user_info tool for agents."""
        if not OPENAI_AGENTS_AVAILABLE:
            return None

        @function_tool
        async def get_current_user_info() -> str:
            """Get current user information including roles and capabilities."""
            try:
                result = await self.tool_registry.call_tool("get_current_user_info")
                if result.get("success"):
                    return str(result.get("data", ""))
                else:
                    return f"Failed to get user info: {result.get('error', 'Unknown error')}"
            except Exception as e:
                return f"User info retrieval failed: {str(e)}"

        return get_current_user_info

    def _create_health_tool(self):
        """Create get_splunk_health tool for agents."""
        if not OPENAI_AGENTS_AVAILABLE:
            return None

        @function_tool
        async def get_splunk_health() -> str:
            """Check Splunk server health and connectivity."""
            try:
                result = await self.tool_registry.call_tool("get_splunk_health")
                if result.get("success"):
                    return str(result.get("data", ""))
                else:
                    return f"Health check failed: {result.get('error', 'Unknown error')}"
            except Exception as e:
                return f"Health check execution failed: {str(e)}"

        return get_splunk_health

    # Dependency management methods (reused from WorkflowManager)
    def _build_dependency_graph(self, tasks: list[TaskDefinition]) -> dict[str, list[str]]:
        """Build a dependency graph from task definitions."""

        logger.debug("Building dependency graph...")
        graph = {}

        for task in tasks:
            graph[task.task_id] = task.dependencies.copy()
            if task.dependencies:
                logger.debug(f"  {task.task_id} depends on: {task.dependencies}")
            else:
                logger.debug(f"  {task.task_id} has no dependencies (can run in parallel)")

        logger.debug(f"Dependency graph complete: {graph}")
        return graph

    def _create_execution_phases(
        self, tasks: list[TaskDefinition], dependency_graph: dict[str, list[str]]
    ) -> list[list[TaskDefinition]]:
        """Create execution phases based on task dependencies."""

        logger.debug("Creating execution phases from dependency graph...")
        phases = []
        completed = set()
        task_map = {task.task_id: task for task in tasks}
        task_ids = set(task_map.keys())
        phase_num = 0

        logger.debug(f"Total tasks to schedule: {len(task_ids)}")
        logger.debug(f"Task IDs: {list(task_ids)}")

        while completed != task_ids:
            phase_num += 1
            logger.debug(f"Planning phase {phase_num}...")

            # Find tasks that can run (all dependencies completed)
            ready_tasks = []
            blocked_tasks = []

            for task_id in task_ids:
                if task_id not in completed:
                    dependencies = dependency_graph[task_id]
                    missing_deps = [dep for dep in dependencies if dep not in completed]

                    if not missing_deps:
                        ready_tasks.append(task_map[task_id])
                        logger.debug(f"  {task_id}: READY (all dependencies satisfied)")
                    else:
                        blocked_tasks.append((task_id, missing_deps))
                        logger.debug(f"  {task_id}: BLOCKED by {missing_deps}")

            if not ready_tasks:
                # Circular dependency or missing dependency
                remaining = task_ids - completed
                logger.error(f"Cannot resolve dependencies for tasks: {remaining}")

                # Log detailed dependency analysis for troubleshooting
                for task_id in remaining:
                    deps = dependency_graph[task_id]
                    missing = [dep for dep in deps if dep not in completed and dep in task_ids]
                    invalid = [dep for dep in deps if dep not in task_ids]

                    if invalid:
                        logger.error(f"  {task_id} has invalid dependencies: {invalid}")
                    if missing:
                        logger.error(f"  {task_id} waiting for: {missing}")

                # Add remaining tasks to final phase to avoid infinite loop
                logger.warning(f"Adding {len(remaining)} unresolved tasks to final phase")
                remaining_tasks = [task_map[task_id] for task_id in remaining]
                phases.append(remaining_tasks)
                break

            logger.debug(
                f"Phase {phase_num}: {len(ready_tasks)} tasks ready - {[t.task_id for t in ready_tasks]}"
            )
            phases.append(ready_tasks)
            completed.update([task.task_id for task in ready_tasks])

            logger.debug(
                f"Phase {phase_num} completed. Total completed: {len(completed)}/{len(task_ids)}"
            )

        logger.debug(f"Execution phases created: {len(phases)} phases total")
        for i, phase in enumerate(phases):
            logger.debug(f"  Phase {i + 1}: {[task.task_id for task in phase]}")

        return phases

    def _calculate_parallel_efficiency(
        self, tasks: list[TaskDefinition], execution_phases: list[list[TaskDefinition]]
    ) -> float:
        """Calculate the parallel execution efficiency (0-1)."""

        total_tasks = len(tasks)
        if total_tasks == 0:
            return 0.0

        # If all tasks could run in parallel, we'd have 1 phase
        # If all tasks are sequential, we'd have n phases
        actual_phases = len(execution_phases)

        # Efficiency = 1 - (actual_phases - 1) / (total_tasks - 1)
        if total_tasks == 1:
            return 1.0

        efficiency = 1.0 - (actual_phases - 1) / (total_tasks - 1)
        return max(0.0, min(1.0, efficiency))

    async def _finalize_workflow_result(
        self,
        workflow: WorkflowDefinition,
        task_results: dict[str, DiagnosticResult],
        execution_phases: list[list[TaskDefinition]],
        execution_metrics: ParallelExecutionMetrics,
        start_time: float,
    ) -> WorkflowResult:
        """Finalize workflow result with comprehensive metrics and analysis."""

        logger.info("=" * 60)
        logger.info("GENERATING PARALLEL WORKFLOW SUMMARY")
        logger.info("=" * 60)

        # Determine overall status
        overall_status = self._determine_overall_status(task_results)
        logger.info(f"Overall workflow status determined: {overall_status}")

        # Log task status breakdown
        status_counts = {}
        for _task_id, result in task_results.items():
            status = result.status
            status_counts[status] = status_counts.get(status, 0) + 1

        logger.info("Task status breakdown:")
        for status, count in status_counts.items():
            logger.info(f"  {status}: {count} tasks")

        # Build dependency graph for result
        dependency_graph = self._build_dependency_graph(workflow.tasks)
        execution_order = [[task.task_id for task in phase] for phase in execution_phases]

        # Generate comprehensive summary
        summary = self._generate_parallel_workflow_summary(
            workflow, task_results, execution_phases, execution_metrics
        )

        result = WorkflowResult(
            workflow_id=workflow.workflow_id,
            status=overall_status,
            execution_time=execution_metrics.total_execution_time,
            task_results=task_results,
            dependency_graph=dependency_graph,
            execution_order=execution_order,
            summary=summary,
        )

        logger.info("=" * 80)
        logger.info(f"PARALLEL WORKFLOW EXECUTION COMPLETED: {workflow.workflow_id}")
        logger.info(f"Total execution time: {execution_metrics.total_execution_time:.2f}s")
        logger.info(f"Overall status: {result.status}")
        logger.info(f"Tasks completed: {len(task_results)}")
        logger.info(f"Execution phases: {len(execution_phases)}")
        logger.info(f"Parallel efficiency: {execution_metrics.parallel_efficiency:.1%}")
        logger.info(
            f"Successful tasks: {execution_metrics.successful_tasks}/{execution_metrics.total_tasks}"
        )
        logger.info("=" * 80)

        return result

    def _determine_overall_status(self, task_results: dict[str, DiagnosticResult]) -> str:
        """Determine overall workflow status from task results."""

        if not task_results:
            logger.warning("No task results available - returning error status")
            return "error"

        statuses = [result.status for result in task_results.values()]
        logger.debug(f"Task statuses for overall determination: {statuses}")

        status_counts = {}
        for status in statuses:
            status_counts[status] = status_counts.get(status, 0) + 1

        logger.debug(f"Status distribution: {status_counts}")

        if "error" in statuses:
            logger.debug("Overall status: error (due to task errors)")
            return "error"
        elif "critical" in statuses:
            logger.debug("Overall status: critical (due to critical issues)")
            return "critical"
        elif "warning" in statuses:
            logger.debug("Overall status: warning (due to warnings)")
            return "warning"
        else:
            logger.debug("Overall status: healthy (all tasks successful)")
            return "healthy"

    def _generate_parallel_workflow_summary(
        self,
        workflow: WorkflowDefinition,
        task_results: dict[str, DiagnosticResult],
        execution_phases: list[list[TaskDefinition]],
        execution_metrics: ParallelExecutionMetrics,
    ) -> dict[str, Any]:
        """Generate a comprehensive summary of parallel workflow execution."""

        # Categorize results
        healthy_tasks = []
        warning_tasks = []
        critical_tasks = []
        error_tasks = []

        for task_id, result in task_results.items():
            if result.status == "healthy":
                healthy_tasks.append(task_id)
            elif result.status == "warning":
                warning_tasks.append(task_id)
            elif result.status == "critical":
                critical_tasks.append(task_id)
            elif result.status == "error":
                error_tasks.append(task_id)

        # Collect all findings and recommendations
        all_findings = []
        all_recommendations = []

        for result in task_results.values():
            all_findings.extend(result.findings)
            all_recommendations.extend(result.recommendations)

        # Remove duplicates while preserving order
        unique_recommendations = []
        seen = set()
        for rec in all_recommendations:
            if rec not in seen:
                unique_recommendations.append(rec)
                seen.add(rec)

        return {
            "workflow_name": workflow.name,
            "execution_method": "parallel_phases",
            "total_tasks": execution_metrics.total_tasks,
            "execution_phases": execution_metrics.total_phases,
            "parallel_efficiency": execution_metrics.parallel_efficiency,
            "total_execution_time": execution_metrics.total_execution_time,
            "phase_execution_times": execution_metrics.phase_execution_times,
            "tasks_per_phase": execution_metrics.tasks_per_phase,
            "task_status_breakdown": {
                "healthy": len(healthy_tasks),
                "warning": len(warning_tasks),
                "critical": len(critical_tasks),
                "error": len(error_tasks),
            },
            "healthy_tasks": healthy_tasks,
            "warning_tasks": warning_tasks,
            "critical_tasks": critical_tasks,
            "error_tasks": error_tasks,
            "total_findings": len(all_findings),
            "total_recommendations": len(unique_recommendations),
            "key_findings": all_findings[:10],  # Top 10 findings
            "recommendations": unique_recommendations,
            "performance_metrics": {
                "fastest_phase": min(execution_metrics.phase_execution_times)
                if execution_metrics.phase_execution_times
                else 0,
                "slowest_phase": max(execution_metrics.phase_execution_times)
                if execution_metrics.phase_execution_times
                else 0,
                "average_phase_time": sum(execution_metrics.phase_execution_times)
                / len(execution_metrics.phase_execution_times)
                if execution_metrics.phase_execution_times
                else 0,
                "max_parallel_tasks": max(execution_metrics.tasks_per_phase)
                if execution_metrics.tasks_per_phase
                else 0,
            },
        }
