"""ITSI MCP resources.

This module exposes ITSI documentation as MCP resources at URIs of the
form ``itsi://docs/<slug>``. Resources are read-only and do not require
the user to have provided credentials.
"""

from __future__ import annotations

from mcp_itsi.core.base import BaseITSIResource
from mcp_itsi.resources.docs_resource import build_doc_resources


def all_resources() -> list[type[BaseITSIResource]]:
    """Return every concrete ITSI resource class."""
    return list(build_doc_resources())


__all__ = ["all_resources"]
