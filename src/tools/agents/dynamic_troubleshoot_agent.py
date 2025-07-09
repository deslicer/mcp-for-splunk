"""
Dynamic Troubleshooting Agent for Direct Splunk Analysis.

This module provides a direct interface to the dynamic coordinator system,
bypassing the triage layer for more efficient troubleshooting workflows.
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
from .dynamic_coordinator import DynamicCoordinator
from .shared import AgentConfig, SplunkDiagnosticContext, SplunkToolRegistry

logger = logging.getLogger(__name__)


class DynamicTroubleshootAgentTool(BaseTool):
    """
    Direct Dynamic Troubleshooting Agent for Splunk Analysis.

    This tool provides direct access to the dynamic coordinator system for efficient
    Splunk troubleshooting using micro-agents. It automatically analyzes problems
    and routes them to the appropriate dynamic workflow based on symptoms.

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

    ## Key Features:
    - **Intelligent Routing**: Automatically selects the best workflow based on problem symptoms
    - **Parallel Execution**: Uses micro-agents for efficient parallel task execution
    - **Minimal Context**: Optimized for OpenAI rate limits with focused agent instructions
    - **Real-time Progress**: Provides detailed progress reporting throughout execution
    - **Comprehensive Analysis**: Follows official Splunk troubleshooting methodologies

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
    4. **Progress Reporting**: Provides real-time updates on task execution and findings
    5. **Comprehensive Results**: Returns detailed analysis with actionable recommendations

    ## Example Use Cases:
    - "My dashboard shows no data for the last 2 hours" → Missing Data Analysis
    - "Searches are running very slowly since yesterday" → Performance Analysis
    - "I can't see events from my forwarders in index=security" → Missing Data Analysis
    - "Getting license violation warnings but don't know why" → Performance Analysis
    - "High CPU usage on search heads affecting performance" → Performance Analysis
    """

    METADATA = ToolMetadata(
        name="dynamic_troubleshoot",
        description="""Direct dynamic troubleshooting agent for efficient Splunk analysis using micro-agents.
This tool provides direct access to the dynamic coordinator system, automatically analyzing problems and routing them to appropriate parallel workflows. It uses intelligent micro-agents for efficient troubleshooting following official Splunk methodologies.

## Workflow Types:
- **Missing Data Analysis**: Comprehensive parallel troubleshooting for data visibility issues
- **Performance Analysis**: System performance diagnosis using Platform Instrumentation
- **Health Check Analysis**: Quick system health assessment
- **Auto-Detection**: Automatically selects the best workflow based on problem symptoms

