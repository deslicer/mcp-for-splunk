"""
Reflection Agent for Iterative Splunk Troubleshooting.

This module implements the reflection pattern from the OpenAI agents SDK
for self-improving and iterative analysis of Splunk troubleshooting workflows.
"""

import os
import asyncio
import logging
import time
from typing import Any, Dict, List, Optional
from dataclasses import dataclass
from enum import Enum

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
    OPENAI_AGENTS_AVAILABLE = True
    logger.info("OpenAI agents SDK loaded successfully for reflection analysis")
except ImportError:
    OPENAI_AGENTS_AVAILABLE = False
    logger.warning("OpenAI agents SDK not available for reflection analysis. Install with: pip install openai-agents")


class ReflectionPhase(Enum):
    """Phases of the reflection workflow."""
    INITIAL_ANALYSIS = "initial_analysis"
    REFLECTION = "reflection"
    VALIDATION = "validation"
    REFINEMENT = "refinement"
    FINAL_SYNTHESIS = "final_synthesis"


@dataclass
class ReflectionContext:
    """Context for managing reflection workflow state."""
    earliest_time: str = "-24h"
    latest_time: str = "now"
    max_iterations: int = 3
    improvement_threshold: float = 0.1
    enable_validation: bool = True
    focus_areas: List[str] = None
    
    def __post_init__(self):
        if self.focus_areas is None:
            self.focus_areas = ["accuracy", "completeness", "actionability"]


@dataclass
class IterationResult:
    """Result from a single reflection iteration."""
    iteration_number: int
    phase: ReflectionPhase
    analysis_result: str
    reflection_insights: str
    improvement_score: float
    validation_result: Optional[str] = None
    execution_time: float = 0.0
    identified_gaps: List[str] = None
    
    def __post_init__(self):
        if self.identified_gaps is None:
            self.identified_gaps = []


