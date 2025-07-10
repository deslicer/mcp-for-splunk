"""Dynamic Coordinator Agent

Coordinates dynamic micro-agents using the workflow manager for task-driven parallelization.
This replaces the static parallel coordinator with a flexible system that can handle
any workflow defined as a set of tasks.
"""

import asyncio
import logging
import time
from typing import Dict, Any, List, Optional

from fastmcp import Context
from .shared import (
    AgentConfig, 
    SplunkDiagnosticContext, 
    SplunkToolRegistry,
    WorkflowManager,
    WorkflowDefinition,
    TaskDefinition,
    execute_missing_data_workflow,
    execute_performance_workflow
)

logger = logging.getLogger(__name__)


class DynamicCoordinator:
    """
    Dynamic coordinator that orchestrates micro-agents based on workflow definitions.
    
    This coordinator can:
    1. Execute predefined workflows (missing data, performance)
    2. Create custom workflows on-the-fly based on problem analysis
    3. Automatically determine optimal parallelization based on task dependencies
    4. Scale the number of agents based on the number of independent tasks
    
    Key advantages:
    - No need for specific agent files - uses dynamic agent template
    - Flexible task definitions that can be reused across workflows
    - Automatic dependency resolution and parallel execution planning
    - Efficient resource usage by creating only needed agents
    """
    
    def __init__(self, config: AgentConfig, tool_registry: SplunkToolRegistry):
        self.config = config
        self.tool_registry = tool_registry
        self.workflow_manager = WorkflowManager(config, tool_registry)
        self.name = "DynamicCoordinator"
        
        logger.info(f"DynamicCoordinator initialized with {len(self.workflow_manager.list_workflows())} workflows")
    
    async def execute_missing_data_analysis(self, 
                                          diagnostic_context: SplunkDiagnosticContext,
                                          problem_description: str,
                                          ctx: Context) -> Dict[str, Any]:
        """
        Execute missing data analysis using dynamic micro-agents with progress reporting.
        
        This method automatically creates and orchestrates the appropriate micro-agents
        for missing data troubleshooting based on the official Splunk workflow.
        """
        start_time = time.time()
        logger.info(f"Starting dynamic missing data analysis")
        
        try:
            # Execute the missing data workflow with progress reporting
            workflow_result = await execute_missing_data_workflow(
                self.workflow_manager, 
                diagnostic_context,
                ctx
            )
            
            # Format results for compatibility with existing systems
            execution_time = time.time() - start_time
            
            # Extract key information from workflow results
            task_summaries = []
            for task_id, result in workflow_result.task_results.items():
                task_summaries.append({
                    "task": task_id,
                    "status": result.status,
                    "findings": result.findings,
                    "recommendations": result.recommendations,
                    "execution_time": result.details.get("execution_time", 0)
                })
            
            return {
                "status": "success",
                "coordinator_type": "dynamic_missing_data",
                "problem_description": problem_description,
                "workflow_execution": {
                    "workflow_id": workflow_result.workflow_id,
                    "overall_status": workflow_result.status,
                    "execution_time": workflow_result.execution_time,
                    "parallel_efficiency": workflow_result.summary.get("parallel_efficiency", 0),
                    "execution_phases": len(workflow_result.execution_order),
                    "total_tasks": len(workflow_result.task_results)
                },
                "task_results": task_summaries,
                "summary": workflow_result.summary,
                "diagnostic_context": {
                    "earliest_time": diagnostic_context.earliest_time,
                    "latest_time": diagnostic_context.latest_time,
                    "indexes": diagnostic_context.indexes,
                    "sourcetypes": diagnostic_context.sourcetypes,
                    "sources": diagnostic_context.sources
                },
                "performance_metrics": {
                    "total_execution_time": execution_time,
                    "workflow_execution_time": workflow_result.execution_time,
                    "tasks_completed": len(workflow_result.task_results),
                    "successful_tasks": len([r for r in workflow_result.task_results.values() if r.status in ["healthy", "warning"]]),
                    "failed_tasks": len([r for r in workflow_result.task_results.values() if r.status == "error"]),
                    "parallel_phases": len(workflow_result.execution_order)
                }
            }
            
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"Dynamic missing data analysis failed: {e}")
            
            return {
                "status": "error",
                "coordinator_type": "dynamic_missing_data",
                "error": str(e),
                "execution_time": execution_time
            }
    
    async def execute_performance_analysis(self,
                                         diagnostic_context: SplunkDiagnosticContext,
                                         problem_description: str,
                                         ctx: Context) -> Dict[str, Any]:
        """
        Execute performance analysis using dynamic micro-agents with progress reporting.
        
        This method automatically creates and orchestrates the appropriate micro-agents
        for performance troubleshooting based on Splunk Platform Instrumentation.
        """
        start_time = time.time()
        logger.info(f"Starting dynamic performance analysis")
        
        try:
            # Execute the performance workflow with progress reporting
            workflow_result = await execute_performance_workflow(
                self.workflow_manager,
                diagnostic_context,
                ctx
            )
            
            # Format results
            execution_time = time.time() - start_time
            
            task_summaries = []
            for task_id, result in workflow_result.task_results.items():
                task_summaries.append({
                    "task": task_id,
                    "status": result.status,
                    "findings": result.findings,
                    "recommendations": result.recommendations,
                    "execution_time": result.details.get("execution_time", 0)
                })
            
            return {
                "status": "success",
                "coordinator_type": "dynamic_performance",
                "problem_description": problem_description,
                "workflow_execution": {
                    "workflow_id": workflow_result.workflow_id,
                    "overall_status": workflow_result.status,
                    "execution_time": workflow_result.execution_time,
                    "parallel_efficiency": workflow_result.summary.get("parallel_efficiency", 0),
                    "execution_phases": len(workflow_result.execution_order),
                    "total_tasks": len(workflow_result.task_results)
                },
                "task_results": task_summaries,
                "summary": workflow_result.summary,
                "diagnostic_context": {
                    "earliest_time": diagnostic_context.earliest_time,
                    "latest_time": diagnostic_context.latest_time,
                    "indexes": diagnostic_context.indexes,
                    "sourcetypes": diagnostic_context.sourcetypes,
                    "sources": diagnostic_context.sources
                },
                "performance_metrics": {
                    "total_execution_time": execution_time,
                    "workflow_execution_time": workflow_result.execution_time,
                    "tasks_completed": len(workflow_result.task_results),
                    "successful_tasks": len([r for r in workflow_result.task_results.values() if r.status in ["healthy", "warning"]]),
                    "failed_tasks": len([r for r in workflow_result.task_results.values() if r.status == "error"]),
                    "parallel_phases": len(workflow_result.execution_order)
                }
            }
            
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"Dynamic performance analysis failed: {e}")
            
            return {
                "status": "error",
                "coordinator_type": "dynamic_performance", 
                "error": str(e),
                "execution_time": execution_time
            }
    
    async def execute_custom_workflow(self,
                                    workflow_definition: WorkflowDefinition,
                                    diagnostic_context: SplunkDiagnosticContext,
                                    problem_description: str,
                                    ctx: Context) -> Dict[str, Any]:
        """
        Execute a custom workflow using dynamic micro-agents with progress reporting.
        
        This method allows for on-the-fly workflow creation and execution,
        enabling maximum flexibility for different troubleshooting scenarios.
        """
        start_time = time.time()
        logger.info(f"Starting custom workflow: {workflow_definition.name}")
        
        try:
            # Register the custom workflow temporarily
            self.workflow_manager.register_workflow(workflow_definition)
            
            # Execute the workflow with progress reporting
            workflow_result = await self.workflow_manager.execute_workflow(
                workflow_definition.workflow_id,
                diagnostic_context,
                ctx
            )
            
            # Format results
            execution_time = time.time() - start_time
            
            task_summaries = []
            for task_id, result in workflow_result.task_results.items():
                task_summaries.append({
                    "task": task_id,
                    "status": result.status,
                    "findings": result.findings,
                    "recommendations": result.recommendations,
                    "execution_time": result.details.get("execution_time", 0)
                })
            
            return {
                "status": "success",
                "coordinator_type": "dynamic_custom",
                "problem_description": problem_description,
                "workflow_execution": {
                    "workflow_id": workflow_result.workflow_id,
                    "workflow_name": workflow_definition.name,
                    "overall_status": workflow_result.status,
                    "execution_time": workflow_result.execution_time,
                    "parallel_efficiency": workflow_result.summary.get("parallel_efficiency", 0),
                    "execution_phases": len(workflow_result.execution_order),
                    "total_tasks": len(workflow_result.task_results)
                },
                "task_results": task_summaries,
                "summary": workflow_result.summary,
                "diagnostic_context": {
                    "earliest_time": diagnostic_context.earliest_time,
                    "latest_time": diagnostic_context.latest_time,
                    "indexes": diagnostic_context.indexes,
                    "sourcetypes": diagnostic_context.sourcetypes,
                    "sources": diagnostic_context.sources
                },
                "performance_metrics": {
                    "total_execution_time": execution_time,
                    "workflow_execution_time": workflow_result.execution_time,
                    "tasks_completed": len(workflow_result.task_results),
                    "successful_tasks": len([r for r in workflow_result.task_results.values() if r.status in ["healthy", "warning"]]),
                    "failed_tasks": len([r for r in workflow_result.task_results.values() if r.status == "error"]),
                    "parallel_phases": len(workflow_result.execution_order)
                }
            }
            
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"Custom workflow execution failed: {e}")
            
            return {
                "status": "error",
                "coordinator_type": "dynamic_custom",
                "error": str(e),
                "execution_time": execution_time
            }
    
    def create_custom_workflow_from_tasks(self,
                                        workflow_id: str,
                                        workflow_name: str,
                                        task_definitions: List[TaskDefinition]) -> WorkflowDefinition:
        """
        Create a custom workflow from a list of task definitions.
        
        This enables dynamic workflow creation based on problem analysis.
        The system will automatically determine the optimal execution order
        based on task dependencies.
        """
        return WorkflowDefinition(
            workflow_id=workflow_id,
            name=workflow_name,
            description=f"Custom workflow with {len(task_definitions)} tasks",
            tasks=task_definitions
        )
    
    def list_available_workflows(self) -> List[Dict[str, Any]]:
        """List all available workflows with their details."""
        
        workflows = []
        for workflow in self.workflow_manager.list_workflows():
            # Calculate potential parallelism
            dependency_graph = self.workflow_manager._build_dependency_graph(workflow.tasks)
            execution_phases = self.workflow_manager._create_execution_phases(workflow.tasks, dependency_graph)
            parallel_efficiency = self.workflow_manager._calculate_parallel_efficiency(workflow.tasks, execution_phases)
            
            workflows.append({
                "workflow_id": workflow.workflow_id,
                "name": workflow.name,
                "description": workflow.description,
                "total_tasks": len(workflow.tasks),
                "execution_phases": len(execution_phases),
                "parallel_efficiency": parallel_efficiency,
                "tasks": [
                    {
                        "task_id": task.task_id,
                        "name": task.name,
                        "description": task.description,
                        "dependencies": task.dependencies,
                        "required_tools": task.required_tools
                    }
                    for task in workflow.tasks
                ]
            })
        
        return workflows 