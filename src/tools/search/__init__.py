"""
Search-related tools for Splunk MCP server.
"""

from .job_search import JobSearch
from .oneshot_search import OneshotSearch

__all__ = ["OneshotSearch", "JobSearch"]
