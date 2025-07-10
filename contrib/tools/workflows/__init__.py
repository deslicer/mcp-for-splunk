"""
Workflow Tools for MCP Server for Splunk.

This package contains tools for creating, validating, and managing
custom troubleshooting workflows.
"""

# Import workflow tools for automatic discovery
try:
    from .workflow_requirements import WorkflowRequirementsTool
    from .workflow_builder import WorkflowBuilderTool
    
    __all__ = [
        "WorkflowRequirementsTool",
        "WorkflowBuilderTool"
    ]
except ImportError as e:
    # Handle import errors gracefully
    import logging
    logging.getLogger(__name__).warning(f"Some workflow tools failed to import: {e}")
    __all__ = [] 