class ReflectionAgentTool(BaseTool):
    """
    OpenAI Agents-based reflection system for iterative Splunk troubleshooting.
    
    This tool implements the reflection pattern where an agent continuously
    improves its analysis through self-assessment, validation, and refinement cycles.
    """

    METADATA = ToolMetadata(
        name="execute_reflection_agent",
        description="Execute iterative self-improving analysis using OpenAI agents with reflection and validation",
        category="agents"
    )

    def __init__(self, name: str, category: str):
        super().__init__(name, category)
        
        logger.info(f"Initializing ReflectionAgentTool: {name}")
        
        if not OPENAI_AGENTS_AVAILABLE:
            logger.error("OpenAI agents SDK is required for reflection analysis")
            raise ImportError(
                "OpenAI agents SDK is required for this tool. "
                "Install with: pip install openai-agents"
            )
        
        logger.debug("Loading OpenAI configuration for reflection analysis...")
        self.config = self._load_config()
        logger.info(f"OpenAI config loaded - Model: {self.config.model}, Temperature: {self.config.temperature}")
        
        self.client = OpenAI(api_key=self.config.api_key)
        
        # Initialize the reflection agent system
        logger.info("Setting up reflection agent system...")
        self._setup_reflection_agents()
        
        # Initialize dynamic coordinator for missing data analysis
        logger.info("Setting up dynamic coordinator for missing data analysis...")
        self._setup_dynamic_coordinator()
        logger.info("ReflectionAgentTool initialization complete")

    def _load_config(self):
        """Load OpenAI configuration from environment variables."""
        logger.debug("Loading OpenAI configuration from environment for reflection analysis")
        
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            logger.error("OPENAI_API_KEY environment variable not found")
            raise ValueError(
                "OPENAI_API_KEY environment variable is required. "
                "Please set it in your .env file or environment."
            )
        
        logger.debug("API key found, creating configuration for reflection analysis")
        
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
        
        logger.info(f"Reflection analysis configuration loaded: model={config.model}, temp={config.temperature}, max_tokens={config.max_tokens}")
        return config

    def _setup_reflection_agents(self):
        """Set up the reflection agent system."""
        
        logger.info("Setting up reflection agent system...")
        
        # Create Splunk tool functions for agents to use
        logger.debug("Creating Splunk tool functions for reflection agents...")
        self._create_splunk_tools()
        logger.info(f"Created {len(self.splunk_tools)} Splunk tool functions for reflection workflow")
        
        # Create specialized reflection agents
        logger.debug("Creating reflection workflow agents...")
        
        logger.debug("Creating primary analyst agent...")
        self.primary_analyst = self._create_primary_analyst()
        logger.info("Primary analyst agent created successfully")
        
        logger.debug("Creating reflection critic agent...")
        self.reflection_critic = self._create_reflection_critic()
        logger.info("Reflection critic agent created successfully")
        
        logger.debug("Creating validation agent...")
        self.validation_agent = self._create_validation_agent()
        logger.info("Validation agent created successfully")
        
        logger.debug("Creating synthesis agent...")
        self.synthesis_agent = self._create_synthesis_agent()
        logger.info("Synthesis agent created successfully")
        
        logger.info("Reflection agent system setup complete - All workflow agents ready")

    def _setup_dynamic_coordinator(self):
        """Set up the dynamic coordinator for missing data analysis."""
        
        logger.info("Setting up dynamic coordinator...")
        
        # Create tool registry for dynamic coordinator
        self.tool_registry = SplunkToolRegistry()
        
        # Create dynamic coordinator with the same config
        self.dynamic_coordinator = DynamicCoordinator(self.config, self.tool_registry)
        
        logger.info("Dynamic coordinator setup complete")

    def _create_splunk_tools(self):
        """Create function tools that wrap MCP server tools for reflection execution."""
        
        logger.debug("Setting up direct tool registry access for reflection execution...")
        
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
            "list_triggered_alerts"
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
        async def run_reflective_search(query: str, earliest_time: str = "-24h", latest_time: str = "now", iteration: int = 1) -> str:
            """Execute a Splunk search query via direct tool registry optimized for reflection workflow."""
            logger.debug(f"[Iteration {iteration}] Executing reflective search: {query[:100]}... (time: {earliest_time} to {latest_time})")
            
            try:
                # Get the tool directly from registry
                tool = tool_registry.get_tool("run_oneshot_search")
                if not tool:
                    raise RuntimeError("run_oneshot_search tool not found in registry")
                
                logger.debug(f"[Iteration {iteration}] Calling tool registry: run_oneshot_search")
                
                # Get current context
                ctx = get_context()
                
                # Call the tool directly
                result = await tool.execute(
                    ctx,
                    query=query,
                    earliest_time=earliest_time,
                    latest_time=latest_time,
                    max_results=100
                )
                
                logger.info(f"[Iteration {iteration}] Direct search completed successfully, result length: {len(str(result))}")
                return str(result)
                
            except Exception as e:
                logger.error(f"[Iteration {iteration}] Error executing direct search: {e}", exc_info=True)
                return f"[Iteration {iteration}] Error executing direct search: {str(e)}"

        @function_tool
        async def validate_analysis_findings(findings: str, iteration: int = 1) -> str:
            """Validate analysis findings using additional direct tool registry searches."""
            logger.debug(f"[Iteration {iteration}] Validating analysis findings via direct registry, length: {len(findings)} characters")
            
            try:
                # Extract key metrics or claims from findings for validation
                validation_queries = [
                    'index=_internal source=*metrics.log* | stats count by group',
                    'index=_internal source=*splunkd.log* log_level=ERROR | stats count by component',
                    'index=_internal source=*scheduler.log* | stats count by status'
                ]
                
                validation_results = []
                for i, query in enumerate(validation_queries):
                    logger.debug(f"[Iteration {iteration}] Running validation query {i+1} via direct registry: {query}")
                    result = await run_reflective_search(query, iteration=iteration)
                    validation_results.append(f"Validation {i+1}: {result[:200]}...")
                
                combined_validation = "\n".join(validation_results)
                logger.info(f"[Iteration {iteration}] Validation completed via direct registry with {len(validation_queries)} queries")
                return combined_validation
                
            except Exception as e:
                logger.error(f"[Iteration {iteration}] Error validating findings via direct registry: {e}", exc_info=True)
                return f"[Iteration {iteration}] Error validating findings via direct registry: {str(e)}"

        @function_tool
        async def gather_additional_context(focus_area: str, iteration: int = 1) -> str:
            """Gather additional context for specific focus areas via direct tool registry."""
            logger.debug(f"[Iteration {iteration}] Gathering additional context via direct registry for: {focus_area}")
            
            try:
                # Focus area specific queries
                context_queries = {
                    "performance": 'index=_internal source=*metrics.log* group=search_concurrency | stats avg(active_hist_searches) as avg_searches',
                    "errors": 'index=_internal source=*splunkd.log* log_level=ERROR | stats count by component | sort -count',
                    "capacity": 'index=_internal source=*metrics.log* group=per_index_thruput | stats sum(kb) as total_kb by series',
                    "health": 'index=_internal source=*splunkd.log* component=TcpOutputFd | stats count by log_level'
                }
                
                query = context_queries.get(focus_area, f'index=_internal source=*metrics.log* | head 10')
                logger.debug(f"[Iteration {iteration}] Using context query for {focus_area}: {query}")
                
                result = await run_reflective_search(query, iteration=iteration)
                logger.info(f"[Iteration {iteration}] Additional context gathered via direct registry for {focus_area}, result length: {len(result)}")
                return result
                
            except Exception as e:
                logger.error(f"[Iteration {iteration}] Error gathering additional context via direct registry: {e}", exc_info=True)
                return f"[Iteration {iteration}] Error gathering additional context via direct registry: {str(e)}"

        @function_tool
        async def execute_dynamic_missing_data_analysis(problem_description: str, earliest_time: str = "-24h", latest_time: str = "now", iteration: int = 1) -> str:
            """Execute missing data analysis using the dynamic coordinator with micro-agents."""
            logger.debug(f"[Iteration {iteration}] Executing dynamic missing data analysis for: {problem_description[:100]}...")
            
            try:
                # Create diagnostic context
                diagnostic_context = SplunkDiagnosticContext(
                    earliest_time=earliest_time,
                    latest_time=latest_time,
                    indexes=[],  # Will be populated by the workflow
                    sourcetypes=[],
                    sources=[]
                )
                
                logger.debug(f"[Iteration {iteration}] Created diagnostic context: {earliest_time} to {latest_time}")
                
                # Set context for the tool registry
                self.tool_registry.set_context(get_context())
                
                # Execute dynamic missing data analysis
                logger.debug(f"[Iteration {iteration}] Calling dynamic coordinator...")
                
                result = await self.dynamic_coordinator.execute_missing_data_analysis(
                    diagnostic_context=diagnostic_context,
                    problem_description=problem_description
                )
                
                # Format result for agent consumption
                if result.get("status") == "success":
                    workflow_exec = result.get("workflow_execution", {})
                    task_results = result.get("task_results", [])
                    performance_metrics = result.get("performance_metrics", {})
                    
                    formatted_result = f"""Dynamic Missing Data Analysis Results:

**Workflow Execution:**
- Workflow ID: {workflow_exec.get('workflow_id', 'unknown')}
- Overall Status: {workflow_exec.get('overall_status', 'unknown')}
- Execution Time: {workflow_exec.get('execution_time', 0):.2f}s
- Parallel Efficiency: {workflow_exec.get('parallel_efficiency', 0):.1%}
- Execution Phases: {workflow_exec.get('execution_phases', 0)}
- Total Tasks: {workflow_exec.get('total_tasks', 0)}

**Task Results:**"""
                    
                    for task in task_results:
                        formatted_result += f"""
- {task.get('task', 'Unknown Task')}: {task.get('status', 'unknown')}
  Findings: {len(task.get('findings', []))} items
  Recommendations: {len(task.get('recommendations', []))} items"""
                        if task.get('findings'):
                            formatted_result += f"\n  Key Finding: {task['findings'][0]}"
                    
                    formatted_result += f"""

**Performance Metrics:**
- Total Execution Time: {performance_metrics.get('total_execution_time', 0):.2f}s
- Tasks Completed: {performance_metrics.get('tasks_completed', 0)}
- Successful Tasks: {performance_metrics.get('successful_tasks', 0)}
- Failed Tasks: {performance_metrics.get('failed_tasks', 0)}
- Parallel Phases: {performance_metrics.get('parallel_phases', 0)}"""
                    
                    logger.info(f"[Iteration {iteration}] Dynamic missing data analysis completed successfully")
                    return formatted_result
                else:
                    error_msg = result.get("error", "Unknown error")
                    logger.error(f"[Iteration {iteration}] Dynamic missing data analysis failed: {error_msg}")
                    return f"Dynamic missing data analysis failed: {error_msg}"
                
            except Exception as e:
                error_msg = f"Error executing dynamic missing data analysis: {str(e)}"
                logger.error(f"[Iteration {iteration}] {error_msg}", exc_info=True)
                return error_msg

        # Store tools for use by agents
        self.splunk_tools = [run_reflective_search, validate_analysis_findings, gather_additional_context, execute_dynamic_missing_data_analysis]
        logger.info(f"Created {len(self.splunk_tools)} direct registry tool wrappers for reflection workflow")

    def _create_primary_analyst(self) -> Agent:
        """Create the primary analysis agent for initial and iterative analysis."""
        logger.debug("Creating primary analyst agent for reflection workflow...")
        
        agent = Agent(
            name="Reflective Primary Analyst",
            instructions="""
You are a Splunk troubleshooting analyst specialized in iterative, self-improving analysis using dynamic micro-agents.

Your responsibilities:
1. Conduct thorough initial analysis of Splunk issues using dynamic workflows
2. Incorporate feedback from reflection and validation cycles
3. Refine your analysis based on identified gaps or weaknesses
4. Use available tools including the dynamic missing data analysis coordinator
5. Continuously improve your understanding and recommendations

Analysis approach:
- For missing data issues, use execute_dynamic_missing_data_analysis for comprehensive parallel analysis
- Use individual tools (run_reflective_search, etc.) for targeted investigation
- Start with broad system assessment using dynamic workflows
- Drill down into specific problem areas with focused searches
- Use metrics and logs to support findings
- Provide specific, actionable recommendations
- Be open to revision based on reflection feedback

Available tools:
- execute_dynamic_missing_data_analysis: Comprehensive missing data troubleshooting using parallel micro-agents
- run_reflective_search: Individual Splunk searches for targeted investigation
- validate_analysis_findings: Validate findings with additional searches
- gather_additional_context: Gather context for specific focus areas

Focus on accuracy, completeness, and actionability in your analysis.
Acknowledge uncertainties and areas where additional investigation may be needed.
            """,
            model=self.config.model,
            tools=self.splunk_tools
        )
        
        logger.debug("Primary analyst agent created with reflection-optimized configuration")
        return agent

    def _create_reflection_critic(self) -> Agent:
        """Create the reflection critic agent for self-assessment."""
        logger.debug("Creating reflection critic agent...")
        
        agent = Agent(
            name="Reflection Critic",
            instructions="""
You are a critical reflection specialist for Splunk troubleshooting analysis.

Your role:
1. Critically evaluate analysis results for accuracy and completeness
2. Identify gaps, weaknesses, or areas for improvement
3. Assess the quality of evidence and reasoning
4. Suggest specific improvements or additional investigation areas
5. Rate the overall quality and actionability of the analysis

Evaluation criteria:
- **Accuracy**: Are findings supported by solid evidence?
- **Completeness**: Are all relevant aspects covered?
- **Actionability**: Are recommendations specific and implementable?
- **Logic**: Is the reasoning sound and well-structured?
- **Evidence**: Is the analysis backed by appropriate data?

Provide constructive criticism with specific suggestions for improvement.
Rate the analysis on a scale of 0.0 to 1.0 for overall quality.
Identify the most critical areas that need enhancement.
            """,
            model=self.config.model
        )
        
        logger.debug("Reflection critic agent created successfully")
        return agent

    def _create_validation_agent(self) -> Agent:
        """Create the validation agent for verifying findings."""
        logger.debug("Creating validation agent...")
        
        agent = Agent(
            name="Analysis Validator",
            instructions="""
You are a Splunk analysis validation specialist.

Your responsibilities:
1. Independently verify key findings and claims
2. Cross-check analysis results against additional data sources
3. Validate recommendations through supporting evidence
4. Identify any contradictions or inconsistencies
5. Assess the reliability of the analysis

Validation approach:
- Use additional Splunk searches to verify claims
- Look for supporting or contradicting evidence
- Check for logical consistency in findings
- Validate that recommendations address the identified issues
- Assess confidence levels for different findings

Provide validation results with confidence ratings.
Highlight any findings that cannot be verified.
            """,
            model=self.config.model,
            tools=self.splunk_tools
        )
        
        logger.debug("Validation agent created successfully")
        return agent

    def _create_synthesis_agent(self) -> Agent:
        """Create the synthesis agent for final consolidation."""
        logger.debug("Creating synthesis agent...")
        
        agent = Agent(
            name="Analysis Synthesizer",
            instructions="""
You are a Splunk analysis synthesis specialist.

Your role:
1. Consolidate findings from multiple reflection iterations
2. Integrate insights from reflection and validation cycles
3. Create a comprehensive, refined final analysis
4. Prioritize recommendations based on impact and feasibility
5. Provide clear, actionable guidance

Synthesis approach:
- Combine the best insights from all iterations
- Resolve any contradictions or inconsistencies
- Prioritize findings by business impact
- Ensure recommendations are specific and actionable
- Include confidence levels and next steps

Create a polished, professional analysis that represents the best collective insights.
Structure the output for maximum clarity and actionability.
            """,
            model=self.config.model
        )
        
        logger.debug("Synthesis agent created successfully")
        return agent

    async def execute(
        self,
        ctx: Context,
        problem_description: str,
        earliest_time: str = "-24h",
        latest_time: str = "now",
        max_iterations: int = 3,
        improvement_threshold: float = 0.1,
        enable_validation: bool = True,
        focus_areas: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Execute iterative reflection-based analysis.
        
        Args:
            ctx: FastMCP context
            problem_description: Description of the Splunk issue to analyze
            earliest_time: Start time for analysis
            latest_time: End time for analysis
            max_iterations: Maximum number of reflection iterations
            improvement_threshold: Minimum improvement score to continue iterating
            enable_validation: Enable validation of findings
            focus_areas: Specific areas to focus reflection on
            
        Returns:
            Dict containing iterative analysis results and final synthesis
        """
        execution_start_time = time.time()
        logger.info("="*80)
        logger.info("STARTING REFLECTION AGENT EXECUTION")
        logger.info("="*80)
        
        try:
            logger.info(f"Problem: {problem_description[:200]}...")
            logger.info(f"Time range: {earliest_time} to {latest_time}")
            logger.info(f"Max iterations: {max_iterations}")
            logger.info(f"Improvement threshold: {improvement_threshold}")
            logger.info(f"Validation enabled: {enable_validation}")
            logger.info(f"Focus areas: {focus_areas}")
            
            # Set the context for tool calls
            if hasattr(self, '_set_context'):
                self._set_context(ctx)
                logger.debug("Context set for direct tool registry access")
            
            await ctx.info(f"🚀 Starting reflection-based analysis for: {problem_description[:100]}...")
            
            # Create reflection context
            logger.debug("Creating reflection context...")
            reflection_context = ReflectionContext(
                earliest_time=earliest_time,
                latest_time=latest_time,
                max_iterations=max_iterations,
                improvement_threshold=improvement_threshold,
                enable_validation=enable_validation,
                focus_areas=focus_areas or ["accuracy", "completeness", "actionability"]
            )
            logger.info(f"Reflection context created: {reflection_context}")
            
            # Execute iterative reflection workflow
            await ctx.info("🔄 Beginning iterative reflection workflow...")
            logger.info("Starting iterative reflection workflow...")
            
            iteration_results = []
            current_analysis = ""
            previous_score = 0.0
            
            for iteration in range(1, max_iterations + 1):
                logger.info(f"="*60)
                logger.info(f"STARTING REFLECTION ITERATION {iteration}/{max_iterations}")
                logger.info(f"="*60)
                
                iteration_start_time = time.time()
                
                await ctx.info(f"🔍 Iteration {iteration}: Conducting analysis...")
                logger.info(f"Starting iteration {iteration} analysis phase")
                
                # Phase 1: Analysis (initial or refined)
                analysis_result = await self._conduct_analysis(
                    ctx, problem_description, reflection_context, iteration, current_analysis
                )
                
                await ctx.info(f"🤔 Iteration {iteration}: Reflecting on analysis...")
                logger.info(f"Starting iteration {iteration} reflection phase")
                
                # Phase 2: Reflection
                reflection_result = await self._conduct_reflection(
                    ctx, analysis_result, reflection_context, iteration
                )
                
                # Phase 3: Validation (if enabled)
                validation_result = None
                if enable_validation:
                    await ctx.info(f"✅ Iteration {iteration}: Validating findings...")
                    logger.info(f"Starting iteration {iteration} validation phase")
                    
                    validation_result = await self._conduct_validation(
                        ctx, analysis_result, reflection_context, iteration
                    )
                
                iteration_execution_time = time.time() - iteration_start_time
                
                # Create iteration result
                iteration_result = IterationResult(
                    iteration_number=iteration,
                    phase=ReflectionPhase.REFINEMENT,
                    analysis_result=analysis_result,
                    reflection_insights=reflection_result["insights"],
                    improvement_score=reflection_result["score"],
                    validation_result=validation_result,
                    execution_time=iteration_execution_time,
                    identified_gaps=reflection_result.get("gaps", [])
                )
                
                iteration_results.append(iteration_result)
                
                logger.info(f"Iteration {iteration} completed in {iteration_execution_time:.2f} seconds")
                logger.info(f"Improvement score: {reflection_result['score']:.3f}")
                logger.info(f"Identified gaps: {len(reflection_result.get('gaps', []))}")
                
                # Check for convergence
                improvement = reflection_result["score"] - previous_score
                logger.info(f"Improvement from previous iteration: {improvement:.3f}")
                
                if iteration > 1 and improvement < improvement_threshold:
                    logger.info(f"Improvement threshold ({improvement_threshold}) not met. Stopping iterations.")
                    await ctx.info(f"📈 Convergence achieved after {iteration} iterations")
                    break
                
                # Update for next iteration
                current_analysis = analysis_result
                previous_score = reflection_result["score"]
                
                logger.info(f"Iteration {iteration} complete. Continuing to next iteration...")
            
            # Final synthesis
            await ctx.info("🎯 Creating final synthesis...")
            logger.info("Starting final synthesis phase")
            
            synthesis_start_time = time.time()
            final_synthesis = await self._create_final_synthesis(
                ctx, iteration_results, problem_description, reflection_context
            )
            synthesis_execution_time = time.time() - synthesis_start_time
            
            logger.info(f"Final synthesis completed in {synthesis_execution_time:.2f} seconds")
            
            total_execution_time = time.time() - execution_start_time
            
            # Compile final results
            final_result = {
                "status": "success",
                "problem_description": problem_description,
                "reflection_context": {
                    "earliest_time": earliest_time,
                    "latest_time": latest_time,
                    "max_iterations": max_iterations,
                    "improvement_threshold": improvement_threshold,
                    "enable_validation": enable_validation,
                    "focus_areas": reflection_context.focus_areas
                },
                "iteration_results": [
                    {
                        "iteration_number": result.iteration_number,
                        "improvement_score": result.improvement_score,
                        "execution_time": result.execution_time,
                        "identified_gaps": result.identified_gaps,
                        "analysis_preview": result.analysis_result[:300] + "..." if len(result.analysis_result) > 300 else result.analysis_result,
                        "reflection_preview": result.reflection_insights[:300] + "..." if len(result.reflection_insights) > 300 else result.reflection_insights,
                        "validation_enabled": result.validation_result is not None
                    }
                    for result in iteration_results
                ],
                "final_synthesis": final_synthesis,
                "execution_times": {
                    "total_execution_time": total_execution_time,
                    "synthesis_execution_time": synthesis_execution_time,
                    "average_iteration_time": sum(r.execution_time for r in iteration_results) / len(iteration_results) if iteration_results else 0
                },
                "performance_metrics": {
                    "iterations_completed": len(iteration_results),
                    "final_improvement_score": iteration_results[-1].improvement_score if iteration_results else 0.0,
                    "total_gaps_identified": sum(len(r.identified_gaps) for r in iteration_results),
                    "convergence_achieved": len(iteration_results) < max_iterations
                }
            }
            
            await ctx.info("✅ Reflection-based analysis completed")
            
            logger.info("="*80)
            logger.info("REFLECTION AGENT EXECUTION COMPLETED SUCCESSFULLY")
            logger.info(f"Total execution time: {total_execution_time:.2f} seconds")
            logger.info(f"Iterations completed: {len(iteration_results)}")
            logger.info(f"Final improvement score: {iteration_results[-1].improvement_score if iteration_results else 0.0:.3f}")
            logger.info("="*80)
            
            return final_result
            
        except Exception as e:
            execution_time = time.time() - execution_start_time
            error_msg = f"Reflection agent execution failed: {str(e)}"
            
            logger.error("="*80)
            logger.error("REFLECTION AGENT EXECUTION FAILED")
            logger.error(f"Error: {error_msg}")
            logger.error(f"Execution time before failure: {execution_time:.2f} seconds")
            logger.error("="*80)
            logger.error(f"Full error details:", exc_info=True)
            
            await ctx.error(error_msg)
            return {
                "status": "error",
                "error": error_msg,
                "error_type": "execution_error",
                "execution_time": execution_time
            }

    async def _conduct_analysis(
        self,
        ctx: Context,
        problem_description: str,
        reflection_context: ReflectionContext,
        iteration: int,
        previous_analysis: str
    ) -> str:
        """Conduct analysis for the current iteration."""
        
        logger.debug(f"[Iteration {iteration}] Starting analysis phase")
        
        try:
            if iteration == 1:
                # Initial analysis
                analysis_input = f"""
**Initial Splunk Analysis Request**

**Problem Description:**
{problem_description}

**Analysis Parameters:**
- Time Range: {reflection_context.earliest_time} to {reflection_context.latest_time}
- Focus Areas: {', '.join(reflection_context.focus_areas)}

Please conduct a comprehensive initial analysis of this Splunk issue:
1. Gather relevant data using available tools
2. Identify key symptoms and potential causes
3. Analyze system metrics and logs
4. Provide specific recommendations
5. Note any areas of uncertainty or need for additional investigation

This is the first iteration of a reflection-based analysis process.
Be thorough but acknowledge limitations and areas for improvement.
"""
                logger.debug(f"[Iteration {iteration}] Created initial analysis input")
            else:
                # Refined analysis based on previous iteration
                analysis_input = f"""
**Refined Splunk Analysis Request - Iteration {iteration}**

**Original Problem:**
{problem_description}

**Previous Analysis:**
{previous_analysis[:1000]}{'...' if len(previous_analysis) > 1000 else ''}

**Analysis Parameters:**
- Time Range: {reflection_context.earliest_time} to {reflection_context.latest_time}
- Focus Areas: {', '.join(reflection_context.focus_areas)}

Please refine and improve the analysis based on previous findings:
1. Address any gaps or weaknesses identified in reflection
2. Gather additional data to strengthen weak areas
3. Refine recommendations based on new insights
4. Improve the accuracy and completeness of the analysis
5. Focus on areas that need enhancement

This is iteration {iteration} of a reflection-based improvement process.
Build upon previous work while addressing identified shortcomings.
"""
                logger.debug(f"[Iteration {iteration}] Created refined analysis input")
            
            logger.debug(f"[Iteration {iteration}] Executing primary analyst...")
            
            # Execute the primary analyst
            result = await Runner.run(self.primary_analyst, input=analysis_input)
            
            logger.info(f"[Iteration {iteration}] Analysis phase completed successfully")
            logger.debug(f"[Iteration {iteration}] Analysis result length: {len(result.final_output) if result.final_output else 0} characters")
            
            return result.final_output or "No analysis result"
            
        except Exception as e:
            error_msg = f"Analysis phase failed in iteration {iteration}: {str(e)}"
            logger.error(f"[Iteration {iteration}] {error_msg}", exc_info=True)
            return f"Analysis error: {error_msg}"

    async def _conduct_reflection(
        self,
        ctx: Context,
        analysis_result: str,
        reflection_context: ReflectionContext,
        iteration: int
    ) -> Dict[str, Any]:
        """Conduct reflection on the current analysis."""
        
        logger.debug(f"[Iteration {iteration}] Starting reflection phase")
        
        try:
            reflection_input = f"""
**Analysis Reflection Request - Iteration {iteration}**

**Analysis to Evaluate:**
{analysis_result}

**Evaluation Criteria:**
- Accuracy: Is the analysis supported by solid evidence?
- Completeness: Are all relevant aspects covered?
- Actionability: Are recommendations specific and implementable?
- Logic: Is the reasoning sound and well-structured?
- Evidence: Is the analysis backed by appropriate data?

**Focus Areas for This Evaluation:**
{', '.join(reflection_context.focus_areas)}

Please provide critical reflection on this analysis:
1. **Strengths**: What aspects are well-done and reliable?
2. **Weaknesses**: What areas need improvement or additional work?
3. **Gaps**: What important aspects are missing or inadequately covered?
4. **Recommendations**: Specific suggestions for improvement
5. **Quality Score**: Rate overall quality from 0.0 to 1.0

Be constructive but critical. Identify specific areas for enhancement.
"""
            
            logger.debug(f"[Iteration {iteration}] Created reflection input")
            logger.debug(f"[Iteration {iteration}] Executing reflection critic...")
            
            # Execute the reflection critic
            result = await Runner.run(self.reflection_critic, input=reflection_input)
            
            # Parse the reflection result to extract score and insights
            reflection_output = result.final_output or "No reflection result"
            
            # Extract quality score (simple pattern matching)
            score_match = None
            import re
            score_patterns = [
                r'score[:\s]*([0-9]*\.?[0-9]+)',
                r'quality[:\s]*([0-9]*\.?[0-9]+)',
                r'rating[:\s]*([0-9]*\.?[0-9]+)'
            ]
            
            for pattern in score_patterns:
                match = re.search(pattern, reflection_output.lower())
                if match:
                    try:
                        score_match = float(match.group(1))
                        if 0.0 <= score_match <= 1.0:
                            break
                    except ValueError:
                        continue
            
            improvement_score = score_match if score_match is not None else 0.5
            
            # Extract gaps (simple pattern matching)
            gaps = []
            if "gaps:" in reflection_output.lower():
                gaps_section = reflection_output.lower().split("gaps:")[1].split("\n\n")[0]
                gaps = [line.strip("- ").strip() for line in gaps_section.split("\n") if line.strip().startswith("-")]
            
            logger.info(f"[Iteration {iteration}] Reflection phase completed successfully")
            logger.debug(f"[Iteration {iteration}] Extracted improvement score: {improvement_score:.3f}")
            logger.debug(f"[Iteration {iteration}] Identified {len(gaps)} gaps")
            
            return {
                "insights": reflection_output,
                "score": improvement_score,
                "gaps": gaps
            }
            
        except Exception as e:
            error_msg = f"Reflection phase failed in iteration {iteration}: {str(e)}"
            logger.error(f"[Iteration {iteration}] {error_msg}", exc_info=True)
            return {
                "insights": f"Reflection error: {error_msg}",
                "score": 0.0,
                "gaps": []
            }

    async def _conduct_validation(
        self,
        ctx: Context,
        analysis_result: str,
        reflection_context: ReflectionContext,
        iteration: int
    ) -> str:
        """Conduct validation of the current analysis."""
        
        logger.debug(f"[Iteration {iteration}] Starting validation phase")
        
        try:
            validation_input = f"""
**Analysis Validation Request - Iteration {iteration}**

**Analysis to Validate:**
{analysis_result[:1500]}{'...' if len(analysis_result) > 1500 else ''}

**Validation Tasks:**
1. Verify key findings using additional Splunk searches
2. Cross-check claims against supporting data
3. Validate that recommendations address identified issues
4. Assess confidence levels for different findings
5. Identify any contradictions or inconsistencies

**Time Range for Validation:**
{reflection_context.earliest_time} to {reflection_context.latest_time}

Use available tools to independently verify the analysis.
Provide validation results with confidence ratings.
Highlight any findings that cannot be verified.
"""
            
            logger.debug(f"[Iteration {iteration}] Created validation input")
            logger.debug(f"[Iteration {iteration}] Executing validation agent...")
            
            # Execute the validation agent
            result = await Runner.run(self.validation_agent, input=validation_input)
            
            logger.info(f"[Iteration {iteration}] Validation phase completed successfully")
            logger.debug(f"[Iteration {iteration}] Validation result length: {len(result.final_output) if result.final_output else 0} characters")
            
            return result.final_output or "No validation result"
            
        except Exception as e:
            error_msg = f"Validation phase failed in iteration {iteration}: {str(e)}"
            logger.error(f"[Iteration {iteration}] {error_msg}", exc_info=True)
            return f"Validation error: {error_msg}"

    async def _create_final_synthesis(
        self,
        ctx: Context,
        iteration_results: List[IterationResult],
        problem_description: str,
        reflection_context: ReflectionContext
    ) -> str:
        """Create final synthesis from all iteration results."""
        
        logger.info("Starting final synthesis phase")
        logger.debug(f"Synthesizing results from {len(iteration_results)} iterations")
        
        try:
            # Prepare synthesis input
            iterations_summary = []
            for result in iteration_results:
                iterations_summary.append(f"""
**Iteration {result.iteration_number}**
- Improvement Score: {result.improvement_score:.3f}
- Execution Time: {result.execution_time:.2f}s
- Identified Gaps: {len(result.identified_gaps)}

Analysis Summary:
{result.analysis_result[:500]}{'...' if len(result.analysis_result) > 500 else ''}

Reflection Insights:
{result.reflection_insights[:300]}{'...' if len(result.reflection_insights) > 300 else ''}
""")
            
            synthesis_input = f"""
**Final Analysis Synthesis**

**Original Problem:**
{problem_description}

**Reflection Process Summary:**
- Total Iterations: {len(iteration_results)}
- Final Improvement Score: {iteration_results[-1].improvement_score if iteration_results else 0.0:.3f}
- Focus Areas: {', '.join(reflection_context.focus_areas)}

**Iteration Results:**
{''.join(iterations_summary)}

**Synthesis Requirements:**
1. Consolidate the best insights from all iterations
2. Resolve any contradictions or inconsistencies
3. Create a comprehensive, refined final analysis
4. Prioritize recommendations by impact and feasibility
5. Include confidence levels and next steps

Create a polished, professional analysis that represents the collective insights.
Structure for maximum clarity and actionability.
"""
            
            logger.debug(f"Created synthesis input, length: {len(synthesis_input)} characters")
            logger.debug("Executing synthesis agent...")
            
            # Execute the synthesis agent
            result = await Runner.run(self.synthesis_agent, input=synthesis_input)
            
            logger.info("Final synthesis completed successfully")
            logger.debug(f"Synthesis result length: {len(result.final_output) if result.final_output else 0} characters")
            
            return result.final_output or "No synthesis result"
            
        except Exception as e:
            error_msg = f"Final synthesis failed: {str(e)}"
            logger.error(f"Final synthesis error: {error_msg}", exc_info=True)
            return f"Synthesis error: {error_msg}" 