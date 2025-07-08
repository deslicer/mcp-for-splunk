"""
Splunk Triage Agent System using OpenAI Agents SDK.

This module implements a hierarchical triage + specialist handoff pattern for
Splunk troubleshooting, following the OpenAI agents SDK patterns.
"""

import os
import asyncio
import logging
import time
from typing import Any, Dict, List, Optional
from dataclasses import dataclass

from fastmcp import Context
from openai import OpenAI

from ...core.base import BaseTool, ToolMetadata
from ...core.registry import prompt_registry
from ...prompts.troubleshooting import (
    TroubleshootPerformancePrompt,
    TroubleshootInputsPrompt,
    TroubleshootIndexingPerformancePrompt,
    TroubleshootInputsPromptMultiAgent
)

logger = logging.getLogger(__name__)

# Only import OpenAI agents if available
try:
    from agents import Agent, Runner, function_tool
    from agents.extensions.handoff_prompt import prompt_with_handoff_instructions
    OPENAI_AGENTS_AVAILABLE = True
    logger.info("OpenAI agents SDK loaded successfully")
except ImportError:
    OPENAI_AGENTS_AVAILABLE = False
    Agent = None
    Runner = None
    function_tool = None
    prompt_with_handoff_instructions = None
    logger.warning("OpenAI agents SDK not available. Install with: pip install openai-agents")


@dataclass
class SplunkDiagnosticContext:
    """Context for maintaining state across Splunk diagnostic workflows."""
    earliest_time: str = "-24h"
    latest_time: str = "now"
    focus_index: Optional[str] = None
    focus_host: Optional[str] = None
    complexity_level: str = "moderate"
    identified_issues: List[str] = None
    baseline_metrics: Dict[str, Any] = None
    validation_results: Dict[str, Any] = None

    def __post_init__(self):
        if self.identified_issues is None:
            self.identified_issues = []
        if self.baseline_metrics is None:
            self.baseline_metrics = {}
        if self.validation_results is None:
            self.validation_results = {}


