"""
Dynamic Troubleshooting Agent for Direct Splunk Analysis.

This module provides a direct interface to the dynamic coordinator system,
bypassing the triage layer for more efficient troubleshooting workflows.
It includes comprehensive tracing, orchestration, and results analysis.
"""

import logging
import os
import time
from typing import Any
from datetime import datetime

from fastmcp import Context
from openai import OpenAI

from src.core.base import BaseTool, ToolMetadata
from .shared import AgentConfig, SplunkDiagnosticContext, SplunkToolRegistry

logger = logging.getLogger(__name__)

# Only import OpenAI agents if available
try:
    from agents import Agent, Runner, function_tool
    from agents.extensions.handoff_prompt import prompt_with_handoff_instructions
    # Import tracing capabilities
    from agents import trace, custom_span

    OPENAI_AGENTS_AVAILABLE = True
    logger.info("OpenAI agents SDK loaded successfully for orchestration")
except ImportError:
    OPENAI_AGENTS_AVAILABLE = False
    Agent = None
    Runner = None
    function_tool = None
    prompt_with_handoff_instructions = None
    trace = None
    custom_span = None
    logger.warning("OpenAI agents SDK not available. Install with: pip install openai-agents")

# Import OpenAI exceptions for retry logic
try:
    from openai import APIConnectionError, APIError, APITimeoutError, RateLimitError

    OPENAI_EXCEPTIONS_AVAILABLE = True
except ImportError:
    OPENAI_EXCEPTIONS_AVAILABLE = False
    RateLimitError = Exception
    APIError = Exception
    APIConnectionError = Exception
    APITimeoutError = Exception


class RetryConfig:
    """Configuration for retry logic with exponential backoff."""

    def __init__(
        self,
        max_retries: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        exponential_base: float = 2.0,
        jitter: bool = True,
    ):
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
        self.jitter = jitter


