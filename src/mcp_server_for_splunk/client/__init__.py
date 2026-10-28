"""
Splunk client management for MCP Server.

This module contains Splunk connection and client management functionality.
"""

from .splunk_client import get_splunk_service, get_splunk_service_safe

__all__ = ["get_splunk_service", "get_splunk_service_safe"]
