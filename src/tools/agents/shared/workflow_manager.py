"""Workflow Manager for Dynamic Micro-Agents

Manages workflow definitions and orchestrates dynamic micro-agents based on tasks.
This enables task-driven parallelization where workflows are defined as sets of tasks,
and each independent task becomes a parallel micro-agent.

Includes comprehensive tracing support for observability.
"""

import asyncio
import logging
import time
from dataclasses import dataclass
from typing import Any

from .config import AgentConfig
from .context import DiagnosticResult, SplunkDiagnosticContext
from .dynamic_agent import (
    AgentExecutionContext,
    TaskDefinition,
    create_dynamic_agent,
)
from .tools import SplunkToolRegistry

logger = logging.getLogger(__name__)

# Import tracing capabilities if available
try:
    from agents import trace, custom_span

    TRACING_AVAILABLE = True
    logger.info("OpenAI Agents tracing capabilities loaded successfully")
except ImportError:
    TRACING_AVAILABLE = False
    trace = None
    custom_span = None
    logger.warning("OpenAI Agents tracing not available")


@dataclass
class WorkflowDefinition:
    """Definition of a workflow containing multiple tasks."""

    workflow_id: str
    name: str
    description: str
    tasks: list[TaskDefinition]
    default_context: dict[str, Any] = None

    def __post_init__(self):
        if self.default_context is None:
            self.default_context = {}


@dataclass
class WorkflowResult:
    """Result from executing a workflow."""

    workflow_id: str
    status: str
    execution_time: float
    task_results: dict[str, DiagnosticResult]
    dependency_graph: dict[str, list[str]]
    execution_order: list[list[str]]  # List of parallel execution phases
    summary: dict[str, Any]


