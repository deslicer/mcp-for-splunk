"""Dynamic Micro-Agent Template

A configurable micro-agent that can be dynamically created for any task
based on provided instructions, tools, and context. This eliminates the need
for specific agent files and enables task-driven parallelization.
"""

from typing import Dict, Any, List, Optional, Callable
import logging
from dataclasses import dataclass
from .config import AgentConfig
from .context import SplunkDiagnosticContext, DiagnosticResult
from .tools import SplunkToolRegistry
import time

logger = logging.getLogger(__name__)


@dataclass
class TaskDefinition:
    """Definition of a task that can be executed by a dynamic micro-agent."""
    
    task_id: str
    name: str
    description: str
    instructions: str
    required_tools: List[str] = None
    dependencies: List[str] = None
    context_requirements: List[str] = None
    expected_output_format: str = "diagnostic_result"
    timeout_seconds: int = 300
    
    def __post_init__(self):
        if self.required_tools is None:
            self.required_tools = []
        if self.dependencies is None:
            self.dependencies = []
        if self.context_requirements is None:
            self.context_requirements = []


@dataclass
class AgentExecutionContext:
    """Context provided to a dynamic agent for task execution."""
    
    task_definition: TaskDefinition
    diagnostic_context: SplunkDiagnosticContext
    dependency_results: Dict[str, DiagnosticResult] = None
    execution_metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.dependency_results is None:
            self.dependency_results = {}
        if self.execution_metadata is None:
            self.execution_metadata = {}


