"""
Shared utilities for Splunk troubleshooting workflows.

This module contains common utilities, configurations, and base classes
that can be reused across different workflow implementations to reduce
code duplication and improve maintainability.

The module includes dynamic micro-agent capabilities that enable
task-driven parallelization where workflows are defined as sets of tasks,
and each independent task becomes a parallel micro-agent.
"""

from .config import AgentConfig, RetryConfig
from .context import DiagnosticResult, SplunkDiagnosticContext
from .dynamic_agent import (
    AgentExecutionContext,
    DynamicMicroAgent,
    TaskDefinition,
    create_dynamic_agent,
)
from .parallel_executor import ParallelExecutionMetrics, ParallelWorkflowExecutor
from .retry import retry_with_exponential_backoff
from .tools import SplunkToolRegistry, create_splunk_tools
from .workflow_manager import (
    WorkflowDefinition,
    WorkflowManager,
    WorkflowResult,
    execute_missing_data_workflow,
    execute_performance_workflow,
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
    # Parallel execution system
    "ParallelWorkflowExecutor",
    "ParallelExecutionMetrics",
]