class WorkflowManager:
    """
    Manages workflow definitions and orchestrates dynamic micro-agents.

    This manager:
    1. Defines workflows as sets of tasks
    2. Analyzes task dependencies to determine parallel execution opportunities
    3. Creates dynamic micro-agents for each task
    4. Orchestrates parallel execution of independent tasks
    5. Manages dependency resolution between tasks
    6. Synthesizes results from all tasks
    """

    def __init__(self, config: AgentConfig, tool_registry: SplunkToolRegistry):
        self.config = config
        self.tool_registry = tool_registry
        self.workflows: dict[str, WorkflowDefinition] = {}

        logger.info("Initializing WorkflowManager...")
        logger.debug(f"Config: model={self.config.model}, temperature={self.config.temperature}")
        logger.debug(f"Tool registry available tools: {self.tool_registry.get_available_tools()}")

        # Register built-in workflows
        logger.info("Registering built-in workflows...")
        self._register_builtin_workflows()

        logger.info(f"WorkflowManager initialized with {len(self.workflows)} workflows")
        for workflow_id, workflow in self.workflows.items():
            logger.debug(f"  - {workflow_id}: {workflow.name} ({len(workflow.tasks)} tasks)")

    def _register_builtin_workflows(self):
        """Register built-in workflows for common Splunk troubleshooting scenarios."""

        logger.debug("Creating missing data troubleshooting workflow...")
        # Missing Data Troubleshooting Workflow
        missing_data_workflow = self._create_missing_data_workflow()
        self.register_workflow(missing_data_workflow)

        logger.debug("Creating performance analysis workflow...")
        # Performance Analysis Workflow
        performance_workflow = self._create_performance_workflow()
        self.register_workflow(performance_workflow)

        logger.debug("Creating basic health check workflow...")
        # Basic Health Check Workflow
        health_check_workflow = self._create_health_check_workflow()
        self.register_workflow(health_check_workflow)

        logger.info("All built-in workflows registered successfully")

    def _create_missing_data_workflow(self) -> WorkflowDefinition:
        """Create the missing data troubleshooting workflow."""

        tasks = [
            TaskDefinition(
                task_id="license_verification",
                name="License & Edition Verification",
                description="Check Splunk license and edition status",
                instructions="""
You are verifying Splunk license and edition information.

**Task:** Check Splunk license state and edition type
**Tools:** Use run_splunk_search to query server info
**Query:** | rest /services/server/info | fields splunk_version, product_type, license_state

**Analysis:**
1. Check if running Splunk Free (has limitations)
2. Verify license state (OK, expired, violation)
3. Note version and product type
4. Identify any license-related issues that could affect data access

**Output:** Return DiagnosticResult with license status and any issues found.
                """,
                required_tools=["run_splunk_search", "get_current_user_info"],
                dependencies=[],  # No dependencies - can run in parallel
                context_requirements=[],
            ),
            TaskDefinition(
                task_id="index_verification",
                name="Index Verification",
                description="Verify target indexes exist and are accessible",
                instructions="""
You are verifying index existence and accessibility.

**Task:** Check if target indexes {indexes} exist and are accessible
**Tools:** Use list_indexes and run_splunk_search for access testing

**Analysis:**
1. Get list of available indexes
2. Check if target indexes {indexes} exist
3. Test accessibility with simple metadata search for each index
4. Identify missing or inaccessible indexes

**Output:** Return DiagnosticResult with index status and accessibility issues.
                """,
                required_tools=["list_splunk_indexes", "run_splunk_search"],
                dependencies=[],  # No dependencies - can run in parallel
                context_requirements=["indexes"],
            ),
            TaskDefinition(
                task_id="permissions_verification",
                name="Permissions & Access Control",
                description="Verify user permissions and role-based access",
                instructions="""
You are verifying user permissions and access control.

**Task:** Check user permissions for data access
**Dependencies:** Use license verification results if available for user info

**Analysis:**
1. Get current user information and roles
2. Test basic search permissions
3. Check access to target indexes {indexes} if specified
4. Verify role-based index access restrictions
5. Check search filters based on role permissions

**Output:** Return DiagnosticResult with permission status and access issues.
                """,
                required_tools=["get_current_user_info", "run_splunk_search"],
                dependencies=["license_verification"],  # Depends on license for user info
                context_requirements=["earliest_time", "latest_time"],
            ),
            TaskDefinition(
                task_id="time_range_verification",
                name="Time Range Issues Analysis",
                description="Check data availability in specified time range and time-related problems",
                instructions="""
You are verifying data availability in the specified time range and analyzing time-related issues.

**Task:** Check for data in time range {earliest_time} to {latest_time} and identify time-related problems
**Context:** Target indexes: {indexes}, sourcetypes: {sourcetypes}

**Analysis:**
1. Build appropriate search query based on available context
2. Execute count query for the time range
3. Check for data gaps or missing recent data
4. Analyze time distribution if significant data found
5. Check for indexing delays using _indextime vs _time
6. Verify timezone settings and future-timestamped events
7. Try "All time" search to catch timing issues

**Output:** Return DiagnosticResult with data availability status and time-related recommendations.
                """,
                required_tools=["run_splunk_search"],
                dependencies=[],  # No dependencies - can run in parallel
                context_requirements=["earliest_time", "latest_time", "focus_index"],
            ),
            TaskDefinition(
                task_id="forwarder_connectivity",
                name="Forwarder Connectivity Analysis",
                description="Check forwarder connections and data flow",
                instructions="""
You are analyzing forwarder connectivity and data flow.

**Task:** Check forwarder connections and data ingestion pipeline
**Context:** Focus host: {focus_host} if specified, index: {focus_index} if specified

**Analysis:**
1. Verify forwarders connecting using tcpin_connections metrics
2. Check output queues for tcpout connections
3. Verify recent host activity using metadata
4. Check connection logs for "Connected to idx" or "cooked mode"
5. Analyze forwarder throughput and connection stability
6. Identify connection drops or network issues

**Searches:**
- index=_internal source=*metrics.log* tcpin_connections | stats count by sourceIp
- index=_internal source=*metrics.log* group=queue tcpout | stats count by name
- | metadata type=hosts index={focus_index} | eval diff=now()-recentTime | where diff < 600
- index=_internal "Connected to idx" OR "cooked mode"

**Output:** Return DiagnosticResult with forwarder connectivity status and issues.
                """,
                required_tools=["run_splunk_search"],
                dependencies=[],  # No dependencies - can run in parallel
                context_requirements=["earliest_time", "latest_time", "focus_index", "focus_host"],
            ),
            TaskDefinition(
                task_id="search_head_configuration",
                name="Search Head Configuration Verification",
                description="Verify search head setup in distributed environments",
                instructions="""
You are verifying search head configuration in distributed environments.

**Task:** Check search head setup and distributed search configuration

**Analysis:**
1. Check search heads are connected to correct indexers
2. Verify distributed search configuration
3. Check search head cluster status if applicable
4. Identify search head connectivity issues
5. Verify search head can reach all required indexers

**Searches:**
- | rest /services/search/distributed/peers | table title, status, is_https
- | rest /services/shcluster/status | table label, status
- index=_internal source=*splunkd.log* component=DistributedSearch

**Output:** Return DiagnosticResult with search head configuration status and issues.
                """,
                required_tools=["run_splunk_search"],
                dependencies=[],  # No dependencies - can run in parallel
                context_requirements=["earliest_time", "latest_time"],
            ),
            TaskDefinition(
                task_id="license_violations_check",
                name="License Violations Analysis",
                description="Check for license violations that prevent searching",
                instructions="""
You are checking for license violations that could prevent data searching.

**Task:** Analyze license usage and violations that block search functionality

**Analysis:**
1. Check for license violations that prevent searching (indexing continues)
2. Analyze license pool usage and quotas
3. Check license violation messages and warnings
4. Identify license-related search restrictions
5. Verify license compliance across pools

**Searches:**
- index=_internal source=*license_usage.log* type=Usage | stats sum(b) by pool
- | rest /services/licenser/messages | table category, message
- index=_internal source=*splunkd.log* LicenseManager | search "pool quota"
- index=_internal source=*license_usage.log* type=RolloverSummary

**Output:** Return DiagnosticResult with license violation status and impact on search capability.
                """,
                required_tools=["run_splunk_search"],
                dependencies=["license_verification"],  # Depends on basic license info
                context_requirements=["earliest_time", "latest_time"],
            ),
            TaskDefinition(
                task_id="scheduled_search_issues",
                name="Scheduled Search Issues Analysis",
                description="Analyze scheduled search performance and configuration",
                instructions="""
You are analyzing scheduled search issues and performance.

**Task:** Check scheduled search configuration and execution issues
**Context:** Time range: {earliest_time} to {latest_time}

**Analysis:**
1. Verify time ranges aren't excluding events in scheduled searches
2. Check for indexing lag affecting recent data in schedules
3. Examine scheduler performance and queue status
4. Identify failed or slow scheduled searches
5. Check search concurrency limits affecting schedules
6. Analyze scheduler.log for performance issues

**Searches:**
- index=_internal source=*scheduler.log* | stats count by status
- index=_internal source=*scheduler.log* | search status=failed | head 10
- index=_internal source=*scheduler.log* | stats avg(run_time) by search_type
- index=_internal source=*metrics.log* group=searchscheduler

**Output:** Return DiagnosticResult with scheduled search status and performance issues.
                """,
                required_tools=["run_splunk_search"],
                dependencies=[],  # No dependencies - can run in parallel
                context_requirements=["earliest_time", "latest_time"],
            ),
            TaskDefinition(
                task_id="search_query_validation",
                name="Search Query Syntax Validation",
                description="Validate search query syntax and logic",
                instructions="""
You are validating search query syntax and logic for common issues.

**Task:** Check for common search syntax problems that prevent data retrieval

**Analysis:**
1. Check logic operators (NOT, AND, OR) usage patterns
2. Verify quote usage and escape characters in searches
3. Confirm correct index, source, sourcetype, host specifications
4. Test subsearch ordering and field passing
5. Check for intentions framework rewrites in drilldowns
6. Validate field names and search syntax
7. Look for common syntax errors in user searches

**Searches:**
- index=_audit action=search | search search!="*typeahead*" | head 10
- index=_internal source=*splunkd.log* component=SearchParser
- index=_internal source=*splunkd.log* "syntax error" OR "parse error"

**Output:** Return DiagnosticResult with search syntax validation status and common issues found.
                """,
                required_tools=["run_splunk_search"],
                dependencies=[],  # No dependencies - can run in parallel
                context_requirements=["earliest_time", "latest_time"],
            ),
            TaskDefinition(
                task_id="field_extraction_issues",
                name="Field Extraction Issues Analysis",
                description="Check field extraction problems and configuration",
                instructions="""
You are analyzing field extraction issues and configuration problems.

**Task:** Check field extraction configuration and functionality

**Analysis:**
1. Test regex patterns with rex command for field extractions
2. Verify extraction permissions and sharing settings
3. Check extractions applied to correct source/sourcetype/host
4. Analyze field extraction performance and conflicts
5. Check for search-time vs index-time extraction issues
6. Verify field extraction precedence and ordering

**Searches:**
- | rest /services/data/props/extractions | search stanza=* | table stanza, attribute, value
- | rest /services/data/transforms/extractions | table stanza, regex, format
- index=_internal source=*splunkd.log* component=AggregatorMiningProcessor
- index=_internal source=*splunkd.log* "Field extraction"

**Output:** Return DiagnosticResult with field extraction status and configuration issues.
                """,
                required_tools=["run_splunk_search"],
                dependencies=[],  # No dependencies - can run in parallel
                context_requirements=["earliest_time", "latest_time"],
            ),
        ]

        return WorkflowDefinition(
            workflow_id="missing_data_troubleshooting",
            name="Missing Data Troubleshooting",
            description="Systematic troubleshooting for missing data issues following Splunk's official workflow",
            tasks=tasks,
        )

    def _create_performance_workflow(self) -> WorkflowDefinition:
        """Create the performance analysis workflow."""

        tasks = [
            TaskDefinition(
                task_id="system_resource_baseline",
                name="System Resource Baseline",
                description="Analyze system resource usage patterns",
                instructions="""
You are analyzing system resource baseline.

**Task:** Check system CPU, memory, and disk usage patterns
**Tools:** Use run_splunk_search to query introspection data

**Analysis:**
1. Query _introspection index for Hostwide component data
2. Check CPU usage patterns (system and user)
3. Analyze memory utilization
4. Identify hosts with high resource usage (>80%)

**Output:** Return DiagnosticResult with resource usage status and bottlenecks.
                """,
                required_tools=["run_splunk_search"],
                dependencies=[],
                context_requirements=["earliest_time", "latest_time"],
            ),
            TaskDefinition(
                task_id="search_concurrency_analysis",
                name="Search Concurrency Analysis",
                description="Analyze search concurrency and performance",
                instructions="""
You are analyzing search concurrency and performance.

**Task:** Check search concurrency patterns and limits
**Time Range:** {earliest_time} to {latest_time}

**Analysis:**
1. Query _introspection for search concurrency data
2. Check if hitting configured limits
3. Analyze scheduler.log for search performance
4. Identify slow or failed searches

**Output:** Return DiagnosticResult with search performance status and issues.
                """,
                required_tools=["run_splunk_search"],
                dependencies=[],
                context_requirements=["earliest_time", "latest_time"],
            ),
            TaskDefinition(
                task_id="indexing_performance_analysis",
                name="Indexing Performance Analysis",
                description="Analyze indexing pipeline performance",
                instructions="""
You are analyzing indexing pipeline performance.

**Task:** Check indexing throughput and pipeline performance
**Context:** Focus on indexes: {indexes}

**Analysis:**
1. Query _internal metrics.log for per_index_thruput
2. Check pipeline processor performance
3. Analyze queue sizes and delays
4. Identify indexing bottlenecks

**Output:** Return DiagnosticResult with indexing performance status and recommendations.
                """,
                required_tools=["run_splunk_search"],
                dependencies=[],
                context_requirements=["earliest_time", "latest_time"],
            ),
        ]

        return WorkflowDefinition(
            workflow_id="performance_analysis",
            name="Performance Analysis",
            description="Comprehensive performance analysis using Splunk Platform Instrumentation",
            tasks=tasks,
        )

    def _create_health_check_workflow(self) -> WorkflowDefinition:
        """Create a basic health check workflow."""

        tasks = [
            TaskDefinition(
                task_id="connectivity_check",
                name="Connectivity Check",
                description="Verify Splunk server connectivity and health",
                instructions="""
You are performing a basic connectivity check.

**Task:** Verify Splunk server is accessible and responsive
**Tools:** Use get_splunk_health for server status

**Analysis:**
1. Check server connectivity and response
2. Verify basic service availability
3. Note any connection issues or warnings

**Output:** Return DiagnosticResult with connectivity status.
                """,
                required_tools=["get_splunk_health"],
                dependencies=[],
                context_requirements=[],
            ),
            TaskDefinition(
                task_id="basic_data_check",
                name="Basic Data Check",
                description="Verify basic data availability",
                instructions="""
You are performing a basic data availability check.

**Task:** Check for recent data ingestion
**Time Range:** {earliest_time} to {latest_time}

**Analysis:**
1. Run simple search for recent data
2. Check multiple indexes if available
3. Verify data is being ingested

**Output:** Return DiagnosticResult with data availability status.
                """,
                required_tools=["run_splunk_search", "list_splunk_indexes"],
                dependencies=[],
                context_requirements=["earliest_time", "latest_time"],
            ),
        ]

        return WorkflowDefinition(
            workflow_id="health_check",
            name="Basic Health Check",
            description="Quick health check for Splunk connectivity and data availability",
            tasks=tasks,
        )

    def register_workflow(self, workflow: WorkflowDefinition):
        """Register a workflow definition."""
        logger.debug(f"Registering workflow: {workflow.workflow_id}")
        logger.debug(f"  Name: {workflow.name}")
        logger.debug(f"  Description: {workflow.description}")
        logger.debug(f"  Tasks: {len(workflow.tasks)}")

        # Log task details
        for task in workflow.tasks:
            logger.debug(f"    Task: {task.task_id} ({task.name})")
            logger.debug(f"      Required tools: {task.required_tools}")
            logger.debug(f"      Dependencies: {task.dependencies}")
            logger.debug(f"      Context requirements: {task.context_requirements}")

        self.workflows[workflow.workflow_id] = workflow
        logger.info(
            f"Registered workflow: {workflow.name} ({workflow.workflow_id}) with {len(workflow.tasks)} tasks"
        )

    def get_workflow(self, workflow_id: str) -> WorkflowDefinition | None:
        """Get a workflow definition by ID."""
        return self.workflows.get(workflow_id)

    def list_workflows(self) -> list[WorkflowDefinition]:
        """List all available workflows."""
        return list(self.workflows.values())

    async def execute_workflow(
        self,
        workflow_id: str,
        diagnostic_context: SplunkDiagnosticContext,
        execution_metadata: dict[str, Any] = None,
    ) -> WorkflowResult:
        """
        Execute a workflow with comprehensive tracing support.

        Args:
            workflow_id: ID of the workflow to execute
            diagnostic_context: Context for the diagnostic analysis
            execution_metadata: Optional metadata for execution

        Returns:
            WorkflowResult with execution details and task results
        """
        start_time = time.time()
        
        if execution_metadata is None:
            execution_metadata = {}

        logger.info(f"Starting workflow execution: {workflow_id}")
        logger.debug(f"Diagnostic context: {diagnostic_context}")
        logger.debug(f"Execution metadata: {execution_metadata}")

        # Create comprehensive trace for workflow execution
        if TRACING_AVAILABLE and trace:
            workflow_name = f"Splunk Workflow: {workflow_id}"
            trace_metadata = {
                "workflow_id": workflow_id,
                "diagnostic_context": {
                    "earliest_time": diagnostic_context.earliest_time,
                    "latest_time": diagnostic_context.latest_time,
                    "focus_index": diagnostic_context.focus_index,
                    "focus_host": diagnostic_context.focus_host,
                    "complexity_level": diagnostic_context.complexity_level,
                },
                "execution_metadata": execution_metadata,
            }
            
            with trace(workflow_name=workflow_name, metadata=trace_metadata):
                return await self._execute_workflow_core(
                    workflow_id, diagnostic_context, execution_metadata, start_time
                )
        else:
            logger.debug("Tracing not available, executing workflow without traces")
            return await self._execute_workflow_core(
                workflow_id, diagnostic_context, execution_metadata, start_time
            )

    async def _execute_workflow_core(
        self,
        workflow_id: str,
        diagnostic_context: SplunkDiagnosticContext,
        execution_metadata: dict[str, Any],
        start_time: float,
    ) -> WorkflowResult:
        """Core workflow execution with tracing spans."""
        
        try:
            # Get workflow definition with tracing
            if TRACING_AVAILABLE and custom_span:
                with custom_span("workflow_definition_lookup") as span:
                    span.set_attribute("workflow_id", workflow_id)
                    
                    workflow = self.get_workflow(workflow_id)
                    if not workflow:
                        span.set_attribute("workflow_found", False)
                        raise ValueError(f"Workflow '{workflow_id}' not found")
                    
                    span.set_attribute("workflow_found", True)
                    span.set_attribute("task_count", len(workflow.tasks))
                    logger.info(f"Found workflow: {workflow.name} with {len(workflow.tasks)} tasks")
            else:
                workflow = self.get_workflow(workflow_id)
                if not workflow:
                    raise ValueError(f"Workflow '{workflow_id}' not found")
                logger.info(f"Found workflow: {workflow.name} with {len(workflow.tasks)} tasks")

            # Build dependency graph with tracing
            if TRACING_AVAILABLE and custom_span:
                with custom_span("dependency_analysis") as span:
                    dependency_graph = self._build_dependency_graph(workflow.tasks)
                    execution_phases = self._create_execution_phases(workflow.tasks, dependency_graph)
                    
                    span.set_attribute("total_tasks", len(workflow.tasks))
                    span.set_attribute("execution_phases", len(execution_phases))
                    span.set_attribute("parallel_efficiency", 
                                     self._calculate_parallel_efficiency(workflow.tasks, execution_phases))
                    
                    logger.info(f"Dependency analysis complete:")
                    logger.info(f"  - Total tasks: {len(workflow.tasks)}")
                    logger.info(f"  - Execution phases: {len(execution_phases)}")
                    logger.info(f"  - Dependency graph: {dependency_graph}")
                    logger.info(f"  - Execution order: {execution_phases}")
            else:
                dependency_graph = self._build_dependency_graph(workflow.tasks)
                execution_phases = self._create_execution_phases(workflow.tasks, dependency_graph)
                
                logger.info(f"Dependency analysis complete:")
                logger.info(f"  - Total tasks: {len(workflow.tasks)}")
                logger.info(f"  - Execution phases: {len(execution_phases)}")
                logger.info(f"  - Dependency graph: {dependency_graph}")
                logger.info(f"  - Execution order: {execution_phases}")

            # Execute tasks in phases with comprehensive tracing
            task_results: dict[str, DiagnosticResult] = {}
            
            for phase_idx, phase_tasks in enumerate(execution_phases):
                phase_name = f"execution_phase_{phase_idx + 1}"
                logger.info(f"Executing phase {phase_idx + 1}/{len(execution_phases)}: {phase_tasks}")
                
                if TRACING_AVAILABLE and custom_span:
                    with custom_span(phase_name) as phase_span:
                        phase_span.set_attribute("phase_number", phase_idx + 1)
                        phase_span.set_attribute("phase_tasks", phase_tasks)
                        phase_span.set_attribute("task_count", len(phase_tasks))
                        
                        # Execute tasks in this phase (potentially in parallel)
                        phase_results = await self._execute_phase_with_tracing(
                            workflow, phase_tasks, diagnostic_context, task_results
                        )
                        
                        # Update task results
                        task_results.update(phase_results)
                        
                        # Add phase completion metrics
                        successful_tasks = [task_id for task_id, result in phase_results.items() 
                                          if result.status in ["healthy", "warning"]]
                        failed_tasks = [task_id for task_id, result in phase_results.items() 
                                      if result.status == "error"]
                        
                        phase_span.set_attribute("successful_tasks", len(successful_tasks))
                        phase_span.set_attribute("failed_tasks", len(failed_tasks))
                        phase_span.set_attribute("phase_success_rate", 
                                               len(successful_tasks) / len(phase_tasks) if phase_tasks else 0)
                        
                        logger.info(f"Phase {phase_idx + 1} completed: {len(successful_tasks)} successful, {len(failed_tasks)} failed")
                else:
                    # Execute tasks in this phase (potentially in parallel)
                    phase_results = await self._execute_phase_with_tracing(
                        workflow, phase_tasks, diagnostic_context, task_results
                    )
                    
                    # Update task results
                    task_results.update(phase_results)
                    
                    successful_tasks = [task_id for task_id, result in phase_results.items() 
                                      if result.status in ["healthy", "warning"]]
                    failed_tasks = [task_id for task_id, result in phase_results.items() 
                                  if result.status == "error"]
                    
                    logger.info(f"Phase {phase_idx + 1} completed: {len(successful_tasks)} successful, {len(failed_tasks)} failed")

            # Finalize workflow result with tracing
            if TRACING_AVAILABLE and custom_span:
                with custom_span("workflow_result_synthesis") as span:
                    span.set_attribute("total_tasks_executed", len(task_results))
                    
                    workflow_result = await self._finalize_workflow_result(
                        workflow_id, workflow, task_results, execution_phases, start_time
                    )
                    
                    span.set_attribute("workflow_status", workflow_result.status)
                    span.set_attribute("execution_time", workflow_result.execution_time)
                    
                    logger.info(f"Workflow result synthesis completed")
                    logger.info(f"  - Overall status: {workflow_result.status}")
                    logger.info(f"  - Execution time: {workflow_result.execution_time:.2f}s")
                    
                    return workflow_result
            else:
                workflow_result = await self._finalize_workflow_result(
                    workflow_id, workflow, task_results, execution_phases, start_time
                )
                
                logger.info(f"Workflow result synthesis completed")
                logger.info(f"  - Overall status: {workflow_result.status}")
                logger.info(f"  - Execution time: {workflow_result.execution_time:.2f}s")
                
                return workflow_result

        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"Workflow execution failed: {e}", exc_info=True)
            
            # Create error result
            return WorkflowResult(
                workflow_id=workflow_id,
                status="error",
                execution_time=execution_time,
                task_results={},
                dependency_graph={},
                execution_order=[],
                summary={
                    "error": str(e),
                    "execution_time": execution_time,
                    "tasks_completed": 0,
                    "successful_tasks": 0,
                    "failed_tasks": 0,
                },
            )

    async def _execute_phase_with_tracing(
        self,
        workflow: WorkflowDefinition,
        phase_tasks: list[str],
        diagnostic_context: SplunkDiagnosticContext,
        completed_task_results: dict[str, DiagnosticResult],
    ) -> dict[str, DiagnosticResult]:
        """Execute a phase of tasks with individual task tracing."""
        
        phase_results = {}
        
        # Create tasks for parallel execution
        async_tasks = []
        
        for task_id in phase_tasks:
            # Find task definition
            task_def = next((task for task in workflow.tasks if task.task_id == task_id), None)
            if not task_def:
                logger.error(f"Task definition not found for task_id: {task_id}")
                continue
            
            # Create execution context
            execution_context = AgentExecutionContext(
                task_definition=task_def,
                diagnostic_context=diagnostic_context,
                dependency_results={
                    dep_id: completed_task_results[dep_id]
                    for dep_id in task_def.dependencies
                    if dep_id in completed_task_results
                },
            )
            
            # Create dynamic agent and execute task with tracing
            if TRACING_AVAILABLE and custom_span:
                async_tasks.append(
                    self._execute_single_task_with_tracing(task_def, execution_context)
                )
            else:
                async_tasks.append(
                    self._execute_single_task_without_tracing(task_def, execution_context)
                )
        
        # Execute tasks in parallel
        if async_tasks:
            logger.info(f"Executing {len(async_tasks)} tasks in parallel...")
            results = await asyncio.gather(*async_tasks, return_exceptions=True)
            
            # Process results
            for i, result in enumerate(results):
                task_id = phase_tasks[i]
                if isinstance(result, Exception):
                    logger.error(f"Task {task_id} failed with exception: {result}")
                    phase_results[task_id] = DiagnosticResult(
                        step=task_id,
                        status="error",
                        findings=[f"Task execution failed: {str(result)}"],
                        recommendations=["Check task configuration and retry"],
                        details={"error": str(result)},
                    )
                else:
                    phase_results[task_id] = result
                    logger.debug(f"Task {task_id} completed with status: {result.status}")
        
        return phase_results

    async def _execute_single_task_with_tracing(
        self,
        task_def: TaskDefinition,
        execution_context: AgentExecutionContext,
    ) -> DiagnosticResult:
        """Execute a single task with comprehensive tracing."""
        
        with custom_span(f"task_execution_{task_def.task_id}") as span:
            span.set_attribute("task_id", task_def.task_id)
            span.set_attribute("task_name", task_def.name)
            span.set_attribute("required_tools", task_def.required_tools)
            span.set_attribute("dependencies", task_def.dependencies)
            
            # Create and execute dynamic agent
            dynamic_agent = create_dynamic_agent(self.config, self.tool_registry, task_def)
            
            try:
                result = await dynamic_agent.execute_task(execution_context)
                
                span.set_attribute("task_status", result.status)
                span.set_attribute("findings_count", len(result.findings))
                span.set_attribute("recommendations_count", len(result.recommendations))
                
                return result
                
            except Exception as e:
                span.set_attribute("task_status", "error")
                span.set_attribute("error", str(e))
                
                logger.error(f"Task {task_def.task_id} execution failed: {e}", exc_info=True)
                raise

    async def _execute_single_task_without_tracing(
        self,
        task_def: TaskDefinition,
        execution_context: AgentExecutionContext,
    ) -> DiagnosticResult:
        """Execute a single task without tracing (fallback)."""
        
        # Create and execute dynamic agent
        dynamic_agent = create_dynamic_agent(self.config, self.tool_registry, task_def)
        return await dynamic_agent.execute_task(execution_context)

    async def _finalize_workflow_result(
        self,
        workflow_id: str,
        workflow: "WorkflowDefinition",
        task_results: dict[str, DiagnosticResult],
        execution_phases: list[list[str]],
        start_time: float,
    ) -> WorkflowResult:
        """Finalize workflow result with summary and analysis."""
        total_time = time.time() - start_time

        logger.info("=" * 60)
        logger.info("GENERATING WORKFLOW SUMMARY")
        logger.info("=" * 60)

        # Generate summary
        logger.debug("Generating workflow summary...")
        summary = self._generate_workflow_summary(workflow, task_results, execution_phases)
        logger.debug(
            f"Summary generated with {summary.get('total_findings', 0)} findings and {summary.get('total_recommendations', 0)} recommendations"
        )

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

        result = WorkflowResult(
            workflow_id=workflow_id,
            status=overall_status,
            execution_time=total_time,
            task_results=task_results,
            dependency_graph=dependency_graph,
            execution_order=execution_phases,
            summary=summary,
        )

        logger.info("=" * 80)
        logger.info(f"WORKFLOW EXECUTION COMPLETED: {workflow_id}")
        logger.info(f"Total execution time: {total_time:.2f}s")
        logger.info(f"Overall status: {result.status}")
        logger.info(f"Tasks completed: {len(task_results)}")
        logger.info(f"Execution phases: {len(execution_phases)}")
        logger.info(f"Parallel efficiency: {summary.get('parallel_efficiency', 0):.1%}")
        logger.info("=" * 80)

        return result

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
    ) -> list[list[str]]:
        """Create execution phases based on task dependencies."""

        logger.debug("Creating execution phases from dependency graph...")
        phases = []
        completed = set()
        task_ids = {task.task_id for task in tasks}
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
                        ready_tasks.append(task_id)
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
                phases.append(list(remaining))
                break

            logger.debug(f"Phase {phase_num}: {len(ready_tasks)} tasks ready - {ready_tasks}")
            phases.append(ready_tasks)
            completed.update(ready_tasks)

            logger.debug(
                f"Phase {phase_num} completed. Total completed: {len(completed)}/{len(task_ids)}"
            )

        logger.debug(f"Execution phases created: {len(phases)} phases total")
        for i, phase in enumerate(phases):
            logger.debug(f"  Phase {i + 1}: {phase}")

        return phases

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

    def _generate_workflow_summary(
        self,
        workflow: WorkflowDefinition,
        task_results: dict[str, DiagnosticResult],
        execution_phases: list[list[str]],
    ) -> dict[str, Any]:
        """Generate a comprehensive summary of workflow execution."""

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
            "total_tasks": len(workflow.tasks),
            "execution_phases": len(execution_phases),
            "parallel_efficiency": self._calculate_parallel_efficiency(
                workflow.tasks, execution_phases
            ),
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
        }

    def _calculate_parallel_efficiency(
        self, tasks: list[TaskDefinition], execution_phases: list[list[str]]
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


# Convenience functions for common workflows
async def execute_missing_data_workflow(
    workflow_manager: WorkflowManager, diagnostic_context: SplunkDiagnosticContext
) -> WorkflowResult:
    """Execute the missing data troubleshooting workflow."""
    return await workflow_manager.execute_workflow(
        "missing_data_troubleshooting", diagnostic_context
    )


async def execute_performance_workflow(
    workflow_manager: WorkflowManager, diagnostic_context: SplunkDiagnosticContext
) -> WorkflowResult:
    """Execute the performance analysis workflow."""
    return await workflow_manager.execute_workflow("performance_analysis", diagnostic_context)


async def execute_health_check_workflow(
    workflow_manager: WorkflowManager, diagnostic_context: SplunkDiagnosticContext
) -> WorkflowResult:
    """Execute the basic health check workflow."""
    return await workflow_manager.execute_workflow("health_check", diagnostic_context)
