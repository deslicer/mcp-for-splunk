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

from fastmcp import Context
from openai import OpenAI

from ...core.base import BaseTool, ToolMetadata
from .dynamic_coordinator import DynamicCoordinator
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
    Enhanced Dynamic Troubleshooting Agent for Splunk Analysis with Orchestration and Tracing.

    This tool provides direct access to the dynamic coordinator system for efficient
    Splunk troubleshooting using micro-agents. It includes an orchestrating agent that
    analyzes and summarizes results, plus comprehensive tracing for observability.

    ## Key Features:
    - **Orchestrating Agent**: Analyzes workflow results and provides intelligent summaries
    - **Comprehensive Tracing**: Full observability of agent execution flows
    - **Intelligent Routing**: Automatically selects the best workflow based on problem symptoms
    - **Parallel Execution**: Uses micro-agents for efficient parallel task execution
    - **Progress Reporting**: Real-time updates throughout execution
    - **Results Analysis**: Deep analysis and synthesis of findings across all tasks

    ## Available Dynamic Workflows:

    ### 🔍 Missing Data Analysis
    Comprehensive missing data troubleshooting using parallel micro-agents:
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

    ### 🚀 Performance Analysis
    System performance diagnosis using Splunk Platform Instrumentation:
    - System resource baseline analysis (CPU, memory, disk)
    - Splunk process resource analysis
    - Search concurrency and performance monitoring
    - Disk usage and I/O performance
    - Indexing pipeline performance
    - Queue analysis and processing delays
    - Search head and KV Store performance
    - License and capacity constraints
    - Network and forwarder performance

    ### 🏥 Health Check Analysis
    Quick system health assessment:
    - Overall system status verification
    - Critical component health checks
    - Basic connectivity validation
    - License status overview

    ## Arguments:

    - **problem_description** (str, required): Detailed description of the Splunk issue or symptoms. Be specific about error messages, expected vs actual behavior, and affected components.

    - **earliest_time** (str, optional): Start time for diagnostic searches in Splunk time format. Examples: "-24h", "-7d@d", "2023-01-01T00:00:00". Default: "-24h"

    - **latest_time** (str, optional): End time for diagnostic searches in Splunk time format. Examples: "now", "-1h", "@d", "2023-01-01T23:59:59". Default: "now"

    - **focus_index** (str, optional): Specific Splunk index to focus the analysis on. Useful when the problem is isolated to a particular data source.

    - **focus_host** (str, optional): Specific host or server to focus the analysis on. Helpful for distributed environment troubleshooting.

    - **complexity_level** (str, optional): Analysis depth level. Options: "basic", "moderate", "advanced". Affects the comprehensiveness of diagnostic checks. Default: "moderate"

    - **workflow_type** (str, optional): Force a specific workflow type. Options: "missing_data", "performance", "health_check", "auto". Default: "auto" (automatic detection)

    ## How It Works:
    1. **Problem Analysis**: Analyzes the problem description to determine the best workflow
    2. **Dynamic Routing**: Routes to the appropriate dynamic workflow (missing data, performance, or health check)
    3. **Parallel Execution**: Executes multiple diagnostic tasks in parallel using micro-agents
    4. **Orchestration**: Uses an orchestrating agent to analyze and synthesize results
    5. **Progress Reporting**: Provides real-time updates on task execution and findings
    6. **Comprehensive Results**: Returns detailed analysis with actionable recommendations and intelligent summaries

    ## Example Use Cases:
    - "My dashboard shows no data for the last 2 hours" → Missing Data Analysis
    - "Searches are running very slowly since yesterday" → Performance Analysis
    - "I can't see events from my forwarders in index=security" → Missing Data Analysis
    - "Getting license violation warnings but don't know why" → Performance Analysis
    - "High CPU usage on search heads affecting performance" → Performance Analysis
    """

    METADATA = ToolMetadata(
        name="dynamic_troubleshoot",
        description="""Enhanced dynamic troubleshooting agent with orchestration and tracing for efficient Splunk analysis.
This tool provides direct access to the dynamic coordinator system with an orchestrating agent that analyzes and summarizes results. It includes comprehensive tracing for observability and intelligent routing to appropriate parallel workflows.

