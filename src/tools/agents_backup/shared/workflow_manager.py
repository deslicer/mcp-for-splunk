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

from fastmcp import Context
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
        """Register built-in workflows by loading from JSON files."""
        from contrib.workflows.loaders import load_and_register_workflows
        
        # Load and register core workflows from src/tools/workflows/core/
        loaded_count = load_and_register_workflows(self, "src/tools/workflows/core/")
        logger.info(f"Loaded {loaded_count} core workflows from JSON")
        
        # Optionally load contrib workflows here if desired, but keep separate as per plan

    def _create_missing_data_workflow(self) -> WorkflowDefinition:
        """Create the missing data troubleshooting workflow following Splunk's official 10-step checklist."""

        tasks = [
            TaskDefinition(
                task_id="splunk_license_edition_verification",
                name="Splunk License & Edition Verification",
                description="Check Splunk license and edition status - Step 1 of official workflow",
                instructions="""
You are performing Step 1 of the official Splunk missing data troubleshooting workflow.

**Check if running Splunk Free:**
- Splunk Free doesn't support multiple users, distributed searching, or alerting
- Saved searches from other users may not be accessible
- Use search: `| rest /services/server/info | fields splunk_version, product_type, license_state`

**Analysis:**
1. Execute the search to get server info
2. Check if product_type indicates Splunk Free
3. Verify license_state is valid
4. Note version and product type
5. Identify any license-related limitations that could affect data access

**Output:** Return DiagnosticResult with license status, edition type, and any limitations found.
                """,
                required_tools=["run_splunk_search", "get_current_user_info"],
                dependencies=[],  # No dependencies - can run in parallel
                context_requirements=[],
            ),
            TaskDefinition(
                task_id="index_verification",
                name="Index Verification",
                description="Verify data was added to correct indexes - Step 2 of official workflow",
                instructions="""
You are performing Step 2 of the official Splunk missing data troubleshooting workflow.


**Was data added to a different index?**
- Some apps write to specific indexes (e.g., *nix/Windows apps use "os" index)
- Check available indexes and verify you're searching the right one
- Use search: `| eventcount summarize=false index={focus_index} | dedup index | table index`
- Try searching specific indexes: `index=os` or `index=main`

**Analysis:**
1. Get list of all available indexes using eventcount
2. Check if target indexes {focus_index} exist (if specified)
3. Test accessibility with simple searches on key indexes
4. Identify missing or unexpected indexes
5. Check for data in common indexes like main, os, etc.

**Output:** Return DiagnosticResult with index availability and accessibility status.
                """,
                required_tools=["list_splunk_indexes", "run_splunk_search"],
                dependencies=[],  # No dependencies - can run in parallel
                context_requirements=["focus_index"],
            ),
            TaskDefinition(
                task_id="permissions_access_control",
                name="Permissions & Access Control",
                description="Verify user permissions allow data access - Step 3 of official workflow",
                instructions="""
You are performing Step 3 of the official Splunk missing data troubleshooting workflow.
**Do your permissions allow you to see the data?**
- **STEP 3A:** First, get current user information: Use tool `get_current_user_info()` to get the user's roles and capabilities
- **STEP 3B:** Extract the role names from the user info response (look for the "roles" field)
- **STEP 3C:** Check role-based index access restrictions using the actual role names
- **Example workflow:**
  1. Call `get_current_user_info()` and note the roles (e.g., ["admin", "power"])
  2. Then use: `| rest /services/authorization/roles | search title IN ("admin", "power") | table title, srchIndexesAllowed, srchIndexesDefault`
  3. Or check each role individually: `| rest /services/authorization/roles | search title="admin" | table title, srchIndexesAllowed, srchIndexesDefault`
- **Alternative for overview:** `| rest /services/authorization/roles | table title, srchIndexesAllowed, srchIndexesDefault`
- Verify search filters aren't blocking data based on the role's index access

**Analysis:**
1. Get current user information and extract roles
2. Query role permissions for index access
3. Check if user roles allow access to target indexes
4. Verify search filters and restrictions
5. Test basic search permissions

**Output:** Return DiagnosticResult with permission status and access control issues.
                """,
                required_tools=["get_current_user_info", "run_splunk_search"],
                dependencies=[],  # No dependencies - can run in parallel
                context_requirements=[],
            ),
            TaskDefinition(
                task_id="time_range_issues",
                name="Time Range Issues",
                description="Check time-related problems - Step 4 of official workflow",
                instructions="""
You are performing Step 4 of the official Splunk missing data troubleshooting workflow.
**Task:** Check for data in time range {earliest_time} to {latest_time} and identify time-related problems
**Context:** Target indexes: {focus_index}, sourcetypes: {focus_sourcetype}
**Check time-related problems:**
- Verify events exist in your search time window
- Try "All time" search to catch future-timestamped events
- Check for indexing delays (replace `YOUR_INDEX` with specific index or use `index=*`):
  `index={focus_index} | eval lag=_indextime-_time | stats avg(lag) max(lag) by index`
- Verify timezone settings for scheduled searches

**Analysis:**
1. Build search query for specified time range {earliest_time} to {latest_time}
2. Execute count query for the time range
3. Try broader time range (All time) to check for future timestamps
4. Check indexing delays using _indextime vs _time comparison
5. Analyze time distribution patterns
6. Identify timezone or timestamp issues

**Output:** Return DiagnosticResult with time range analysis and indexing delay information.
                """,
                required_tools=["run_splunk_search"],
                dependencies=[],  # No dependencies - can run in parallel
                context_requirements=["earliest_time", "latest_time", "focus_index"],
            ),
            TaskDefinition(
                task_id="forwarder_connectivity",
                name="Forwarder Connectivity",
                description="Check forwarder connections if using forwarders - Step 5 of official workflow",
                instructions="""
You are performing Step 5 of the official Splunk missing data troubleshooting workflow.
**Context:** Focus host: {focus_host} if specified, index: {focus_index} if specified
**Check forwarder connections:**
- Verify forwarders connecting `index=_internal source=*metrics.log* tcpin_connections | stats count by sourceIp`
- Check output queues: `index=_internal source=*metrics.log* group=queue tcpout | stats count by name`
- Verify recent host activity:
  `| metadata type=hosts index={focus_index} | eval diff=now()-recentTime | where diff < 600`
- Check connection logs: `index=_internal "Connected to idx" OR "cooked mode"`

**Analysis:**
1. Check forwarder connections using tcpin_connections metrics
2. Analyze output queue status for tcpout connections
3. Verify recent host activity using metadata
4. Check connection logs for forwarder connectivity
5. Identify connection drops or network issues
6. Focus on specific host {focus_host} if provided

**Output:** Return DiagnosticResult with forwarder connectivity status and connection issues.
                """,
                required_tools=["run_splunk_search"],
                dependencies=[],  # No dependencies - can run in parallel
                context_requirements=["focus_index", "focus_host"],
            ),
            TaskDefinition(
                task_id="search_head_configuration",
                name="Search Head Configuration",
                description="Verify search head setup in distributed environment - Step 6 of official workflow",
                instructions="""
You are performing Step 6 of the official Splunk missing data troubleshooting workflow.

**Verify search head setup:**
- Check search heads are connected to correct indexers
- Verify distributed search configuration
- Use search: `| rest /services/search/distributed/peers | table title, status, is_https`

**Analysis:**
1. Check distributed search peer configuration
2. Verify search head connections to indexers
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
                context_requirements=[],
            ),
            TaskDefinition(
                task_id="license_violations",
                name="License Violations",
                description="Check for license violations that prevent searching - Step 7 of official workflow",
                instructions="""
You are performing Step 7 of the official Splunk missing data troubleshooting workflow.

**Check for license issues:**
- License violations prevent searching (but indexing continues)
- Use search: `index=_internal source=*license_usage.log* type=Usage | stats sum(b) by pool`
- Verify license status
- Use search: `| rest /services/licenser/messages | table category, message`

**Analysis:**
1. Check license usage by pool to identify violations
2. Query license manager messages for warnings/errors
3. Verify license compliance across pools
4. Check for license-related search restrictions
5. Identify any license violations blocking search functionality

**Searches:**
- index=_internal source=*license_usage.log* type=Usage | stats sum(b) by pool
- | rest /services/licenser/messages | table category, message
- index=_internal source=*splunkd.log* LicenseManager | search "pool quota"
- index=_internal source=*license_usage.log* type=RolloverSummary

**Output:** Return DiagnosticResult with license violation status and impact on search capability.
                """,
                required_tools=["run_splunk_search", "report_specialist_progress"],
                dependencies=["splunk_license_edition_verification"],  # Depends on basic license info
                context_requirements=[],
            ),
            TaskDefinition(
                task_id="scheduled_search_issues",
                name="Scheduled Search Issues",
                description="Analyze scheduled search problems - Step 8 of official workflow",
                instructions="""
You are performing Step 8 of the official Splunk missing data troubleshooting workflow.
**Context:** Time range: {earliest_time} to {latest_time}

**For scheduled searches:**
- Verify time ranges aren't excluding events
- Check for indexing lag affecting recent data
- Examine scheduler performance
- Use search: `index=_internal source=*scheduler.log* | stats count by status`

**Analysis:**
1. Check scheduler.log for search execution status
2. Identify failed or slow scheduled searches
3. Verify time ranges in scheduled searches aren't excluding data
4. Check for indexing lag affecting recent data in schedules
5. Analyze scheduler performance and queue status
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
                name="Search Query Validation",
                description="Verify search syntax and logic - Step 9 of official workflow",
                instructions="""
You are performing Step 9 of the official Splunk missing data troubleshooting workflow.

**Verify search syntax:**
- Check logic operators (NOT, AND, OR) usage
- Verify quote usage and escape characters
- Confirm correct index, source, sourcetype, host specifications
- Test subsearch ordering and field passing
- Check for intentions framework rewrites in drilldowns

**Analysis:**
1. Check audit logs for recent search patterns and syntax errors
2. Look for common search syntax problems
3. Verify field names and search logic
4. Check for search parser errors
5. Validate query construction and operator usage

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
                name="Field Extraction Issues",
                description="Check field extraction problems - Step 10 of official workflow",
                instructions="""
You are performing Step 10 of the official Splunk missing data troubleshooting workflow.
**Context:** Focus sourcetype: {focus_sourcetype} if specified, index: {focus_index} if specified
Check field extraction configuration and functionality
**For field extraction problems:**
- Test regex patterns with rex command
- Verify extraction permissions and sharing
- Check extractions applied to correct source/sourcetype/host
- Use search: `| rest /services/data/props/extractions | search stanza={focus_sourcetype} | table stanza, attribute, value`

**Analysis:**
1. Check field extraction configuration using props/extractions
2. Verify extraction permissions and sharing settings
3. Test regex patterns and field extraction functionality
4. Check extractions applied to correct source/sourcetype/host
5. Analyze field extraction performance and conflicts


**Output:** Return DiagnosticResult with field extraction status and configuration issues.
                """,
                required_tools=["run_splunk_search", "report_specialist_progress"],
                dependencies=[],  # No dependencies - can run in parallel
                context_requirements=["focus_sourcetype"],
            ),
        ]

        return WorkflowDefinition(
            workflow_id="missing_data_troubleshooting",
            name="Missing Data Troubleshooting",
            description="Systematic troubleshooting for missing data issues following Splunk's official 10-step workflow",
            tasks=tasks,
        )

    def _create_performance_workflow(self) -> WorkflowDefinition:
        """Create the performance analysis workflow following Splunk Platform Instrumentation 10-step checklist."""

        tasks = [
            TaskDefinition(
                task_id="system_resource_baseline",
                name="System Resource Baseline",
                description="Analyze system resource usage patterns - Step 1 of performance workflow",
                instructions="""
You are performing Step 1 of the systematic performance troubleshooting workflow.

**Check overall CPU, memory, and disk usage patterns:**
- Search: `index=_introspection component=Hostwide | stats avg(data.cpu_system_pct) as avg_cpu_system, avg(data.cpu_user_pct) as avg_cpu_user, avg(data.mem_used) as avg_mem_used by host`
- Establish baseline resource utilization across all Splunk instances
- Look for hosts with consistently high resource usage (>80% CPU or memory)

**Analysis:**
1. Query _introspection index for Hostwide component data
2. Check CPU usage patterns (system and user)
3. Analyze memory utilization across hosts
4. Identify hosts with high resource usage (>80% CPU or memory)
5. Focus on specific host {focus_host} if provided

**Output:** Return DiagnosticResult with resource usage status and bottlenecks.
                """,
                required_tools=["run_splunk_search"],
                dependencies=[],  # No dependencies - can run in parallel
                context_requirements=["earliest_time", "latest_time", "focus_host"],
            ),
            TaskDefinition(
                task_id="splunk_process_resource_analysis",
                name="Splunk Process Resource Analysis",
                description="Analyze resource usage specific to Splunk processes - Step 2 of performance workflow",
                instructions="""
You are performing Step 2 of the systematic performance troubleshooting workflow.

**Analyze resource usage specific to Splunk processes:**
- Identify processes consuming excessive resources
- Use search: `index=_introspection component=PerProcess data.process_class=search | stats median(data.pct_cpu) as median_cpu, median(data.pct_memory) as median_memory by data.search_type`
- Check for memory leaks or CPU spikes in splunkd processes
- Use search: `index=_introspection component=PerProcess data.process=splunkd | stats avg(data.pct_cpu) as avg_splunkd_cpu, avg(data.pct_memory) as avg_splunkd_memory by host`

**Analysis:**
1. Query _introspection for PerProcess component data
2. Analyze search process resource consumption by search type
3. Check splunkd process resource usage patterns
4. Identify processes consuming excessive resources
5. Look for memory leaks or CPU spikes
6. Focus on specific host {focus_host} if provided

**Output:** Return DiagnosticResult with Splunk process resource usage and issues.
                """,
                required_tools=["run_splunk_search"],
                dependencies=[],  # No dependencies - can run in parallel
                context_requirements=["earliest_time", "latest_time", "focus_host"],
            ),
            TaskDefinition(
                task_id="search_concurrency_performance",
                name="Search Concurrency and Performance",
                description="Examine search concurrency patterns and limits - Step 3 of performance workflow",
                instructions="""
You are performing Step 3 of the systematic performance troubleshooting workflow.

**Examine search concurrency patterns and limits:**
- Check if search concurrency is hitting configured limits
- Use search: `index=_introspection component=Hostwide | stats median(data.splunk_search_concurrency) as median_search_concurrency by host`
- Identify slow or failed scheduled searches
- Use search: `index=_internal source=*scheduler.log* | stats count by status, search_type | sort -count`

**Analysis:**
1. Query search concurrency metrics from _introspection
2. Check if hitting configured concurrency limits
3. Analyze scheduler.log for search performance patterns
4. Identify slow or failed searches
5. Focus on specific host {focus_host} if provided

**Output:** Return DiagnosticResult with search concurrency status and performance issues.
                """,
                required_tools=["run_splunk_search"],
                dependencies=[],  # No dependencies - can run in parallel
                context_requirements=["earliest_time", "latest_time", "focus_host"],
            ),
            TaskDefinition(
                task_id="disk_usage_io_performance",
                name="Disk Usage and I/O Performance",
                description="Analyze disk space utilization and I/O patterns - Step 4 of performance workflow",
                instructions="""
You are performing Step 4 of the systematic performance troubleshooting workflow.

**Analyze disk space utilization and I/O patterns:**
- Check for disk space issues (>85% usage)
- Use search: `index=_introspection component=DiskObjects | stats latest(data.capacity) as capacity, latest(data.available) as available by data.mount_point, host | eval pct_used=round(((capacity-available)/capacity)*100,2)`
- Monitor I/O wait times and disk performance bottlenecks
- Use search: `index=_introspection component=Hostwide | stats avg(data.read_ops) as avg_read_ops, avg(data.write_ops) as avg_write_ops by host`

**Analysis:**
1. Query DiskObjects component for disk space utilization
2. Calculate disk usage percentages and identify >85% usage
3. Monitor I/O operations and performance patterns
4. Identify disk performance bottlenecks
5. Focus on specific host {focus_host} if provided

**Output:** Return DiagnosticResult with disk usage and I/O performance status.
                """,
                required_tools=["run_splunk_search"],
                dependencies=[],  # No dependencies - can run in parallel
                context_requirements=["earliest_time", "latest_time", "focus_host"],
            ),
            TaskDefinition(
                task_id="indexing_pipeline_performance",
                name="Indexing Pipeline Performance",
                description="Analyze indexing delays and throughput issues - Step 5 of performance workflow",
                instructions="""
You are performing Step 5 of the systematic performance troubleshooting workflow.

**Analyze indexing delays and throughput issues:**
- Check for indexing delays or pipeline bottlenecks
- Use search: `index=_internal source=*metrics.log* group=per_index_thruput | stats avg(kb) as avg_kb_per_sec by series`
- Identify indexes with low throughput or high processing times
- Use search: `index=_internal source=*metrics.log* group=pipeline | stats avg(cpu_seconds) as avg_cpu_seconds, avg(executes) as avg_executes by processor`

**Analysis:**
1. Query per_index_thruput metrics for throughput analysis
2. Calculate average throughput by index series
3. Analyze pipeline processor performance
4. Identify indexes with low throughput or high processing times
5. Focus on specific index {focus_index} if provided

**Output:** Return DiagnosticResult with indexing pipeline performance status and recommendations.
                """,
                required_tools=["run_splunk_search"],
                dependencies=[],  # No dependencies - can run in parallel
                context_requirements=["earliest_time", "latest_time", "focus_index"],
            ),
            TaskDefinition(
                task_id="queue_analysis_processing_delays",
                name="Queue Analysis and Processing Delays",
                description="Examine queue depths and processing delays - Step 6 of performance workflow",
                instructions="""
You are performing Step 6 of the systematic performance troubleshooting workflow.

**Examine queue depths and processing delays:**
- Look for consistently full queues (parsing, indexing, typing)
- Use search: `index=_internal source=*metrics.log* group=queue | stats max(current_size) as max_queue_size, avg(current_size) as avg_queue_size by name`
- Identify queue bottlenecks affecting performance
- Use search: `index=_internal source=*metrics.log* group=queue | where current_size > 0 | stats count by name | sort -count`

**Analysis:**
1. Query queue metrics for current sizes and patterns
2. Identify consistently full queues (parsing, indexing, typing)
3. Calculate maximum and average queue sizes by queue name
4. Identify queue bottlenecks affecting performance
5. Focus on queues related to specific index {focus_index} if provided

**Output:** Return DiagnosticResult with queue analysis and processing delay information.
                """,
                required_tools=["run_splunk_search"],
                dependencies=[],  # No dependencies - can run in parallel
                context_requirements=["earliest_time", "latest_time", "focus_index"],
            ),
            TaskDefinition(
                task_id="search_head_kvstore_performance",
                name="Search Head and KV Store Performance",
                description="Analyze search head cluster and KV Store performance - Step 7 of performance workflow",
                instructions="""
You are performing Step 7 of the systematic performance troubleshooting workflow.

**Analyze search head cluster and KV Store performance:**
- Check KV Store health and connectivity issues
- Use search: `index=_internal source=*splunkd.log* component=KVStoreMgr | stats count by log_level | sort -count`
- Monitor file descriptor usage for splunkweb processes
- Use search: `index=_introspection component=Hostwide | stats avg(data.splunkweb_fd_used) as avg_fd_used by host`

**Analysis:**
1. Query KV Store manager logs for health status
2. Check KV Store connectivity and error patterns
3. Monitor file descriptor usage for splunkweb processes
4. Identify search head performance issues
5. Focus on specific host {focus_host} if provided

**Output:** Return DiagnosticResult with search head and KV Store performance status.
                """,
                required_tools=["run_splunk_search"],
                dependencies=[],  # No dependencies - can run in parallel
                context_requirements=["earliest_time", "latest_time", "focus_host"],
            ),
            TaskDefinition(
                task_id="license_capacity_constraints",
                name="License and Capacity Constraints",
                description="Check for license violations affecting performance - Step 8 of performance workflow",
                instructions="""
You are performing Step 8 of the systematic performance troubleshooting workflow.

**Check for license violations affecting performance:**
- Identify license pool violations that may throttle indexing
- Use search: `index=_internal source=*license_usage.log* type=Usage | stats sum(b) as total_bytes by pool | eval total_gb=round(total_bytes/1024/1024/1024,2)`
- Check for capacity planning issues
- Use search: `index=_internal source=*splunkd.log* LicenseManager | search "pool quota" | head 20`

**Analysis:**
1. Query license usage by pool to identify violations
2. Calculate total bytes and GB usage by license pool
3. Check for license pool quota violations
4. Identify capacity planning issues affecting performance
5. Analyze license manager logs for quota warnings

**Output:** Return DiagnosticResult with license and capacity constraint status.
                """,
                required_tools=["run_splunk_search"],
                dependencies=[],  # No dependencies - can run in parallel
                context_requirements=["earliest_time", "latest_time"],
            ),
            TaskDefinition(
                task_id="network_forwarder_performance",
                name="Network and Forwarder Performance",
                description="Examine forwarder connectivity and network performance - Step 9 of performance workflow",
                instructions="""
You are performing Step 9 of the systematic performance troubleshooting workflow.

**Examine forwarder connectivity and network performance:**
- Check forwarder connection stability and throughput
- Use search: `index=_internal source=*metrics.log* group=tcpin_connections | stats dc(connectionType) as connection_types, avg(kb) as avg_kb_per_sec by sourceHost`
- Identify network bottlenecks or connection issues
- Use search: `index=_internal source=*splunkd.log* component=TcpInputProc | stats count by log_level | sort -count`

**Analysis:**
1. Query tcpin_connections metrics for forwarder performance
2. Calculate connection types and throughput by source host
3. Check TcpInputProc logs for connection issues
4. Identify network bottlenecks or connection problems
5. Focus on specific host {focus_host} if provided

**Output:** Return DiagnosticResult with network and forwarder performance status.
                """,
                required_tools=["run_splunk_search"],
                dependencies=[],  # No dependencies - can run in parallel
                context_requirements=["earliest_time", "latest_time", "focus_host"],
            ),
            TaskDefinition(
                task_id="performance_recommendations_optimization",
                name="Performance Recommendations and Optimization",
                description="Correlate findings and provide optimization recommendations - Step 10 of performance workflow",
                instructions="""
You are performing Step 10 of the systematic performance troubleshooting workflow.

**Correlate findings and provide specific optimization recommendations:**
- Use search: `index=_internal source=*splunkd.log* log_level=WARN OR log_level=ERROR | stats count by component | sort -count | head 10`
- Provide tuning recommendations based on identified bottlenecks
- Suggest configuration changes with expected performance impact
- Document baseline metrics for future comparison

**Analysis:**
1. Query splunkd.log for warning and error patterns by component
2. Correlate findings from previous performance analysis steps
3. Identify top components generating warnings/errors
4. Provide specific tuning recommendations based on bottlenecks
5. Suggest configuration changes with expected impact
6. Document baseline metrics for future monitoring

**Critical Performance Indicators to address:**
- CPU usage >80% sustained
- Memory usage >85% sustained
- Disk usage >85% of capacity
- Search concurrency at configured limits
- Queue sizes consistently >0
- Indexing throughput below expected rates
- License pool violations
- Network connection drops or errors

**Output:** Return DiagnosticResult with performance optimization recommendations and tuning suggestions.
                """,
                required_tools=["run_splunk_search"],
                dependencies=[
                    "system_resource_baseline",
                    "splunk_process_resource_analysis",
                    "search_concurrency_performance",
                    "disk_usage_io_performance",
                    "indexing_pipeline_performance",
                    "queue_analysis_processing_delays",
                    "search_head_kvstore_performance",
                    "license_capacity_constraints",
                    "network_forwarder_performance"
                ],  # Depends on all previous analysis steps
                context_requirements=["earliest_time", "latest_time", "focus_host", "focus_index"],
            ),
        ]

        return WorkflowDefinition(
            workflow_id="performance_analysis",
            name="Performance Analysis",
            description="Comprehensive performance analysis using Splunk Platform Instrumentation 10-step workflow",
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
        ctx: Context,
        execution_metadata: dict[str, Any] = None,
    ) -> WorkflowResult:
        """
        Execute a workflow by orchestrating dynamic micro-agents with progress reporting.

        Args:
            workflow_id: ID of the workflow to execute
            diagnostic_context: Context for diagnostic execution
            ctx: FastMCP context for progress reporting and logging
            execution_metadata: Optional metadata for execution tracking

        Returns:
            WorkflowResult containing execution results and summary
        """
        start_time = time.time()

        if execution_metadata is None:
            execution_metadata = {}

        logger.info("=" * 80)
        logger.info(f"STARTING WORKFLOW EXECUTION: {workflow_id}")
        logger.info("=" * 80)

        # Add comprehensive tracing for workflow execution
        if TRACING_AVAILABLE and trace:
            # Create unique trace name to avoid conflicts
            trace_timestamp = int(time.time() * 1000)
            trace_name = f"Workflow Execution {workflow_id} {trace_timestamp}"

            # Convert metadata to strings for OpenAI API compatibility
            trace_metadata = {
                "workflow_id": str(workflow_id),
                "earliest_time": str(diagnostic_context.earliest_time),
                "latest_time": str(diagnostic_context.latest_time),
                "focus_index": str(diagnostic_context.focus_index) if diagnostic_context.focus_index else "all",
                "focus_host": str(diagnostic_context.focus_host) if diagnostic_context.focus_host else "all",
                "complexity_level": str(diagnostic_context.complexity_level),
                "trace_timestamp": str(trace_timestamp),
            }

            with trace(workflow_name=trace_name, metadata=trace_metadata):
                return await self._execute_workflow_core(
                    workflow_id, diagnostic_context, ctx, execution_metadata, start_time
                )
        else:
            # Fallback execution without tracing
            logger.warning("OpenAI Agents tracing not available, executing without traces")
            return await self._execute_workflow_core(
                workflow_id, diagnostic_context, ctx, execution_metadata, start_time
            )

    async def _execute_workflow_core(
        self,
        workflow_id: str,
        diagnostic_context: SplunkDiagnosticContext,
        ctx: Context,
        execution_metadata: dict[str, Any],
        start_time: float,
    ) -> WorkflowResult:
        """Core workflow execution with tracing spans and progress reporting."""

        try:
            # Report initial progress
            await ctx.report_progress(progress=0, total=100)
            await ctx.info(f"🚀 Starting workflow: {workflow_id}")

            # Get workflow definition with tracing
            if TRACING_AVAILABLE and custom_span:
                with custom_span("workflow_definition_lookup"):
                    workflow = self.get_workflow(workflow_id)
                    if not workflow:
                        raise ValueError(f"Workflow '{workflow_id}' not found")

                    logger.info(f"Found workflow: {workflow.name} with {len(workflow.tasks)} tasks")
            else:
                workflow = self.get_workflow(workflow_id)
                if not workflow:
                    raise ValueError(f"Workflow '{workflow_id}' not found")
                logger.info(f"Found workflow: {workflow.name} with {len(workflow.tasks)} tasks")

            # Report progress: Workflow loaded
            await ctx.report_progress(progress=10, total=100)
            await ctx.info(f"📋 Loaded {workflow.name} with {len(workflow.tasks)} tasks")

            # Build dependency graph with tracing
            if TRACING_AVAILABLE and custom_span:
                with custom_span("dependency_analysis"):
                    dependency_graph = self._build_dependency_graph(workflow.tasks)
                    execution_phases = self._create_execution_phases(workflow.tasks, dependency_graph)

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

            # Report progress: Dependencies analyzed
            await ctx.report_progress(progress=20, total=100)
            await ctx.info(f"🔗 Analyzed dependencies: {len(execution_phases)} execution phases")

            # Execute tasks in phases with comprehensive tracing
            task_results: dict[str, DiagnosticResult] = {}
            phase_progress_step = 60 / len(execution_phases)  # 60% of progress for task execution

            for phase_idx, phase_tasks in enumerate(execution_phases):
                phase_name = f"execution_phase_{phase_idx + 1}"
                logger.info(f"Executing phase {phase_idx + 1}/{len(execution_phases)}: {phase_tasks}")

                # Report progress for this phase
                phase_progress = 20 + (phase_idx * phase_progress_step)
                await ctx.report_progress(progress=phase_progress, total=100)
                await ctx.info(f"⚡ Phase {phase_idx + 1}/{len(execution_phases)}: {len(phase_tasks)} parallel tasks")

                if TRACING_AVAILABLE and custom_span:
                    with custom_span(phase_name):
                        # Execute tasks in this phase (potentially in parallel)
                        phase_results = await self._execute_phase_with_tracing(
                            workflow, phase_tasks, diagnostic_context, task_results, ctx
                        )

                        # Update task results
                        task_results.update(phase_results)

                        # Add phase completion metrics
                        successful_tasks = [task_id for task_id, result in phase_results.items()
                                          if result.status in ["healthy", "warning"]]
                        failed_tasks = [task_id for task_id, result in phase_results.items()
                                      if result.status == "error"]

                        logger.info(f"Phase {phase_idx + 1} completed: {len(successful_tasks)} successful, {len(failed_tasks)} failed")
                        await ctx.info(f"✅ Phase {phase_idx + 1} complete: {len(successful_tasks)} successful, {len(failed_tasks)} failed")
                else:
                    # Execute tasks in this phase (potentially in parallel)
                    phase_results = await self._execute_phase_with_tracing(
                        workflow, phase_tasks, diagnostic_context, task_results, ctx
                    )

                    # Update task results
                    task_results.update(phase_results)

                    # Add phase completion metrics
                    successful_tasks = [task_id for task_id, result in phase_results.items()
                                      if result.status in ["healthy", "warning"]]
                    failed_tasks = [task_id for task_id, result in phase_results.items()
                                  if result.status == "error"]

                    logger.info(f"Phase {phase_idx + 1} completed: {len(successful_tasks)} successful, {len(failed_tasks)} failed")
                    await ctx.info(f"✅ Phase {phase_idx + 1} complete: {len(successful_tasks)} successful, {len(failed_tasks)} failed")

            # Report progress: Task execution complete
            await ctx.report_progress(progress=80, total=100)
            await ctx.info(f"🔄 All tasks completed, generating summary...")

            # Finalize workflow result with tracing
            if TRACING_AVAILABLE and custom_span:
                with custom_span("workflow_result_synthesis"):
                    workflow_result = await self._finalize_workflow_result(
                        workflow_id, workflow, task_results, execution_phases, start_time
                    )

                    logger.info(f"Workflow execution completed successfully")
                    logger.info(f"  - Status: {workflow_result.status}")
                    logger.info(f"  - Execution time: {workflow_result.execution_time:.2f}s")
                    logger.info(f"  - Tasks executed: {len(task_results)}")
            else:
                workflow_result = await self._finalize_workflow_result(
                    workflow_id, workflow, task_results, execution_phases, start_time
                )

                logger.info(f"Workflow execution completed successfully")
                logger.info(f"  - Status: {workflow_result.status}")
                logger.info(f"  - Execution time: {workflow_result.execution_time:.2f}s")
                logger.info(f"  - Tasks executed: {len(task_results)}")

            # Report final progress
            await ctx.report_progress(progress=100, total=100)
            await ctx.info(f"✅ Workflow {workflow_id} completed with status: {workflow_result.status}")

            return workflow_result

        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"Workflow execution failed: {e}", exc_info=True)
            await ctx.error(f"❌ Workflow {workflow_id} failed: {str(e)}")

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
        ctx: Context,
    ) -> dict[str, DiagnosticResult]:
        """Execute a phase of tasks with individual task tracing and progress reporting."""

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
                    self._execute_single_task_with_tracing(task_def, execution_context, ctx)
                )
            else:
                async_tasks.append(
                    self._execute_single_task_without_tracing(task_def, execution_context, ctx)
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
                    await ctx.error(f"❌ Task {task_id} failed: {str(result)}")
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
        ctx: Context,
    ) -> DiagnosticResult:
        """Execute a single task with comprehensive tracing and progress reporting."""

        with custom_span(f"task_execution_{task_def.task_id}"):
            # Create and execute dynamic agent
            dynamic_agent = create_dynamic_agent(self.config, self.tool_registry, task_def)

            try:
                result = await dynamic_agent.execute_task(execution_context, ctx)
                return result

            except Exception as e:
                logger.error(f"Task {task_def.task_id} execution failed: {e}", exc_info=True)
                await ctx.error(f"❌ Task {task_def.task_id} failed: {str(e)}")
                raise

    async def _execute_single_task_without_tracing(
        self,
        task_def: TaskDefinition,
        execution_context: AgentExecutionContext,
        ctx: Context,
    ) -> DiagnosticResult:
        """Execute a single task without tracing (fallback) but with progress reporting."""

        # Create and execute dynamic agent
        dynamic_agent = create_dynamic_agent(self.config, self.tool_registry, task_def)
        return await dynamic_agent.execute_task(execution_context, ctx)

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
    workflow_manager: WorkflowManager, diagnostic_context: SplunkDiagnosticContext, ctx: Context
) -> WorkflowResult:
    """Execute the missing data troubleshooting workflow with progress reporting."""
    return await workflow_manager.execute_workflow(
        "missing_data_troubleshooting", diagnostic_context, ctx
    )


async def execute_performance_workflow(
    workflow_manager: WorkflowManager, diagnostic_context: SplunkDiagnosticContext, ctx: Context
) -> WorkflowResult:
    """Execute the performance analysis workflow with progress reporting."""
    return await workflow_manager.execute_workflow("performance_analysis", diagnostic_context, ctx)



