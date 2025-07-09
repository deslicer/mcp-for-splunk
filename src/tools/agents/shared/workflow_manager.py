"""Workflow Manager for Dynamic Micro-Agents

Manages workflow definitions and orchestrates dynamic micro-agents based on tasks.
This enables task-driven parallelization where workflows are defined as sets of tasks,
and each independent task becomes a parallel micro-agent.

Includes comprehensive tracing support for observability.
"""

import asyncio
import time
import logging
from typing import Dict, Any, List, Optional, Set
from dataclasses import dataclass
from .config import AgentConfig
from .context import SplunkDiagnosticContext, DiagnosticResult
from .tools import SplunkToolRegistry
from .dynamic_agent import TaskDefinition, AgentExecutionContext, DynamicMicroAgent, create_dynamic_agent

logger = logging.getLogger(__name__)

# Import tracing capabilities if available
try:
    from agents import trace
    from agents.tracing import TraceProvider, add_trace_processor, set_trace_processors
    TRACING_AVAILABLE = True
    logger.info("OpenAI Agents tracing capabilities loaded successfully")
except ImportError:
    TRACING_AVAILABLE = False
    trace = None
    TraceProvider = None
    add_trace_processor = None
    set_trace_processors = None
    logger.warning("OpenAI Agents tracing not available")


@dataclass
class WorkflowDefinition:
    """Definition of a workflow containing multiple tasks."""
    
    workflow_id: str
    name: str
    description: str
    tasks: List[TaskDefinition]
    default_context: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.default_context is None:
            self.default_context = {}


@dataclass
class WorkflowResult:
    """Result from executing a workflow."""
    
    workflow_id: str
    status: str
    execution_time: float
    task_results: Dict[str, DiagnosticResult]
    dependency_graph: Dict[str, List[str]]
    execution_order: List[List[str]]  # List of parallel execution phases
    summary: Dict[str, Any]


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
        self.workflows: Dict[str, WorkflowDefinition] = {}
        
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
**Tools:** Use run_oneshot_search to query server info
**Query:** | rest /services/server/info | fields splunk_version, product_type, license_state

**Analysis:**
1. Check if running Splunk Free (has limitations)
2. Verify license state (OK, expired, violation)
3. Note version and product type
4. Identify any license-related issues that could affect data access

**Output:** Return DiagnosticResult with license status and any issues found.
                """,
                required_tools=["run_oneshot_search", "get_current_user_info"],
                dependencies=[],  # No dependencies - can run in parallel
                context_requirements=[]
            ),
            
            TaskDefinition(
                task_id="index_verification", 
                name="Index Verification",
                description="Verify target indexes exist and are accessible",
                instructions="""
You are verifying index existence and accessibility.

**Task:** Check if target indexes {indexes} exist and are accessible
**Tools:** Use list_indexes and run_oneshot_search for access testing

**Analysis:**
1. Get list of available indexes
2. Check if target indexes {indexes} exist
3. Test accessibility with simple metadata search for each index
4. Identify missing or inaccessible indexes

**Output:** Return DiagnosticResult with index status and accessibility issues.
                """,
                required_tools=["list_splunk_indexes", "run_oneshot_search"],
                dependencies=[],  # No dependencies - can run in parallel
                context_requirements=["indexes"]
            ),
            
            TaskDefinition(
                task_id="time_range_verification",
                name="Time Range Verification", 
                description="Check data availability in specified time range",
                instructions="""
You are verifying data availability in the specified time range.

**Task:** Check for data in time range {earliest_time} to {latest_time}
**Context:** Target indexes: {indexes}, sourcetypes: {sourcetypes}

**Analysis:**
1. Build appropriate search query based on available context
2. Execute count query for the time range
3. Check for data gaps or missing recent data
4. Analyze time distribution if significant data found