## Key Benefits:
- Parallel execution for faster results
- Minimal context per agent (optimized for OpenAI rate limits)
- Real-time progress reporting
- Comprehensive analysis following Splunk best practices
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
        category="troubleshooting"
    )

    def __init__(self, name: str, category: str):
        super().__init__(name, category)

        logger.info(f"Initializing DynamicTroubleshootAgentTool: {name}")

        logger.debug("Loading OpenAI configuration...")
        self.config = self._load_config()
        logger.info(f"OpenAI config loaded - Model: {self.config.model}, Temperature: {self.config.temperature}")

        self.client = OpenAI(api_key=self.config.api_key)

        # Initialize the dynamic coordinator system
        logger.info("Setting up dynamic coordinator system...")
        self._setup_dynamic_coordinator()
        logger.info("DynamicTroubleshootAgentTool initialization complete")

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
            max_tokens=int(os.getenv("OPENAI_MAX_TOKENS", "4000"))
        )

        logger.info(f"Configuration loaded: model={config.model}, temp={config.temperature}, max_tokens={config.max_tokens}")
        return config

    def _setup_dynamic_coordinator(self):
        """Set up the dynamic coordinator system."""

        logger.info("Setting up dynamic coordinator...")

        # Create tool registry for dynamic coordinator
        self.tool_registry = SplunkToolRegistry()

        # Create dynamic coordinator with the same config
        self.dynamic_coordinator = DynamicCoordinator(self.config, self.tool_registry)

        logger.info("Dynamic coordinator setup complete")

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
            "can't find", "no data", "missing", "empty results", "no results",
            "not showing", "not appearing", "dashboard empty", "no events",
            "expected data", "should be there", "permission", "access",
            "search returns nothing", "zero results", "data not visible"
        ]
        
        # Performance indicators
        performance_keywords = [
            "slow", "performance", "high cpu", "high memory", "timeout",
            "taking long", "resource", "capacity", "queue", "delay",
            "indexing slow", "search slow", "system slow", "bottleneck",
            "high usage", "overloaded", "lag", "latency"
        ]
        
        # Health check indicators (simple/quick checks)
        health_keywords = [
            "health check", "status", "connectivity", "basic check",
            "quick check", "overall status", "system status"
        ]
        
        # Count keyword matches
        missing_data_score = sum(1 for keyword in missing_data_keywords if keyword in problem_lower)
        performance_score = sum(1 for keyword in performance_keywords if keyword in problem_lower)
        health_score = sum(1 for keyword in health_keywords if keyword in problem_lower)
        
        logger.debug(f"Problem analysis scores - Missing Data: {missing_data_score}, Performance: {performance_score}, Health: {health_score}")
        
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

    async def execute(
        self,
        ctx: Context,
        problem_description: str,
        earliest_time: str = "-24h",
        latest_time: str = "now",
        focus_index: Optional[str] = None,
        focus_host: Optional[str] = None,
        complexity_level: str = "moderate",
        workflow_type: str = "auto"
    ) -> Dict[str, Any]:
        """
        Execute dynamic troubleshooting analysis.

        This method analyzes the problem and routes it directly to the appropriate
        dynamic workflow for efficient parallel execution.

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
            Dict containing the dynamic analysis results
        """
        execution_start_time = time.time()
        logger.info("="*80)
        logger.info("STARTING DYNAMIC TROUBLESHOOT AGENT EXECUTION")
        logger.info("="*80)

        try:
            logger.info(f"Problem: {problem_description[:200]}...")
            logger.info(f"Time range: {earliest_time} to {latest_time}")
            logger.info(f"Focus - Index: {focus_index}, Host: {focus_host}")
            logger.info(f"Complexity level: {complexity_level}")
            logger.info(f"Workflow type: {workflow_type}")

            # Report initial progress
            await ctx.report_progress(progress=0, total=100)
            await ctx.info(f"🔍 Starting dynamic troubleshooting analysis for: {problem_description[:100]}...")

            # Set the context for tool calls
            self.tool_registry.set_context(ctx)
            logger.debug("Context set for tool registry access")

            # Report progress: Setup complete
            await ctx.report_progress(progress=10, total=100)

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

            # Determine workflow type
            if workflow_type == "auto":
                detected_workflow = self._analyze_problem_type(problem_description)
                logger.info(f"Auto-detected workflow type: {detected_workflow}")
                await ctx.info(f"🤖 Auto-detected workflow: {detected_workflow}")
            else:
                detected_workflow = workflow_type
                logger.info(f"Using specified workflow type: {detected_workflow}")
                await ctx.info(f"🎯 Using specified workflow: {detected_workflow}")

            # Report progress: Workflow selected
            await ctx.report_progress(progress=30, total=100)

            # Execute the appropriate dynamic workflow
            logger.info(f"Executing dynamic {detected_workflow} workflow...")
            
            if detected_workflow == "missing_data":
                await ctx.info("🔍 Executing missing data analysis with parallel micro-agents...")
                result = await self.dynamic_coordinator.execute_missing_data_analysis(
                    diagnostic_context, problem_description
                )
            elif detected_workflow == "performance":
                await ctx.info("🚀 Executing performance analysis with parallel micro-agents...")
                result = await self.dynamic_coordinator.execute_performance_analysis(
                    diagnostic_context, problem_description
                )
            elif detected_workflow == "health_check":
                await ctx.info("🏥 Executing health check analysis with micro-agents...")
                result = await self.dynamic_coordinator.execute_health_check(diagnostic_context)
            else:
                raise ValueError(f"Unknown workflow type: {detected_workflow}")

            # Report progress: Workflow execution complete
            await ctx.report_progress(progress=90, total=100)

            total_execution_time = time.time() - execution_start_time

            # Enhance the result with additional metadata
            enhanced_result = {
                **result,
                "tool_type": "dynamic_troubleshoot_agent",
                "detected_workflow_type": detected_workflow,
                "requested_workflow_type": workflow_type,
                "problem_description": problem_description,
                "diagnostic_context": {
                    "earliest_time": earliest_time,
                    "latest_time": latest_time,
                    "focus_index": focus_index,
                    "focus_host": focus_host,
                    "complexity_level": complexity_level
                },
                "execution_metadata": {
                    "total_execution_time": total_execution_time,
                    "workflow_detection_used": workflow_type == "auto",
                    "direct_routing": True  # This tool routes directly to coordinator
                }
            }

            # Report final progress
            await ctx.report_progress(progress=100, total=100)
            await ctx.info("✅ Dynamic troubleshooting analysis completed")

            logger.info("="*80)
            logger.info("DYNAMIC TROUBLESHOOT AGENT EXECUTION COMPLETED SUCCESSFULLY")
            logger.info(f"Total execution time: {total_execution_time:.2f} seconds")
            logger.info(f"Workflow executed: {detected_workflow}")
            logger.info(f"Status: {enhanced_result.get('status', 'unknown')}")
            logger.info("="*80)

            return enhanced_result

        except Exception as e:
            execution_time = time.time() - execution_start_time
            error_msg = f"Dynamic troubleshoot agent execution failed: {str(e)}"

            logger.error("="*80)
            logger.error("DYNAMIC TROUBLESHOOT AGENT EXECUTION FAILED")
            logger.error(f"Error: {error_msg}")
            logger.error(f"Execution time before failure: {execution_time:.2f} seconds")
            logger.error("="*80)
            logger.error(f"Full error details:", exc_info=True)

            await ctx.error(error_msg)
            return {
                "status": "error",
                "tool_type": "dynamic_troubleshoot_agent",
                "error": error_msg,
                "error_type": "execution_error",
                "execution_time": execution_time,
                "diagnostic_context": {
                    "earliest_time": earliest_time,
                    "latest_time": latest_time,
                    "focus_index": focus_index,
                    "focus_host": focus_host,
                    "complexity_level": complexity_level
                }
            } 