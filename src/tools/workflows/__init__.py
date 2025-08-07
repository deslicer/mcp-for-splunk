"""
Core Workflow Tools for MCP Server for Splunk.

This package contains core tools for creating, validating, and managing
custom troubleshooting workflows that integrate with the dynamic troubleshoot agent.
"""

# Import workflow tools for automatic discovery
try:
    from .workflow_requirements import WorkflowRequirementsTool
    from .workflow_builder import WorkflowBuilderTool
    from .list_workflows import ListWorkflowsTool
    from .workflow_runner import WorkflowRunnerTool
    from .summarization_tool import create_summarization_tool, SummarizationTool
    
    __all__ = [
        "WorkflowRequirementsTool",
        "WorkflowBuilderTool",
        "ListWorkflowsTool",
        "WorkflowRunnerTool",
        "create_summarization_tool",
        "SummarizationTool"
    ]
except ImportError as e:
    # Handle import errors gracefully
    import logging
    logging.getLogger(__name__).warning(f"Some workflow tools failed to import: {e}")
    __all__ = [] 