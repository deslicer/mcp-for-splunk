"""
Agent tools for MCP Server for Splunk.

This module contains tools that implement AI agent capabilities for automated
troubleshooting and analysis workflows.
"""

# Import only what's needed to avoid circular imports during testing
try:
    from .splunk_triage_agent import SplunkTriageAgentTool
    from .dynamic_troubleshoot_agent import DynamicTroubleshootAgentTool
    
    __all__ = [
        "SplunkTriageAgentTool",
        "DynamicTroubleshootAgentTool"
    ]
except ImportError as e:
    # Handle import errors during testing
    import logging
    logging.getLogger(__name__).warning(f"Some agent imports failed: {e}")
    __all__ = [] 