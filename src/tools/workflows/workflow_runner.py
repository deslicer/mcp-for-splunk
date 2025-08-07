"""
Workflow Runner Tool for Executing Custom and Built-in Workflows.

This tool provides the capability to execute any available workflow in the system,
including both built-in core workflows and user-contributed workflows, with 
comprehensive parameter support and parallel execution.
"""

import logging
import os
import time
from typing import Any, Optional

from fastmcp import Context
from openai import OpenAI

from src.core.base import BaseTool, ToolMetadata

# Import workflow execution infrastructure
from ..agents.shared import AgentConfig, SplunkDiagnosticContext, SplunkToolRegistry
from ..agents.shared.parallel_executor import ParallelWorkflowExecutor
from ..agents.shared.workflow_manager import WorkflowManager
from ..agents.summarization_tool import create_summarization_tool

logger = logging.getLogger(__name__)

# Only import OpenAI agents if available
try:
    from agents import Agent, Runner, custom_span, function_tool, trace

    OPENAI_AGENTS_AVAILABLE = True
    logger.info("OpenAI agents SDK loaded successfully for workflow runner")
except ImportError:
    OPENAI_AGENTS_AVAILABLE = False
    Agent = None
    Runner = None
    function_tool = None
    trace = None
    custom_span = None
    logger.warning("OpenAI agents SDK not available. Install with: pip install openai-agents")