class SplunkTriageAgentTool(BaseTool):
    """
    Splunk Missing Data Troubleshooting Tool using OpenAI Agents SDK.

    This tool implements the official Splunk "I can't find my data!" troubleshooting workflow
    following the structured checklist from Splunk's documentation. It systematically works
    through 10 key diagnostic steps to identify and resolve missing data issues.

    The workflow covers:
    - License and edition verification
    - Index configuration and access validation
    - Permissions and role-based access control
    - Time range and timestamp analysis
    - Forwarder connectivity checks
    - Search head configuration verification
    - License violation detection
    - Scheduled search issue analysis
    - Search query syntax validation
    - Field extraction troubleshooting
    """

    METADATA = ToolMetadata(
        name="execute_splunk_missing_data_troubleshooting",
        description="Execute the official Splunk 'I can't find my data!' troubleshooting workflow with systematic diagnostic steps and comprehensive step-by-step summary",
        category="troubleshooting"
    )

    def __init__(self, name: str, category: str):
        super().__init__(name, category)

        logger.info(f"Initializing SplunkTriageAgentTool: {name}")

        if not OPENAI_AGENTS_AVAILABLE:
            logger.error("OpenAI agents SDK is required for this tool")
            raise ImportError(
                "OpenAI agents SDK is required for this tool. "
                "Install with: pip install openai-agents"
            )

        logger.debug("Loading OpenAI configuration...")
        self.config = self._load_config()
        logger.info(f"OpenAI config loaded - Model: {self.config.model}, Temperature: {self.config.temperature}")

        self.client = OpenAI(api_key=self.config.api_key)

        # Initialize the agent system
        logger.info("Setting up agent system...")
        self._setup_agents()
        logger.info("SplunkTriageAgentTool initialization complete")

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

        from dataclasses import dataclass

        @dataclass
        class AgentConfig:
            api_key: str
            model: str = "gpt-4o"
            temperature: float = 0.7
            max_tokens: int = 4000

        config = AgentConfig(
            api_key=api_key,
            model=os.getenv("OPENAI_MODEL", "gpt-4o"),
            temperature=float(os.getenv("OPENAI_TEMPERATURE", "0.7")),
            max_tokens=int(os.getenv("OPENAI_MAX_TOKENS", "4000"))
        )

        logger.info(f"Configuration loaded: model={config.model}, temp={config.temperature}, max_tokens={config.max_tokens}")
        return config

    def _setup_agents(self):
        """Set up the hierarchical agent system."""

        logger.info("Setting up hierarchical agent system...")

        # Create Splunk tool functions for agents to use
        logger.debug("Creating Splunk tool functions...")
        self._create_splunk_tools()
        logger.info(f"Created {len(self.splunk_tools)} Splunk tool functions")

        # Create specialist agents
        logger.debug("Creating specialist agents...")

        logger.debug("Creating missing data specialist...")
        try:
            self.missing_data_specialist = self._create_missing_data_specialist()
            logger.info("Missing data specialist created successfully")
        except Exception as e:
            logger.error(f"Failed to create missing data specialist: {e}", exc_info=True)
            raise

        logger.debug("Creating inputs specialist...")
        self.inputs_specialist = self._create_inputs_specialist()
        logger.info("Inputs specialist created successfully")

        logger.debug("Creating performance specialist...")
        self.performance_specialist = self._create_performance_specialist()
        logger.info("Performance specialist created successfully")

        logger.debug("Creating indexing specialist...")
        self.indexing_specialist = self._create_indexing_specialist()
        logger.info("Indexing specialist created successfully")

        logger.debug("Creating general specialist...")
        self.general_specialist = self._create_general_specialist()
        logger.info("General specialist created successfully")

        # Create the main triage agent
        logger.debug("Creating main triage agent...")
        self.triage_agent = self._create_triage_agent()
        logger.info("Main triage agent created successfully")

        # Validate handoff configuration
        logger.debug("Validating handoff configuration...")
        if hasattr(self.triage_agent, 'handoffs') and self.triage_agent.handoffs:
            logger.info(f"Triage agent configured with {len(self.triage_agent.handoffs)} handoffs:")
            for i, handoff in enumerate(self.triage_agent.handoffs):
                if hasattr(handoff, 'name'):
                    logger.info(f"  {i+1}. {handoff.name}")
                else:
                    logger.info(f"  {i+1}. {type(handoff).__name__}")
        else:
            logger.warning("Triage agent has no handoffs configured!")

        logger.info("Agent system setup complete - All specialists and triage agent ready")

    def _create_splunk_tools(self):
        """Create function tools that wrap MCP server tools for triage execution."""

        logger.debug("Setting up direct tool registry access for triage execution...")

        # Import required modules
        try:
            from agents import function_tool
            logger.info("Successfully imported function_tool from OpenAI agents")
        except ImportError as e:
            logger.error(f"Failed to import OpenAI agents components: {e}")
            raise ImportError("OpenAI agents support required. Ensure openai-agents is installed.")

        # Import tool registry for direct access
        from ...core.registry import tool_registry

        # Define allowed tools (same filter as before)
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

        # Store the actual context for use in tool calls
        self._current_context = None

        def set_context(ctx):
            """Set the current context for tool calls."""
            self._current_context = ctx

        def get_context():
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

        # Store context setter for later use
        self._set_context = set_context

        @function_tool
        async def run_splunk_search(query: str, earliest_time: str = "-24h", latest_time: str = "now") -> str:
            """Execute a Splunk search query via direct tool registry and return results."""
            logger.debug(f"Executing direct search: {query[:100]}... (time: {earliest_time} to {latest_time})")

            try:
                # Get current context
                ctx = get_context()

                # Report progress for search execution
                if hasattr(ctx, 'info'):
                    await ctx.info(f"🔍 Executing search: {query[:50]}...")

                # Get the tool directly from registry
                tool = tool_registry.get_tool("run_oneshot_search")
                if not tool:
                    raise RuntimeError("run_oneshot_search tool not found in registry")

                logger.debug("Calling tool registry: run_oneshot_search")

                # Call the tool directly
                result = await tool.execute(
                    ctx,
                    query=query,
                    earliest_time=earliest_time,
                    latest_time=latest_time,
                    max_results=50
                )

                # Report completion
                if hasattr(ctx, 'info'):
                    await ctx.info(f"✅ Search completed, found {str(result).count('|') if '|' in str(result) else 'N/A'} results")

                logger.info(f"Direct search completed successfully, result length: {len(str(result))}")
                return str(result)

            except Exception as e:
                logger.error(f"Error executing direct search: {e}", exc_info=True)
                # Report error to context
                ctx = get_context()
                if hasattr(ctx, 'error'):
                    await ctx.error(f"Search failed: {str(e)}")
                return f"Error executing direct search: {str(e)}"

        @function_tool
        async def list_splunk_indexes() -> str:
            """List available Splunk indexes via direct tool registry."""
            logger.debug("Listing Splunk indexes via direct registry...")

            try:
                # Get current context
                ctx = get_context()

                # Report progress
                if hasattr(ctx, 'info'):
                    await ctx.info("📋 Retrieving available Splunk indexes...")

                # Get the tool directly from registry
                tool = tool_registry.get_tool("list_indexes")
                if not tool:
                    raise RuntimeError("list_indexes tool not found in registry")

                logger.debug("Calling tool registry: list_indexes")

                result = await tool.execute(ctx)

                # Report completion
                if hasattr(ctx, 'info'):
                    index_count = str(result).count('index:') if 'index:' in str(result) else 'unknown'
                    await ctx.info(f"✅ Retrieved {index_count} indexes")

                logger.info(f"Direct indexes listed successfully, result length: {len(str(result))}")
                return str(result)

            except Exception as e:
                logger.error(f"Error listing indexes via direct registry: {e}", exc_info=True)
                # Report error to context
                ctx = get_context()
                if hasattr(ctx, 'error'):
                    await ctx.error(f"Failed to list indexes: {str(e)}")
                return f"Error listing indexes via direct registry: {str(e)}"

        @function_tool
        async def get_splunk_health() -> str:
            """Check Splunk server health via direct tool registry."""
            logger.debug("Checking Splunk health via direct registry...")

            try:
                # Get current context
                ctx = get_context()
                # Report progress
                if hasattr(ctx, 'info'):
                    await ctx.info("🏥 Checking Splunk server health...")

                # Get the tool directly from registry
                tool = tool_registry.get_tool("get_splunk_health")
                if not tool:
                    raise RuntimeError("get_splunk_health tool not found in registry")

                logger.debug("Calling tool registry: get_splunk_health")

                result = await tool.execute(ctx)

                # Report completion
                if hasattr(ctx, 'info'):
                    status = 'healthy' if 'connected' in str(result) else 'issues detected'
                    await ctx.info(f"✅ Health check complete - Status: {status}")

                logger.info(f"Direct health check completed successfully, result length: {len(str(result))}")
                return str(result)

            except Exception as e:
                logger.error(f"Error checking health via direct registry: {e}", exc_info=True)
                # Report error to context
                ctx = get_context()
                if hasattr(ctx, 'error'):
                    await ctx.error(f"Health check failed: {str(e)}")
                return f"Error checking health via direct registry: {str(e)}"

        @function_tool
        async def get_current_user_info() -> str:
            """Get current authenticated user information including roles and capabilities via direct tool registry."""
            logger.debug("Getting current user information via direct registry...")

            try:
                # Get current context
                ctx = get_context()

                # Report progress
                if hasattr(ctx, 'info'):
                    await ctx.info("👤 Retrieving current user information...")

                # Get the tool directly from registry
                tool = tool_registry.get_tool("me")
                if not tool:
                    raise RuntimeError("me tool not found in registry")

                logger.debug("Calling tool registry: me")

                result = await tool.execute(ctx)

                # Report completion
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
                # Report error to context
                ctx = get_context()
                if hasattr(ctx, 'error'):
                    await ctx.error(f"Failed to get user information: {str(e)}")
                return f"Error getting user info via direct registry: {str(e)}"

        # Enhanced function to report specialist progress
        @function_tool
        async def report_specialist_progress(step_name: str, progress_percent: int = None) -> str:
            """Report progress from specialist agents back to the main context."""
            try:
                ctx = get_context()
                
                if progress_percent is not None and hasattr(ctx, 'report_progress'):
                    # Report numeric progress (specialist progress is in 40-85% range)
                    specialist_progress = 40 + int((progress_percent / 100) * 45)  # Map to 40-85% range
                    await ctx.report_progress(progress=specialist_progress, total=100)
                
                if hasattr(ctx, 'info'):
                    await ctx.info(f"🔧 Specialist: {step_name}")
                
                logger.info(f"Specialist progress reported: {step_name} ({progress_percent}%)")
                return f"Progress reported: {step_name}"
                
            except Exception as e:
                logger.error(f"Error reporting specialist progress: {e}")
                return f"Error reporting progress: {str(e)}"

        # Store tools for use by agents
        self.splunk_tools = [
            run_splunk_search, 
            list_splunk_indexes, 
            get_splunk_health, 
            get_current_user_info,
            report_specialist_progress
        ]
        logger.info(f"Created {len(self.splunk_tools)} direct registry tool wrappers for triage execution")

    def _create_missing_data_specialist(self) -> Agent:
        """Create the missing data troubleshooting specialist agent following Splunk's official workflow."""
        logger.debug("Creating missing data specialist agent...")

        agent = Agent(
            name="Splunk Missing Data Specialist",
            handoff_description="Expert in Splunk's official 'I can't find my data!' troubleshooting workflow",
            instructions=prompt_with_handoff_instructions("""
You are a Splunk missing data troubleshooting specialist following the official "I can't find my data!" workflow from Splunk documentation.

**IMPORTANT: Progress Reporting**
You MUST report progress at each major step using the `report_specialist_progress` function to prevent timeouts:
- Call `report_specialist_progress("Step X: Description", progress_percent)` at the start of each major step
- Progress should go from 0% to 100% across all 10 steps (approximately 10% per step)
- Always report progress BEFORE executing searches or other time-consuming operations

You systematically work through this structured checklist:

## 🔍 OFFICIAL SPLUNK MISSING DATA TROUBLESHOOTING CHECKLIST

### 1. SPLUNK LICENSE & EDITION VERIFICATION
**Start by reporting:** `report_specialist_progress("Step 1: Checking Splunk license and edition", 10)`

**Check if running Splunk Free:**
- Splunk Free doesn't support multiple users, distributed searching, or alerting
- Saved searches from other users may not be accessible
- Use search: `| rest /services/server/info | fields splunk_version, product_type, license_state`

### 2. INDEX VERIFICATION
**Start by reporting:** `report_specialist_progress("Step 2: Verifying index configuration", 20)`

**Was data added to a different index?**
- Some apps write to specific indexes (e.g., *nix/Windows apps use "os" index)
- Check available indexes and verify you're searching the right one
- Use search: `| eventcount summarize=false index=* | dedup index | table index`
- Try searching specific indexes: `index=os` or `index=main`

### 3. PERMISSIONS & ACCESS CONTROL
**Start by reporting:** `report_specialist_progress("Step 3: Checking permissions and access control", 30)`

**Do your permissions allow you to see the data?**
- First, get current user information: Use `get_current_user_info()` to get the user's roles and capabilities
- Check role-based index access restrictions
- Verify search filters aren't blocking data
- Use search: `| rest /services/authorization/roles | search title=<your_role> | table title, srchIndexesAllowed, srchIndexesDefault`

### 4. TIME RANGE ISSUES
**Start by reporting:** `report_specialist_progress("Step 4: Analyzing time range issues", 40)`

**Check time-related problems:**
- Verify events exist in your search time window
- Try "All time" search to catch future-timestamped events
- Check for indexing delays with: ` index=<your_index> | eval lag=_indextime-_time | stats avg(lag) max(lag) by index`
- Verify timezone settings for scheduled searches

### 5. FORWARDER CONNECTIVITY (if using forwarders)
**Start by reporting:** `report_specialist_progress("Step 5: Checking forwarder connectivity", 50)`

**Check forwarder connections:**
- Verify forwarders connecting: `index=_internal source=*metrics.log* tcpin_connections | stats count by sourceIp`
- Check output queues: `index=_internal source=*metrics.log* group=queue tcpout | stats count by name`
- Verify recent host activity: `| metadata type=hosts | eval diff=now()-recentTime | where diff < 600`
- Check connection logs: `index=_internal "Connected to idx" OR "cooked mode"`

### 6. SEARCH HEAD CONFIGURATION (distributed environment)
**Start by reporting:** `report_specialist_progress("Step 6: Verifying search head configuration", 60)`

**Verify search head setup:**
- Check search heads are connected to correct indexers
- Verify distributed search configuration
- Use: `| rest /services/search/distributed/peers | table title, status, is_https`

### 7. LICENSE VIOLATIONS
**Start by reporting:** `report_specialist_progress("Step 7: Checking for license violations", 70)`

**Check for license issues:**
- License violations prevent searching (but indexing continues)
- Check: `index=_internal source=*license_usage.log* type=Usage | stats sum(b) by pool`
- Verify license status: `| rest /services/licenser/messages | table category, message`

### 8. SCHEDULED SEARCH ISSUES
**Start by reporting:** `report_specialist_progress("Step 8: Analyzing scheduled search issues", 80)`

**For scheduled searches:**
- Verify time ranges aren't excluding events
- Check for indexing lag affecting recent data
- Examine scheduler performance: `index=_internal source=*scheduler.log* | stats count by status`
- Check dispatch directory for search artifacts

### 9. SEARCH QUERY VALIDATION
**Start by reporting:** `report_specialist_progress("Step 9: Validating search query syntax", 90)`

**Verify search syntax:**
- Check logic operators (NOT, AND, OR) usage
- Verify quote usage and escape characters
- Confirm correct index, source, sourcetype, host specifications
- Test subsearch ordering and field passing
- Check for intentions framework rewrites in drilldowns

### 10. FIELD EXTRACTION ISSUES
**Start by reporting:** `report_specialist_progress("Step 10: Checking field extraction issues", 100)`

**For field extraction problems:**
- Test regex patterns with rex command
- Verify extraction permissions and sharing
- Check extractions applied to correct source/sourcetype/host
- Use: `| rest /services/data/props/extractions | search stanza=<your_sourcetype>`

## 🎯 SYSTEMATIC APPROACH:

1. **Always start each step with progress reporting** using `report_specialist_progress`
2. **Start with basics**: Check Splunk edition, license, and obvious issues
3. **Index verification**: Confirm data location and access permissions
4. **Time analysis**: Rule out time range and timestamp issues
5. **Infrastructure**: Verify forwarders, search heads, and connectivity
6. **Search validation**: Check query syntax and field extractions
7. **Advanced diagnostics**: Deep dive into specific component issues

## 📊 KEY DIAGNOSTIC SEARCHES:

Always provide specific search queries for each check and explain the expected results.
Interpret findings in context of the user's specific problem.
Provide clear next steps based on what you discover.

Use the available Splunk tools to systematically work through this checklist.
Document your findings at each step and provide actionable recommendations.

**CRITICAL: Always call `report_specialist_progress` before executing searches or time-consuming operations to prevent timeouts!**
            """),
            model=self.config.model,
            tools=self.splunk_tools
        )

        logger.debug("Missing data specialist agent created with official workflow and progress reporting")
        return agent

    def _create_inputs_specialist(self) -> Agent:
        """Create the inputs troubleshooting specialist agent."""
        logger.debug("Creating inputs specialist agent...")

        agent = Agent(
            name="Splunk Inputs Specialist",
            handoff_description="Expert in Splunk data input and ingestion troubleshooting",
            instructions=prompt_with_handoff_instructions("""
You are a Splunk inputs troubleshooting specialist. You excel at diagnosing and resolving:

**IMPORTANT: Progress Reporting**
You MUST report progress using `report_specialist_progress` function to prevent timeouts:
- Call `report_specialist_progress("Step description", progress_percent)` at each major step
- Report progress BEFORE executing searches or time-consuming operations

- Data ingestion issues and missing data
- Universal Forwarder connectivity problems
- Input configuration and parsing issues
- Source and sourcetype problems
- Network connectivity for data inputs

Your approach:
1. **Start:** `report_specialist_progress("Starting inputs analysis", 10)`
2. Get current user information to understand permissions and access
3. **Progress:** `report_specialist_progress("Checking system health", 25)`
4. Check system health and available indexes
5. **Progress:** `report_specialist_progress("Analyzing input throughput", 50)`
6. Analyze metrics.log for input throughput patterns
7. **Progress:** `report_specialist_progress("Investigating metrics", 75)`
8. Investigate per_index_thruput and per_host_thruput metrics
9. Examine source and sourcetype distributions
10. **Complete:** `report_specialist_progress("Finalizing analysis", 100)`
11. Correlate findings with error logs
12. Provide specific, actionable recommendations

Use the available Splunk tools to gather data and provide comprehensive analysis.
Start with `get_current_user_info()` to understand the user's role and index access.
Always explain your reasoning and cite specific metrics or log entries.

**CRITICAL: Always call `report_specialist_progress` before executing searches to prevent timeouts!**
            """),
            model=self.config.model,
            tools=self.splunk_tools
        )

        logger.debug("Inputs specialist agent created with model, tools, and progress reporting configured")
        return agent

    def _create_performance_specialist(self) -> Agent:
        """Create the performance troubleshooting specialist agent."""
        logger.debug("Creating performance specialist agent...")

        agent = Agent(
            name="Splunk Performance Specialist",
            handoff_description="Expert in Splunk system performance and capacity analysis",
            instructions=prompt_with_handoff_instructions("""
You are a Splunk performance specialist. You excel at diagnosing and optimizing:

**IMPORTANT: Progress Reporting**
You MUST report progress using `report_specialist_progress` function to prevent timeouts:
- Call `report_specialist_progress("Step description", progress_percent)` at each major step
- Report progress BEFORE executing searches or time-consuming operations

- System resource utilization (CPU, memory, disk I/O)
- Search performance and concurrency issues
- Indexing throughput and capacity planning
- Queue management and processing bottlenecks
- Network performance and bandwidth utilization

Your approach:
1. **Start:** `report_specialist_progress("Starting performance analysis", 15)`
2. Establish baseline performance metrics
3. **Progress:** `report_specialist_progress("Analyzing resource utilization", 35)`
4. Analyze resource utilization patterns
5. **Progress:** `report_specialist_progress("Examining search concurrency", 55)`
6. Examine search concurrency and scheduling
7. **Progress:** `report_specialist_progress("Investigating queue management", 75)`
8. Investigate queue sizes and processing delays
9. **Progress:** `report_specialist_progress("Correlating performance events", 90)`
10. Correlate performance with system events
11. **Complete:** `report_specialist_progress("Generating recommendations", 100)`
12. Provide optimization recommendations

Use Splunk searches to gather performance data from _internal index.
Focus on metrics.log, scheduler.log, and resource usage patterns.
Provide specific tuning recommendations with expected impact.

**CRITICAL: Always call `report_specialist_progress` before executing searches to prevent timeouts!**
            """),
            model=self.config.model,
            tools=self.splunk_tools
        )

        logger.debug("Performance specialist agent created with model, tools, and progress reporting configured")
        return agent

    def _create_indexing_specialist(self) -> Agent:
        """Create the indexing performance specialist agent."""
        logger.debug("Creating indexing specialist agent...")

        agent = Agent(
            name="Splunk Indexing Specialist",
            handoff_description="Expert in Splunk indexing performance and pipeline optimization",
            instructions=prompt_with_handoff_instructions("""
You are a Splunk indexing specialist. You excel at diagnosing and optimizing:

**IMPORTANT: Progress Reporting**
You MUST report progress using `report_specialist_progress` function to prevent timeouts:
- Call `report_specialist_progress("Step description", progress_percent)` at each major step
- Report progress BEFORE executing searches or time-consuming operations

- Indexing delays and processing latency
- Hot/warm/cold bucket management
- Index clustering and replication issues
- Parsing and transformation performance
- Storage optimization and retention policies

Your approach:
1. **Start:** `report_specialist_progress("Starting indexing analysis", 12)`
2. Analyze indexing delay patterns and trends
3. **Progress:** `report_specialist_progress("Examining bucket management", 30)`
4. Examine bucket management and storage utilization
5. **Progress:** `report_specialist_progress("Investigating parsing efficiency", 50)`
6. Investigate parsing efficiency and transformation costs
7. **Progress:** `report_specialist_progress("Checking cluster health", 70)`
8. Check cluster health and replication status
9. **Progress:** `report_specialist_progress("Reviewing retention policies", 85)`
10. Review retention policies and storage allocation
11. **Complete:** `report_specialist_progress("Finalizing indexing recommendations", 100)`
12. Provide indexing optimization strategies

Use detailed analysis of per_index_thruput metrics and avg_age indicators.
Focus on identifying bottlenecks in the indexing pipeline.
Provide specific configuration recommendations for optimal performance.

**CRITICAL: Always call `report_specialist_progress` before executing searches to prevent timeouts!**
            """),
            model=self.config.model,
            tools=self.splunk_tools
        )

        logger.debug("Indexing specialist agent created with model, tools, and progress reporting configured")
        return agent

    def _create_general_specialist(self) -> Agent:
        """Create the general troubleshooting specialist agent."""
        logger.debug("Creating general specialist agent...")

        agent = Agent(
            name="Splunk General Specialist",
            handoff_description="General Splunk troubleshooting and system health expert",
            instructions=prompt_with_handoff_instructions("""
You are a general Splunk troubleshooting specialist. You handle:

**IMPORTANT: Progress Reporting**
You MUST report progress using `report_specialist_progress` function to prevent timeouts:
- Call `report_specialist_progress("Step description", progress_percent)` at each major step
- Report progress BEFORE executing searches or time-consuming operations

- Overall system health assessment
- Configuration validation and best practices
- License usage and compliance monitoring
- General diagnostic workflows
- Cross-component issue correlation

Your approach:
1. **Start:** `report_specialist_progress("Starting general analysis", 10)`
2. Get current user information to understand context and permissions
3. **Progress:** `report_specialist_progress("Performing health check", 25)`
4. Perform comprehensive system health check
5. **Progress:** `report_specialist_progress("Reviewing system metrics", 45)`
6. Review overall system metrics and trends
7. **Progress:** `report_specialist_progress("Identifying configuration issues", 65)`
8. Identify potential configuration issues
9. **Progress:** `report_specialist_progress("Checking license constraints", 80)`
10. Check for license or capacity constraints
11. **Progress:** `report_specialist_progress("Generating recommendations", 95)`
12. Provide general recommendations and next steps
13. **Complete:** `report_specialist_progress("Analysis complete", 100)`
14. Route to specialists if specific issues are identified

Start with `get_current_user_info()` to understand the user's role and access levels.
Then perform broad system assessment using available tools.
Look for obvious issues or patterns that need specialist attention.
Provide clear, actionable guidance for common problems.

**CRITICAL: Always call `report_specialist_progress` before executing searches to prevent timeouts!**
            """),
            model=self.config.model,
            tools=self.splunk_tools
        )

        logger.debug("General specialist agent created with model, tools, and progress reporting configured")
        return agent

    def _create_triage_agent(self) -> Agent:
        """Create the main triage agent that routes to specialists."""
        logger.debug("Creating main triage agent...")

        agent = Agent(
            name="Splunk Diagnostic Triage Agent",
            instructions=prompt_with_handoff_instructions("""
You are a Splunk expert triage agent. Your role is to analyze user problems and route them to the appropriate specialist agent.

ROUTING DECISION TREE:

🔍 **Missing Data Issues** → Transfer to Splunk Missing Data Specialist
- "Can't find my data" or "No results found"
- Missing events or empty search results
- Data that should be there but isn't showing up
- Dashboard showing "No result data"
- Scheduled searches returning no results
- Expected data not appearing in searches

⚡ **Input/Ingestion Issues** → Transfer to Splunk Inputs Specialist
- Data ingestion problems (new data not coming in)
- Forwarder connectivity issues
- Source/sourcetype configuration problems
- Data parsing or format issues
- Network input failures

🚀 **Performance Issues** → Transfer to Splunk Performance Specialist
- Slow search performance
- High resource utilization (CPU, memory, disk)
- System capacity concerns
- Search concurrency problems
- General system slowness

📊 **Indexing Issues** → Transfer to Splunk Indexing Specialist
- Indexing delays or high latency
- Bucket management problems
- Storage optimization needs
- Index clustering issues
- Parsing performance problems

🏥 **General/Health Issues** → Transfer to Splunk General Specialist
- Overall system health checks
- Configuration validation
- License monitoring
- General troubleshooting
- Multiple component issues

## KEY ROUTING LOGIC:

**Missing Data vs Input Issues:**
- Missing Data = Expected data exists but can't find it (search/access problem)
- Input Issues = New data not being ingested (ingestion problem)

**Performance vs Indexing:**
- Performance = Search speed, resource usage, general slowness
- Indexing = Specific delays in data processing pipeline

ANALYSIS APPROACH:
1. Carefully read the user's problem description
2. Identify key symptoms and affected components
3. Determine the primary issue category
4. Select the most appropriate specialist
5. Use the transfer tool to handoff to that specialist

CRITICAL HANDOFF REQUIREMENT:
When you identify the appropriate specialist for the user's problem, you MUST immediately use the corresponding transfer tool to handoff the conversation. Do NOT just explain that you will route - you must actually execute the transfer.

Available transfer tools:
- transfer_to_splunk_missing_data_specialist: For missing data issues
- transfer_to_splunk_inputs_specialist: For input/ingestion problems
- transfer_to_splunk_performance_specialist: For performance issues
- transfer_to_splunk_indexing_specialist: For indexing problems
- transfer_to_splunk_general_specialist: For general troubleshooting

Example: If the user reports "I can't find my data in index=cca_insights", immediately call transfer_to_splunk_inputs_specialist since this is an input/ingestion issue.
            """),
            handoffs=[
                self.missing_data_specialist,
                self.inputs_specialist,
                self.performance_specialist,
                self.indexing_specialist,
                self.general_specialist
            ],
            model=self.config.model
        )

        logger.debug("Main triage agent created with handoffs to all specialists including missing data")
        logger.info(f"Triage agent configured with {len(agent.handoffs)} specialist handoffs")
        return agent

    async def execute(
        self,
        ctx: Context,
        problem_description: str,
        earliest_time: str = "-24h",
        latest_time: str = "now",
        focus_index: Optional[str] = None,
        focus_host: Optional[str] = None,
        complexity_level: str = "moderate"
    ) -> Dict[str, Any]:
        """
        Execute the Splunk triage agent system.

        This method uses the triage agent to analyze the problem and route to the
        appropriate specialist agent for detailed troubleshooting.

        Args:
            ctx: FastMCP context
            problem_description: Description of the issue to troubleshoot
            earliest_time: Start time for analysis
            latest_time: End time for analysis
            focus_index: Specific index to focus on (optional)
            focus_host: Specific host to focus on (optional)
            complexity_level: Analysis complexity level

        Returns:
            Dict containing the triage and specialist analysis results
        """
        execution_start_time = time.time()
        logger.info("="*80)
        logger.info("STARTING SPLUNK TRIAGE AGENT EXECUTION")
        logger.info("="*80)

        try:
            logger.info(f"Problem: {problem_description[:200]}...")
            logger.info(f"Time range: {earliest_time} to {latest_time}")
            logger.info(f"Focus - Index: {focus_index}, Host: {focus_host}")
            logger.info(f"Complexity level: {complexity_level}")

            # Report initial progress
            await ctx.report_progress(progress=0, total=100)
            await ctx.info(f"🔍 Starting Splunk triage analysis for: {problem_description[:100]}...")

            # Set the context for tool calls
            if hasattr(self, '_set_context'):
                self._set_context(ctx)
                logger.debug("Context set for direct tool registry access")

            # Report progress: Setup complete
            await ctx.report_progress(progress=10, total=100)
            logger.info(f"Starting Splunk triage agent execution")

            # Create diagnostic context
            logger.debug("Creating diagnostic context...")
            diagnostic_context = SplunkDiagnosticContext(
                earliest_time=earliest_time,
                latest_time=latest_time,
                focus_index=focus_index,
                focus_host=focus_host,
                complexity_level=complexity_level
            )
            logger.info(f"Diagnostic context created: {diagnostic_context}")

            # Report progress: Context created
            await ctx.report_progress(progress=20, total=100)

            # Create enhanced input for triage analysis
            logger.debug("Creating enhanced input for triage agent...")
            enhanced_input = self._create_enhanced_input(
                problem_description, diagnostic_context
            )
            logger.info(f"Enhanced input created, length: {len(enhanced_input)} characters")
            logger.debug(f"Enhanced input preview: {enhanced_input[:300]}...")

            # Report progress: Input prepared
            await ctx.report_progress(progress=30, total=100)
            await ctx.info("🤖 Executing triage agent with OpenAI Runner...")
            logger.info("Executing triage agent with OpenAI Runner...")

            # Run the triage agent which will route to appropriate specialist
            agent_start_time = time.time()
            logger.debug("Calling Runner.run() with triage agent...")

            # Report progress: Agent execution starting
            await ctx.report_progress(progress=40, total=100)

            # Create a task to periodically report progress during agent execution
            async def periodic_progress_reporter():
                """Report progress periodically during agent execution."""
                progress = 40
                while progress < 85:
                    await asyncio.sleep(5)  # Report every 5 seconds
                    progress = min(85, progress + 5)
                    await ctx.report_progress(progress=progress, total=100)
                    await ctx.info(f"🤖 Agent analysis in progress... ({progress}%)")

            # Start the progress reporter
            progress_task = asyncio.create_task(periodic_progress_reporter())

            try:
                result = await Runner.run(
                    self.triage_agent,
                    input=enhanced_input,
                    context=diagnostic_context,
                    max_turns=20  # Allow multiple turns for handoffs
                )
            finally:
                # Cancel the progress reporter
                progress_task.cancel()
                try:
                    await progress_task
                except asyncio.CancelledError:
                    pass

            # Report progress: Agent execution complete
            await ctx.report_progress(progress=90, total=100)

            agent_execution_time = time.time() - agent_start_time
            logger.info(f"Agent execution completed in {agent_execution_time:.2f} seconds")

            # Log detailed results
            logger.info("AGENT EXECUTION RESULTS:")
            logger.info(f"- Final output length: {len(result.final_output) if result.final_output else 0}")
            logger.info(f"- Last agent: {result.last_agent.name if result.last_agent else 'Unknown'}")
            logger.info(f"- New items count: {len(result.new_items)}")
            logger.info(f"- Conversation length: {len(result.to_input_list())}")

            # Log handoff information
            if hasattr(result, 'handoffs_occurred'):
                logger.info(f"- Handoffs occurred: {result.handoffs_occurred}")

            # Extract step-by-step analysis from conversation
            conversation_history = result.to_input_list()

            # Log conversation structure for debugging
            logger.debug("="*50)
            logger.debug("CONVERSATION STRUCTURE DEBUG")
            logger.debug("="*50)
            for i, msg in enumerate(conversation_history):
                if isinstance(msg, dict):
                    role = msg.get('role', 'unknown')
                    content = msg.get('content', '')

                    # Log content structure
                    if isinstance(content, list):
                        logger.debug(f"Message {i} ({role}): List with {len(content)} items")
                        for j, item in enumerate(content[:2]):  # First 2 items
                            logger.debug(f"  Item {j}: {type(item)} - {str(item)[:100]}...")
                    else:
                        logger.debug(f"Message {i} ({role}): {type(content)} - {str(content)[:100]}...")

                    # Check for tool_calls
                    if 'tool_calls' in msg:
                        logger.debug(f"  Has tool_calls: {msg['tool_calls']}")
                else:
                    logger.debug(f"Message {i}: {type(msg)} - {str(msg)[:100]}...")
            logger.debug("="*50)

            step_summary = self._extract_step_summary(conversation_history, result.last_agent)

            logger.debug(f"Conversation history ({len(conversation_history)} items):")
            for i, item in enumerate(conversation_history):
                if isinstance(item, dict):
                    role = item.get('role', 'unknown')
                    content_preview = str(item.get('content', ''))[:100]
                    logger.debug(f"  {i}: {role} - {content_preview}...")

            # Log agent response preview
            if result.final_output:
                logger.debug(f"Agent response preview: {result.final_output[:500]}...")

            # Report progress: Processing results
            await ctx.report_progress(progress=95, total=100)
            await ctx.info("✅ Triage agent execution completed")
            logger.info("Triage agent execution completed successfully")

            total_execution_time = time.time() - execution_start_time

            execution_result = {
                "status": "success",
                "workflow_type": "triage_system",
                "problem_description": problem_description,
                "diagnostic_context": {
                    "earliest_time": earliest_time,
                    "latest_time": latest_time,
                    "focus_index": focus_index,
                    "focus_host": focus_host,
                    "complexity_level": complexity_level
                },
                "troubleshooting_results": result.final_output,
                "routed_to_specialist": result.last_agent.name if result.last_agent else "No handoff occurred",
                "analysis_steps": len(result.new_items),
                "conversation_length": len(result.to_input_list()),
                "step_summary": step_summary,
                "execution_times": {
                    "total_execution_time": total_execution_time,
                    "workflow_execution_time": agent_execution_time
                }
            }

            # Report final progress
            await ctx.report_progress(progress=100, total=100)

            logger.info("="*80)
            logger.info("TRIAGE AGENT EXECUTION COMPLETED SUCCESSFULLY")
            logger.info(f"Total execution time: {total_execution_time:.2f} seconds")
            logger.info(f"Routed to specialist: {execution_result['routed_to_specialist']}")
            logger.info("="*80)

            return execution_result

        except Exception as e:
            execution_time = time.time() - execution_start_time
            error_msg = f"Triage agent execution failed: {str(e)}"

            logger.error("="*80)
            logger.error("TRIAGE AGENT EXECUTION FAILED")
            logger.error(f"Error: {error_msg}")
            logger.error(f"Execution time before failure: {execution_time:.2f} seconds")
            logger.error("="*80)
            logger.error(f"Full error details:", exc_info=True)

            await ctx.error(error_msg)
            return {
                "status": "error",
                "workflow_type": "triage_system",
                "error": error_msg,
                "error_type": "workflow_execution_error",
                "execution_time": execution_time,
                "step_summary": {
                    "workflow_overview": {
                        "initial_triage": "Failed during execution",
                        "specialist_assigned": "None - execution failed",
                        "total_conversation_turns": 0
                    },
                    "execution_summary": {
                        "tools_used": 0,
                        "diagnostic_steps_performed": 0,
                        "key_findings_identified": 0,
                        "recommendations_provided": 0,
                        "routing_successful": False
                    },
                    "error_details": {
                        "failure_point": "Agent execution",
                        "error_message": error_msg
                    }
                }
            }

    def _create_missing_data_input(
        self,
        problem_description: str,
        context: SplunkDiagnosticContext
    ) -> str:
        """Create enhanced input specifically for missing data troubleshooting workflow."""

        logger.debug("Creating enhanced input for missing data troubleshooting...")

        context_info = []

        if context.earliest_time and context.latest_time:
            context_info.append(f"Time Range: {context.earliest_time} to {context.latest_time}")

        if context.focus_index:
            context_info.append(f"Focus Index: {context.focus_index}")

        if context.focus_host:
            context_info.append(f"Focus Host: {context.focus_host}")

        context_info.append(f"Analysis Complexity: {context.complexity_level}")

        context_str = "\n".join([f"- {info}" for info in context_info])

        enhanced_input = f"""
**Splunk Missing Data Troubleshooting Request**

**Problem Description:**
{problem_description}

**Diagnostic Context:**
{context_str}

**Workflow Instructions:**
Please execute the complete official Splunk "I can't find my data!" troubleshooting workflow.
Work through each step systematically:

1. Check Splunk license and edition
2. Verify index configuration and access
3. Validate permissions and role restrictions
4. Analyze time range and timestamp issues
5. Check forwarder connectivity (if applicable)
6. Verify search head configuration (if distributed)
7. Check for license violations
8. Analyze scheduled search issues (if applicable)
9. Validate search query syntax and logic
10. Check field extraction configurations

For each step, provide:
- The specific diagnostic search query used
- The results obtained
- Your interpretation of the findings
- Recommended next actions

Document your complete analysis and provide actionable recommendations for resolving the missing data issue.
"""

        logger.debug(f"Enhanced missing data input created with {len(context_info)} context items")
        return enhanced_input

    def _create_enhanced_input(
        self,
        problem_description: str,
        context: SplunkDiagnosticContext
    ) -> str:
        """Create enhanced input with diagnostic context (legacy method for compatibility)."""

        logger.debug("Creating enhanced input with diagnostic context...")

        context_info = []

        if context.earliest_time and context.latest_time:
            context_info.append(f"Time Range: {context.earliest_time} to {context.latest_time}")

        if context.focus_index:
            context_info.append(f"Focus Index: {context.focus_index}")

        if context.focus_host:
            context_info.append(f"Focus Host: {context.focus_host}")

        context_info.append(f"Analysis Complexity: {context.complexity_level}")

        context_str = "\n".join([f"- {info}" for info in context_info])

        enhanced_input = f"""
**Splunk Troubleshooting Request**

**Problem Description:**
{problem_description}

**Diagnostic Context:**
{context_str}

Please analyze this issue and route to the appropriate specialist agent for detailed troubleshooting.
"""

        logger.debug(f"Enhanced input created with {len(context_info)} context items")
        return enhanced_input

    def _extract_step_summary(self, conversation_history: List[Dict], last_agent) -> Dict[str, Any]:
        """
        Extract a comprehensive step-by-step summary from the agent conversation.

        This method analyzes the conversation history to identify:
        - Routing decisions made by the triage agent
        - Tools called by specialists
        - Key findings and diagnostics performed
        - Actions taken and recommendations provided

        Args:
            conversation_history: List of conversation messages
            last_agent: The final agent that handled the request

        Returns:
            Dict containing structured summary of steps taken
        """
        logger.debug("Extracting step summary from conversation history...")
        logger.debug(f"Conversation history length: {len(conversation_history)}")

        summary = {
            "workflow_overview": {
                "initial_triage": "Analyzed problem and routed to appropriate specialist",
                "specialist_assigned": last_agent.name if last_agent else "No specialist assigned",
                "total_conversation_turns": len(conversation_history)
            },
            "routing_decision": {
                "decision_made": True,  # We know routing happened if we have a last_agent
                "routing_rationale": "Triage agent analyzed the problem and routed to specialist",
                "target_specialist": last_agent.name if last_agent else "Unknown"
            },
            "tools_executed": [],
            "diagnostic_steps": [],
            "key_findings": [],
            "recommendations": [],
            "timeline": []
        }

        current_step = 1
        tools_called = set()

        # Enhanced debug logging to understand conversation structure
        logger.debug("="*60)
        logger.debug("DETAILED CONVERSATION ANALYSIS")
        logger.debug("="*60)
        
        for i, message in enumerate(conversation_history):
            logger.debug(f"\nMessage {i}:")
            logger.debug(f"  Type: {type(message)}")
            
            if isinstance(message, dict):
                logger.debug(f"  Keys: {list(message.keys())}")
                role = message.get('role', 'unknown')
                logger.debug(f"  Role: {role}")
                
                # Check for tool_calls in various possible locations
                tool_calls_found = []
                
                # Check direct tool_calls key
                if 'tool_calls' in message:
                    tool_calls_found.append(f"Direct tool_calls: {message['tool_calls']}")
                
                # Check for tool_calls in content if content is dict
                content = message.get('content', '')
                if isinstance(content, dict) and 'tool_calls' in content:
                    tool_calls_found.append(f"Content tool_calls: {content['tool_calls']}")
                
                # Check for function_call (alternative format)
                if 'function_call' in message:
                    tool_calls_found.append(f"Function call: {message['function_call']}")
                
                # Check for any keys that might contain tool info
                for key in message.keys():
                    if 'tool' in key.lower() or 'function' in key.lower():
                        tool_calls_found.append(f"Key '{key}': {message[key]}")
                
                if tool_calls_found:
                    logger.debug(f"  Tool calls found: {tool_calls_found}")
                else:
                    logger.debug("  No tool calls found in this message")
                
                # Log content structure
                logger.debug(f"  Content type: {type(content)}")
                if isinstance(content, str):
                    logger.debug(f"  Content preview: {content[:200]}...")
                elif isinstance(content, list):
                    logger.debug(f"  Content list length: {len(content)}")
                    for j, item in enumerate(content[:2]):
                        logger.debug(f"    Item {j}: {type(item)} - {str(item)[:100]}...")
                elif isinstance(content, dict):
                    logger.debug(f"  Content dict keys: {list(content.keys())}")
            else:
                logger.debug(f"  Non-dict message: {str(message)[:200]}...")
        
        logger.debug("="*60)

        # Now process messages with improved tool detection
        for i, message in enumerate(conversation_history):
            if not isinstance(message, dict):
                continue

            role = message.get('role', '')
            content = message.get('content', '')

            # Handle different content formats from OpenAI agents
            if isinstance(content, list):
                # OpenAI format: content is a list of content blocks
                content_text = ""
                for block in content:
                    if isinstance(block, dict):
                        if block.get('type') == 'text':
                            content_text += block.get('text', '')
                        elif 'text' in block:
                            content_text += block.get('text', '')
                        else:
                            # Handle other block types that might contain text
                            content_text += str(block)
                content = content_text
            elif isinstance(content, dict):
                # Handle dict content
                content = content.get('text', str(content))

            content = str(content)
            timestamp = i  # Use message index as relative timestamp

            # Enhanced tool call detection - check multiple possible locations
            tool_calls_detected = []
            
            # Method 1: Check direct tool_calls key (standard OpenAI format)
            if 'tool_calls' in message:
                tool_calls = message.get('tool_calls', [])
                if isinstance(tool_calls, list):
                    tool_calls_detected.extend(tool_calls)
                elif tool_calls:  # Single tool call
                    tool_calls_detected.append(tool_calls)
            
            # Method 2: Check function_call (alternative format)
            if 'function_call' in message:
                function_call = message.get('function_call', {})
                if isinstance(function_call, dict) and function_call.get('name'):
                    tool_calls_detected.append({
                        'function': {
                            'name': function_call.get('name'),
                            'arguments': function_call.get('arguments', {})
                        }
                    })
            
            # Method 3: Check content for tool calls (if content is dict)
            original_content = message.get('content', '')
            if isinstance(original_content, dict) and 'tool_calls' in original_content:
                content_tool_calls = original_content.get('tool_calls', [])
                if isinstance(content_tool_calls, list):
                    tool_calls_detected.extend(content_tool_calls)
            
            # Method 4: OpenAI Agents SDK format - direct tool call message
            # Check if this message itself IS a tool call (has name, arguments, call_id)
            if 'name' in message and 'arguments' in message and 'call_id' in message:
                # This is a tool call message in OpenAI agents format
                function_name = message.get('name', '')
                arguments = message.get('arguments', {})
                call_id = message.get('call_id', '')
                
                if function_name:
                    tool_calls_detected.append({
                        'function': {
                            'name': function_name,
                            'arguments': arguments
                        },
                        'id': call_id,
                        'type': 'function'
                    })
                    logger.debug(f"Detected OpenAI agents tool call: {function_name} with call_id: {call_id}")
            
            # Process detected tool calls
            for tool_call in tool_calls_detected:
                if isinstance(tool_call, dict):
                    # Handle different tool call formats
                    function_name = None
                    arguments = {}
                    call_id = tool_call.get('id', '')
                    
                    # Format 1: OpenAI standard format
                    if 'function' in tool_call:
                        function_info = tool_call.get('function', {})
                        function_name = function_info.get('name', '')
                        arguments = function_info.get('arguments', {})
                    
                    # Format 2: Direct format
                    elif 'name' in tool_call:
                        function_name = tool_call.get('name', '')
                        arguments = tool_call.get('arguments', {})
                    
                    # Format 3: Alternative format
                    elif 'tool_name' in tool_call:
                        function_name = tool_call.get('tool_name', '')
                        arguments = tool_call.get('arguments', {})
                    
                    if function_name and function_name not in tools_called:
                        tools_called.add(function_name)
                        description = self._get_tool_description(function_name)
                        
                        # Parse arguments if they're a string
                        if isinstance(arguments, str):
                            try:
                                import json
                                arguments = json.loads(arguments)
                            except:
                                arguments = {}
                        
                        summary["tools_executed"].append({
                            "step": current_step,
                            "tool": function_name,
                            "description": description,
                            "arguments": arguments,
                            "call_id": call_id,
                            "timestamp": timestamp
                        })
                        current_step += 1
                        
                        logger.debug(f"Detected tool call: {function_name} with args: {arguments}")

            # Enhanced tool mention detection in content (as fallback)
            tool_patterns = [
                ('get_current_user_info', 'Retrieved current user information and permissions'),
                ('list_splunk_indexes', 'Listed available Splunk indexes'),
                ('get_splunk_health', 'Checked Splunk server health status'),
                ('run_splunk_search', 'Executed Splunk search query'),
                ('list_sources', 'Listed available data sources'),
                ('list_sourcetypes', 'Listed available sourcetypes'),
                ('list_triggered_alerts', 'Checked triggered alerts')
            ]

            # Look for tool mentions in content (as fallback)
            for tool_name, description in tool_patterns:
                # Check for various patterns that might indicate tool usage
                patterns_to_check = [
                    tool_name,
                    f'`{tool_name}`',
                    f'"{tool_name}"',
                    f"'{tool_name}'",
                    f'calling {tool_name}',
                    f'execute {tool_name}',
                    f'run {tool_name}',
                    f'using {tool_name}'
                ]
                
                for pattern in patterns_to_check:
                    if pattern in content.lower() and tool_name not in tools_called:
                        tools_called.add(tool_name)
                        summary["tools_executed"].append({
                            "step": current_step,
                            "tool": tool_name,
                            "description": description,
                            "arguments": {},
                            "timestamp": timestamp,
                            "detection_method": "content_pattern"
                        })
                        current_step += 1
                        logger.debug(f"Detected tool mention in content: {tool_name}")
                        break

            # Extract diagnostic steps from assistant messages
            if role == 'assistant' and len(content) > 50:
                # Look for section headers and step patterns
                if any(pattern in content for pattern in ['###', '##', 'STEP', 'Step', 'step']):
                    # Extract sections/steps
                    lines = content.split('\n')
                    current_section = ""
                    for line in lines:
                        if line.strip().startswith('#') or 'step' in line.lower():
                            if current_section and len(current_section) > 20:
                                summary["diagnostic_steps"].append({
                                    "step": len(summary["diagnostic_steps"]) + 1,
                                    "action": current_section.strip(),
                                    "timestamp": timestamp
                                })
                            current_section = line.strip()
                        elif current_section and line.strip():
                            current_section += " " + line.strip()

                    # Add the last section
                    if current_section and len(current_section) > 20:
                        summary["diagnostic_steps"].append({
                            "step": len(summary["diagnostic_steps"]) + 1,
                            "action": current_section.strip(),
                            "timestamp": timestamp
                        })

            # Extract key findings - look for specific patterns
            finding_patterns = [
                'events are present', 'timestamps are set', 'found in', 'discovered that',
                'analysis shows', 'results indicate', 'data shows', 'identified'
            ]

            if role == 'assistant':
                for pattern in finding_patterns:
                    if pattern in content.lower():
                        # Extract the sentence containing the finding
                        sentences = content.split('.')
                        for sentence in sentences:
                            if pattern in sentence.lower() and len(sentence.strip()) > 20:
                                finding = sentence.strip()
                                if finding not in [f["finding"] for f in summary["key_findings"]]:
                                    summary["key_findings"].append({
                                        "finding": finding,
                                        "timestamp": timestamp
                                    })
                                break

            # Enhanced recommendation extraction
            if role == 'assistant' and ('recommendation' in content.lower() or 'suggest' in content.lower() or 'recommend' in content.lower()):
                # Look for recommendation sections and conclusion sections
                lines = content.split('\n')
                in_recommendations = False
                current_recommendation = ""

                for line in lines:
                    line_lower = line.lower()
                    # Start of recommendation section
                    if any(word in line_lower for word in ['recommendation', 'suggest', 'recommend', 'conclusion', 'next steps']):
                        in_recommendations = True
                        if current_recommendation:
                            summary["recommendations"].append({
                                "recommendation": current_recommendation.strip(),
                                "timestamp": timestamp
                            })
                            current_recommendation = ""
                        continue
                    elif in_recommendations:
                        # Look for list items or actionable statements
                        if line.strip().startswith(('1.', '2.', '3.', '4.', '5.', '-', '*', '•')):
                            if current_recommendation:
                                summary["recommendations"].append({
                                    "recommendation": current_recommendation.strip(),
                                    "timestamp": timestamp
                                })
                            current_recommendation = line.strip()
                        elif line.strip() and not line.strip().startswith('#'):
                            current_recommendation += " " + line.strip()
                        elif not line.strip() and current_recommendation:
                            # End of recommendation section
                            if current_recommendation:
                                summary["recommendations"].append({
                                    "recommendation": current_recommendation.strip(),
                                    "timestamp": timestamp
                                })
                            current_recommendation = ""
                            in_recommendations = False

                # Add the last recommendation
                if current_recommendation:
                    summary["recommendations"].append({
                        "recommendation": current_recommendation.strip(),
                        "timestamp": timestamp
                    })

        # Create timeline summary
        all_activities = []

        # Add routing decision
        if summary["routing_decision"]["decision_made"]:
            all_activities.append({
                "step": "Triage & Routing",
                "description": f"Analyzed problem and routed to {summary['routing_decision']['target_specialist']}",
                "timestamp": 0
            })

        # Add tool executions
        for tool in summary["tools_executed"]:
            all_activities.append({
                "step": f"Tool Execution",
                "description": tool["description"],
                "timestamp": tool["timestamp"]
            })

        # Add diagnostic steps
        for step in summary["diagnostic_steps"]:
            all_activities.append({
                "step": f"Diagnostic Step {step['step']}",
                "description": step["action"][:100] + "..." if len(step["action"]) > 100 else step["action"],
                "timestamp": step["timestamp"]
            })

        # Sort by timestamp and create timeline
        all_activities.sort(key=lambda x: x["timestamp"])
        summary["timeline"] = all_activities

        # Add summary statistics
        summary["execution_summary"] = {
            "tools_used": len(summary["tools_executed"]),
            "diagnostic_steps_performed": len(summary["diagnostic_steps"]),
            "key_findings_identified": len(summary["key_findings"]),
            "recommendations_provided": len(summary["recommendations"]),
            "routing_successful": summary["routing_decision"]["decision_made"]
        }

        logger.info(f"Step summary extracted: {summary['execution_summary']}")
        logger.debug(f"Tools found: {[t['tool'] for t in summary['tools_executed']]}")
        logger.debug(f"Findings: {len(summary['key_findings'])}")
        logger.debug(f"Recommendations: {len(summary['recommendations'])}")

        return summary

    def _get_tool_description(self, tool_name: str) -> str:
        """Get a user-friendly description for a tool name."""
        tool_descriptions = {
            'get_current_user_info': 'Retrieved current user information and permissions',
            'list_splunk_indexes': 'Listed available Splunk indexes',
            'get_splunk_health': 'Checked Splunk server health status',
            'run_splunk_search': 'Executed Splunk search query',
            'list_sources': 'Listed available data sources',
            'list_sourcetypes': 'Listed available sourcetypes',
            'list_triggered_alerts': 'Checked triggered alerts'
        }
        return tool_descriptions.get(tool_name, f'Executed {tool_name}')