## Workflow Types:
- **Missing Data Analysis**: Comprehensive parallel troubleshooting for data visibility issues
- **Performance Analysis**: System performance diagnosis using Platform Instrumentation
- **Health Check Analysis**: Quick system health assessment
- **Auto-Detection**: Automatically selects the best workflow based on problem symptoms

## Key Benefits:
- Orchestrating agent for intelligent result analysis and summarization
- Comprehensive tracing with OpenAI Agents SDK integration
- Parallel execution for faster results
- Real-time progress reporting
- Deep analysis and synthesis of findings across all tasks
- Direct routing without triage overhead

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
        super().__init__(name, category)

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
        """Set up the dynamic coordinator system."""

        logger.info("Setting up dynamic coordinator...")

        # Create tool registry for dynamic coordinator
        self.tool_registry = SplunkToolRegistry()

        # Initialize Splunk tools for the registry
        logger.info("Setting up Splunk tools for dynamic agents...")
        from .shared.tools import create_splunk_tools

        tools = create_splunk_tools(self.tool_registry)
        logger.info(f"Initialized {len(tools)} Splunk tools for dynamic agents")

        # Create dynamic coordinator with the same config
        self.dynamic_coordinator = DynamicCoordinator(self.config, self.tool_registry)

        logger.info("Dynamic coordinator setup complete")

    def _setup_orchestrating_agent(self):
        """Set up the orchestrating agent for result analysis and summarization."""

        logger.info("Setting up orchestrating agent...")

        # Create the orchestrating agent that analyzes workflow results
        self.orchestrating_agent = Agent(
            name="Splunk Analysis Orchestrator",
            instructions=prompt_with_handoff_instructions("""
You are a senior Splunk expert orchestrating agent responsible for analyzing and synthesizing results from dynamic troubleshooting workflows.

Your role is to:
1. **Analyze Workflow Results**: Review the results from all parallel micro-agents that executed diagnostic tasks
2. **Synthesize Findings**: Combine findings from multiple tasks into coherent insights
3. **Prioritize Issues**: Identify the most critical issues requiring immediate attention
4. **Generate Actionable Recommendations**: Provide specific, prioritized recommendations for resolution
5. **Create Executive Summary**: Provide a clear, concise summary for both technical and non-technical stakeholders

## Analysis Framework:

### 1. Result Categorization
- **Critical Issues**: Problems requiring immediate attention that could impact system availability
- **Performance Issues**: Problems affecting system performance or efficiency
- **Configuration Issues**: Misconfigurations that could lead to problems
- **Informational**: Status information and baseline metrics

### 2. Root Cause Analysis
- Look for patterns across multiple task results
- Identify common themes and underlying causes
- Correlate findings from different diagnostic areas
- Distinguish between symptoms and root causes

### 3. Impact Assessment
- Assess the business impact of identified issues
- Consider both immediate and potential future impacts
- Evaluate the scope of affected systems or users

### 4. Recommendation Prioritization
- **Priority 1**: Critical issues requiring immediate action
- **Priority 2**: Important issues to address within 24-48 hours
- **Priority 3**: Optimization opportunities and preventive measures

## Output Format:

Provide your analysis in the following structure:

**EXECUTIVE SUMMARY**
- Brief overview of the analysis
- Key findings summary
- Overall system health assessment

**CRITICAL ISSUES IDENTIFIED**
- List of critical issues requiring immediate attention
- Impact assessment for each issue
- Immediate action items

**DETAILED FINDINGS**
- Comprehensive analysis of all findings
- Task-by-task breakdown with insights
- Correlation analysis between different areas

**PRIORITIZED RECOMMENDATIONS**
- Priority 1: Immediate actions (0-4 hours)
- Priority 2: Short-term actions (1-2 days)
- Priority 3: Long-term improvements (1-2 weeks)

**MONITORING AND FOLLOW-UP**
- Suggested monitoring to track resolution
- Follow-up actions to prevent recurrence
- Key metrics to watch

## Analysis Guidelines:

- **Be Specific**: Provide concrete, actionable recommendations with specific commands or configuration changes where possible
- **Consider Context**: Take into account the original problem description and focus areas
- **Think Systematically**: Consider how different components interact and affect each other
- **Prioritize Safety**: Always prioritize system stability and data integrity
- **Explain Reasoning**: Provide clear reasoning for your conclusions and recommendations

Remember: Your analysis should provide value to both immediate troubleshooting efforts and long-term system health improvements.
            """),
            model=self.config.model,
        )

        logger.info("Orchestrating agent setup complete")

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
        trace_name = f"Splunk Dynamic Troubleshooting: {problem_description[:50]}..."
        trace_metadata = {
            "problem_description": problem_description,
            "time_range": f"{earliest_time} to {latest_time}",
            "focus_index": focus_index,
            "focus_host": focus_host,
            "complexity_level": complexity_level,
            "workflow_type": workflow_type,
            "tool_name": "dynamic_troubleshoot_agent",
        }

        if OPENAI_AGENTS_AVAILABLE and trace:
            # Use OpenAI Agents SDK tracing
            with trace(
                workflow_name=trace_name,
                metadata=trace_metadata
            ):
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
                with custom_span("diagnostic_context_creation") as span:
                    span.set_attribute("complexity_level", complexity_level)
                    span.set_attribute("earliest_time", earliest_time)
                    span.set_attribute("latest_time", latest_time)
                    if focus_index:
                        span.set_attribute("focus_index", focus_index)
                    if focus_host:
                        span.set_attribute("focus_host", focus_host)
                    
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
                with custom_span("workflow_type_detection") as span:
                    span.set_attribute("requested_workflow_type", workflow_type)
                    
                    if workflow_type == "auto":
                        detected_workflow = self._analyze_problem_type(problem_description)
                        span.set_attribute("detected_workflow_type", detected_workflow)
                        span.set_attribute("auto_detection_used", True)
                        logger.info(f"Auto-detected workflow type: {detected_workflow}")
                        await ctx.info(f"🤖 Auto-detected workflow: {detected_workflow}")
                    else:
                        detected_workflow = workflow_type
                        span.set_attribute("detected_workflow_type", detected_workflow)
                        span.set_attribute("auto_detection_used", False)
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
                with custom_span(f"workflow_execution_{detected_workflow}") as span:
                    span.set_attribute("workflow_type", detected_workflow)
                    span.set_attribute("problem_description", problem_description[:200])
                    
                    workflow_result = await self._execute_workflow_with_tracing(
                        detected_workflow, diagnostic_context, problem_description
                    )
                    
                    span.set_attribute("workflow_status", workflow_result.get("status", "unknown"))
                    span.set_attribute("tasks_completed", len(workflow_result.get("task_results", [])))
            else:
                workflow_result = await self._execute_workflow_with_tracing(
                    detected_workflow, diagnostic_context, problem_description
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
                    with custom_span("orchestration_analysis") as span:
                        span.set_attribute("input_length", len(orchestration_input))
                        span.set_attribute("workflow_type", detected_workflow)
                        
                        # Use Runner to execute the orchestrating agent
                        orchestration_result = await Runner.run(
                            self.orchestrating_agent,
                            input=orchestration_input,
                            max_turns=5,  # Allow multiple turns for thorough analysis
                        )

                        orchestration_analysis = orchestration_result.final_output
                        span.set_attribute("output_length", len(orchestration_analysis))
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
                    "trace_name": trace_name if OPENAI_AGENTS_AVAILABLE and trace else None,
                    "trace_metadata": trace_metadata if OPENAI_AGENTS_AVAILABLE and trace else None,
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
    ) -> dict[str, Any]:
        """Execute the workflow with proper tracing context."""
        
        if detected_workflow == "missing_data":
            return await self.dynamic_coordinator.execute_missing_data_analysis(
                diagnostic_context, problem_description
            )
        elif detected_workflow == "performance":
            return await self.dynamic_coordinator.execute_performance_analysis(
                diagnostic_context, problem_description
            )
        elif detected_workflow == "health_check":
            return await self.dynamic_coordinator.execute_health_check(
                diagnostic_context
            )
        else:
            raise ValueError(f"Unknown workflow type: {detected_workflow}")
