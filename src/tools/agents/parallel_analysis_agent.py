"""
Parallel Analysis Agent for Complex Splunk Troubleshooting.

This module implements the parallel execution pattern from the OpenAI agents SDK
for conducting simultaneous multi-component analysis of Splunk systems.
"""

import os
import asyncio
import logging
import time
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor

from fastmcp import Context
from openai import OpenAI

from ...core.base import BaseTool, ToolMetadata

logger = logging.getLogger(__name__)

# Only import OpenAI agents if available
try:
    from agents import Agent, Runner, function_tool
    from agents.extensions.handoff_prompt import prompt_with_handoff_instructions
    OPENAI_AGENTS_AVAILABLE = True
    logger.info("OpenAI agents SDK loaded successfully for parallel analysis")
except ImportError:
    OPENAI_AGENTS_AVAILABLE = False
    logger.warning("OpenAI agents SDK not available for parallel analysis. Install with: pip install openai-agents")


@dataclass
class ParallelAnalysisContext:
    """Context for coordinating parallel analysis workflows."""
    earliest_time: str = "-24h"
    latest_time: str = "now"
    focus_components: List[str] = None
    analysis_depth: str = "standard"
    enable_cross_validation: bool = True
    parallel_execution_limit: int = 3
    
    def __post_init__(self):
        if self.focus_components is None:
            self.focus_components = ["inputs", "indexing", "search_performance"]


@dataclass
class ComponentAnalysisResult:
    """Result from a single component analysis."""
    component: str
    agent_name: str
    analysis_result: str
    execution_time: float
    status: str
    error_message: Optional[str] = None


