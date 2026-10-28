"""
Routes package for MCP Server for Splunk

This package contains route handlers for different server endpoints.
"""

from .health import setup_health_routes

__all__ = ["setup_health_routes"]
