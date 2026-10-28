"""MCP Server for Splunk's import namespace.

Keep package imports lightweight. The server is initialized only when explicitly
imported, including through the existing ``from mcp_server_for_splunk import mcp`` API.
"""

from importlib import import_module

__all__ = ["mcp"]


def __getattr__(name: str):
    if name == "mcp":
        return import_module(".server", __name__).mcp
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
