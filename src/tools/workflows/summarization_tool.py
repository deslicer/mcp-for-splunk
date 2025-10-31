"""
Summarization Tool for Diagnostic Agent Results

This standalone tool analyzes results from multiple diagnostic agents and provides
comprehensive insights, recommendations, and executive summaries. It can be reused
across different workflows and agent systems.
"""

import json
import logging
from dataclasses import dataclass
from typing import Any

from fastmcp import Context

from .shared.config import AgentConfig
from .shared.context import DiagnosticResult, SplunkDiagnosticContext
from .shared.tools import SplunkToolRegistry

logger = logging.getLogger(__name__)

# Import OpenAI agents if available
try:
    from agents import Agent, Runner, custom_span, function_tool

    OPENAI_AGENTS_AVAILABLE = True
    logger.info("OpenAI agents SDK loaded successfully for summarization tool")
except ImportError:
    OPENAI_AGENTS_AVAILABLE = False
    Agent = None
    Runner = None
    function_tool = None
    custom_span = None
    logger.warning(
        "OpenAI agents SDK not available for summarization tool. Install with: pip install openai-agents"
    )


@dataclass
class SummarizationResult:
    """Result of the summarization analysis."""

    executive_summary: str
    root_cause_analysis: str
    action_items: list[str]
    priority_recommendations: list[str]
    severity_assessment: str
    resolution_timeline: str
    follow_up_actions: list[str]
    technical_details: dict[str, Any]
    confidence_score: float


