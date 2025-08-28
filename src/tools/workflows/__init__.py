"""
Core Workflow Tools for MCP Server for Splunk.

This package contains core tools for creating, validating, and managing
custom troubleshooting workflows that integrate with the dynamic troubleshoot agent.
"""

# Import workflow tools for automatic discovery
try:
    from .get_executed_workflows import GetExecutedWorkflowsTool
    from .list_workflows import ListWorkflowsTool
    from .summarization_tool import SummarizationTool, create_summarization_tool
    from .workflow_builder import WorkflowBuilderTool
    from .workflow_requirements import WorkflowRequirementsTool
    from .workflow_runner import WorkflowRunnerTool

    __all__ = [
        "WorkflowRequirementsTool",
        "WorkflowBuilderTool",
        "ListWorkflowsTool",
        "WorkflowRunnerTool",
        "create_summarization_tool",
        "SummarizationTool",
        "GetExecutedWorkflowsTool",
    ]
except ImportError as e:
    # Handle import errors gracefully
    import logging

    logging.getLogger(__name__).warning(f"Some workflow tools failed to import: {e}")
    __all__ = []