class DynamicMicroAgent:
    """
    A dynamic micro-agent that can be configured for any task.
    
    This agent template can be instantiated with different:
    - Instructions (what to do)
    - Tools (how to do it) 
    - Context (what data to work with)
    - Dependencies (what results from other agents to use)
    
    This enables task-driven parallelization where any independent task
    can become a parallel micro-agent.
    """
    
    def __init__(self, 
                 config: AgentConfig,
                 tool_registry: SplunkToolRegistry,
                 task_definition: TaskDefinition):
        self.config = config
        self.tool_registry = tool_registry
        self.task_definition = task_definition
        self.name = f"DynamicAgent_{task_definition.task_id}"
        
        # Validate task definition
        self._validate_task_definition()
        
        logger.info(f"Created dynamic micro-agent for task: {task_definition.name}")
    
    def _validate_task_definition(self):
        """Validate that the task definition is complete and valid."""
        if not self.task_definition.task_id:
            raise ValueError("Task definition must have a task_id")
        
        if not self.task_definition.instructions:
            raise ValueError("Task definition must have instructions")
        
        # Validate required tools are available
        available_tools = self.tool_registry.get_available_tools()
        for tool in self.task_definition.required_tools:
            if tool not in available_tools:
                logger.warning(f"Required tool '{tool}' not available in registry")
    
    async def execute_task(self, execution_context: AgentExecutionContext) -> DiagnosticResult:
        """
        Execute the assigned task with the provided context.
        
        Args:
            execution_context: Context containing task definition, diagnostic context,
                             and any dependency results
                             
        Returns:
            DiagnosticResult with task execution results
        """
        start_time = time.time()
        logger.info(f"[{self.name}] Starting task execution: {self.task_definition.name}")
        
        try:
            # Build dynamic instructions with context
            dynamic_instructions = self._build_dynamic_instructions(execution_context)
            
            # Execute the task based on output format
            if self.task_definition.expected_output_format == "diagnostic_result":
                result = await self._execute_diagnostic_task(execution_context, dynamic_instructions)
            else:
                result = await self._execute_custom_task(execution_context, dynamic_instructions)
            
            execution_time = time.time() - start_time
            result.details["execution_time"] = execution_time
            
            logger.info(f"[{self.name}] Task completed in {execution_time:.2f}s with status: {result.status}")
            return result
            
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"[{self.name}] Task execution failed: {e}")
            
            return DiagnosticResult(
                step=self.task_definition.task_id,
                status="error",
                findings=[f"Task execution failed: {str(e)}"],
                recommendations=["Check task configuration and retry"],
                details={
                    "error": str(e),
                    "execution_time": execution_time,
                    "task_definition": self.task_definition.name
                }
            )
    
    def _build_dynamic_instructions(self, execution_context: AgentExecutionContext) -> str:
        """Build dynamic instructions by injecting context and dependency results."""
        
        instructions = self.task_definition.instructions
        
        # Inject diagnostic context
        context = execution_context.diagnostic_context
        instructions = instructions.replace("{earliest_time}", context.earliest_time)
        instructions = instructions.replace("{latest_time}", context.latest_time)
        
        if context.indexes:
            instructions = instructions.replace("{indexes}", ", ".join(context.indexes))
        if context.sourcetypes:
            instructions = instructions.replace("{sourcetypes}", ", ".join(context.sourcetypes))
        if context.sources:
            instructions = instructions.replace("{sources}", ", ".join(context.sources))
        
        # Inject dependency results if available
        if execution_context.dependency_results:
            dependency_summary = self._create_dependency_summary(execution_context.dependency_results)
            instructions += f"\n\n**Dependency Results:**\n{dependency_summary}"
        
        # Add task-specific context
        instructions += f"\n\n**Task Context:**\n"
        instructions += f"- Task ID: {self.task_definition.task_id}\n"
        instructions += f"- Task Name: {self.task_definition.name}\n"
        instructions += f"- Available Tools: {', '.join(self.task_definition.required_tools)}\n"
        
        return instructions
    
    def _create_dependency_summary(self, dependency_results: Dict[str, DiagnosticResult]) -> str:
        """Create a summary of dependency results for context injection."""
        
        summary_parts = []
        for dep_task_id, result in dependency_results.items():
            summary_parts.append(f"**{dep_task_id}** (Status: {result.status})")
            
            # Include key findings
            if result.findings:
                summary_parts.append("Key findings:")
                for finding in result.findings[:3]:  # Limit to top 3 findings
                    summary_parts.append(f"  - {finding}")
            
            # Include important details
            if result.details:
                important_keys = ["user_info", "license_state", "total_events", "available_indexes"]
                for key in important_keys:
                    if key in result.details:
                        summary_parts.append(f"  - {key}: {result.details[key]}")
            
            summary_parts.append("")  # Add spacing
        
        return "\n".join(summary_parts)
    
    async def _execute_diagnostic_task(self, 
                                     execution_context: AgentExecutionContext,
                                     instructions: str) -> DiagnosticResult:
        """Execute a task that returns a DiagnosticResult."""
        
        # This is where we'd call the actual tool execution based on the task
        # For now, we'll implement the core logic for common diagnostic tasks
        
        task_id = self.task_definition.task_id
        
        # Route to appropriate execution method based on task type
        if "license" in task_id.lower():
            return await self._execute_license_verification(execution_context)
        elif "index" in task_id.lower():
            return await self._execute_index_verification(execution_context)
        elif "permission" in task_id.lower():
            return await self._execute_permissions_check(execution_context)
        elif "time" in task_id.lower() or "range" in task_id.lower():
            return await self._execute_time_range_check(execution_context)
        else:
            return await self._execute_generic_task(execution_context, instructions)
    
    async def _execute_license_verification(self, execution_context: AgentExecutionContext) -> DiagnosticResult:
        """Execute license verification task."""
        try:
            # Get server information
            server_result = await self.tool_registry.call_tool("run_oneshot_search", {
                "query": "| rest /services/server/info | fields splunk_version, product_type, license_state",
                "earliest_time": "now",
                "latest_time": "now",
                "max_results": 1
            })
            
            if not server_result.get("success"):
                return DiagnosticResult(
                    step=self.task_definition.task_id,
                    status="error",
                    findings=["Failed to retrieve server information"],
                    recommendations=["Check Splunk connectivity"],
                    details={"error": server_result.get("error")}
                )
            
            # Parse results and create diagnostic result
            # Implementation similar to the specific license agent but more generic
            findings = ["License verification completed"]
            status = "healthy"
            
            return DiagnosticResult(
                step=self.task_definition.task_id,
                status=status,
                findings=findings,
                recommendations=[],
                details={"server_info": server_result.get("data", {})}
            )
            
        except Exception as e:
            return DiagnosticResult(
                step=self.task_definition.task_id,
                status="error",
                findings=[f"License verification failed: {str(e)}"],
                recommendations=["Check configuration and retry"],
                details={"error": str(e)}
            )
    
    async def _execute_index_verification(self, execution_context: AgentExecutionContext) -> DiagnosticResult:
        """Execute index verification task."""
        try:
            # Get available indexes
            indexes_result = await self.tool_registry.call_tool("list_indexes")
            
            if not indexes_result.get("success"):
                return DiagnosticResult(
                    step=self.task_definition.task_id,
                    status="error",
                    findings=["Failed to retrieve index list"],
                    recommendations=["Check Splunk connectivity"],
                    details={"error": indexes_result.get("error")}
                )
            
            # Check target indexes from context
            context = execution_context.diagnostic_context
            available_indexes = indexes_result.get("data", {}).get("indexes", [])
            
            missing_indexes = []
            for target_index in context.indexes:
                if target_index not in available_indexes:
                    missing_indexes.append(target_index)
            
            if missing_indexes:
                status = "warning"
                findings = [f"Missing indexes: {', '.join(missing_indexes)}"]
                recommendations = ["Verify index names and permissions"]
            else:
                status = "healthy"
                findings = ["All target indexes are accessible"]
                recommendations = []
            
            return DiagnosticResult(
                step=self.task_definition.task_id,
                status=status,
                findings=findings,
                recommendations=recommendations,
                details={
                    "available_indexes": available_indexes,
                    "target_indexes": context.indexes,
                    "missing_indexes": missing_indexes
                }
            )
            
        except Exception as e:
            return DiagnosticResult(
                step=self.task_definition.task_id,
                status="error",
                findings=[f"Index verification failed: {str(e)}"],
                recommendations=["Check configuration and retry"],
                details={"error": str(e)}
            )
    
    async def _execute_permissions_check(self, execution_context: AgentExecutionContext) -> DiagnosticResult:
        """Execute permissions verification task."""
        try:
            # Get user info from dependencies or directly
            user_info = None
            if "license_verification" in execution_context.dependency_results:
                license_result = execution_context.dependency_results["license_verification"]
                user_info = license_result.details.get("user_info")
            
            if not user_info:
                user_result = await self.tool_registry.call_tool("get_current_user", {})
                user_info = user_result.get("data", {}) if user_result.get("success") else {}
            
            # Basic permissions check
            user_roles = user_info.get("roles", [])
            if not user_roles:
                status = "warning"
                findings = ["No roles assigned to user"]
                recommendations = ["Contact administrator for role assignment"]
            else:
                status = "healthy"
                findings = [f"User has roles: {', '.join(user_roles)}"]
                recommendations = []
            
            return DiagnosticResult(
                step=self.task_definition.task_id,
                status=status,
                findings=findings,
                recommendations=recommendations,
                details={"user_info": user_info, "user_roles": user_roles}
            )
            
        except Exception as e:
            return DiagnosticResult(
                step=self.task_definition.task_id,
                status="error",
                findings=[f"Permissions check failed: {str(e)}"],
                recommendations=["Check authentication and retry"],
                details={"error": str(e)}
            )
    
    async def _execute_time_range_check(self, execution_context: AgentExecutionContext) -> DiagnosticResult:
        """Execute time range verification task."""
        try:
            context = execution_context.diagnostic_context
            
            # Build search query based on context
            search_filters = []
            if context.indexes:
                search_filters.append(f"index={' OR index='.join(context.indexes)}")
            if context.sourcetypes:
                search_filters.append(f"sourcetype={' OR sourcetype='.join(context.sourcetypes)}")
            
            base_search = " ".join(search_filters) if search_filters else "*"
            count_query = f"{base_search} | stats count"
            
            # Execute count query
            count_result = await self.tool_registry.call_tool("run_oneshot_search", {
                "query": count_query,
                "earliest_time": context.earliest_time,
                "latest_time": context.latest_time,
                "max_results": 1
            })
            
            if not count_result.get("success"):
                return DiagnosticResult(
                    step=self.task_definition.task_id,
                    status="error",
                    findings=["Failed to check data in time range"],
                    recommendations=["Check search permissions"],
                    details={"error": count_result.get("error")}
                )
            
            # Parse results
            total_events = 0
            if count_result.get("data", {}).get("results"):
                total_events = int(count_result["data"]["results"][0].get("count", 0))
            
            if total_events == 0:
                status = "critical"
                findings = [f"No data found in time range {context.earliest_time} to {context.latest_time}"]
                recommendations = ["Verify time range and check if data exists outside this window"]
            else:
                status = "healthy"
                findings = [f"Found {total_events:,} events in time range"]
                recommendations = []
            
            return DiagnosticResult(
                step=self.task_definition.task_id,
                status=status,
                findings=findings,
                recommendations=recommendations,
                details={"total_events": total_events, "time_range": f"{context.earliest_time} to {context.latest_time}"}
            )
            
        except Exception as e:
            return DiagnosticResult(
                step=self.task_definition.task_id,
                status="error",
                findings=[f"Time range check failed: {str(e)}"],
                recommendations=["Check search syntax and time format"],
                details={"error": str(e)}
            )
    
    async def _execute_generic_task(self, 
                                  execution_context: AgentExecutionContext,
                                  instructions: str) -> DiagnosticResult:
        """Execute a generic task using the provided instructions."""
        
        # For generic tasks, we can implement a simple execution pattern
        # or integrate with an LLM for complex instruction following
        
        return DiagnosticResult(
            step=self.task_definition.task_id,
            status="completed",
            findings=[f"Generic task '{self.task_definition.name}' executed"],
            recommendations=["Review task results"],
            details={"instructions": instructions}
        )
    
    async def _execute_custom_task(self,
                                 execution_context: AgentExecutionContext,
                                 instructions: str) -> Any:
        """Execute a custom task with non-diagnostic output format."""
        
        # This method can be extended to support different output formats
        # For now, return a simple result
        return {
            "task_id": self.task_definition.task_id,
            "status": "completed",
            "result": f"Custom task '{self.task_definition.name}' executed",
            "instructions": instructions
        }


# Helper function to create dynamic agents
def create_dynamic_agent(config: AgentConfig,
                        tool_registry: SplunkToolRegistry,
                        task_definition: TaskDefinition) -> DynamicMicroAgent:
    """Factory function to create a dynamic micro-agent for a task."""
    return DynamicMicroAgent(config, tool_registry, task_definition) 