class SummarizationTool:
    """
    Standalone tool for analyzing and summarizing diagnostic agent results.

    This tool:
    1. Analyzes results from multiple diagnostic agents
    2. Identifies patterns and correlations across findings
    3. Provides executive-level summaries and technical deep-dives
    4. Generates prioritized action items and recommendations
    5. Assesses severity and provides resolution timelines
    6. Can be reused across different workflows and contexts
    """

    def __init__(self, config: AgentConfig, tool_registry: SplunkToolRegistry = None):
        self.config = config
        self.tool_registry = tool_registry

        logger.info("Initializing SummarizationTool...")

        if not OPENAI_AGENTS_AVAILABLE:
            logger.error("OpenAI agents SDK is required for summarization tool")
            raise ImportError(
                "OpenAI agents SDK is required for summarization tool. "
                "Install with: pip install openai-agents"
            )

        # Create the summarization agent
        self._create_summarization_agent()

        logger.info("SummarizationTool initialized successfully")

    def _create_summarization_agent(self):
        """Create the OpenAI Agent for summarization analysis."""

        instructions = """
You are an expert Splunk diagnostic analyst and technical writer specializing in comprehensive result analysis and executive reporting.

**Your Role:**
- Analyze diagnostic results from multiple specialized agents
- Identify patterns, correlations, and root causes across findings
- Provide clear, actionable insights for both technical teams and executives
- Generate prioritized recommendations with realistic timelines

**Analysis Framework:**
1. **Executive Summary**: High-level overview suitable for management
2. **Root Cause Analysis**: Technical deep-dive into underlying issues
3. **Action Items**: Specific, prioritized tasks with owners and timelines
4. **Severity Assessment**: Risk levels and business impact
5. **Resolution Timeline**: Realistic estimates for issue resolution

**Output Requirements:**
- Use clear, professional language appropriate for technical and non-technical audiences
- Prioritize recommendations by impact and urgency
- Provide specific, actionable steps rather than vague suggestions
- Include confidence levels for assessments
- Consider resource requirements and implementation complexity

**Key Principles:**
- Focus on business impact and user experience
- Distinguish between symptoms and root causes
- Provide both immediate fixes and long-term improvements
- Consider operational constraints and maintenance windows
- Emphasize preventive measures to avoid future issues

Always structure your analysis comprehensively and provide practical, implementable recommendations.
        """

        # Create tools for the summarization agent
        tools = [self._create_return_summary_tool()]

        self.summarization_agent = Agent(
            name="DiagnosticSummarizationAgent",
            instructions=instructions,
            model=self.config.model,
            tools=tools,
        )

        logger.debug("Created summarization agent with specialized analysis instructions")

    def _create_return_summary_tool(self):
        """Create tool for returning structured summarization results."""

        @function_tool
        async def return_summarization_result(
            executive_summary: str,
            root_cause_analysis: str,
            action_items: str,  # JSON string of list
            priority_recommendations: str,  # JSON string of list
            severity_assessment: str,
            resolution_timeline: str,
            follow_up_actions: str,  # JSON string of list
            technical_details: str,  # JSON string of dict
            confidence_score: float,
        ) -> str:
            """Return the comprehensive summarization analysis.

            Args:
                executive_summary: High-level summary for management
                root_cause_analysis: Technical analysis of underlying issues
                action_items: JSON string of prioritized action items (list)
                priority_recommendations: JSON string of priority recommendations (list)
                severity_assessment: Overall severity and business impact assessment
                resolution_timeline: Realistic timeline for issue resolution
                follow_up_actions: JSON string of follow-up actions (list)
                technical_details: JSON string of additional technical context (dict)
                confidence_score: Confidence level in the analysis (0.0-1.0)
            """
            try:
                # Parse JSON strings
                action_items_list = json.loads(action_items) if action_items else []
                priority_recommendations_list = (
                    json.loads(priority_recommendations) if priority_recommendations else []
                )
                follow_up_actions_list = json.loads(follow_up_actions) if follow_up_actions else []
                technical_details_dict = json.loads(technical_details) if technical_details else {}
            except json.JSONDecodeError as e:
                logger.error(f"JSON parsing error in summarization result: {e}")
                # Fallback to treating as plain text
                action_items_list = [action_items] if action_items else []
                priority_recommendations_list = (
                    [priority_recommendations] if priority_recommendations else []
                )
                follow_up_actions_list = [follow_up_actions] if follow_up_actions else []
                technical_details_dict = (
                    {"raw_details": technical_details} if technical_details else {}
                )

            # Store the result for retrieval
            self._summarization_result = SummarizationResult(
                executive_summary=executive_summary,
                root_cause_analysis=root_cause_analysis,
                action_items=action_items_list,
                priority_recommendations=priority_recommendations_list,
                severity_assessment=severity_assessment,
                resolution_timeline=resolution_timeline,
                follow_up_actions=follow_up_actions_list,
                technical_details=technical_details_dict,
                confidence_score=max(0.0, min(1.0, confidence_score)),
            )

            logger.debug(f"Summarization result stored with confidence: {confidence_score:.2f}")
            return f"Summarization analysis completed with confidence: {confidence_score:.2f}"

        return return_summarization_result

    async def execute(
        self,
        ctx: Context,
        workflow_results: dict[str, DiagnosticResult],
        problem_description: str,
        diagnostic_context: SplunkDiagnosticContext,
        execution_metadata: dict[str, Any] = None,
    ) -> dict[str, Any]:
        """
        Execute comprehensive summarization analysis of diagnostic results.

        Args:
            ctx: FastMCP context for progress reporting and logging
            workflow_results: Results from diagnostic agents
            problem_description: Original problem description from user
            diagnostic_context: Context used for diagnostic execution
            execution_metadata: Optional metadata from workflow execution

        Returns:
            Comprehensive summarization analysis including executive summary,
            root cause analysis, action items, and recommendations
        """
        if execution_metadata is None:
            execution_metadata = {}

        logger.info("=" * 80)
        logger.info("STARTING DIAGNOSTIC RESULTS SUMMARIZATION")
        logger.info("=" * 80)

        # Report initial progress
        await ctx.report_progress(progress=0, total=100)
        await ctx.info(f"🔍 Analyzing {len(workflow_results)} diagnostic results...")

        try:
            # Add comprehensive tracing for summarization
            if OPENAI_AGENTS_AVAILABLE and custom_span:
                with custom_span("diagnostic_summarization"):
                    return await self._execute_summarization_core(
                        ctx,
                        workflow_results,
                        problem_description,
                        diagnostic_context,
                        execution_metadata,
                    )
            else:
                return await self._execute_summarization_core(
                    ctx,
                    workflow_results,
                    problem_description,
                    diagnostic_context,
                    execution_metadata,
                )

        except Exception as e:
            logger.error(f"Summarization execution failed: {e}", exc_info=True)
            await ctx.error(f"❌ Summarization failed: {str(e)}")

            return {
                "status": "error",
                "error": str(e),
                "executive_summary": f"Summarization analysis failed: {str(e)}",
                "recommendations": [
                    "Review diagnostic results manually",
                    "Check summarization tool configuration",
                ],
                "execution_metadata": execution_metadata,
            }

    async def _execute_summarization_core(
        self,
        ctx: Context,
        workflow_results: dict[str, DiagnosticResult],
        problem_description: str,
        diagnostic_context: SplunkDiagnosticContext,
        execution_metadata: dict[str, Any],
    ) -> dict[str, Any]:
        """Core summarization execution with comprehensive analysis."""

        # Initialize result storage
        self._summarization_result = None

        # Build comprehensive analysis input
        if OPENAI_AGENTS_AVAILABLE and custom_span:
            with custom_span("analysis_preparation"):
                analysis_input = self._build_analysis_input(
                    workflow_results, problem_description, diagnostic_context, execution_metadata
                )
        else:
            analysis_input = self._build_analysis_input(
                workflow_results, problem_description, diagnostic_context, execution_metadata
            )

        # Report progress: Analysis input prepared
        await ctx.report_progress(progress=20, total=100)
        await ctx.info("📋 Analysis framework prepared, executing summarization agent...")

        # Execute summarization agent
        if OPENAI_AGENTS_AVAILABLE and custom_span:
            with custom_span("summarization_agent_execution"):
                agent_result = await Runner.run(
                    self.summarization_agent,
                    input=analysis_input,
                    max_turns=5,  # Allow multiple turns for comprehensive analysis
                )
        else:
            agent_result = await Runner.run(
                self.summarization_agent,
                input=analysis_input,
                max_turns=5,
            )

        # Report progress: Agent execution complete
        await ctx.report_progress(progress=80, total=100)

        # Extract structured result
        if hasattr(self, "_summarization_result") and self._summarization_result:
            logger.debug("Retrieved structured summarization result")
            await ctx.info("✅ Comprehensive analysis completed")

            # Convert to final result format
            result = self._format_final_result(
                self._summarization_result, workflow_results, execution_metadata
            )
        else:
            logger.warning("No structured result stored, creating from agent output")
            await ctx.warning("⚠️ Summarization completed without structured result")

            # Create fallback result from agent output
            result = self._create_fallback_result(
                agent_result, workflow_results, execution_metadata
            )

        # Report final progress
        await ctx.report_progress(progress=100, total=100)
        await ctx.info(f"📊 Summarization analysis completed: {result['severity_assessment']}")

        logger.info("=" * 80)
        logger.info("DIAGNOSTIC RESULTS SUMMARIZATION COMPLETED")
        logger.info(f"Severity Assessment: {result['severity_assessment']}")
        logger.info(f"Confidence Score: {result['confidence_score']:.2f}")
        logger.info(f"Action Items: {len(result['action_items'])}")
        logger.info(f"Recommendations: {len(result['priority_recommendations'])}")
        logger.info("=" * 80)

        return result

    def _build_analysis_input(
        self,
        workflow_results: dict[str, DiagnosticResult],
        problem_description: str,
        diagnostic_context: SplunkDiagnosticContext,
        execution_metadata: dict[str, Any],
    ) -> str:
        """Build comprehensive analysis input for the summarization agent."""

        # Start with problem context
        analysis_input = f"""
**DIAGNOSTIC ANALYSIS REQUEST**

**Original Problem:**
{problem_description}

**Diagnostic Context:**
- Time Range: {diagnostic_context.earliest_time} to {diagnostic_context.latest_time}
- Complexity Level: {diagnostic_context.complexity_level}
- Focus Index: {diagnostic_context.focus_index or "All indexes"}
- Focus Host: {diagnostic_context.focus_host or "All hosts"}
"""

        if diagnostic_context.problem_description:
            analysis_input += f"- Original Problem: {diagnostic_context.problem_description}\n"
        if diagnostic_context.workflow_type:
            analysis_input += f"- Workflow Type: {diagnostic_context.workflow_type}\n"
        if diagnostic_context.indexes:
            analysis_input += f"- Target Indexes: {', '.join(diagnostic_context.indexes)}\n"
        if diagnostic_context.sourcetypes:
            analysis_input += f"- Target Sourcetypes: {', '.join(diagnostic_context.sourcetypes)}\n"
        if diagnostic_context.sources:
            analysis_input += f"- Target Sources: {', '.join(diagnostic_context.sources)}\n"

        # Add execution metadata
        if execution_metadata:
            analysis_input += "\n**Execution Metadata:**\n"
            if "total_execution_time" in execution_metadata:
                analysis_input += (
                    f"- Total Execution Time: {execution_metadata['total_execution_time']:.2f}s\n"
                )
            if "execution_phases" in execution_metadata:
                analysis_input += f"- Execution Phases: {execution_metadata['execution_phases']}\n"
            if "parallel_efficiency" in execution_metadata:
                analysis_input += (
                    f"- Parallel Efficiency: {execution_metadata['parallel_efficiency']:.1%}\n"
                )

        # Add diagnostic results
        analysis_input += f"\n**DIAGNOSTIC RESULTS ({len(workflow_results)} agents):**\n\n"

        # Categorize results by status
        status_groups = {"healthy": [], "warning": [], "critical": [], "error": []}

        for task_id, result in workflow_results.items():
            # Handle both DiagnosticResult objects and plain dictionaries
            if hasattr(result, "status"):
                # DiagnosticResult object
                status = result.status
            elif isinstance(result, dict) and "status" in result:
                # Plain dictionary format
                status = result["status"]
            else:
                # Fallback
                status = "unknown"

            status_groups[status].append((task_id, result))

        # Present results by severity (most critical first)
        for status in ["error", "critical", "warning", "healthy"]:
            if status_groups[status]:
                analysis_input += (
                    f"**{status.upper()} STATUS ({len(status_groups[status])} agents):**\n"
                )

                for task_id, result in status_groups[status]:
                    analysis_input += f"\n**Agent: {task_id}**\n"

                    # Handle both DiagnosticResult objects and plain dictionaries
                    if hasattr(result, "status"):
                        # DiagnosticResult object
                        result_status = result.status
                        result_findings = result.findings or []
                        result_recommendations = result.recommendations or []
                        result_details = result.details or {}
                        result_severity = getattr(result, "severity", result_status)
                        result_success_score = getattr(result, "success_score", None)
                        result_trace_url = getattr(result, "trace_url", None)
                    elif isinstance(result, dict):
                        # Plain dictionary format
                        result_status = result.get("status", "unknown")
                        result_findings = result.get("findings", [])
                        result_recommendations = result.get("recommendations", [])
                        result_details = result.get("details", {})
                        result_severity = result.get("severity", result_status)
                        result_success_score = result.get("success_score")
                        result_trace_url = result.get("trace_url")
                    else:
                        # Fallback
                        result_status = "unknown"
                        result_findings = []
                        result_recommendations = []
                        result_details = {}
                        result_severity = "unknown"
                        result_success_score = None
                        result_trace_url = None

                    analysis_input += f"Status: {result_status}\n"
                    analysis_input += f"Severity: {result_severity}\n"
                    if result_success_score is not None:
                        analysis_input += f"Success Score: {result_success_score:.2f}\n"
                    if result_trace_url:
                        analysis_input += f"Trace: {result_trace_url}\n"

                    if result_findings:
                        analysis_input += "Findings:\n"
                        for finding in result_findings:
                            analysis_input += f"  - {finding}\n"

                    if result_recommendations:
                        analysis_input += "Recommendations:\n"
                        for rec in result_recommendations:
                            analysis_input += f"  - {rec}\n"

                    # Include key details
                    if result_details:
                        important_keys = [
                            "user_info",
                            "license_state",
                            "total_events",
                            "available_indexes",
                            "server_info",
                            "error",
                            "execution_time",
                            "agent_output",
                            "trace_url",
                        ]
                        detail_items = []
                        for key in important_keys:
                            if key in result_details:
                                value = result_details[key]
                                if isinstance(value, dict | list):
                                    detail_items.append(f"{key}: {str(value)[:200]}...")
                                else:
                                    detail_items.append(f"{key}: {value}")

                        if detail_items:
                            analysis_input += "Key Details:\n"
                            for item in detail_items[:5]:  # Limit to top 5 details
                                analysis_input += f"  - {item}\n"

                    analysis_input += "\n"

        # Add analysis instructions
        analysis_input += """
**ANALYSIS REQUIREMENTS:**

Please provide a comprehensive analysis using the return_summarization_result function with:

1. **Executive Summary**: 2-3 paragraphs suitable for management, focusing on business impact
2. **Root Cause Analysis**: Technical deep-dive into underlying issues and their relationships
3. **Action Items**: JSON array of specific, prioritized tasks with clear owners and timelines
4. **Priority Recommendations**: JSON array of high-impact recommendations ordered by urgency
5. **Severity Assessment**: Overall risk level and business impact (Critical/High/Medium/Low)
6. **Resolution Timeline**: Realistic estimates for addressing identified issues
7. **Follow-up Actions**: JSON array of preventive measures and monitoring recommendations
8. **Technical Details**: JSON object with additional context, metrics, and implementation notes
9. **Confidence Score**: Your confidence in this analysis (0.0-1.0)

**Focus Areas:**
- Identify patterns and correlations across agent findings
- Distinguish between symptoms and root causes
- Prioritize by business impact and implementation complexity
- Provide specific, actionable guidance
- Consider operational constraints and maintenance windows
- Include both immediate fixes and long-term improvements

Use JSON strings for array and object parameters to ensure proper parsing.
"""

        return analysis_input

    def _format_final_result(
        self,
        summarization_result: SummarizationResult,
        workflow_results: dict[str, DiagnosticResult],
        execution_metadata: dict[str, Any],
    ) -> dict[str, Any]:
        """Format the final summarization result for return."""

        # Calculate additional metrics
        total_findings = 0
        total_recommendations = 0
        status_breakdown = {}

        for result in workflow_results.values():
            # Handle both DiagnosticResult objects and plain dictionaries
            if hasattr(result, "status"):
                # DiagnosticResult object
                status = result.status
                findings_count = len(result.findings or [])
                recommendations_count = len(result.recommendations or [])
            elif isinstance(result, dict):
                # Plain dictionary format
                status = result.get("status", "unknown")
                findings_count = len(result.get("findings", []))
                recommendations_count = len(result.get("recommendations", []))
            else:
                # Fallback
                status = "unknown"
                findings_count = 0
                recommendations_count = 0

            total_findings += findings_count
            total_recommendations += recommendations_count
            status_breakdown[status] = status_breakdown.get(status, 0) + 1

        return {
            "status": "completed",
            "executive_summary": summarization_result.executive_summary,
            "root_cause_analysis": summarization_result.root_cause_analysis,
            "action_items": summarization_result.action_items,
            "priority_recommendations": summarization_result.priority_recommendations,
            "severity_assessment": summarization_result.severity_assessment,
            "resolution_timeline": summarization_result.resolution_timeline,
            "follow_up_actions": summarization_result.follow_up_actions,
            "confidence_score": summarization_result.confidence_score,
            "technical_details": summarization_result.technical_details,
            "analysis_metadata": {
                "total_agents_analyzed": len(workflow_results),
                "total_findings": total_findings,
                "total_recommendations": total_recommendations,
                "agent_status_breakdown": status_breakdown,
                "summarization_method": "openai_agent",
                "execution_metadata": execution_metadata,
            },
        }

    def _create_fallback_result(
        self,
        agent_result: Any,
        workflow_results: dict[str, DiagnosticResult],
        execution_metadata: dict[str, Any],
    ) -> dict[str, Any]:
        """Create fallback result when structured output is not available."""

        # Extract agent output
        output = (
            agent_result.final_output
            if hasattr(agent_result, "final_output")
            else str(agent_result)
        )

        # Simple parsing for basic structure
        lines = output.split("\n")
        executive_summary = "Analysis completed with partial results."
        action_items = ["Review diagnostic results manually"]

        # Look for key sections in output
        for i, line in enumerate(lines):
            if "summary" in line.lower() and i + 1 < len(lines):
                executive_summary = lines[i + 1].strip()
                break

        # Determine severity based on workflow results
        statuses = []
        for result in workflow_results.values():
            # Handle both DiagnosticResult objects and plain dictionaries
            if hasattr(result, "status"):
                statuses.append(result.status)
            elif isinstance(result, dict):
                statuses.append(result.get("status", "unknown"))
            else:
                statuses.append("unknown")

        if "error" in statuses or "critical" in statuses:
            severity = "High"
        elif "warning" in statuses:
            severity = "Medium"
        else:
            severity = "Low"

        return {
            "status": "completed",
            "executive_summary": executive_summary,
            "root_cause_analysis": "Detailed analysis available in agent output.",
            "action_items": action_items,
            "priority_recommendations": [
                "Review individual agent findings",
                "Implement recommended fixes",
            ],
            "severity_assessment": severity,
            "resolution_timeline": "To be determined based on specific issues",
            "follow_up_actions": ["Monitor system after implementing fixes"],
            "confidence_score": 0.6,  # Lower confidence for fallback
            "technical_details": {"agent_output": output},
            "analysis_metadata": {
                "total_agents_analyzed": len(workflow_results),
                "summarization_method": "fallback_parsing",
                "execution_metadata": execution_metadata,
            },
        }


# Factory function for easy instantiation
def create_summarization_tool(
    config: AgentConfig, tool_registry: SplunkToolRegistry = None
) -> SummarizationTool:
    """Factory function to create a summarization tool."""
    return SummarizationTool(config, tool_registry)
