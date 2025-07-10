"""
Community Contributed Tools for MCP Server for Splunk.

This package contains community-contributed tools that extend the
functionality of the MCP Server for Splunk.
"""

# Import workflow tools for discovery
try:
    from .workflows import *
except ImportError:
    # Workflow tools may not be available
    pass 