**Output:** Return DiagnosticResult with data availability status and recommendations.
                """,
                required_tools=["run_oneshot_search"],
                dependencies=[],  # No dependencies - can run in parallel
                context_requirements=["earliest_time", "latest_time"]
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
4. Identify permission-related issues

**Output:** Return DiagnosticResult with permission status and access issues.
                """,
                required_tools=["get_current_user_info", "run_oneshot_search"],
                dependencies=["license_verification"],  # Depends on license for user info
                context_requirements=[]
            )
        ]
        
        return WorkflowDefinition(
            workflow_id="missing_data_troubleshooting",
            name="Missing Data Troubleshooting",
            description="Systematic troubleshooting for missing data issues following Splunk's official workflow",
            tasks=tasks
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
**Tools:** Use run_oneshot_search to query introspection data

**Analysis:**
1. Query _introspection index for Hostwide component data
2. Check CPU usage patterns (system and user)
3. Analyze memory utilization
4. Identify hosts with high resource usage (>80%)

**Output:** Return DiagnosticResult with resource usage status and bottlenecks.
                """,
                required_tools=["run_oneshot_search"],
                dependencies=[],
                context_requirements=["earliest_time", "latest_time"]
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
                required_tools=["run_oneshot_search"],
                dependencies=[],
                context_requirements=["earliest_time", "latest_time"]
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
                required_tools=["run_oneshot_search"],
                dependencies=[],
                context_requirements=["earliest_time", "latest_time"]
            )
        ]
        
        return WorkflowDefinition(
            workflow_id="performance_analysis",
            name="Performance Analysis",
            description="Comprehensive performance analysis using Splunk Platform Instrumentation",
            tasks=tasks
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
                context_requirements=[]
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
                required_tools=["run_oneshot_search", "list_splunk_indexes"],
                dependencies=[],
                context_requirements=["earliest_time", "latest_time"]
            )
        ]
        
        return WorkflowDefinition(
            workflow_id="health_check",
            name="Basic Health Check",
            description="Quick health check for Splunk connectivity and data availability",
            tasks=tasks
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
        logger.info(f"Registered workflow: {workflow.name} ({workflow.workflow_id}) with {len(workflow.tasks)} tasks")
    
    def get_workflow(self, workflow_id: str) -> Optional[WorkflowDefinition]:
        """Get a workflow definition by ID."""
        return self.workflows.get(workflow_id)
    
    def list_workflows(self) -> List[WorkflowDefinition]:
        """List all available workflows."""
        return list(self.workflows.values())
    
    async def execute_workflow(self,
                             workflow_id: str,
                             diagnostic_context: SplunkDiagnosticContext,
                             execution_metadata: Dict[str, Any] = None) -> WorkflowResult:
        """
        Execute a workflow using dynamic micro-agents with comprehensive tracing.
        
        Args:
            workflow_id: ID of the workflow to execute
            diagnostic_context: Context for the diagnostic session
            execution_metadata: Additional metadata for execution
            
        Returns:
            WorkflowResult with execution results and analysis
        """
        start_time = time.time()
        
        if execution_metadata is None:
            execution_metadata = {}
        
        logger.info("="*80)
        logger.info(f"STARTING WORKFLOW EXECUTION: {workflow_id}")
        logger.info("="*80)
        
        # Start tracing if available
        if TRACING_AVAILABLE:
            with trace(f"workflow_execution_{workflow_id}") as workflow_trace:
                workflow_trace.set_attribute("workflow.id", workflow_id)
                workflow_trace.set_attribute("workflow.diagnostic_context.earliest_time", diagnostic_context.earliest_time)
                workflow_trace.set_attribute("workflow.diagnostic_context.latest_time", diagnostic_context.latest_time)
                workflow_trace.set_attribute("workflow.diagnostic_context.focus_index", diagnostic_context.focus_index or "")
                workflow_trace.set_attribute("workflow.diagnostic_context.focus_host", diagnostic_context.focus_host or "")
                workflow_trace.set_attribute("workflow.diagnostic_context.complexity_level", diagnostic_context.complexity_level)
                
                return await self._execute_workflow_with_tracing(
                    workflow_id, diagnostic_context, execution_metadata, start_time, workflow_trace
                )
        else:
            return await self._execute_workflow_without_tracing(
                workflow_id, diagnostic_context, execution_metadata, start_time
            )
    
    async def _execute_workflow_with_tracing(self,
                                           workflow_id: str,
                                           diagnostic_context: SplunkDiagnosticContext,
                                           execution_metadata: Dict[str, Any],
                                           start_time: float,
                                           workflow_trace) -> WorkflowResult:
        """Execute workflow with tracing enabled."""
        with span("workflow_setup") as setup_span:
            setup_span.set_attribute("workflow.id", workflow_id)
            
            logger.info(f"Diagnostic context:")
            logger.info(f"  - Time range: {diagnostic_context.earliest_time} to {diagnostic_context.latest_time}")
            logger.info(f"  - Focus index: {diagnostic_context.focus_index}")
            logger.info(f"  - Focus host: {diagnostic_context.focus_host}")
            logger.info(f"  - Complexity level: {diagnostic_context.complexity_level}")
            logger.info(f"  - Indexes: {diagnostic_context.indexes}")
            logger.info(f"  - Sourcetypes: {diagnostic_context.sourcetypes}")
            logger.info(f"  - Sources: {diagnostic_context.sources}")
            logger.info(f"Execution metadata: {execution_metadata}")
            
            # Get workflow definition
            workflow = self.get_workflow(workflow_id)
            if not workflow:
                error_msg = f"Workflow not found: {workflow_id}"
                logger.error(error_msg)
                logger.error(f"Available workflows: {list(self.workflows.keys())}")
                setup_span.set_attribute("error.message", error_msg)
                raise ValueError(error_msg)
            
            setup_span.set_attribute("workflow.name", workflow.name)
            setup_span.set_attribute("workflow.description", workflow.description)
            setup_span.set_attribute("workflow.total_tasks", len(workflow.tasks))
            
            logger.info(f"Found workflow: {workflow.name}")
            logger.info(f"Description: {workflow.description}")
            logger.info(f"Total tasks: {len(workflow.tasks)}")
            
            # Analyze dependencies and create execution plan
            logger.info("Analyzing task dependencies...")
            dependency_graph = self._build_dependency_graph(workflow.tasks)
            logger.debug(f"Dependency graph: {dependency_graph}")
            
            logger.info("Creating execution phases...")
            execution_phases = self._create_execution_phases(workflow.tasks, dependency_graph)
            
            setup_span.set_attribute("workflow.execution_phases", len(execution_phases))
            
            logger.info(f"Workflow has {len(execution_phases)} execution phases")
            for i, phase in enumerate(execution_phases):
                logger.info(f"  Phase {i+1}: {len(phase)} tasks - {', '.join(phase)}")
            
            # Calculate parallel efficiency
            parallel_efficiency = self._calculate_parallel_efficiency(workflow.tasks, execution_phases)
            setup_span.set_attribute("workflow.parallel_efficiency", parallel_efficiency)
            logger.info(f"Parallel execution efficiency: {parallel_efficiency:.1%}")
        
        # Execute workflow in phases with tracing
        task_results = {}
        
        for phase_num, task_ids in enumerate(execution_phases):
            with span(f"phase_{phase_num + 1}_execution") as phase_span:
                phase_span.set_attribute("phase.number", phase_num + 1)
                phase_span.set_attribute("phase.task_count", len(task_ids))
                phase_span.set_attribute("phase.task_ids", ",".join(task_ids))
                
                logger.info("="*60)
                logger.info(f"EXECUTING PHASE {phase_num + 1}/{len(execution_phases)}: {', '.join(task_ids)}")
                logger.info("="*60)
                
                # Create agents for this phase
                phase_agents = []
                phase_contexts = []
                
                for task_id in task_ids:
                    with span(f"task_{task_id}_setup") as task_setup_span:
                        task_setup_span.set_attribute("task.id", task_id)
                        
                        logger.debug(f"Setting up task: {task_id}")
                        task_def = next(t for t in workflow.tasks if t.task_id == task_id)
                        
                        task_setup_span.set_attribute("task.name", task_def.name)
                        task_setup_span.set_attribute("task.description", task_def.description)
                        task_setup_span.set_attribute("task.required_tools", ",".join(task_def.required_tools))
                        task_setup_span.set_attribute("task.dependencies", ",".join(task_def.dependencies))
                        
                        logger.debug(f"  Task name: {task_def.name}")
                        logger.debug(f"  Required tools: {task_def.required_tools}")
                        logger.debug(f"  Dependencies: {task_def.dependencies}")
                        
                        # Create dynamic agent for this task
                        logger.debug(f"Creating dynamic agent for task: {task_id}")
                        agent = create_dynamic_agent(self.config, self.tool_registry, task_def)
                        
                        # Create execution context with dependency results
                        dependency_results = {dep_id: task_results[dep_id] 
                                            for dep_id in task_def.dependencies 
                                            if dep_id in task_results}
                        
                        if dependency_results:
                            task_setup_span.set_attribute("task.dependency_count", len(dependency_results))
                            logger.debug(f"  Using dependency results from: {list(dependency_results.keys())}")
                            for dep_id, dep_result in dependency_results.items():
                                logger.debug(f"    {dep_id}: status={dep_result.status}, findings={len(dep_result.findings)}")
                        else:
                            task_setup_span.set_attribute("task.dependency_count", 0)
                            logger.debug(f"  No dependencies for task: {task_id}")
                        
                        exec_context = AgentExecutionContext(
                            task_definition=task_def,
                            diagnostic_context=diagnostic_context,
                            dependency_results=dependency_results,
                            execution_metadata=execution_metadata
                        )
                        
                        phase_agents.append(agent)
                        phase_contexts.append(exec_context)
                        logger.debug(f"Task {task_id} setup complete")
                
                # Execute phase tasks in parallel with tracing
                logger.info(f"Starting parallel execution of {len(phase_agents)} tasks...")
                phase_start = time.time()
                
                try:
                    # Create traced task execution coroutines
                    traced_tasks = []
                    for agent, context in zip(phase_agents, phase_contexts):
                        traced_tasks.append(self._execute_task_with_tracing(agent, context))
                    
                    phase_results = await asyncio.gather(*traced_tasks, return_exceptions=True)
                    
                except Exception as e:
                    logger.error(f"Critical error during phase {phase_num + 1} execution: {e}", exc_info=True)
                    phase_span.set_attribute("error.message", str(e))
                    raise
                
                phase_duration = time.time() - phase_start
                phase_span.set_attribute("phase.execution_time", phase_duration)
                logger.info(f"Phase {phase_num + 1} parallel execution completed in {phase_duration:.2f}s")
                
                # Process phase results
                phase_success_count = 0
                phase_error_count = 0
                
                for i, result in enumerate(phase_results):
                    task_id = task_ids[i]
                    logger.debug(f"Processing result for task: {task_id}")
                    
                    if isinstance(result, Exception):
                        logger.error(f"Task {task_id} failed with exception: {result}", exc_info=True)
                        phase_error_count += 1
                        task_results[task_id] = DiagnosticResult(
                            step=task_id,
                            status="error",
                            findings=[f"Task execution failed: {str(result)}"],
                            recommendations=["Check task configuration and retry"],
                            details={"error": str(result), "exception_type": type(result).__name__}
                        )
                    else:
                        logger.info(f"Task {task_id} completed successfully with status: {result.status}")
                        logger.debug(f"  Findings: {len(result.findings)} items")
                        logger.debug(f"  Recommendations: {len(result.recommendations)} items")
                        logger.debug(f"  Execution time: {result.details.get('execution_time', 'unknown')}")
                        
                        if result.findings:
                            logger.debug(f"  Key finding: {result.findings[0]}")
                        
                        phase_success_count += 1
                        task_results[task_id] = result
                
                phase_span.set_attribute("phase.successful_tasks", phase_success_count)
                phase_span.set_attribute("phase.failed_tasks", phase_error_count)
                
                logger.info(f"Phase {phase_num + 1} completed: {phase_success_count} successful, {phase_error_count} failed")
                logger.info(f"Phase {phase_num + 1} total duration: {phase_duration:.2f}s")
        
        return await self._finalize_workflow_result(workflow_id, workflow, task_results, execution_phases, start_time)
    
    async def _execute_workflow_without_tracing(self,
                                              workflow_id: str,
                                              diagnostic_context: SplunkDiagnosticContext,
                                              execution_metadata: Dict[str, Any],
                                              start_time: float) -> WorkflowResult:
        """Execute workflow without tracing (fallback implementation)."""
        logger.info(f"Diagnostic context:")
        logger.info(f"  - Time range: {diagnostic_context.earliest_time} to {diagnostic_context.latest_time}")
        logger.info(f"  - Focus index: {diagnostic_context.focus_index}")
        logger.info(f"  - Focus host: {diagnostic_context.focus_host}")
        logger.info(f"  - Complexity level: {diagnostic_context.complexity_level}")
        logger.info(f"  - Indexes: {diagnostic_context.indexes}")
        logger.info(f"  - Sourcetypes: {diagnostic_context.sourcetypes}")
        logger.info(f"  - Sources: {diagnostic_context.sources}")
        logger.info(f"Execution metadata: {execution_metadata}")
        
        # Get workflow definition
        workflow = self.get_workflow(workflow_id)
        if not workflow:
            error_msg = f"Workflow not found: {workflow_id}"
            logger.error(error_msg)
            logger.error(f"Available workflows: {list(self.workflows.keys())}")
            raise ValueError(error_msg)
        
        logger.info(f"Found workflow: {workflow.name}")
        logger.info(f"Description: {workflow.description}")
        logger.info(f"Total tasks: {len(workflow.tasks)}")
        
        # Analyze dependencies and create execution plan
        logger.info("Analyzing task dependencies...")
        dependency_graph = self._build_dependency_graph(workflow.tasks)
        logger.debug(f"Dependency graph: {dependency_graph}")
        
        logger.info("Creating execution phases...")
        execution_phases = self._create_execution_phases(workflow.tasks, dependency_graph)
        
        logger.info(f"Workflow has {len(execution_phases)} execution phases")
        for i, phase in enumerate(execution_phases):
            logger.info(f"  Phase {i+1}: {len(phase)} tasks - {', '.join(phase)}")
        
        # Calculate parallel efficiency
        parallel_efficiency = self._calculate_parallel_efficiency(workflow.tasks, execution_phases)
        logger.info(f"Parallel execution efficiency: {parallel_efficiency:.1%}")
        
        # Execute workflow in phases
        task_results = {}
        
        for phase_num, task_ids in enumerate(execution_phases):
            logger.info("="*60)
            logger.info(f"EXECUTING PHASE {phase_num + 1}/{len(execution_phases)}: {', '.join(task_ids)}")
            logger.info("="*60)
            
            # Create agents for this phase
            phase_agents = []
            phase_contexts = []
            
            for task_id in task_ids:
                logger.debug(f"Setting up task: {task_id}")
                task_def = next(t for t in workflow.tasks if t.task_id == task_id)
                logger.debug(f"  Task name: {task_def.name}")
                logger.debug(f"  Required tools: {task_def.required_tools}")
                logger.debug(f"  Dependencies: {task_def.dependencies}")
                
                # Create dynamic agent for this task
                logger.debug(f"Creating dynamic agent for task: {task_id}")
                agent = create_dynamic_agent(self.config, self.tool_registry, task_def)
                
                # Create execution context with dependency results
                dependency_results = {dep_id: task_results[dep_id] 
                                    for dep_id in task_def.dependencies 
                                    if dep_id in task_results}
                
                if dependency_results:
                    logger.debug(f"  Using dependency results from: {list(dependency_results.keys())}")
                    for dep_id, dep_result in dependency_results.items():
                        logger.debug(f"    {dep_id}: status={dep_result.status}, findings={len(dep_result.findings)}")
                else:
                    logger.debug(f"  No dependencies for task: {task_id}")
                
                exec_context = AgentExecutionContext(
                    task_definition=task_def,
                    diagnostic_context=diagnostic_context,
                    dependency_results=dependency_results,
                    execution_metadata=execution_metadata
                )
                
                phase_agents.append(agent)
                phase_contexts.append(exec_context)
                logger.debug(f"Task {task_id} setup complete")
            
            # Execute phase tasks in parallel
            logger.info(f"Starting parallel execution of {len(phase_agents)} tasks...")
            phase_start = time.time()
            
            try:
                phase_results = await asyncio.gather(
                    *[agent.execute_task(context) for agent, context in zip(phase_agents, phase_contexts)],
                    return_exceptions=True
                )
            except Exception as e:
                logger.error(f"Critical error during phase {phase_num + 1} execution: {e}", exc_info=True)
                raise
            
            phase_duration = time.time() - phase_start
            logger.info(f"Phase {phase_num + 1} parallel execution completed in {phase_duration:.2f}s")
            
            # Process phase results
            phase_success_count = 0
            phase_error_count = 0
            
            for i, result in enumerate(phase_results):
                task_id = task_ids[i]
                logger.debug(f"Processing result for task: {task_id}")
                
                if isinstance(result, Exception):
                    logger.error(f"Task {task_id} failed with exception: {result}", exc_info=True)
                    phase_error_count += 1
                    task_results[task_id] = DiagnosticResult(
                        step=task_id,
                        status="error",
                        findings=[f"Task execution failed: {str(result)}"],
                        recommendations=["Check task configuration and retry"],
                        details={"error": str(result), "exception_type": type(result).__name__}
                    )
                else:
                    logger.info(f"Task {task_id} completed successfully with status: {result.status}")
                    logger.debug(f"  Findings: {len(result.findings)} items")
                    logger.debug(f"  Recommendations: {len(result.recommendations)} items")
                    logger.debug(f"  Execution time: {result.details.get('execution_time', 'unknown')}")
                    
                    if result.findings:
                        logger.debug(f"  Key finding: {result.findings[0]}")
                    
                    phase_success_count += 1
                    task_results[task_id] = result
            
            logger.info(f"Phase {phase_num + 1} completed: {phase_success_count} successful, {phase_error_count} failed")
            logger.info(f"Phase {phase_num + 1} total duration: {phase_duration:.2f}s")
        
        return await self._finalize_workflow_result(workflow_id, workflow, task_results, execution_phases, start_time)
    
    async def _execute_task_with_tracing(self, agent: DynamicMicroAgent, context: AgentExecutionContext) -> DiagnosticResult:
        """Execute a single task with tracing."""
        task_id = context.task_definition.task_id
        
        if TRACING_AVAILABLE:
            with span(f"task_{task_id}_execution") as task_span:
                task_span.set_attribute("task.id", task_id)
                task_span.set_attribute("task.name", context.task_definition.name)
                task_span.set_attribute("task.description", context.task_definition.description)
                task_span.set_attribute("task.required_tools", ",".join(context.task_definition.required_tools))
                task_span.set_attribute("task.dependencies", ",".join(context.task_definition.dependencies))
                
                try:
                    result = await agent.execute_task(context)
                    task_span.set_attribute("task.status", result.status)
                    task_span.set_attribute("task.findings_count", len(result.findings))
                    task_span.set_attribute("task.recommendations_count", len(result.recommendations))
                    task_span.set_attribute("task.execution_time", result.details.get("execution_time", 0))
                    return result
                except Exception as e:
                    task_span.set_attribute("error.message", str(e))
                    task_span.set_attribute("error.type", type(e).__name__)
                    raise
        else:
            return await agent.execute_task(context)
    
    async def _finalize_workflow_result(self,
                                      workflow_id: str,
                                      workflow: 'WorkflowDefinition',
                                      task_results: Dict[str, DiagnosticResult],
                                      execution_phases: List[List[str]],
                                      start_time: float) -> WorkflowResult:
        """Finalize workflow result with summary and analysis."""
        total_time = time.time() - start_time
        
        logger.info("="*60)
        logger.info("GENERATING WORKFLOW SUMMARY")
        logger.info("="*60)
        
        # Generate summary
        logger.debug("Generating workflow summary...")
        summary = self._generate_workflow_summary(workflow, task_results, execution_phases)
        logger.debug(f"Summary generated with {summary.get('total_findings', 0)} findings and {summary.get('total_recommendations', 0)} recommendations")
        
        # Determine overall status
        overall_status = self._determine_overall_status(task_results)
        logger.info(f"Overall workflow status determined: {overall_status}")
        
        # Log task status breakdown
        status_counts = {}
        for task_id, result in task_results.items():
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
            summary=summary
        )
        
        logger.info("="*80)
        logger.info(f"WORKFLOW EXECUTION COMPLETED: {workflow_id}")
        logger.info(f"Total execution time: {total_time:.2f}s")
        logger.info(f"Overall status: {result.status}")
        logger.info(f"Tasks completed: {len(task_results)}")
        logger.info(f"Execution phases: {len(execution_phases)}")
        logger.info(f"Parallel efficiency: {summary.get('parallel_efficiency', 0):.1%}")
        logger.info("="*80)
        
        return result
        
        for phase_num, task_ids in enumerate(execution_phases):
            logger.info("="*60)
            logger.info(f"EXECUTING PHASE {phase_num + 1}/{len(execution_phases)}: {', '.join(task_ids)}")
            logger.info("="*60)
            
            # Create agents for this phase
            phase_agents = []
            phase_contexts = []
            
            for task_id in task_ids:
                logger.debug(f"Setting up task: {task_id}")
                task_def = next(t for t in workflow.tasks if t.task_id == task_id)
                logger.debug(f"  Task name: {task_def.name}")
                logger.debug(f"  Required tools: {task_def.required_tools}")
                logger.debug(f"  Dependencies: {task_def.dependencies}")
                
                # Create dynamic agent for this task
                logger.debug(f"Creating dynamic agent for task: {task_id}")
                agent = create_dynamic_agent(self.config, self.tool_registry, task_def)
                
                # Create execution context with dependency results
                dependency_results = {dep_id: task_results[dep_id] 
                                    for dep_id in task_def.dependencies 
                                    if dep_id in task_results}
                
                if dependency_results:
                    logger.debug(f"  Using dependency results from: {list(dependency_results.keys())}")
                    for dep_id, dep_result in dependency_results.items():
                        logger.debug(f"    {dep_id}: status={dep_result.status}, findings={len(dep_result.findings)}")
                else:
                    logger.debug(f"  No dependencies for task: {task_id}")
                
                exec_context = AgentExecutionContext(
                    task_definition=task_def,
                    diagnostic_context=diagnostic_context,
                    dependency_results=dependency_results,
                    execution_metadata=execution_metadata
                )
                
                phase_agents.append(agent)
                phase_contexts.append(exec_context)
                logger.debug(f"Task {task_id} setup complete")
            
            # Execute phase tasks in parallel
            logger.info(f"Starting parallel execution of {len(phase_agents)} tasks...")
            phase_start = time.time()
            
            try:
                phase_results = await asyncio.gather(
                    *[agent.execute_task(context) for agent, context in zip(phase_agents, phase_contexts)],
                    return_exceptions=True
                )
            except Exception as e:
                logger.error(f"Critical error during phase {phase_num + 1} execution: {e}", exc_info=True)
                raise
            
            phase_duration = time.time() - phase_start
            logger.info(f"Phase {phase_num + 1} parallel execution completed in {phase_duration:.2f}s")
            
            # Process phase results
            phase_success_count = 0
            phase_error_count = 0
            
            for i, result in enumerate(phase_results):
                task_id = task_ids[i]
                logger.debug(f"Processing result for task: {task_id}")
                
                if isinstance(result, Exception):
                    logger.error(f"Task {task_id} failed with exception: {result}", exc_info=True)
                    phase_error_count += 1
                    task_results[task_id] = DiagnosticResult(
                        step=task_id,
                        status="error",
                        findings=[f"Task execution failed: {str(result)}"],
                        recommendations=["Check task configuration and retry"],
                        details={"error": str(result), "exception_type": type(result).__name__}
                    )
                else:
                    logger.info(f"Task {task_id} completed successfully with status: {result.status}")
                    logger.debug(f"  Findings: {len(result.findings)} items")
                    logger.debug(f"  Recommendations: {len(result.recommendations)} items")
                    logger.debug(f"  Execution time: {result.details.get('execution_time', 'unknown')}")
                    
                    if result.findings:
                        logger.debug(f"  Key finding: {result.findings[0]}")
                    
                    phase_success_count += 1
                    task_results[task_id] = result
            
            logger.info(f"Phase {phase_num + 1} completed: {phase_success_count} successful, {phase_error_count} failed")
            logger.info(f"Phase {phase_num + 1} total duration: {phase_duration:.2f}s")
        
        # Create workflow result
        total_time = time.time() - start_time
        
        logger.info("="*60)
        logger.info("GENERATING WORKFLOW SUMMARY")
        logger.info("="*60)
        
        # Generate summary
        logger.debug("Generating workflow summary...")
        summary = self._generate_workflow_summary(workflow, task_results, execution_phases)
        logger.debug(f"Summary generated with {summary.get('total_findings', 0)} findings and {summary.get('total_recommendations', 0)} recommendations")
        
        # Determine overall status
        overall_status = self._determine_overall_status(task_results)
        logger.info(f"Overall workflow status determined: {overall_status}")
        
        # Log task status breakdown
        status_counts = {}
        for task_id, result in task_results.items():
            status = result.status
            status_counts[status] = status_counts.get(status, 0) + 1
        
        logger.info("Task status breakdown:")
        for status, count in status_counts.items():
            logger.info(f"  {status}: {count} tasks")
        
        result = WorkflowResult(
            workflow_id=workflow_id,
            status=overall_status,
            execution_time=total_time,
            task_results=task_results,
            dependency_graph=dependency_graph,
            execution_order=execution_phases,
            summary=summary
        )
        
        logger.info("="*80)
        logger.info(f"WORKFLOW EXECUTION COMPLETED: {workflow_id}")
        logger.info(f"Total execution time: {total_time:.2f}s")
        logger.info(f"Overall status: {result.status}")
        logger.info(f"Tasks completed: {len(task_results)}")
        logger.info(f"Execution phases: {len(execution_phases)}")
        logger.info(f"Parallel efficiency: {summary.get('parallel_efficiency', 0):.1%}")
        logger.info("="*80)
        
        return result
    
    def _build_dependency_graph(self, tasks: List[TaskDefinition]) -> Dict[str, List[str]]:
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
    
    def _create_execution_phases(self, 
                               tasks: List[TaskDefinition], 
                               dependency_graph: Dict[str, List[str]]) -> List[List[str]]:
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
            
            logger.debug(f"Phase {phase_num} completed. Total completed: {len(completed)}/{len(task_ids)}")
        
        logger.debug(f"Execution phases created: {len(phases)} phases total")
        for i, phase in enumerate(phases):
            logger.debug(f"  Phase {i+1}: {phase}")
        
        return phases
    
    def _determine_overall_status(self, task_results: Dict[str, DiagnosticResult]) -> str:
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
    
    def _generate_workflow_summary(self,
                                 workflow: WorkflowDefinition,
                                 task_results: Dict[str, DiagnosticResult],
                                 execution_phases: List[List[str]]) -> Dict[str, Any]:
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
            "parallel_efficiency": self._calculate_parallel_efficiency(workflow.tasks, execution_phases),
            "task_status_breakdown": {
                "healthy": len(healthy_tasks),
                "warning": len(warning_tasks), 
                "critical": len(critical_tasks),
                "error": len(error_tasks)
            },
            "healthy_tasks": healthy_tasks,
            "warning_tasks": warning_tasks,
            "critical_tasks": critical_tasks,
            "error_tasks": error_tasks,
            "total_findings": len(all_findings),
            "total_recommendations": len(unique_recommendations),
            "key_findings": all_findings[:10],  # Top 10 findings
            "recommendations": unique_recommendations
        }
    
    def _calculate_parallel_efficiency(self, 
                                     tasks: List[TaskDefinition],
                                     execution_phases: List[List[str]]) -> float:
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
async def execute_missing_data_workflow(workflow_manager: WorkflowManager,
                                      diagnostic_context: SplunkDiagnosticContext) -> WorkflowResult:
    """Execute the missing data troubleshooting workflow."""
    return await workflow_manager.execute_workflow("missing_data_troubleshooting", diagnostic_context)


async def execute_performance_workflow(workflow_manager: WorkflowManager,
                                     diagnostic_context: SplunkDiagnosticContext) -> WorkflowResult:
    """Execute the performance analysis workflow.""" 
    return await workflow_manager.execute_workflow("performance_analysis", diagnostic_context)


async def execute_health_check_workflow(workflow_manager: WorkflowManager,
                                      diagnostic_context: SplunkDiagnosticContext) -> WorkflowResult:
    """Execute the basic health check workflow."""
    return await workflow_manager.execute_workflow("health_check", diagnostic_context) 