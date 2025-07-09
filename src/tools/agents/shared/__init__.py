"""
Shared utilities for Splunk troubleshooting agents.

This module contains common utilities, configurations, and base classes
that can be reused across different agent implementations to reduce
code duplication and improve maintainability.

The module now includes dynamic micro-agent capabilities that enable
task-driven parallelization where workflows are defined as sets of tasks,
and each independent task becomes a parallel micro-agent.
"""

from .config import AgentConfig, RetryConfig
from .context import SplunkDiagnosticContext, DiagnosticResult
from .tools import create_splunk_tools, SplunkToolRegistry
from .retry import retry_with_exponential_backoff
from .dynamic_agent import TaskDefinition, AgentExecutionContext, DynamicMicroAgent, create_dynamic_agent
from .workflow_manager import (
    WorkflowDefinition, 
    WorkflowResult, 
    WorkflowManager,
    execute_missing_data_workflow,
    execute_performance_workflow,
    execute_health_check_workflow
)

__all__ = [
    # Core configuration and context
    "AgentConfig",
    "RetryConfig", 
    "SplunkDiagnosticContext",
    "DiagnosticResult",
    
    # Tool registry and utilities
    "create_splunk_tools",
    "SplunkToolRegistry",
    "retry_with_exponential_backoff",
    
    # Dynamic micro-agent system
    "TaskDefinition",
    "AgentExecutionContext", 
    "DynamicMicroAgent",
    "create_dynamic_agent",
    
    # Workflow management system
    "WorkflowDefinition",
    "WorkflowResult",
    "WorkflowManager",
    "execute_missing_data_workflow",
    "execute_performance_workflow", 
    "execute_health_check_workflow"
] 