class ParallelAnalysisAgentTool(BaseTool):
    """
    OpenAI Agents-based parallel analysis system for complex Splunk troubleshooting.
    
    This tool implements parallel execution patterns where multiple specialist agents
    analyze different components simultaneously, then correlate findings for 
    comprehensive system-wide insights.
    """

    METADATA = ToolMetadata(
        name="execute_parallel_analysis_agent",
        description="Execute parallel multi-component analysis using OpenAI agents for comprehensive Splunk troubleshooting",
        category="agents"
    )

    def __init__(self, name: str, category: str):
        super().__init__(name, category)
        
        logger.info(f"Initializing ParallelAnalysisAgentTool: {name}")
        
        if not OPENAI_AGENTS_AVAILABLE:
            logger.error("OpenAI agents SDK is required for parallel analysis")
            raise ImportError(
                "OpenAI agents SDK is required for this tool. "
                "Install with: pip install openai-agents"
            )
        
        logger.debug("Loading OpenAI configuration for parallel analysis...")
        self.config = self._load_config()
        logger.info(f"OpenAI config loaded - Model: {self.config.model}, Temperature: {self.config.temperature}")
        
        self.client = OpenAI(api_key=self.config.api_key)
        
        # Initialize the parallel agent system
        logger.info("Setting up parallel agent system...")
        self._setup_parallel_agents()
        logger.info("ParallelAnalysisAgentTool initialization complete")

    def _load_config(self):
        """Load OpenAI configuration from environment variables."""
        logger.debug("Loading OpenAI configuration from environment for parallel analysis")
        
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            logger.error("OPENAI_API_KEY environment variable not found")
            raise ValueError(
                "OPENAI_API_KEY environment variable is required. "
                "Please set it in your .env file or environment."
            )
        
        logger.debug("API key found, creating configuration for parallel analysis")
        
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
        
        logger.info(f"Parallel analysis configuration loaded: model={config.model}, temp={config.temperature}, max_tokens={config.max_tokens}")
        return config

    def _setup_parallel_agents(self):
        """Set up the parallel analysis agent system."""
        
        logger.info("Setting up parallel analysis agent system...")
        
        # Create Splunk tool functions for agents to use
        logger.debug("Creating Splunk tool functions for parallel agents...")
        self._create_splunk_tools()
        logger.info(f"Created {len(self.splunk_tools)} Splunk tool functions for parallel execution")
        
        # Create component-specific analysis agents
        logger.debug("Creating component analysis agents...")
        
        logger.debug("Creating inputs analysis agent...")
        self.inputs_analyzer = self._create_inputs_analyzer()
        logger.info("Inputs analysis agent created successfully")
        
        logger.debug("Creating indexing analysis agent...")
        self.indexing_analyzer = self._create_indexing_analyzer()
        logger.info("Indexing analysis agent created successfully")
        
        logger.debug("Creating search performance analysis agent...")
        self.search_analyzer = self._create_search_analyzer()
        logger.info("Search performance analysis agent created successfully")
        
        logger.debug("Creating system health analysis agent...")
        self.system_analyzer = self._create_system_analyzer()
        logger.info("System health analysis agent created successfully")
        
        # Create the correlation agent
        logger.debug("Creating correlation analysis agent...")
        self.correlation_agent = self._create_correlation_agent()
        logger.info("Correlation analysis agent created successfully")
        
        # Map components to agents
        self.component_agents = {
            "inputs": self.inputs_analyzer,
            "indexing": self.indexing_analyzer,
            "search_performance": self.search_analyzer,
            "system_health": self.system_analyzer
        }
        
        logger.info(f"Parallel agent system setup complete - {len(self.component_agents)} component agents + correlation agent ready")

    def _create_splunk_tools(self):
        """Create function tools that wrap MCP server tools for parallel execution."""
        
        logger.debug("Setting up direct tool registry access for parallel execution...")
        
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
        async def run_parallel_search(query: str, earliest_time: str = "-24h", latest_time: str = "now", component: str = "unknown") -> str:
            """Execute a Splunk search query via direct tool registry optimized for parallel execution."""
            logger.debug(f"[{component}] Executing parallel search: {query[:100]}... (time: {earliest_time} to {latest_time})")
            
            try:
                # Get the tool directly from registry
                tool = tool_registry.get_tool("run_oneshot_search")
                if not tool:
                    raise RuntimeError("run_oneshot_search tool not found in registry")
                
                logger.debug(f"[{component}] Calling tool registry: run_oneshot_search")
                
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
                
                logger.info(f"[{component}] Direct search completed successfully, result length: {len(str(result))}")
                return str(result)
                
            except Exception as e:
                logger.error(f"[{component}] Error executing direct search: {e}", exc_info=True)
                return f"[{component}] Error executing direct search: {str(e)}"

        @function_tool
        async def get_component_metrics(component: str, earliest_time: str = "-24h", latest_time: str = "now") -> str:
            """Get specific metrics for a component via direct tool registry with parallel-safe execution."""
            logger.debug(f"[{component}] Getting component metrics via direct registry for time range: {earliest_time} to {latest_time}")
            
            try:
                # Component-specific metric queries
                metric_queries = {
                    "inputs": 'index=_internal source=*metrics.log* group=per_host_thruput | stats avg(kb) as avg_kb by host',
                    "indexing": 'index=_internal source=*metrics.log* group=per_index_thruput | stats avg(kb) as avg_kb by series',
                    "search_performance": 'index=_internal source=*metrics.log* group=search_concurrency | stats avg(active_hist_searches) as avg_searches',
                    "system_health": 'index=_internal source=*metrics.log* group=resource_usage | stats avg(cpu_seconds) as avg_cpu'
                }
                
                query = metric_queries.get(component, f'index=_internal source=*metrics.log* | head 10')
                logger.debug(f"[{component}] Using metric query: {query}")
                
                return await run_parallel_search(query, earliest_time, latest_time, component)
                
            except Exception as e:
                logger.error(f"[{component}] Error getting component metrics via direct registry: {e}", exc_info=True)
                return f"[{component}] Error getting component metrics via direct registry: {str(e)}"

        @function_tool
        async def analyze_component_health(component: str, earliest_time: str = "-24h", latest_time: str = "now") -> str:
            """Analyze health indicators for a specific component via direct tool registry."""
            logger.debug(f"[{component}] Analyzing component health via direct registry for time range: {earliest_time} to {latest_time}")
            
            try:
                # Component-specific health queries
                health_queries = {
                    "inputs": 'index=_internal source=*splunkd.log* component=AggregatorMiningProcessor OR component=TcpInputProc | stats count by component, log_level',
                    "indexing": 'index=_internal source=*splunkd.log* component=IndexProcessor OR component=BucketMover | stats count by component, log_level',
                    "search_performance": 'index=_internal source=*scheduler.log* | stats count by status',
                    "system_health": 'index=_internal source=*splunkd.log* log_level=ERROR OR log_level=WARN | stats count by log_level, component'
                }
                
                query = health_queries.get(component, f'index=_internal source=*splunkd.log* component=*{component}* | head 10')
                logger.debug(f"[{component}] Using health query: {query}")
                
                return await run_parallel_search(query, earliest_time, latest_time, component)
                
            except Exception as e:
                logger.error(f"[{component}] Error analyzing component health via direct registry: {e}", exc_info=True)
                return f"[{component}] Error analyzing component health via direct registry: {str(e)}"

        @function_tool
        async def list_splunk_indexes(component: str = "metadata") -> str:
            """List available Splunk indexes via direct tool registry."""
            logger.debug(f"[{component}] Listing Splunk indexes via direct registry...")
            
            try:
                # Get the tool directly from registry
                tool = tool_registry.get_tool("list_indexes")
                if not tool:
                    raise RuntimeError("list_indexes tool not found in registry")
                
                logger.debug(f"[{component}] Calling tool registry: list_indexes")
                
                # Get current context
                ctx = get_context()
                
                result = await tool.execute(ctx)
                
                logger.info(f"[{component}] Direct indexes listed successfully, result length: {len(str(result))}")
                return str(result)
                
            except Exception as e:
                logger.error(f"[{component}] Error listing indexes via direct registry: {e}", exc_info=True)
                return f"[{component}] Error listing indexes via direct registry: {str(e)}"

        @function_tool
        async def get_splunk_health_status(component: str = "health") -> str:
            """Check Splunk server health via direct tool registry."""
            logger.debug(f"[{component}] Checking Splunk health via direct registry...")
            
            try:
                # Get the tool directly from registry
                tool = tool_registry.get_tool("get_splunk_health")
                if not tool:
                    raise RuntimeError("get_splunk_health tool not found in registry")
                
                logger.debug(f"[{component}] Calling tool registry: get_splunk_health")
                
                # Get current context
                ctx = get_context()
                
                result = await tool.execute(ctx)
                
                logger.info(f"[{component}] Direct health check completed successfully, result length: {len(str(result))}")
                return str(result)
                
            except Exception as e:
                logger.error(f"[{component}] Error checking health via direct registry: {e}", exc_info=True)
                return f"[{component}] Error checking health via direct registry: {str(e)}"

        # Store tools for use by agents
        self.splunk_tools = [
            run_parallel_search, 
            get_component_metrics, 
            analyze_component_health,
            list_splunk_indexes,
            get_splunk_health_status
        ]
        logger.info(f"Created {len(self.splunk_tools)} direct registry tool wrappers for parallel execution")

    def _create_inputs_analyzer(self) -> Agent:
        """Create the inputs analysis agent for parallel execution."""
        logger.debug("Creating inputs analysis agent for parallel execution...")
        
        agent = Agent(
            name="Parallel Inputs Analyzer",
            instructions="""
You are a Splunk inputs analysis specialist optimized for parallel execution.

Focus on rapid analysis of:
- Data ingestion rates and patterns
- Forwarder connectivity and health
- Input configuration effectiveness
- Source/sourcetype distribution

Execute efficiently in parallel with other component analyzers.
Provide concise, actionable findings that can be correlated with other components.
Use the available tools to gather targeted metrics and health indicators.
            """,
            model=self.config.model,
            tools=self.splunk_tools
        )
        
        logger.debug("Inputs analysis agent created with parallel-optimized configuration")
        return agent

    def _create_indexing_analyzer(self) -> Agent:
        """Create the indexing analysis agent for parallel execution."""
        logger.debug("Creating indexing analysis agent for parallel execution...")
        
        agent = Agent(
            name="Parallel Indexing Analyzer",
            instructions="""
You are a Splunk indexing analysis specialist optimized for parallel execution.

Focus on rapid analysis of:
- Indexing throughput and delays
- Bucket management efficiency
- Storage utilization patterns
- Parsing and transformation performance

Execute efficiently in parallel with other component analyzers.
Provide concise, actionable findings that can be correlated with other components.
Use the available tools to gather targeted metrics and health indicators.
            """,
            model=self.config.model,
            tools=self.splunk_tools
        )
        
        logger.debug("Indexing analysis agent created with parallel-optimized configuration")
        return agent

    def _create_search_analyzer(self) -> Agent:
        """Create the search performance analysis agent for parallel execution."""
        logger.debug("Creating search performance analysis agent for parallel execution...")
        
        agent = Agent(
            name="Parallel Search Analyzer",
            instructions="""
You are a Splunk search performance analysis specialist optimized for parallel execution.

Focus on rapid analysis of:
- Search concurrency and scheduling
- Query performance patterns
- Resource utilization during searches
- Search head capacity and load

Execute efficiently in parallel with other component analyzers.
Provide concise, actionable findings that can be correlated with other components.
Use the available tools to gather targeted metrics and health indicators.
            """,
            model=self.config.model,
            tools=self.splunk_tools
        )
        
        logger.debug("Search performance analysis agent created with parallel-optimized configuration")
        return agent

    def _create_system_analyzer(self) -> Agent:
        """Create the system health analysis agent for parallel execution."""
        logger.debug("Creating system health analysis agent for parallel execution...")
        
        agent = Agent(
            name="Parallel System Analyzer",
            instructions="""
You are a Splunk system health analysis specialist optimized for parallel execution.

Focus on rapid analysis of:
- Overall system resource utilization
- Error patterns and log anomalies
- License usage and compliance
- General system stability indicators

Execute efficiently in parallel with other component analyzers.
Provide concise, actionable findings that can be correlated with other components.
Use the available tools to gather targeted metrics and health indicators.
            """,
            model=self.config.model,
            tools=self.splunk_tools
        )
        
        logger.debug("System health analysis agent created with parallel-optimized configuration")
        return agent

    def _create_correlation_agent(self) -> Agent:
        """Create the correlation agent that synthesizes parallel analysis results."""
        logger.debug("Creating correlation agent for parallel analysis synthesis...")
        
        agent = Agent(
            name="Parallel Analysis Correlator",
            instructions="""
You are a Splunk system correlation specialist that synthesizes findings from parallel component analyses.

Your role:
1. Receive analysis results from multiple component specialists
2. Identify cross-component correlations and dependencies
3. Synthesize findings into comprehensive insights
4. Prioritize issues based on system-wide impact
5. Provide unified recommendations

Focus on:
- Correlation patterns between components
- Root cause identification across systems
- Impact assessment and prioritization
- Comprehensive remediation strategies
- System-wide optimization opportunities

Provide a structured analysis that connects the dots between component findings.
            """,
            model=self.config.model
        )
        
        logger.debug("Correlation agent created for parallel analysis synthesis")
        return agent

    async def execute(
        self,
        ctx: Context,
        problem_description: str,
        earliest_time: str = "-24h",
        latest_time: str = "now",
        focus_components: Optional[List[str]] = None,
        analysis_depth: str = "standard",
        enable_cross_validation: bool = True,
        parallel_execution_limit: int = 3
    ) -> Dict[str, Any]:
        """
        Execute parallel multi-component analysis.
        
        Args:
            ctx: FastMCP context
            problem_description: Description of the Splunk issue to analyze
            earliest_time: Start time for analysis
            latest_time: End time for analysis
            focus_components: List of components to analyze (optional)
            analysis_depth: Depth of analysis to perform
            enable_cross_validation: Enable cross-component validation
            parallel_execution_limit: Maximum parallel executions
            
        Returns:
            Dict containing parallel analysis results and correlations
        """
        execution_start_time = time.time()
        logger.info("="*80)
        logger.info("STARTING PARALLEL ANALYSIS AGENT EXECUTION")
        logger.info("="*80)
        
        try:
            logger.info(f"Problem: {problem_description[:200]}...")
            logger.info(f"Time range: {earliest_time} to {latest_time}")
            logger.info(f"Focus components: {focus_components}")
            logger.info(f"Analysis depth: {analysis_depth}")
            logger.info(f"Cross-validation: {enable_cross_validation}")
            logger.info(f"Parallel limit: {parallel_execution_limit}")
            
            # Set the context for tool calls
            if hasattr(self, '_set_context'):
                self._set_context(ctx)
                logger.debug("Context set for direct tool registry access")
            
            await ctx.info(f"🚀 Starting parallel analysis for: {problem_description[:100]}...")
            
            # Create analysis context
            logger.debug("Creating parallel analysis context...")
            analysis_context = ParallelAnalysisContext(
                earliest_time=earliest_time,
                latest_time=latest_time,
                focus_components=focus_components or ["inputs", "indexing", "search_performance", "system_health"],
                analysis_depth=analysis_depth,
                enable_cross_validation=enable_cross_validation,
                parallel_execution_limit=parallel_execution_limit
            )
            logger.info(f"Analysis context created: {analysis_context}")
            
            await ctx.info("🔄 Executing parallel component analysis...")
            logger.info("Starting parallel component analysis execution...")
            
            # Execute parallel component analysis
            parallel_start_time = time.time()
            component_results = await self._execute_parallel_analysis(
                ctx, problem_description, analysis_context
            )
            parallel_execution_time = time.time() - parallel_start_time
            
            logger.info(f"Parallel analysis completed in {parallel_execution_time:.2f} seconds")
            logger.info(f"Component analysis results: {len(component_results)} components analyzed")
            
            # Log individual component results
            for result in component_results:
                logger.info(f"- {result.component}: {result.status} (agent: {result.agent_name}, time: {result.execution_time:.2f}s)")
                if result.error_message:
                    logger.warning(f"  Error: {result.error_message}")
            
            await ctx.info("🔗 Correlating findings across components...")
            logger.info("Starting cross-component correlation analysis...")
            
            # Correlate findings
            correlation_start_time = time.time()
            correlation_result = await self._correlate_findings(
                ctx, component_results, problem_description, analysis_context
            )
            correlation_execution_time = time.time() - correlation_start_time
            
            logger.info(f"Correlation analysis completed in {correlation_execution_time:.2f} seconds")
            
            total_execution_time = time.time() - execution_start_time
            
            # Compile final results
            final_result = {
                "status": "success",
                "problem_description": problem_description,
                "analysis_context": {
                    "earliest_time": earliest_time,
                    "latest_time": latest_time,
                    "focus_components": analysis_context.focus_components,
                    "analysis_depth": analysis_depth,
                    "enable_cross_validation": enable_cross_validation,
                    "parallel_execution_limit": parallel_execution_limit
                },
                "component_results": [
                    {
                        "component": result.component,
                        "agent_name": result.agent_name,
                        "status": result.status,
                        "execution_time": result.execution_time,
                        "analysis_result": result.analysis_result[:500] + "..." if len(result.analysis_result) > 500 else result.analysis_result,
                        "error_message": result.error_message
                    }
                    for result in component_results
                ],
                "correlation_analysis": correlation_result,
                "execution_times": {
                    "total_execution_time": total_execution_time,
                    "parallel_execution_time": parallel_execution_time,
                    "correlation_execution_time": correlation_execution_time
                },
                "performance_metrics": {
                    "components_analyzed": len(component_results),
                    "successful_analyses": len([r for r in component_results if r.status == "success"]),
                    "failed_analyses": len([r for r in component_results if r.status == "error"]),
                    "average_component_time": sum(r.execution_time for r in component_results) / len(component_results) if component_results else 0
                }
            }
            
            await ctx.info("✅ Parallel analysis execution completed")
            
            logger.info("="*80)
            logger.info("PARALLEL ANALYSIS EXECUTION COMPLETED SUCCESSFULLY")
            logger.info(f"Total execution time: {total_execution_time:.2f} seconds")
            logger.info(f"Components analyzed: {len(component_results)}")
            logger.info(f"Success rate: {len([r for r in component_results if r.status == 'success'])}/{len(component_results)}")
            logger.info("="*80)
            
            return final_result
            
        except Exception as e:
            execution_time = time.time() - execution_start_time
            error_msg = f"Parallel analysis execution failed: {str(e)}"
            
            logger.error("="*80)
            logger.error("PARALLEL ANALYSIS EXECUTION FAILED")
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

    async def _execute_parallel_analysis(
        self,
        ctx: Context,
        problem_description: str,
        analysis_context: ParallelAnalysisContext
    ) -> List[ComponentAnalysisResult]:
        """Execute parallel analysis across multiple components."""
        
        logger.info(f"Executing parallel analysis for {len(analysis_context.focus_components)} components")
        logger.debug(f"Components to analyze: {analysis_context.focus_components}")
        
        # Create analysis tasks
        analysis_tasks = []
        
        for component in analysis_context.focus_components:
            if component in self.component_agents:
                logger.debug(f"Creating analysis task for component: {component}")
                task = self._analyze_component(
                    component, 
                    self.component_agents[component],
                    problem_description,
                    analysis_context
                )
                analysis_tasks.append(task)
            else:
                logger.warning(f"No agent available for component: {component}")
        
        logger.info(f"Created {len(analysis_tasks)} parallel analysis tasks")
        
        # Execute tasks with limited concurrency
        logger.info(f"Executing tasks with concurrency limit: {analysis_context.parallel_execution_limit}")
        
        semaphore = asyncio.Semaphore(analysis_context.parallel_execution_limit)
        
        async def limited_task(task):
            async with semaphore:
                return await task
        
        # Execute all tasks in parallel with concurrency control
        parallel_start = time.time()
        logger.debug("Starting parallel task execution...")
        
        results = await asyncio.gather(
            *[limited_task(task) for task in analysis_tasks],
            return_exceptions=True
        )
        
        parallel_duration = time.time() - parallel_start
        logger.info(f"Parallel execution completed in {parallel_duration:.2f} seconds")
        
        # Process results
        component_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                component = analysis_context.focus_components[i] if i < len(analysis_context.focus_components) else f"component_{i}"
                logger.error(f"Component {component} analysis failed with exception: {result}")
                component_results.append(ComponentAnalysisResult(
                    component=component,
                    agent_name="Unknown",
                    analysis_result="",
                    execution_time=0.0,
                    status="error",
                    error_message=str(result)
                ))
            else:
                component_results.append(result)
        
        logger.info(f"Processed {len(component_results)} component analysis results")
        return component_results

    async def _analyze_component(
        self,
        component: str,
        agent: Agent,
        problem_description: str,
        analysis_context: ParallelAnalysisContext
    ) -> ComponentAnalysisResult:
        """Analyze a single component using its specialist agent."""
        
        component_start_time = time.time()
        logger.debug(f"[{component}] Starting component analysis with agent: {agent.name}")
        
        try:
            # Create component-specific input
            component_input = f"""
**Component Analysis Request: {component.upper()}**

**Problem Description:**
{problem_description}

**Analysis Parameters:**
- Time Range: {analysis_context.earliest_time} to {analysis_context.latest_time}
- Analysis Depth: {analysis_context.analysis_depth}
- Component Focus: {component}

Please perform focused analysis of the {component} component and provide:
1. Current status and health indicators
2. Performance metrics and trends
3. Identified issues or anomalies
4. Component-specific recommendations

Keep analysis concise for parallel execution and correlation with other components.
"""
            
            logger.debug(f"[{component}] Created component input, length: {len(component_input)} characters")
            logger.debug(f"[{component}] Executing agent analysis...")
            
            # Execute the agent
            result = await Runner.run(agent, input=component_input)
            
            execution_time = time.time() - component_start_time
            
            logger.info(f"[{component}] Analysis completed successfully in {execution_time:.2f} seconds")
            logger.debug(f"[{component}] Result length: {len(result.final_output) if result.final_output else 0} characters")
            
            return ComponentAnalysisResult(
                component=component,
                agent_name=agent.name,
                analysis_result=result.final_output or "No analysis result",
                execution_time=execution_time,
                status="success"
            )
            
        except Exception as e:
            execution_time = time.time() - component_start_time
            error_msg = f"Component {component} analysis failed: {str(e)}"
            
            logger.error(f"[{component}] Analysis failed after {execution_time:.2f} seconds: {error_msg}")
            logger.error(f"[{component}] Full error details:", exc_info=True)
            
            return ComponentAnalysisResult(
                component=component,
                agent_name=agent.name,
                analysis_result="",
                execution_time=execution_time,
                status="error",
                error_message=error_msg
            )

    async def _correlate_findings(
        self,
        ctx: Context,
        component_results: List[ComponentAnalysisResult],
        problem_description: str,
        analysis_context: ParallelAnalysisContext
    ) -> str:
        """Correlate findings from parallel component analyses."""
        
        logger.info("Starting cross-component correlation analysis")
        logger.debug(f"Correlating findings from {len(component_results)} components")
        
        try:
            # Prepare correlation input
            successful_results = [r for r in component_results if r.status == "success"]
            logger.info(f"Correlating {len(successful_results)} successful component analyses")
            
            correlation_input = f"""
**Cross-Component Correlation Analysis**

**Original Problem:**
{problem_description}

**Component Analysis Results:**
"""
            
            for result in successful_results:
                correlation_input += f"""

### {result.component.upper()} Analysis (by {result.agent_name})
**Status:** {result.status}
**Execution Time:** {result.execution_time:.2f}s
**Findings:**
{result.analysis_result[:1000]}{'...' if len(result.analysis_result) > 1000 else ''}
"""
            
            if len(component_results) > len(successful_results):
                failed_components = [r.component for r in component_results if r.status == "error"]
                correlation_input += f"""

**Failed Analyses:** {', '.join(failed_components)}
Note: Consider the impact of missing data from failed component analyses.
"""
            
            correlation_input += f"""

**Correlation Instructions:**
1. Identify patterns and correlations across component findings
2. Determine root causes that may affect multiple components
3. Assess system-wide impact and priorities
4. Provide unified recommendations
5. Suggest follow-up actions

Focus on actionable insights that address the original problem comprehensively.
"""
            
            logger.debug(f"Created correlation input, length: {len(correlation_input)} characters")
            logger.debug("Executing correlation agent...")
            
            # Execute correlation analysis
            correlation_result = await Runner.run(
                self.correlation_agent,
                input=correlation_input
            )
            
            logger.info("Correlation analysis completed successfully")
            logger.debug(f"Correlation result length: {len(correlation_result.final_output) if correlation_result.final_output else 0} characters")
            
            return correlation_result.final_output or "No correlation analysis result"
            
        except Exception as e:
            error_msg = f"Correlation analysis failed: {str(e)}"
            logger.error(f"Correlation analysis error: {error_msg}", exc_info=True)
            return f"Correlation analysis failed: {error_msg}" 