class DynamicTroubleshootAgentTool(BaseTool):
    """
    Enhanced Dynamic Troubleshooting Agent with Handoff-Based Orchestration and Comprehensive Tracing.

    This tool provides a sophisticated handoff-based orchestration system for efficient
    Splunk troubleshooting using specialized micro-agents. It leverages the OpenAI Agents SDK
    handoff pattern for intelligent routing and comprehensive tracing throughout the entire
    diagnostic process.

    ## Key Features:
    - **Handoff-Based Orchestration**: Uses OpenAI Agents SDK handoff pattern for intelligent agent coordination
    - **Specialized Micro-Agents**: Individual agents for specific diagnostic tasks (license, permissions, performance, etc.)
    - **Comprehensive Tracing**: Full observability of agent execution flows and handoffs
    - **Intelligent Routing**: Automatically selects and coordinates appropriate specialists based on problem symptoms
    - **Context Preservation**: Maintains diagnostic context across all agent handoffs
    - **Progress Reporting**: Real-time updates throughout the orchestration process
    - **Detailed Analysis**: Deep synthesis of findings from all engaged specialists

    ## Handoff-Based Architecture:

    ### 🎯 Orchestrating Agent
    Central coordinator that analyzes problems and hands off to appropriate specialists:
    - Analyzes problem descriptions and symptoms
    - Determines which specialists to engage based on issue type
    - Coordinates handoffs to specialized micro-agents
    - Synthesizes results from all engaged agents
    - Provides comprehensive analysis and recommendations

    ### 🔍 Missing Data Specialists
    Specialized agents for comprehensive missing data troubleshooting:
    - **License Verification Agent**: Splunk license and edition verification
    - **Index Verification Agent**: Index accessibility and configuration verification
    - **Permissions Agent**: User permissions and role-based access control analysis
    - **Time Range Agent**: Time-related data availability and timestamp issues
    - **Forwarder Connectivity Agent**: Forwarder connections and data ingestion pipeline
    - **Search Head Configuration Agent**: Search head setup and distributed search verification

    ### 🚀 Performance Analysis Specialists  
    Specialized agents for system performance diagnosis:
    - **System Resource Agent**: CPU, memory, and disk usage analysis
    - **Search Concurrency Agent**: Search performance and concurrency analysis
    - **Indexing Performance Agent**: Indexing pipeline and throughput analysis

    ### 🏥 Health Check Specialists
    Specialized agents for quick system health assessment:
    - **Connectivity Agent**: Basic Splunk server connectivity verification
    - **Data Availability Agent**: Recent data ingestion and availability checks

    ## Tracing and Observability:

    The tool provides comprehensive tracing through:
    - **OpenAI Agents SDK Tracing**: Native trace integration with the agents framework
    - **Handoff Tracking**: Visibility into which agents are engaged and when
    - **Context Flow**: Tracking of diagnostic context across agent handoffs
    - **Performance Metrics**: Execution times and agent engagement statistics
    - **Turn Analysis**: Detailed view of conversation turns and agent interactions

    ## Arguments:

    - **problem_description** (str, required): Detailed description of the Splunk issue or symptoms. Be specific about error messages, expected vs actual behavior, and affected components.

    - **earliest_time** (str, optional): Start time for diagnostic searches in Splunk time format. Examples: "-24h", "-7d@d", "2023-01-01T00:00:00". Default: "-24h"

    - **latest_time** (str, optional): End time for diagnostic searches in Splunk time format. Examples: "now", "-1h", "@d", "2023-01-01T23:59:59". Default: "now"

    - **focus_index** (str, optional): Specific Splunk index to focus the analysis on. Useful when the problem is isolated to a particular data source.

    - **focus_host** (str, optional): Specific host or server to focus the analysis on. Helpful for distributed environment troubleshooting.

    - **complexity_level** (str, optional): Analysis depth level. Options: "basic", "moderate", "advanced". Affects the comprehensiveness of diagnostic checks. Default: "moderate"

    - **workflow_type** (str, optional): Force a specific workflow type. Options: "missing_data", "performance", "health_check", "auto". Default: "auto" (automatic detection)

    ## How Handoff Orchestration Works:
    1. **Problem Analysis**: Orchestrating agent analyzes the problem description to determine issue type
    2. **Specialist Selection**: Automatically selects appropriate specialist agents based on symptoms
    3. **Intelligent Handoffs**: Uses OpenAI Agents SDK handoff pattern to engage specialists
    4. **Context Preservation**: Maintains diagnostic context across all agent interactions
    5. **Result Synthesis**: Orchestrating agent synthesizes findings from all engaged specialists
    6. **Comprehensive Analysis**: Returns detailed analysis with actionable recommendations and tracing metadata

    ## Example Use Cases:
    - "My dashboard shows no data for the last 2 hours" → Engages missing data specialists
    - "Searches are running very slowly since yesterday" → Engages performance analysis specialists
    - "I can't see events from my forwarders in index=security" → Engages missing data specialists
    - "Getting license violation warnings but don't know why" → Engages license and performance specialists
    - "High CPU usage on search heads affecting performance" → Engages performance analysis specialists

    ## Tracing Benefits:
    - **End-to-End Visibility**: Complete view of the diagnostic process from problem to resolution
    - **Agent Interaction Tracking**: See which specialists were engaged and their contributions
    - **Performance Analysis**: Understand execution times and bottlenecks in the diagnostic process
    - **Context Validation**: Verify that appropriate context is being passed to specialists
    - **Debugging Support**: Detailed traces for troubleshooting the troubleshooting process itself
    """

    METADATA = ToolMetadata(
        name="dynamic_troubleshoot",
        description="""Enhanced dynamic troubleshooting agent with handoff-based orchestration and comprehensive tracing for efficient Splunk analysis.
This tool uses the OpenAI Agents SDK handoff pattern to coordinate specialized micro-agents for intelligent diagnostic routing. It provides end-to-end tracing of agent interactions and maintains context across all handoffs.

## Handoff-Based Architecture:
- **Orchestrating Agent**: Central coordinator that analyzes problems and hands off to specialists
- **Specialized Micro-Agents**: Individual agents for license, permissions, performance, connectivity, and health checks
- **Intelligent Routing**: Automatic selection of appropriate specialists based on problem symptoms
- **Context Preservation**: Diagnostic context maintained across all agent handoffs

## Workflow Types:
- **Missing Data Analysis**: Comprehensive handoff-based troubleshooting for data visibility issues
- **Performance Analysis**: System performance diagnosis using specialized performance agents
- **Health Check Analysis**: Quick system health assessment with connectivity and data availability agents
- **Auto-Detection**: Automatically selects the best specialists based on problem symptoms

## Key Benefits:
- Handoff-based orchestration for intelligent specialist coordination
- Comprehensive tracing with OpenAI Agents SDK integration
- Context preservation across agent interactions
- Real-time progress reporting throughout orchestration
- Deep synthesis of findings from all engaged specialists
- End-to-end visibility of diagnostic process

## Parameters:
- problem_description (required): Detailed issue description
- earliest_time (optional): Start time for analysis (default: "-24h")
- latest_time (optional): End time for analysis (default: "now")
- focus_index (optional): Specific index to focus on
- focus_host (optional): Specific host to focus on
- complexity_level (optional): "basic", "moderate", "advanced" (default: "moderate")
- workflow_type (optional): "missing_data", "performance", "health_check", "auto" (default: "auto")
""",
        category="troubleshooting",
    )

    def __init__(self, name: str, category: str):
        super().__init__(name, self.METADATA.description)
        self.category = category

        logger.info(f"Initializing Enhanced DynamicTroubleshootAgentTool: {name}")

        if not OPENAI_AGENTS_AVAILABLE:
            logger.error("OpenAI agents SDK is required for orchestration and tracing")
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

        # Configure retry settings from environment variables
        self.retry_config = RetryConfig(
            max_retries=int(os.getenv("OPENAI_MAX_RETRIES", "3")),
            base_delay=float(os.getenv("OPENAI_RETRY_BASE_DELAY", "1.0")),
            max_delay=float(os.getenv("OPENAI_RETRY_MAX_DELAY", "60.0")),
            exponential_base=float(os.getenv("OPENAI_RETRY_EXPONENTIAL_BASE", "2.0")),
            jitter=os.getenv("OPENAI_RETRY_JITTER", "true").lower() == "true",
        )

        # Initialize the dynamic coordinator system
        logger.info("Setting up dynamic coordinator system...")
        self._setup_dynamic_coordinator()

        # Initialize the orchestrating agent system
        logger.info("Setting up orchestrating agent system...")
        self._setup_orchestrating_agent()

        logger.info("Enhanced DynamicTroubleshootAgentTool initialization complete")

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

    def _setup_dynamic_coordinator(self):
        """Set up the tool registry for handoff-based micro-agents."""

        logger.info("Setting up tool registry for handoff-based micro-agents...")

        # Create tool registry for micro-agents
        self.tool_registry = SplunkToolRegistry()

        # Initialize Splunk tools for the registry
        logger.info("Setting up Splunk tools for handoff-based agents...")
        from .shared.tools import create_splunk_tools

        tools = create_splunk_tools(self.tool_registry)
        logger.info(f"Initialized {len(tools)} Splunk tools for handoff-based agents")

        logger.info("Tool registry setup complete for handoff-based orchestration")

    def _setup_orchestrating_agent(self):
        """Set up the orchestrating agent with handoffs to specialized micro-agents."""

        logger.info("Setting up orchestrating agent with handoffs...")

        # Create specialized micro-agents for different diagnostic tasks
        self._create_micro_agents()

        # Create the main orchestrating agent with handoffs
        from agents.extensions.handoff_prompt import prompt_with_handoff_instructions

        self.orchestrating_agent = Agent(
            name="Splunk Troubleshooting Orchestrator",
            instructions=prompt_with_handoff_instructions("""
You are a senior Splunk troubleshooting orchestrator responsible for coordinating specialized micro-agents to diagnose and resolve Splunk issues.

Your role is to:
1. **Analyze the Problem**: Understand the user's problem description and determine which specialized agents to engage
2. **Coordinate Handoffs**: Hand off specific diagnostic tasks to the appropriate micro-agents
3. **Synthesize Results**: Combine findings from multiple agents into coherent insights
4. **Provide Recommendations**: Generate actionable recommendations based on all agent findings

## Available Specialized Agents:

### Missing Data Analysis Agents:
- **License Verification Agent**: Checks Splunk license status and edition limitations
- **Index Verification Agent**: Verifies target indexes exist and are accessible  
- **Permissions Agent**: Analyzes user permissions and role-based access control
- **Time Range Agent**: Checks data availability in specified time ranges
- **Forwarder Connectivity Agent**: Analyzes forwarder connections and data flow
- **Search Head Configuration Agent**: Verifies search head setup in distributed environments

### Performance Analysis Agents:
- **System Resource Agent**: Analyzes CPU, memory, and disk usage patterns
- **Search Concurrency Agent**: Analyzes search performance and concurrency limits
- **Indexing Performance Agent**: Analyzes indexing pipeline performance

### Health Check Agents:
- **Connectivity Agent**: Verifies basic Splunk server connectivity
- **Data Availability Agent**: Checks for recent data ingestion

## Handoff Strategy:

Based on the problem description, determine which agents to engage:

**For Missing Data Issues**: Hand off to license verification, index verification, permissions, time range, and forwarder connectivity agents
**For Performance Issues**: Hand off to system resource, search concurrency, and indexing performance agents  
**For General Health Checks**: Hand off to connectivity and data availability agents

## Instructions:
1. Analyze the problem description to understand the issue type
2. Hand off to the appropriate specialized agents based on the problem symptoms
3. Wait for results from each agent
4. Synthesize the findings into a comprehensive analysis
5. Provide prioritized recommendations for resolution

Always start by understanding the problem scope, then systematically engage the relevant agents to gather comprehensive diagnostic data.
            """),
            model=self.config.model,
            handoffs=self.micro_agents,
        )

        logger.info(f"Orchestrating agent setup complete with {len(self.micro_agents)} specialized agents")

    def _create_micro_agents(self):
        """Create specialized micro-agents for different diagnostic tasks."""
        
        logger.info("Creating specialized micro-agents...")
        
        self.micro_agents = []
        
        # Missing Data Analysis Agents
        self.micro_agents.extend(self._create_missing_data_agents())
        
        # Performance Analysis Agents  
        self.micro_agents.extend(self._create_performance_agents())
        
        # Health Check Agents
        self.micro_agents.extend(self._create_health_check_agents())
        
        logger.info(f"Created {len(self.micro_agents)} specialized micro-agents")

    def _create_missing_data_agents(self):
        """Create specialized agents for missing data analysis."""
        
        from agents.extensions.handoff_prompt import prompt_with_handoff_instructions
        
        agents = []
        
        # License Verification Agent
        license_agent = Agent(
            name="License Verification Agent",
            handoff_description="Specialist for Splunk license and edition verification",
            instructions=prompt_with_handoff_instructions("""
You are a specialized Splunk license verification agent.

**Your Expertise**: Splunk licensing, edition limitations, and license-related data access issues

**Your Tasks**:
1. Check Splunk license state and edition type
2. Verify license compliance and violations
3. Identify license-related restrictions on data access
4. Analyze license pool usage and quotas

**Available Tools**: You have access to Splunk search capabilities to query license information.

**Key Searches**:
- `| rest /services/server/info | fields splunk_version, product_type, license_state`
- `| rest /services/licenser/messages | table category, message`
- `index=_internal source=*license_usage.log* type=Usage`

**Analysis Focus**:
- Check if running Splunk Free (has search limitations)
- Verify license state (OK, expired, violation)
- Identify license violations that prevent searching
- Note version and product type compatibility

**Return Format**: Provide structured findings with:
- License status and edition
- Any violations or restrictions found
- Impact on data access capabilities
- Specific recommendations for license-related issues
            """),
            model=self.config.model,
            tools=self._create_splunk_tools_for_agent(),
        )
        agents.append(license_agent)
        
        # Index Verification Agent
        index_agent = Agent(
            name="Index Verification Agent", 
            handoff_description="Specialist for index accessibility and configuration verification",
            instructions=prompt_with_handoff_instructions("""
You are a specialized Splunk index verification agent.

**Your Expertise**: Index configuration, accessibility, and data visibility issues

**Your Tasks**:
1. Verify target indexes exist and are accessible
2. Test index permissions and access rights
3. Check index configuration and settings
4. Analyze index-specific data flow issues

**Available Tools**: You have access to Splunk search and index listing capabilities.

**Key Searches**:
- List available indexes using list_splunk_indexes tool
- Test index accessibility with metadata searches
- Check index-specific data counts and recent activity

**Analysis Focus**:
- Verify target indexes exist in the system
- Test user access to specified indexes
- Check for index-level permissions issues
- Identify missing or inaccessible indexes

**Return Format**: Provide structured findings with:
- Index availability status
- Access verification results
- Any missing or inaccessible indexes
- Specific recommendations for index-related issues
            """),
            model=self.config.model,
            tools=self._create_splunk_tools_for_agent(),
        )
        agents.append(index_agent)
        
        # Permissions Agent
        permissions_agent = Agent(
            name="Permissions Agent",
            handoff_description="Specialist for user permissions and role-based access control analysis", 
            instructions=prompt_with_handoff_instructions("""
You are a specialized Splunk permissions and access control agent.

**Your Expertise**: User roles, permissions, and role-based access control (RBAC)

**Your Tasks**:
1. Verify user permissions and assigned roles
2. Check role-based index access restrictions
3. Analyze search filters and capabilities based on roles
4. Identify permission-related data access issues

**Available Tools**: You have access to user information and Splunk search capabilities.

**Key Searches**:
- Get current user info and roles
- Test basic search permissions
- Check role-based index access restrictions
- Verify search filters based on role permissions

**Analysis Focus**:
- Current user roles and capabilities
- Index access permissions by role
- Search restrictions and filters
- Permission-related barriers to data access

**Return Format**: Provide structured findings with:
- User role and permission status
- Access restrictions identified
- Role-based limitations affecting data visibility
- Specific recommendations for permission issues
            """),
            model=self.config.model,
            tools=self._create_splunk_tools_for_agent(),
        )
        agents.append(permissions_agent)
        
        # Time Range Agent  
        time_range_agent = Agent(
            name="Time Range Agent",
            handoff_description="Specialist for time-related data availability and timestamp issues",
            instructions=prompt_with_handoff_instructions("""
You are a specialized Splunk time range and timestamp analysis agent.

**Your Expertise**: Time-based data queries, timestamp issues, and temporal data availability

**Your Tasks**:
1. Check data availability in specified time ranges
2. Analyze time distribution and data gaps
3. Identify indexing delays and timestamp issues
4. Verify timezone settings and time-related problems

**Available Tools**: You have access to Splunk search capabilities for time-based analysis.

**Key Searches**:
- Count queries for specified time ranges
- Time distribution analysis using timechart
- Index time vs event time comparison
- "All time" searches to catch timing issues

**Analysis Focus**:
- Data availability in target time range
- Identification of data gaps or missing periods
- Indexing delays (_indextime vs _time)
- Timezone and future-timestamped event issues

**Return Format**: Provide structured findings with:
- Data availability status for time range
- Time-related issues identified
- Indexing delay analysis
- Specific recommendations for time-related problems
            """),
            model=self.config.model,
            tools=self._create_splunk_tools_for_agent(),
        )
        agents.append(time_range_agent)
        
        # Forwarder Connectivity Agent
        forwarder_agent = Agent(
            name="Forwarder Connectivity Agent",
            handoff_description="Specialist for forwarder connections and data ingestion pipeline analysis",
            instructions=prompt_with_handoff_instructions("""
You are a specialized Splunk forwarder connectivity and data flow agent.

**Your Expertise**: Universal forwarders, data ingestion pipeline, and network connectivity

**Your Tasks**:
1. Verify forwarder connections and status
2. Check data flow from forwarders to indexers
3. Analyze connection stability and throughput
4. Identify network or connectivity issues

**Available Tools**: You have access to Splunk search capabilities for forwarder analysis.

**Key Searches**:
- `index=_internal source=*metrics.log* tcpin_connections`
- `index=_internal source=*metrics.log* group=queue tcpout`
- `| metadata type=hosts` for recent host activity
- `index=_internal "Connected to idx" OR "cooked mode"`

**Analysis Focus**:
- Active forwarder connections
- Data throughput and connection stability
- Recent host activity and data flow
- Connection drops or network issues

**Return Format**: Provide structured findings with:
- Forwarder connectivity status
- Data flow analysis results
- Connection stability assessment
- Specific recommendations for connectivity issues
            """),
            model=self.config.model,
            tools=self._create_splunk_tools_for_agent(),
        )
        agents.append(forwarder_agent)
        
        # Search Head Configuration Agent
        search_head_agent = Agent(
            name="Search Head Configuration Agent",
            handoff_description="Specialist for search head configuration and distributed search setup",
            instructions=prompt_with_handoff_instructions("""
You are a specialized Splunk search head configuration agent.

**Your Expertise**: Search head clusters, distributed search, and search head connectivity

**Your Tasks**:
1. Verify search head configuration in distributed environments
2. Check search head cluster status and health
3. Analyze distributed search peer connections
4. Identify search head connectivity issues

**Available Tools**: You have access to Splunk search capabilities for search head analysis.

**Key Searches**:
- `| rest /services/search/distributed/peers`
- `| rest /services/shcluster/status`
- `index=_internal source=*splunkd.log* component=DistributedSearch`

**Analysis Focus**:
- Search head to indexer connectivity
- Distributed search configuration
- Search head cluster health
- Peer connection status and issues

**Return Format**: Provide structured findings with:
- Search head configuration status
- Distributed search connectivity results
- Cluster health assessment
- Specific recommendations for search head issues
            """),
            model=self.config.model,
            tools=self._create_splunk_tools_for_agent(),
        )
        agents.append(search_head_agent)
        
        return agents

    def _create_performance_agents(self):
        """Create specialized agents for performance analysis."""
        
        from agents.extensions.handoff_prompt import prompt_with_handoff_instructions
        
        agents = []
        
        # System Resource Agent
        system_resource_agent = Agent(
            name="System Resource Agent",
            handoff_description="Specialist for system resource analysis and performance monitoring",
            instructions=prompt_with_handoff_instructions("""
You are a specialized Splunk system resource analysis agent.

**Your Expertise**: System performance, resource utilization, and hardware bottlenecks

**Your Tasks**:
1. Analyze system CPU, memory, and disk usage patterns
2. Identify resource bottlenecks and constraints
3. Check host-level performance metrics
4. Analyze resource usage trends and spikes

**Available Tools**: You have access to Splunk search capabilities for introspection data analysis.

**Key Searches**:
- `index=_introspection component=Hostwide`
- `index=_introspection component=PerProcess`
- System resource metrics and performance data

**Analysis Focus**:
- CPU usage patterns (system and user)
- Memory utilization and availability
- Disk I/O performance and capacity
- Hosts with high resource usage (>80%)

**Return Format**: Provide structured findings with:
- Resource usage baseline and current status
- Identified bottlenecks and constraints
- Performance trends and anomalies
- Specific recommendations for resource optimization
            """),
            model=self.config.model,
            tools=self._create_splunk_tools_for_agent(),
        )
        agents.append(system_resource_agent)
        
        # Search Concurrency Agent
        search_concurrency_agent = Agent(
            name="Search Concurrency Agent", 
            handoff_description="Specialist for search performance and concurrency analysis",
            instructions=prompt_with_handoff_instructions("""
You are a specialized Splunk search concurrency and performance agent.

**Your Expertise**: Search performance, concurrency limits, and scheduler optimization

**Your Tasks**:
1. Analyze search concurrency patterns and limits
2. Check search performance and execution times
3. Identify slow or failed searches
4. Analyze scheduler performance and queue status

**Available Tools**: You have access to Splunk search capabilities for search performance analysis.

**Key Searches**:
- `index=_introspection component=SearchConcurrency`
- `index=_internal source=*scheduler.log*`
- `index=_audit action=search`
- Search performance metrics and statistics

**Analysis Focus**:
- Current search concurrency vs configured limits
- Search execution times and performance patterns
- Failed or slow search identification
- Scheduler queue status and delays

**Return Format**: Provide structured findings with:
- Search concurrency status and limits
- Performance bottlenecks identified
- Slow or failed search analysis
- Specific recommendations for search optimization
            """),
            model=self.config.model,
            tools=self._create_splunk_tools_for_agent(),
        )
        agents.append(search_concurrency_agent)
        
        # Indexing Performance Agent
        indexing_performance_agent = Agent(
            name="Indexing Performance Agent",
            handoff_description="Specialist for indexing pipeline performance and throughput analysis", 
            instructions=prompt_with_handoff_instructions("""
You are a specialized Splunk indexing performance agent.

**Your Expertise**: Indexing pipeline, data ingestion throughput, and indexer performance

**Your Tasks**:
1. Analyze indexing throughput and pipeline performance
2. Check queue sizes and processing delays
3. Identify indexing bottlenecks and constraints
4. Monitor per-index performance metrics

**Available Tools**: You have access to Splunk search capabilities for indexing performance analysis.

**Key Searches**:
- `index=_internal source=*metrics.log* group=per_index_thruput`
- `index=_internal source=*metrics.log* group=queue`
- `index=_internal source=*metrics.log* group=pipeline`
- Indexing performance and throughput metrics

**Analysis Focus**:
- Indexing throughput by index and time
- Queue sizes and processing delays
- Pipeline processor performance
- Indexing bottlenecks and constraints

**Return Format**: Provide structured findings with:
- Indexing performance status and throughput
- Queue analysis and bottleneck identification
- Pipeline performance assessment
- Specific recommendations for indexing optimization
            """),
            model=self.config.model,
            tools=self._create_splunk_tools_for_agent(),
        )
        agents.append(indexing_performance_agent)
        
        return agents

    def _create_health_check_agents(self):
        """Create specialized agents for health checks."""
        
        from agents.extensions.handoff_prompt import prompt_with_handoff_instructions
        
        agents = []
        
        # Connectivity Agent
        connectivity_agent = Agent(
            name="Connectivity Agent",
            handoff_description="Specialist for basic Splunk server connectivity and health verification",
            instructions=prompt_with_handoff_instructions("""
You are a specialized Splunk connectivity verification agent.

**Your Expertise**: Server connectivity, basic health checks, and service availability

**Your Tasks**:
1. Verify Splunk server connectivity and responsiveness
2. Check basic service availability and status
3. Validate authentication and API access
4. Identify connection issues or service problems

**Available Tools**: You have access to Splunk health check capabilities.

**Analysis Focus**:
- Server connectivity and response times
- Service availability and status
- Authentication and access verification
- Basic system health indicators

**Return Format**: Provide structured findings with:
- Connectivity status and response times
- Service availability assessment
- Any connection issues identified
- Specific recommendations for connectivity problems
            """),
            model=self.config.model,
            tools=self._create_splunk_tools_for_agent(),
        )
        agents.append(connectivity_agent)
        
        # Data Availability Agent
        data_availability_agent = Agent(
            name="Data Availability Agent",
            handoff_description="Specialist for basic data ingestion and availability verification",
            instructions=prompt_with_handoff_instructions("""
You are a specialized Splunk data availability verification agent.

**Your Expertise**: Data ingestion verification, basic data availability, and recent data checks

**Your Tasks**:
1. Verify recent data ingestion across indexes
2. Check basic data availability and counts
3. Identify data ingestion issues or gaps
4. Validate data flow and recent activity

**Available Tools**: You have access to Splunk search and index listing capabilities.

**Key Searches**:
- Recent data counts across indexes
- Data availability verification
- Index activity and recent ingestion
- Basic data flow validation

**Analysis Focus**:
- Recent data ingestion status
- Data availability across indexes
- Data flow verification
- Basic ingestion health indicators

**Return Format**: Provide structured findings with:
- Data availability status
- Recent ingestion verification results
- Any data flow issues identified
- Specific recommendations for data availability problems
            """),
            model=self.config.model,
            tools=self._create_splunk_tools_for_agent(),
        )
        agents.append(data_availability_agent)
        
        return agents

    def _create_splunk_tools_for_agent(self):
        """Create Splunk tools for micro-agents using the tool registry."""
        
        if not OPENAI_AGENTS_AVAILABLE:
            return []
            
        tools = []
        
        # Create function tools that delegate to the tool registry
        @function_tool
        async def run_splunk_search(query: str, earliest_time: str = "-24h", latest_time: str = "now") -> str:
            """Execute a Splunk search query."""
            try:
                result = await self.tool_registry.call_tool(
                    "run_splunk_search",
                    {"query": query, "earliest_time": earliest_time, "latest_time": latest_time}
                )
                if result.get("success"):
                    return str(result.get("data", ""))
                else:
                    return f"Search failed: {result.get('error', 'Unknown error')}"
            except Exception as e:
                return f"Search execution failed: {str(e)}"
        
        @function_tool  
        async def run_oneshot_search(query: str, earliest_time: str = "-15m", latest_time: str = "now", max_results: int = 100) -> str:
            """Execute a quick Splunk oneshot search."""
            try:
                result = await self.tool_registry.call_tool(
                    "run_oneshot_search",
                    {
                        "query": query,
                        "earliest_time": earliest_time, 
                        "latest_time": latest_time,
                        "max_results": max_results,
                    }
                )
                if result.get("success"):
                    return str(result.get("data", ""))
                else:
                    return f"Oneshot search failed: {result.get('error', 'Unknown error')}"
            except Exception as e:
                return f"Oneshot search execution failed: {str(e)}"
        
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
        
        tools = [run_splunk_search, run_oneshot_search, list_splunk_indexes, get_current_user_info, get_splunk_health]
        
        return tools

    def _analyze_problem_type(self, problem_description: str) -> str:
        """
        Analyze the problem description to determine the most appropriate workflow type.

        Args:
            problem_description: The user's problem description

        Returns:
            str: The recommended workflow type ("missing_data", "performance", or "health_check")
        """
        problem_lower = problem_description.lower()

        # Missing data indicators
        missing_data_keywords = [
            "can't find",
            "no data",
            "missing",
            "empty results",
            "no results",
            "not showing",
            "not appearing",
            "dashboard empty",
            "no events",
            "expected data",
            "should be there",
            "permission",
            "access",
            "search returns nothing",
            "zero results",
            "data not visible",
        ]

        # Performance indicators
        performance_keywords = [
            "slow",
            "performance",
            "high cpu",
            "high memory",
            "timeout",
            "taking long",
            "resource",
            "capacity",
            "queue",
            "delay",
            "indexing slow",
            "search slow",
            "system slow",
            "bottleneck",
            "high usage",
            "overloaded",
            "lag",
            "latency",
        ]

        # Health check indicators (simple/quick checks)
        health_keywords = [
            "health check",
            "status",
            "connectivity",
            "basic check",
            "quick check",
            "overall status",
            "system status",
        ]

        # Count keyword matches
        missing_data_score = sum(1 for keyword in missing_data_keywords if keyword in problem_lower)
        performance_score = sum(1 for keyword in performance_keywords if keyword in problem_lower)
        health_score = sum(1 for keyword in health_keywords if keyword in problem_lower)

        logger.debug(
            f"Problem analysis scores - Missing Data: {missing_data_score}, Performance: {performance_score}, Health: {health_score}"
        )

        # Determine the best workflow
        if health_score > 0 and "health check" in problem_lower:
            return "health_check"
        elif missing_data_score > performance_score:
            return "missing_data"
        elif performance_score > 0:
            return "performance"
        else:
            # Default to missing data for ambiguous cases
            return "missing_data"

    def _create_orchestration_input(
        self,
        problem_description: str,
        workflow_result: dict[str, Any],
        diagnostic_context: SplunkDiagnosticContext,
    ) -> str:
        """Create enhanced input for the orchestrating agent."""

        # Extract key information from workflow result
        workflow_type = workflow_result.get("coordinator_type", "unknown")
        task_results = workflow_result.get("task_results", [])
        summary = workflow_result.get("summary", {})
        performance_metrics = workflow_result.get("performance_metrics", {})

        # Format task results for analysis
        task_analysis = []
        for task in task_results:
            task_info = f"""
**Task: {task.get("task", "Unknown")}**
- Status: {task.get("status", "unknown")}
- Execution Time: {task.get("execution_time", 0):.2f}s
- Findings: {len(task.get("findings", []))} items
- Recommendations: {len(task.get("recommendations", []))} items

Key Findings:
{chr(10).join([f"  • {finding}" for finding in task.get("findings", [])[:3]])}

Recommendations:
{chr(10).join([f"  • {rec}" for rec in task.get("recommendations", [])[:3]])}
"""
            task_analysis.append(task_info)

        orchestration_input = f"""
**SPLUNK TROUBLESHOOTING ANALYSIS REQUEST**

**Original Problem:**
{problem_description}

**Analysis Context:**
- Workflow Type: {workflow_type}
- Time Range: {diagnostic_context.earliest_time} to {diagnostic_context.latest_time}
- Focus Index: {diagnostic_context.focus_index or "All indexes"}
- Focus Host: {diagnostic_context.focus_host or "All hosts"}
- Complexity Level: {diagnostic_context.complexity_level}

**Workflow Execution Summary:**
- Overall Status: {workflow_result.get("status", "unknown")}
- Execution Time: {performance_metrics.get("total_execution_time", 0):.2f}s
- Tasks Completed: {performance_metrics.get("tasks_completed", 0)}
- Successful Tasks: {performance_metrics.get("successful_tasks", 0)}
- Failed Tasks: {performance_metrics.get("failed_tasks", 0)}
- Parallel Phases: {performance_metrics.get("parallel_phases", 0)}

**Task Results Analysis:**
{chr(10).join(task_analysis)}

**Workflow Summary:**
{summary}

**ORCHESTRATION INSTRUCTIONS:**
Please analyze these results comprehensively and provide:

1. **Executive Summary**: High-level assessment of the situation
2. **Critical Issues**: Immediate problems requiring attention
3. **Detailed Analysis**: Deep dive into findings and their implications
4. **Prioritized Recommendations**: Specific, actionable steps organized by priority
5. **Monitoring Guidance**: What to watch for going forward

Focus on providing actionable insights that address the original problem while considering the broader system health implications.
"""

        return orchestration_input

    def _inspect_agent_context(
        self,
        orchestration_input: str,
        diagnostic_context: SplunkDiagnosticContext,
        problem_description: str,
    ) -> dict[str, Any]:
        """Inspect and return detailed information about context being sent to agents."""
        
        context_inspection = {
            "orchestration_input": {
                "total_length": len(orchestration_input),
                "sections": {
                    "problem_description_length": len(problem_description),
                    "diagnostic_context_info": {
                        "earliest_time": diagnostic_context.earliest_time,
                        "latest_time": diagnostic_context.latest_time,
                        "focus_index": diagnostic_context.focus_index,
                        "focus_host": diagnostic_context.focus_host,
                        "complexity_level": diagnostic_context.complexity_level,
                        "indexes_count": len(diagnostic_context.indexes) if diagnostic_context.indexes else 0,
                        "sourcetypes_count": len(diagnostic_context.sourcetypes) if diagnostic_context.sourcetypes else 0,
                        "sources_count": len(diagnostic_context.sources) if diagnostic_context.sources else 0,
                    },
                    "instructions_length": len(orchestration_input) - len(problem_description),
                }
            },
            "agent_context": {
                "available_specialists": len(self.micro_agents),
                "specialist_names": [agent.name for agent in self.micro_agents],
                "tools_per_agent": len(self._create_splunk_tools_for_agent()),
                "orchestrating_agent_model": self.config.model,
                "orchestrating_agent_temperature": self.config.temperature,
            },
            "tracing_context": {
                "openai_agents_available": OPENAI_AGENTS_AVAILABLE,
                "tracing_available": OPENAI_AGENTS_AVAILABLE and trace is not None,
                "custom_span_available": OPENAI_AGENTS_AVAILABLE and custom_span is not None,
            },
            "context_optimization": {
                "problem_description_ratio": len(problem_description) / len(orchestration_input) if orchestration_input else 0,
                "context_efficiency_score": self._calculate_context_efficiency(orchestration_input, diagnostic_context),
                "recommendations": self._get_context_optimization_recommendations(orchestration_input, diagnostic_context),
            }
        }
        
        # Log context inspection for debugging
        logger.info("=" * 80)
        logger.info("AGENT CONTEXT INSPECTION")
        logger.info("=" * 80)
        logger.info(f"Total orchestration input length: {context_inspection['orchestration_input']['total_length']} characters")
        logger.info(f"Problem description length: {context_inspection['orchestration_input']['sections']['problem_description_length']} characters")
        logger.info(f"Available specialists: {context_inspection['agent_context']['available_specialists']}")
        logger.info(f"Tools per agent: {context_inspection['agent_context']['tools_per_agent']}")
        logger.info(f"Context efficiency score: {context_inspection['context_optimization']['context_efficiency_score']:.2f}")
        logger.info("Specialist agents:")
        for name in context_inspection['agent_context']['specialist_names']:
            logger.info(f"  - {name}")
        logger.info("Context optimization recommendations:")
        for rec in context_inspection['context_optimization']['recommendations']:
            logger.info(f"  - {rec}")
        logger.info("=" * 80)
        
        return context_inspection

    def _calculate_context_efficiency(self, orchestration_input: str, diagnostic_context: SplunkDiagnosticContext) -> float:
        """Calculate a context efficiency score (0-1) based on information density."""
        
        if not orchestration_input:
            return 0.0
            
        # Factors that contribute to efficiency
        factors = []
        
        # Problem description should be substantial but not overwhelming (20-40% of total)
        problem_ratio = len(diagnostic_context.earliest_time or "") / len(orchestration_input)
        if 0.2 <= problem_ratio <= 0.4:
            factors.append(1.0)
        else:
            factors.append(max(0.0, 1.0 - abs(problem_ratio - 0.3) * 2))
        
        # Context specificity (having focus areas is good)
        specificity_score = 0.0
        if diagnostic_context.focus_index:
            specificity_score += 0.3
        if diagnostic_context.focus_host:
            specificity_score += 0.3
        if diagnostic_context.indexes:
            specificity_score += 0.2
        if diagnostic_context.sourcetypes:
            specificity_score += 0.2
        factors.append(specificity_score)
        
        # Input length should be reasonable (not too short, not too long)
        length_score = 1.0
        if len(orchestration_input) < 500:
            length_score = len(orchestration_input) / 500
        elif len(orchestration_input) > 5000:
            length_score = max(0.2, 5000 / len(orchestration_input))
        factors.append(length_score)
        
        return sum(factors) / len(factors)

    def _get_context_optimization_recommendations(self, orchestration_input: str, diagnostic_context: SplunkDiagnosticContext) -> list[str]:
        """Get recommendations for optimizing context sent to agents."""
        
        recommendations = []
        
        # Check input length
        if len(orchestration_input) > 5000:
            recommendations.append("Consider reducing orchestration input length for better agent performance")
        elif len(orchestration_input) < 300:
            recommendations.append("Consider adding more context details for better agent understanding")
        
        # Check context specificity
        if not diagnostic_context.focus_index and not diagnostic_context.focus_host:
            recommendations.append("Consider specifying focus_index or focus_host for more targeted analysis")
        
        if not diagnostic_context.indexes:
            recommendations.append("Consider providing specific indexes for more efficient searches")
        
        # Check time range
        if diagnostic_context.earliest_time == "-24h" and diagnostic_context.latest_time == "now":
            recommendations.append("Consider using more specific time ranges if the issue is time-bounded")
        
        # Check complexity level
        if diagnostic_context.complexity_level == "advanced":
            recommendations.append("Advanced complexity may result in longer execution times and more context")
        
        if not recommendations:
            recommendations.append("Context appears well-optimized for agent processing")
        
        return recommendations

    async def execute(
        self,
        ctx: Context,
        problem_description: str,
        earliest_time: str = "-24h",
        latest_time: str = "now",
        focus_index: str | None = None,
        focus_host: str | None = None,
        complexity_level: str = "moderate",
        workflow_type: str = "auto",
    ) -> dict[str, Any]:
        """
        Execute enhanced dynamic troubleshooting analysis with orchestration and tracing.

        This method analyzes the problem, routes it to the appropriate dynamic workflow,
        and then uses an orchestrating agent to analyze and synthesize the results.

        Args:
            ctx: FastMCP context
            problem_description: Description of the issue to troubleshoot
            earliest_time: Start time for analysis
            latest_time: End time for analysis
            focus_index: Specific index to focus on (optional)
            focus_host: Specific host to focus on (optional)
            complexity_level: Analysis complexity level
            workflow_type: Force specific workflow or use auto-detection

        Returns:
            Dict containing the enhanced analysis results with orchestration
        """
        execution_start_time = time.time()
        
        # Create comprehensive trace for the entire troubleshooting workflow
        # Make trace name unique to avoid "Trace already exists" warnings
        trace_timestamp = int(time.time() * 1000)  # milliseconds for uniqueness
        trace_name = f"Splunk Dynamic Troubleshooting {trace_timestamp}"
        
        # Convert all metadata values to strings for OpenAI API compatibility
        trace_metadata = {
            "problem_description": str(problem_description)[:100],
            "time_range": f"{earliest_time} to {latest_time}",
            "focus_index": str(focus_index) if focus_index else "all",
            "focus_host": str(focus_host) if focus_host else "all",
            "complexity_level": str(complexity_level),
            "workflow_type": str(workflow_type),
            "tool_name": "dynamic_troubleshoot_agent",
            "trace_timestamp": str(trace_timestamp),
        }

        if OPENAI_AGENTS_AVAILABLE and trace:
            # Use OpenAI Agents SDK tracing with correct API
            with trace(workflow_name=trace_name, metadata=trace_metadata):
                return await self._execute_with_tracing(
                    ctx, problem_description, earliest_time, latest_time,
                    focus_index, focus_host, complexity_level, workflow_type,
                    execution_start_time
                )
        else:
            # Fallback without tracing
            logger.warning("OpenAI Agents tracing not available, executing without traces")
            return await self._execute_with_tracing(
                ctx, problem_description, earliest_time, latest_time,
                focus_index, focus_host, complexity_level, workflow_type,
                execution_start_time
            )

    async def _execute_with_tracing(
        self,
        ctx: Context,
        problem_description: str,
        earliest_time: str,
        latest_time: str,
        focus_index: str | None,
        focus_host: str | None,
        complexity_level: str,
        workflow_type: str,
        execution_start_time: float,
    ) -> dict[str, Any]:
        """Execute the troubleshooting workflow with comprehensive tracing."""
        
        logger.info("=" * 80)
        logger.info("STARTING ENHANCED DYNAMIC TROUBLESHOOT AGENT EXECUTION")
        logger.info("=" * 80)

        try:
            logger.info(f"Problem: {problem_description[:200]}...")
            logger.info(f"Time range: {earliest_time} to {latest_time}")
            logger.info(f"Focus - Index: {focus_index}, Host: {focus_host}")
            logger.info(f"Complexity level: {complexity_level}")
            logger.info(f"Workflow type: {workflow_type}")

            # Report initial progress
            await ctx.report_progress(progress=0, total=100)
            await ctx.info(
                f"🔍 Starting enhanced dynamic troubleshooting analysis for: {problem_description[:100]}..."
            )

            # Set the context for tool calls
            self.tool_registry.set_context(ctx)
            logger.debug("Context set for tool registry access")

            # Report progress: Setup complete
            await ctx.report_progress(progress=5, total=100)

            # Create diagnostic context with tracing span
            if OPENAI_AGENTS_AVAILABLE and custom_span:
                with custom_span("diagnostic_context_creation"):
                    diagnostic_context = SplunkDiagnosticContext(
                        earliest_time=earliest_time,
                        latest_time=latest_time,
                        focus_index=focus_index,
                        focus_host=focus_host,
                        complexity_level=complexity_level,
                    )
                    logger.info(f"Diagnostic context created: {diagnostic_context}")
            else:
                diagnostic_context = SplunkDiagnosticContext(
                    earliest_time=earliest_time,
                    latest_time=latest_time,
                    focus_index=focus_index,
                    focus_host=focus_host,
                    complexity_level=complexity_level,
                )
                logger.info(f"Diagnostic context created: {diagnostic_context}")

            # Report progress: Context created
            await ctx.report_progress(progress=10, total=100)

            # Determine workflow type with tracing
            if OPENAI_AGENTS_AVAILABLE and custom_span:
                with custom_span("workflow_type_detection"):
                    if workflow_type == "auto":
                        detected_workflow = self._analyze_problem_type(problem_description)
                        logger.info(f"Auto-detected workflow type: {detected_workflow}")
                        await ctx.info(f"🤖 Auto-detected workflow: {detected_workflow}")
                    else:
                        detected_workflow = workflow_type
                        logger.info(f"Using specified workflow type: {detected_workflow}")
                        await ctx.info(f"🎯 Using specified workflow: {detected_workflow}")
            else:
                if workflow_type == "auto":
                    detected_workflow = self._analyze_problem_type(problem_description)
                    logger.info(f"Auto-detected workflow type: {detected_workflow}")
                    await ctx.info(f"🤖 Auto-detected workflow: {detected_workflow}")
                else:
                    detected_workflow = workflow_type
                    logger.info(f"Using specified workflow type: {detected_workflow}")
                    await ctx.info(f"🎯 Using specified workflow: {detected_workflow}")

            # Report progress: Workflow selected
            await ctx.report_progress(progress=15, total=100)

            # Execute the appropriate dynamic workflow with tracing
            logger.info(f"Executing dynamic {detected_workflow} workflow...")
            await ctx.info(
                f"⚡ Executing {detected_workflow} analysis with parallel micro-agents..."
            )

            workflow_start_time = time.time()
            
            if OPENAI_AGENTS_AVAILABLE and custom_span:
                with custom_span(f"workflow_execution_{detected_workflow}"):
                    workflow_result = await self._execute_workflow_with_tracing(
                        detected_workflow, diagnostic_context, problem_description, ctx 
                    )
            else:
                workflow_result = await self._execute_workflow_with_tracing(
                    detected_workflow, diagnostic_context, problem_description, ctx
                )

            workflow_execution_time = time.time() - workflow_start_time
            logger.info(f"Workflow execution completed in {workflow_execution_time:.2f}s")

            # Report progress: Workflow execution complete
            await ctx.report_progress(progress=70, total=100)
            await ctx.info("✅ Workflow execution completed, starting orchestration analysis...")

            # Execute orchestrating agent for result analysis with tracing
            logger.info("Starting orchestrating agent analysis...")
            orchestration_start_time = time.time()

            # Create enhanced input for orchestrating agent
            orchestration_input = self._create_orchestration_input(
                problem_description, workflow_result, diagnostic_context
            )

            logger.debug(
                f"Orchestration input created, length: {len(orchestration_input)} characters"
            )

            # Execute orchestrating agent with tracing
            await ctx.info(
                "🧠 Orchestrating agent analyzing results and generating recommendations..."
            )

            try:
                if OPENAI_AGENTS_AVAILABLE and custom_span:
                    # Use custom_span instead of trace for orchestration
                    with custom_span("orchestration_analysis"):
                        # Use Runner to execute the orchestrating agent
                        orchestration_result = await Runner.run(
                            self.orchestrating_agent,
                            input=orchestration_input,
                            max_turns=5,  # Allow multiple turns for thorough analysis
                        )

                        orchestration_analysis = orchestration_result.final_output
                        logger.info(
                            f"Orchestration analysis completed, output length: {len(orchestration_analysis)} characters"
                        )
                else:
                    # Use Runner to execute the orchestrating agent
                    orchestration_result = await Runner.run(
                        self.orchestrating_agent,
                        input=orchestration_input,
                        max_turns=5,  # Allow multiple turns for thorough analysis
                    )

                    orchestration_analysis = orchestration_result.final_output
                    logger.info(
                        f"Orchestration analysis completed, output length: {len(orchestration_analysis)} characters"
                    )

            except Exception as e:
                logger.error(f"Orchestration analysis failed: {e}", exc_info=True)
                orchestration_analysis = f"Orchestration analysis failed: {str(e)}\n\nFalling back to basic summary from workflow results."

            orchestration_execution_time = time.time() - orchestration_start_time
            logger.info(f"Orchestration analysis completed in {orchestration_execution_time:.2f}s")

            # Report progress: Orchestration complete
            await ctx.report_progress(progress=90, total=100)

            total_execution_time = time.time() - execution_start_time

            # Create enhanced result with orchestration and tracing metadata
            enhanced_result = {
                **workflow_result,
                "tool_type": "enhanced_dynamic_troubleshoot_agent",
                "detected_workflow_type": detected_workflow,
                "requested_workflow_type": workflow_type,
                "problem_description": problem_description,
                "diagnostic_context": {
                    "earliest_time": earliest_time,
                    "latest_time": latest_time,
                    "focus_index": focus_index,
                    "focus_host": focus_host,
                    "complexity_level": complexity_level,
                },
                "orchestration": {
                    "analysis": orchestration_analysis,
                    "execution_time": orchestration_execution_time,
                    "agent_used": "Splunk Analysis Orchestrator",
                    "input_length": len(orchestration_input),
                    "output_length": len(orchestration_analysis),
                },
                "execution_metadata": {
                    "total_execution_time": total_execution_time,
                    "workflow_execution_time": workflow_execution_time,
                    "orchestration_execution_time": orchestration_execution_time,
                    "workflow_detection_used": workflow_type == "auto",
                    "direct_routing": True,
                    "orchestration_enabled": True,
                    "tracing_enabled": OPENAI_AGENTS_AVAILABLE and trace is not None,
                },
                "tracing_info": {
                    "trace_available": OPENAI_AGENTS_AVAILABLE and trace is not None,
                    "workflow_traced": True,
                    "orchestration_traced": True,
                    "trace_name": f"Splunk Dynamic Troubleshooting: {problem_description[:50]}..." if OPENAI_AGENTS_AVAILABLE and trace else None,
                    "trace_metadata": {
                        "problem_description": problem_description[:100],
                        "time_range": f"{earliest_time} to {latest_time}",
                        "focus_index": str(focus_index) if focus_index else None,
                        "focus_host": str(focus_host) if focus_host else None,
                        "complexity_level": complexity_level,
                        "workflow_type": workflow_type,
                        "tool_name": "dynamic_troubleshoot_agent",
                    } if OPENAI_AGENTS_AVAILABLE and trace else None,
                },
            }

            # Report final progress
            await ctx.report_progress(progress=100, total=100)
            await ctx.info(
                "✅ Enhanced dynamic troubleshooting analysis completed with orchestration"
            )

            logger.info("=" * 80)
            logger.info("ENHANCED DYNAMIC TROUBLESHOOT AGENT EXECUTION COMPLETED SUCCESSFULLY")
            logger.info(f"Total execution time: {total_execution_time:.2f}s")
            logger.info(f"Workflow executed: {detected_workflow}")
            logger.info(f"Workflow execution time: {workflow_execution_time:.2f}s")
            logger.info(f"Orchestration execution time: {orchestration_execution_time:.2f}s")
            logger.info(f"Status: {enhanced_result.get('status', 'unknown')}")
            logger.info(f"Orchestration analysis length: {len(orchestration_analysis)} characters")
            logger.info(f"Tracing enabled: {OPENAI_AGENTS_AVAILABLE and trace is not None}")
            logger.info("=" * 80)

            return enhanced_result

        except Exception as e:
            execution_time = time.time() - execution_start_time
            error_msg = f"Enhanced dynamic troubleshoot agent execution failed: {str(e)}"

            logger.error("=" * 80)
            logger.error("ENHANCED DYNAMIC TROUBLESHOOT AGENT EXECUTION FAILED")
            logger.error(f"Error: {error_msg}")
            logger.error(f"Execution time before failure: {execution_time:.2f} seconds")
            logger.error("=" * 80)
            logger.error("Full error details:", exc_info=True)

            await ctx.error(error_msg)
            return {
                "status": "error",
                "tool_type": "enhanced_dynamic_troubleshoot_agent",
                "error": error_msg,
                "error_type": "execution_error",
                "execution_time": execution_time,
                "diagnostic_context": {
                    "earliest_time": earliest_time,
                    "latest_time": latest_time,
                    "focus_index": focus_index,
                    "focus_host": focus_host,
                    "complexity_level": complexity_level,
                },
                "orchestration": {
                    "analysis": "Orchestration failed due to execution error",
                    "execution_time": 0,
                    "agent_used": None,
                    "error": error_msg,
                },
                "tracing_info": {
                    "trace_available": OPENAI_AGENTS_AVAILABLE and trace is not None,
                    "workflow_traced": False,
                    "orchestration_traced": False,
                    "error": error_msg,
                },
            }

    async def _execute_workflow_with_tracing(
        self,
        detected_workflow: str,
        diagnostic_context: SplunkDiagnosticContext,
        problem_description: str,
        ctx: Context,
    ) -> dict[str, Any]:
        """Execute the workflow using handoff-based orchestrating agent with comprehensive tracing."""
        
        logger.info(f"Executing {detected_workflow} workflow using handoff-based orchestration")
        
        # Set the context for tool calls
        self.tool_registry.set_context(ctx)
        
        # Create enhanced input for the orchestrating agent
        orchestration_input = self._create_handoff_orchestration_input(
            problem_description, detected_workflow, diagnostic_context
        )
        
        # Inspect and log context being sent to agents
        context_inspection = self._inspect_agent_context(
            orchestration_input, diagnostic_context, problem_description
        )
        
        # Report progress before agent execution
        await ctx.report_progress(progress=40, total=100)
        await ctx.info(f"🤖 Starting handoff-based orchestration for {detected_workflow}")
        await ctx.info(f"📊 Context: {context_inspection['orchestration_input']['total_length']} chars, {context_inspection['agent_context']['available_specialists']} specialists, efficiency: {context_inspection['context_optimization']['context_efficiency_score']:.2f}")
        
        try:
            # Execute the orchestrating agent with handoffs
            if OPENAI_AGENTS_AVAILABLE and custom_span:
                with custom_span("handoff_orchestration_execution"):
                    orchestration_result = await Runner.run(
                        self.orchestrating_agent,
                        input=orchestration_input,
                        max_turns=20,  # Allow multiple turns for handoffs and coordination
                    )
            else:
                orchestration_result = await Runner.run(
                    self.orchestrating_agent,
                    input=orchestration_input,
                    max_turns=20,  # Allow multiple turns for handoffs and coordination
                )
            
            # Report progress after orchestration
            await ctx.report_progress(progress=80, total=100)
            await ctx.info(f"✅ Handoff-based orchestration completed")
            
            # Extract findings and analysis from the orchestration result
            orchestration_analysis = orchestration_result.final_output
            
            # Create structured result in the expected format
            workflow_result = {
                "status": "success",
                "coordinator_type": f"handoff_based_{detected_workflow}",
                "problem_description": problem_description,
                "workflow_execution": {
                    "workflow_id": f"handoff_{detected_workflow}",
                    "overall_status": "completed",
                    "execution_method": "handoff_orchestration",
                    "turns_executed": len(orchestration_result.turns) if hasattr(orchestration_result, 'turns') else 1,
                    "agents_engaged": len(self.micro_agents),
                },
                "orchestration_analysis": orchestration_analysis,
                "summary": {
                    "approach": "Handoff-based orchestration with specialized micro-agents",
                    "agents_available": len(self.micro_agents),
                    "orchestration_method": "OpenAI Agents SDK with handoffs",
                    "tracing_enabled": OPENAI_AGENTS_AVAILABLE and custom_span is not None,
                },
                "diagnostic_context": {
                    "earliest_time": diagnostic_context.earliest_time,
                    "latest_time": diagnostic_context.latest_time,
                    "focus_index": diagnostic_context.focus_index,
                    "focus_host": diagnostic_context.focus_host,
                    "complexity_level": diagnostic_context.complexity_level,
                },
                "handoff_metadata": {
                    "orchestrating_agent": "Splunk Troubleshooting Orchestrator",
                    "available_specialists": [agent.name for agent in self.micro_agents],
                    "handoff_approach": "Intelligent routing based on problem analysis",
                    "tracing_spans": OPENAI_AGENTS_AVAILABLE and custom_span is not None,
                },
                "context_inspection": context_inspection,
            }
            
            logger.info(f"Handoff-based {detected_workflow} workflow completed successfully")
            return workflow_result
            
        except Exception as e:
            logger.error(f"Handoff-based orchestration failed: {e}", exc_info=True)
            await ctx.error(f"❌ Handoff orchestration failed: {str(e)}")
            
            return {
                "status": "error",
                "coordinator_type": f"handoff_based_{detected_workflow}",
                "error": str(e),
                "error_type": "handoff_orchestration_error",
                "workflow_execution": {
                    "workflow_id": f"handoff_{detected_workflow}",
                    "overall_status": "failed",
                    "execution_method": "handoff_orchestration",
                    "error": str(e),
                },
                "diagnostic_context": {
                    "earliest_time": diagnostic_context.earliest_time,
                    "latest_time": diagnostic_context.latest_time,
                    "focus_index": diagnostic_context.focus_index,
                    "focus_host": diagnostic_context.focus_host,
                    "complexity_level": diagnostic_context.complexity_level,
                },
            }

    def _create_handoff_orchestration_input(
        self,
        problem_description: str,
        workflow_type: str,
        diagnostic_context: SplunkDiagnosticContext,
    ) -> str:
        """Create enhanced input for the handoff-based orchestrating agent."""

        orchestration_input = f"""
**SPLUNK TROUBLESHOOTING ORCHESTRATION REQUEST**

**Problem Description:**
{problem_description}

**Detected Workflow Type:** {workflow_type}

**Diagnostic Context:**
- Time Range: {diagnostic_context.earliest_time} to {diagnostic_context.latest_time}
- Focus Index: {diagnostic_context.focus_index or "All indexes"}
- Focus Host: {diagnostic_context.focus_host or "All hosts"}
- Complexity Level: {diagnostic_context.complexity_level}

**Available Context Information:**
- Indexes: {', '.join(diagnostic_context.indexes) if diagnostic_context.indexes else "Not specified"}
- Sourcetypes: {', '.join(diagnostic_context.sourcetypes) if diagnostic_context.sourcetypes else "Not specified"}
- Sources: {', '.join(diagnostic_context.sources) if diagnostic_context.sources else "Not specified"}

**Orchestration Instructions:**

Based on the problem description and workflow type, you should:

1. **Analyze the Problem**: Understand the specific symptoms and scope of the issue
2. **Determine Agent Strategy**: Based on the workflow type "{workflow_type}", decide which specialized agents to engage
3. **Coordinate Handoffs**: Hand off specific diagnostic tasks to the appropriate micro-agents
4. **Synthesize Results**: Combine findings from all engaged agents into a comprehensive analysis
5. **Provide Recommendations**: Generate prioritized, actionable recommendations

**Handoff Strategy for {workflow_type.title()} Issues:**
"""

        # Add workflow-specific guidance
        if workflow_type == "missing_data":
            orchestration_input += """
For missing data issues, systematically engage these agents:
- **License Verification Agent**: Check for license limitations affecting data access
- **Index Verification Agent**: Verify target indexes exist and are accessible
- **Permissions Agent**: Analyze user permissions and role-based access control
- **Time Range Agent**: Check data availability in specified time ranges
- **Forwarder Connectivity Agent**: Analyze data flow from forwarders
- **Search Head Configuration Agent**: Verify distributed search setup

Start with license and permissions, then move to index and time range analysis, followed by connectivity checks.
"""
        elif workflow_type == "performance":
            orchestration_input += """
For performance issues, systematically engage these agents:
- **System Resource Agent**: Analyze CPU, memory, and disk usage patterns
- **Search Concurrency Agent**: Check search performance and concurrency limits
- **Indexing Performance Agent**: Analyze indexing pipeline and throughput

Start with system resources to establish baseline, then analyze search and indexing performance.
"""
        elif workflow_type == "health_check":
            orchestration_input += """
For health check requests, engage these agents:
- **Connectivity Agent**: Verify basic Splunk server connectivity and health
- **Data Availability Agent**: Check recent data ingestion and availability

Start with connectivity verification, then check data availability.
"""

        orchestration_input += """

**Expected Output:**
After engaging the appropriate agents and receiving their findings, provide:

1. **Executive Summary**: High-level assessment of the situation
2. **Detailed Findings**: Comprehensive analysis from all engaged agents
3. **Root Cause Analysis**: Identification of underlying issues
4. **Prioritized Recommendations**: Specific, actionable steps organized by priority
5. **Next Steps**: Follow-up actions and monitoring guidance

**Important**: Ensure you engage the relevant specialists and wait for their complete analysis before providing your final synthesis and recommendations.
"""

        return orchestration_input