class WorkflowRunnerTool(BaseTool):
    """
    Workflow Runner Tool for Executing Available Workflows.

    This tool provides comprehensive workflow execution capabilities, allowing users to run
    any available workflow in the system with full parameter control and parallel execution.
    It serves as a flexible interface to the workflow execution engine.

    ## Key Features:
    - **Universal Workflow Execution**: Run any core or contrib workflow by ID
    - **Flexible Parameter Control**: Full control over diagnostic context and execution parameters
    - **Parallel Execution**: Leverages dependency-aware parallel task execution
    - **Comprehensive Results**: Detailed execution results with performance metrics
    - **Tracing Support**: Full observability with OpenAI Agents tracing
    - **Progress Reporting**: Real-time progress updates during execution

    ## Workflow Types Supported:

    ### Core Workflows
    Built-in workflows provided by the system:
    - **missing_data_troubleshooting**: Systematic missing data analysis following Splunk's 10-step checklist
    - **performance_analysis**: Comprehensive performance diagnostics using Platform Instrumentation

    ### Contrib Workflows
    User-contributed workflows from contrib/workflows/:
    - Custom security analysis workflows
    - Specialized data quality assessments
    - Performance deep-dive workflows
    - Custom troubleshooting procedures

    ## Execution Model:
    1. **Workflow Discovery**: Validates workflow ID exists and is accessible
    2. **Parameter Validation**: Ensures all required context parameters are provided
    3. **Parallel Execution**: Tasks execute in dependency-aware parallel phases
    4. **Result Synthesis**: Comprehensive analysis and recommendations generation
    5. **Performance Metrics**: Detailed execution timing and efficiency reporting

    ## Parameters:

    - **workflow_id** (str, required): Unique identifier of the workflow to execute.
      Use list_workflows tool to discover available workflow IDs.
      Examples: "missing_data_troubleshooting", "performance_analysis", "custom_security_analysis"

    - **problem_description** (str, optional): Description of the specific issue being investigated.
      Provides context for the workflow execution and helps with result interpretation.

    - **earliest_time** (str, optional): Start time for diagnostic searches in Splunk time format.
      Examples: "-24h", "-7d@d", "2023-01-01T00:00:00". Default: "-24h"

    - **latest_time** (str, optional): End time for diagnostic searches in Splunk time format.
      Examples: "now", "-1h", "@d", "2023-01-01T23:59:59". Default: "now"

    - **focus_index** (str, optional): Specific Splunk index to focus the analysis on.
      Useful when the problem is isolated to a particular data source.

    - **focus_host** (str, optional): Specific host or server to focus the analysis on.
      Helpful for distributed environment troubleshooting.

    - **focus_sourcetype** (str, optional): Specific sourcetype to focus the analysis on.
      Useful when the problem is related to a particular data format or source type.

    - **complexity_level** (str, optional): Analysis depth level. Options: "basic", "moderate", "advanced".
      Affects the comprehensiveness of diagnostic checks. Default: "moderate"

    - **enable_summarization** (bool, optional): Whether to enable AI-powered result summarization.
      When enabled, provides executive summaries and enhanced recommendations. Default: True

    ## How It Works:
    1. **Workflow Validation**: Verifies the specified workflow ID exists and is accessible
    2. **Context Creation**: Builds diagnostic context from provided parameters
    3. **Parallel Execution**: Executes workflow tasks using dependency-aware parallel processing
    4. **Result Analysis**: Optionally runs AI-powered summarization for enhanced insights
    5. **Comprehensive Reporting**: Returns detailed execution results with metrics

    ## Example Use Cases:
    - Run missing data analysis: workflow_id="missing_data_troubleshooting"
    - Execute performance analysis: workflow_id="performance_analysis"
    - Run custom security workflow: workflow_id="custom_security_analysis"
    - Execute contrib data quality workflow: workflow_id="data_quality_assessment"

    ## Benefits:
    - **Workflow Flexibility**: Execute any available workflow with consistent interface
    - **Parameter Control**: Fine-tune execution context for specific scenarios
    - **Parallel Performance**: Benefit from optimized parallel task execution
    - **Comprehensive Results**: Get detailed analysis with performance metrics
    - **Extensibility**: Works with both core and user-contributed workflows
    """

    METADATA = ToolMetadata(
        name="workflow_runner",
        description="""Execute any available workflow by ID with comprehensive parameter control and parallel execution.

This tool provides a flexible interface to execute both core (built-in) and contrib (user-contributed) workflows
with full control over execution parameters and diagnostic context. It leverages the same parallel execution
engine used by the dynamic troubleshoot agent for optimal performance.

## Core Capabilities:
- **Universal Execution**: Run any workflow by ID - core or contrib workflows
- **Parameter Flexibility**: Full control over time ranges, focus areas, and complexity levels
- **Parallel Processing**: Dependency-aware parallel task execution for optimal performance
- **Comprehensive Results**: Detailed execution results with performance metrics and summaries
- **Progress Tracking**: Real-time progress reporting during workflow execution

## Key Parameters:
- workflow_id (required): ID of workflow to execute (use list_workflows to discover)
- problem_description (optional): Context about the specific issue being investigated
- earliest_time/latest_time (optional): Time range for diagnostic searches (default: "-24h" to "now")
- focus_index/focus_host/focus_sourcetype (optional): Specific focus areas for targeted analysis
- complexity_level (optional): "basic", "moderate", "advanced" analysis depth (default: "moderate")
- enable_summarization (optional): AI-powered result summarization (default: True)

## Supported Workflows:
- **Core Workflows**: missing_data_troubleshooting, performance_analysis
- **Contrib Workflows**: Any custom workflows from contrib/workflows/ directory

## Benefits:
- Consistent interface for all workflow types
- Optimized parallel execution with dependency management
- Flexible parameter control for different scenarios
- Comprehensive result analysis and reporting
- Integration with existing workflow infrastructure

Perfect for executing specific workflows when you know exactly which diagnostic procedure
you need to run, or for building automated troubleshooting pipelines.""",
        category="workflows",
    )

    def __init__(self, name: str, category: str):
        super().__init__(name, self.METADATA.description)
        self.category = category

        logger.info(f"Initializing WorkflowRunnerTool: {name}")

        if not OPENAI_AGENTS_AVAILABLE:
            logger.error("OpenAI agents SDK is required for workflow execution")
            raise ImportError(
                "OpenAI agents SDK is required for this tool. "
                "Install with: pip install openai-agents"
            )

        logger.debug("Loading OpenAI configuration...")
        self.config = self._load_config()
        logger.info(
            f"OpenAI config loaded - Model: {self.config.model}, Temperature: {self.config.temperature}"
        )

        self.client = OpenAI(api_key=self.config.api_key)

        # Initialize the workflow execution infrastructure
        logger.info("Setting up workflow execution infrastructure...")
        self._setup_workflow_infrastructure()

        logger.info("WorkflowRunnerTool initialization complete")

    def _load_config(self):
        """Load OpenAI configuration from environment variables."""
        logger.debug("Loading OpenAI configuration from environment")

        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            logger.error("OPENAI_API_KEY environment variable not found")
            raise ValueError(
                "OPENAI_API_KEY environment variable is required. "
                "Please set it in your .env file or environment."
            )

        logger.debug("API key found, creating configuration")

        config = AgentConfig(
            api_key=api_key,
            model=os.getenv("OPENAI_MODEL", "gpt-4o"),
            temperature=float(os.getenv("OPENAI_TEMPERATURE", "0.7")),
            max_tokens=int(os.getenv("OPENAI_MAX_TOKENS", "4000")),
        )

        logger.info(
            f"Configuration loaded: model={config.model}, temp={config.temperature}, max_tokens={config.max_tokens}"
        )
        return config

    def _setup_workflow_infrastructure(self):
        """Set up the workflow execution infrastructure."""

        logger.info("Setting up workflow execution infrastructure...")

        # Create tool registry for workflow execution
        self.tool_registry = SplunkToolRegistry()

        # Initialize Splunk tools for the registry
        logger.info("Setting up Splunk tools for workflow execution...")
        from ..agents.shared.tools import create_splunk_tools

        tools = create_splunk_tools(self.tool_registry)
        logger.info(f"Initialized {len(tools)} Splunk tools for workflow execution")

        # Create workflow manager for workflow definitions
        logger.info("Initializing workflow manager...")
        self.workflow_manager = WorkflowManager(config=self.config, tool_registry=self.tool_registry)
        logger.info("Workflow manager initialized with available workflows")

        # Create parallel workflow executor
        logger.info("Initializing parallel workflow executor...")
        self.parallel_executor = ParallelWorkflowExecutor(config=self.config, tool_registry=self.tool_registry)
        logger.info("Parallel workflow executor initialized")

        # Create summarization tool
        logger.info("Initializing summarization tool...")
        self.summarization_tool = create_summarization_tool(config=self.config, tool_registry=self.tool_registry)
        logger.info("Summarization tool initialized")

        logger.info("Workflow execution infrastructure setup complete")

    async def execute(
        self,
        ctx: Context,
        workflow_id: str,
        problem_description: Optional[str] = None,
        earliest_time: str = "-24h",
        latest_time: str = "now",
        focus_index: Optional[str] = None,
        focus_host: Optional[str] = None,
        focus_sourcetype: Optional[str] = None,
        complexity_level: str = "moderate",
        enable_summarization: bool = True,
    ) -> dict[str, Any]:
        """
        Execute a specific workflow with comprehensive parameter control.

        Args:
            ctx: FastMCP context
            workflow_id: Unique identifier of the workflow to execute
            problem_description: Description of the specific issue being investigated
            earliest_time: Start time for analysis
            latest_time: End time for analysis
            focus_index: Specific index to focus on (optional)
            focus_host: Specific host to focus on (optional)
            focus_sourcetype: Specific sourcetype to focus on (optional)
            complexity_level: Analysis complexity level
            enable_summarization: Whether to enable AI-powered result summarization

        Returns:
            Dict containing the comprehensive workflow execution results
        """
        execution_start_time = time.time()

        # Basic parameter validation
        if not workflow_id or len(workflow_id.strip()) == 0:
            raise ValueError("workflow_id is required and cannot be empty")
        if complexity_level not in ["basic", "moderate", "advanced"]:
            raise ValueError(f"complexity_level must be 'basic', 'moderate', or 'advanced', got: {complexity_level}")

        # Normalize empty strings to None
        problem_description = problem_description if problem_description and problem_description.strip() else None
        focus_index = focus_index if focus_index and focus_index.strip() else None
        focus_host = focus_host if focus_host and focus_host.strip() else None
        focus_sourcetype = focus_sourcetype if focus_sourcetype and focus_sourcetype.strip() else None

        # Create comprehensive trace for the workflow execution
        trace_timestamp = int(time.time() * 1000)  # milliseconds for uniqueness
        trace_name = f"Workflow Runner: {workflow_id} {trace_timestamp}"

        # Convert all metadata values to strings for OpenAI API compatibility
        trace_metadata = {
            "workflow_id": str(workflow_id),
            "problem_description": str(problem_description)[:100] if problem_description else "none",
            "time_range": f"{earliest_time} to {latest_time}",
            "focus_index": str(focus_index) if focus_index else "all",
            "focus_host": str(focus_host) if focus_host else "all",
            "focus_sourcetype": str(focus_sourcetype) if focus_sourcetype else "all",
            "complexity_level": str(complexity_level),
            "enable_summarization": str(enable_summarization),
            "tool_name": "workflow_runner",
            "trace_timestamp": str(trace_timestamp),
        }

        if OPENAI_AGENTS_AVAILABLE and trace:
            # Use OpenAI Agents SDK tracing with correct API
            with trace(workflow_name=trace_name, metadata=trace_metadata):
                return await self._execute_with_tracing(
                    ctx, workflow_id, problem_description, earliest_time, latest_time,
                    focus_index, focus_host, focus_sourcetype, complexity_level, 
                    enable_summarization, execution_start_time
                )
        else:
            # Fallback without tracing
            logger.warning("OpenAI Agents tracing not available, executing without traces")
            return await self._execute_with_tracing(
                ctx, workflow_id, problem_description, earliest_time, latest_time,
                focus_index, focus_host, focus_sourcetype, complexity_level, 
                enable_summarization, execution_start_time
            )

    async def _execute_with_tracing(
        self,
        ctx: Context,
        workflow_id: str,
        problem_description: str | None,
        earliest_time: str,
        latest_time: str,
        focus_index: str | None,
        focus_host: str | None,
        focus_sourcetype: str | None,
        complexity_level: str,
        enable_summarization: bool,
        execution_start_time: float,
    ) -> dict[str, Any]:
        """Execute the workflow with comprehensive tracing."""

        # Create unique trace timestamp to avoid conflicts
        trace_timestamp = int(time.time() * 1000)

        logger.info("=" * 80)
        logger.info("STARTING WORKFLOW RUNNER EXECUTION")
        logger.info("=" * 80)

        try:
            logger.info(f"Workflow ID: {workflow_id}")
            logger.info(f"Problem: {problem_description}")
            logger.info(f"Time range: {earliest_time} to {latest_time}")
            logger.info(f"Focus - Index: {focus_index}, Host: {focus_host}, Sourcetype: {focus_sourcetype}")
            logger.info(f"Complexity level: {complexity_level}")
            logger.info(f"Summarization enabled: {enable_summarization}")

            # Report initial progress
            await ctx.report_progress(progress=0, total=100)
            await ctx.info(f"🚀 Starting workflow execution: {workflow_id}")

            # Set the context for tool calls
            self.tool_registry.set_context(ctx)
            logger.debug("Context set for tool registry access")

            # Report progress: Setup complete
            await ctx.report_progress(progress=5, total=100)

            # Validate workflow exists
            if OPENAI_AGENTS_AVAILABLE and custom_span:
                with custom_span("workflow_validation"):
                    workflow_definition = self.workflow_manager.get_workflow(workflow_id)
            else:
                workflow_definition = self.workflow_manager.get_workflow(workflow_id)

            if not workflow_definition:
                # Get available workflows for error message
                available_workflows = self.workflow_manager.list_workflows()
                available_ids = [w.workflow_id for w in available_workflows]
                
                error_msg = f"Workflow '{workflow_id}' not found. Available workflows: {', '.join(available_ids)}"
                logger.error(error_msg)
                await ctx.error(error_msg)
                return {
                    "status": "error",
                    "error": error_msg,
                    "error_type": "workflow_not_found",
                    "available_workflows": available_ids,
                    "execution_time": time.time() - execution_start_time,
                }

            logger.info(f"Workflow found: {workflow_definition.name} with {len(workflow_definition.tasks)} tasks")
            await ctx.info(f"✅ Workflow validated: {workflow_definition.name}")

            # Report progress: Workflow validated
            await ctx.report_progress(progress=10, total=100)

            # Create diagnostic context
            if OPENAI_AGENTS_AVAILABLE and custom_span:
                with custom_span("diagnostic_context_creation"):
                    diagnostic_context = SplunkDiagnosticContext(
                        earliest_time=earliest_time,
                        latest_time=latest_time,
                        focus_index=focus_index,
                        focus_host=focus_host,
                        focus_sourcetype=focus_sourcetype,
                        complexity_level=complexity_level,
                        problem_description=problem_description,
                        workflow_type=workflow_id,
                    )
            else:
                diagnostic_context = SplunkDiagnosticContext(
                    earliest_time=earliest_time,
                    latest_time=latest_time,
                    focus_index=focus_index,
                    focus_host=focus_host,
                    focus_sourcetype=focus_sourcetype,
                    complexity_level=complexity_level,
                    problem_description=problem_description,
                    workflow_type=workflow_id,
                )

            logger.info(f"Diagnostic context created for workflow: {workflow_id}")

            # Report progress: Context created
            await ctx.report_progress(progress=15, total=100)

            # Execute the workflow using parallel executor
            logger.info(f"Executing workflow '{workflow_id}' with parallel execution...")
            await ctx.info(f"⚡ Executing {workflow_definition.name} with parallel micro-agents...")

            workflow_start_time = time.time()

            if OPENAI_AGENTS_AVAILABLE and custom_span:
                with custom_span(f"workflow_execution_{workflow_id}"):
                    workflow_result = await self.parallel_executor.execute_workflow(
                        workflow_definition, diagnostic_context, ctx
                    )
            else:
                workflow_result = await self.parallel_executor.execute_workflow(
                    workflow_definition, diagnostic_context, ctx
                )

            workflow_execution_time = time.time() - workflow_start_time
            logger.info(f"Workflow execution completed in {workflow_execution_time:.2f}s")

            # Report progress: Workflow execution complete
            await ctx.report_progress(progress=70, total=100)
            await ctx.info("✅ Workflow execution completed")

            # Execute summarization if enabled
            summarization_result = None
            summarization_execution_time = 0

            if enable_summarization:
                logger.info("Starting summarization analysis...")
                await ctx.info("🧠 Analyzing results and generating comprehensive summary...")

                summarization_start_time = time.time()

                try:
                    if OPENAI_AGENTS_AVAILABLE and custom_span:
                        with custom_span("summarization_analysis"):
                            summarization_result = await self.summarization_tool.execute(
                                ctx=ctx,
                                workflow_results=workflow_result.task_results,
                                problem_description=problem_description or f"Workflow execution: {workflow_id}",
                                diagnostic_context=diagnostic_context,
                                execution_metadata={"workflow_id": workflow_id},
                            )
                    else:
                        summarization_result = await self.summarization_tool.execute(
                            ctx=ctx,
                            workflow_results=workflow_result.task_results,
                            problem_description=problem_description or f"Workflow execution: {workflow_id}",
                            diagnostic_context=diagnostic_context,
                            execution_metadata={"workflow_id": workflow_id},
                        )

                    summarization_execution_time = time.time() - summarization_start_time
                    logger.info(f"Summarization completed in {summarization_execution_time:.2f}s")

                except Exception as e:
                    logger.error(f"Summarization failed: {e}", exc_info=True)
                    summarization_result = {
                        "status": "error",
                        "error": str(e),
                        "executive_summary": f"Summarization failed: {str(e)}",
                    }
                    summarization_execution_time = time.time() - summarization_start_time

            # Report progress: Summarization complete
            await ctx.report_progress(progress=90, total=100)

            total_execution_time = time.time() - execution_start_time

            # Create comprehensive result
            result = {
                "status": workflow_result.status,
                "tool_type": "workflow_runner",
                "workflow_id": workflow_id,
                "workflow_name": workflow_definition.name,
                "workflow_description": workflow_definition.description,
                "problem_description": problem_description,
                "diagnostic_context": {
                    "earliest_time": earliest_time,
                    "latest_time": latest_time,
                    "focus_index": focus_index,
                    "focus_host": focus_host,
                    "focus_sourcetype": focus_sourcetype,
                    "complexity_level": complexity_level,
                },
                "workflow_execution": {
                    "workflow_id": workflow_result.workflow_id,
                    "overall_status": workflow_result.status,
                    "execution_method": "parallel_phases",
                    "total_tasks": len(workflow_result.task_results),
                    "successful_tasks": len([r for r in workflow_result.task_results.values() if r.status in ["healthy", "warning"]]),
                    "failed_tasks": len([r for r in workflow_result.task_results.values() if r.status == "error"]),
                    "execution_phases": workflow_result.summary.get("execution_phases", 0),
                    "parallel_efficiency": workflow_result.summary.get("parallel_efficiency", 0.0),
                },
                "task_results": {task_id: {
                    "status": result.status,
                    "findings": result.findings,
                    "recommendations": result.recommendations,
                    "details": result.details
                } for task_id, result in workflow_result.task_results.items()},
                "workflow_summary": workflow_result.summary,
                "summarization": {
                    "enabled": enable_summarization,
                    "execution_time": summarization_execution_time,
                    "result": summarization_result,
                } if enable_summarization else {
                    "enabled": False,
                    "reason": "Summarization disabled by user",
                },
                "execution_metadata": {
                    "total_execution_time": total_execution_time,
                    "workflow_execution_time": workflow_execution_time,
                    "summarization_execution_time": summarization_execution_time,
                    "parallel_execution": True,
                    "summarization_enabled": enable_summarization,
                    "tracing_enabled": OPENAI_AGENTS_AVAILABLE and trace is not None,
                },
                "tracing_info": {
                    "trace_available": OPENAI_AGENTS_AVAILABLE and trace is not None,
                    "workflow_traced": True,
                    "summarization_traced": enable_summarization,
                    "trace_name": f"Workflow Runner: {workflow_id} {trace_timestamp}" if OPENAI_AGENTS_AVAILABLE and trace else None,
                },
            }

            # Report final progress
            await ctx.report_progress(progress=100, total=100)
            await ctx.info(f"✅ Workflow runner execution completed: {workflow_result.status}")

            logger.info("=" * 80)
            logger.info("WORKFLOW RUNNER EXECUTION COMPLETED SUCCESSFULLY")
            logger.info(f"Workflow: {workflow_id} ({workflow_definition.name})")
            logger.info(f"Total execution time: {total_execution_time:.2f}s")
            logger.info(f"Workflow execution time: {workflow_execution_time:.2f}s")
            logger.info(f"Summarization time: {summarization_execution_time:.2f}s")
            logger.info(f"Status: {workflow_result.status}")
            logger.info(f"Successful tasks: {len([r for r in workflow_result.task_results.values() if r.status in ['healthy', 'warning']])}/{len(workflow_result.task_results)}")
            logger.info(f"Summarization enabled: {enable_summarization}")
            logger.info("=" * 80)

            return result

        except Exception as e:
            execution_time = time.time() - execution_start_time
            error_msg = f"Workflow runner execution failed: {str(e)}"

            logger.error("=" * 80)
            logger.error("WORKFLOW RUNNER EXECUTION FAILED")
            logger.error(f"Workflow ID: {workflow_id}")
            logger.error(f"Error: {error_msg}")
            logger.error(f"Execution time before failure: {execution_time:.2f} seconds")
            logger.error("=" * 80)
            logger.error("Full error details:", exc_info=True)

            await ctx.error(error_msg)
            return {
                "status": "error",
                "tool_type": "workflow_runner",
                "workflow_id": workflow_id,
                "error": error_msg,
                "error_type": "execution_error",
                "execution_time": execution_time,
                "diagnostic_context": {
                    "earliest_time": earliest_time,
                    "latest_time": latest_time,
                    "focus_index": focus_index,
                    "focus_host": focus_host,
                    "focus_sourcetype": focus_sourcetype,
                    "complexity_level": complexity_level,
                },
                "summarization": {
                    "enabled": enable_summarization,
                    "execution_time": 0,
                    "error": error_msg,
                },
                "tracing_info": {
                    "trace_available": OPENAI_AGENTS_AVAILABLE and trace is not None,
                    "workflow_traced": False,
                    "summarization_traced": False,
                    "error": error_msg,
                },
            } 