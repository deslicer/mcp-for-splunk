"""Expose the bundled ``llms.txt`` as an MCP resource.

``llms.txt`` (https://llmstxt.org/) is a concise, agent-facing map of how to
use this server effectively. Serving it at ``itsi://llms.txt`` lets a connected
LLM read the golden-path workflow before it starts calling tools.
"""

from __future__ import annotations

import logging
from collections.abc import Iterable
from pathlib import Path

from fastmcp import Context

from mcp_itsi.core.base import BaseITSIResource, ResourceMetadata

logger = logging.getLogger(__name__)

_LLMS_TXT_PATH = Path(__file__).resolve().parents[1] / "llms.txt"


class LlmsTxtResource(BaseITSIResource):
    """Serve the bundled ``llms.txt`` usage guide for LLM agents."""

    METADATA = ResourceMetadata(
        uri="itsi://llms.txt",
        name="ITSI MCP — llms.txt usage guide",
        description=(
            "Agent-facing guide to using this server effectively: the "
            "schema-first golden path, tool families, resources, and gotchas."
        ),
        mime_type="text/markdown",
        category="overview",
        tags=("llms-txt", "overview", "guide"),
    )

    async def read(self, mcp_ctx: Context) -> str:
        try:
            return _LLMS_TXT_PATH.read_text(encoding="utf-8")
        except FileNotFoundError:  # pragma: no cover - packaging guard
            logger.warning("llms.txt missing at %s", _LLMS_TXT_PATH)
            return "# ITSI MCP Server\n\n_(llms.txt not bundled)_\n"


def build_llms_resources() -> Iterable[type[BaseITSIResource]]:
    return [LlmsTxtResource]
