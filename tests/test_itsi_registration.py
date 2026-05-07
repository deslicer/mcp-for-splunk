"""Tests for `mcp_itsi.core.registration` tag forwarding.

The plugin's tool/resource/prompt classes carry their toolset tag
(`"itsi"`) on their metadata. Without forwarding those tags into FastMCP
the host-side `ToolsetFilterMiddleware` has nothing to filter on. These
tests pin the contract: every register_* helper passes `tags=` through.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import pytest

from mcp_itsi.core.base import (
    BaseITSIPrompt,
    BaseITSIResource,
    BaseITSITool,
    PromptMetadata,
    ResourceMetadata,
    ToolMetadata,
)
from mcp_itsi.core.registration import (
    register_prompts,
    register_resources,
    register_tools,
)


class _FakeTool(BaseITSITool):
    """Minimal ITSI tool fixture; never executed in these tests."""

    METADATA = ToolMetadata(
        name="itsi_test_tool",
        description="A fake ITSI tool used in tests.",
        category="testing",
        tags=("itsi", "test"),
    )

    async def execute(  # type: ignore[override]
        self,
        mcp_ctx,
        ctx,
        *args,
        **kwargs,
    ):  # pragma: no cover - never invoked
        return {"status": "success"}


class _FakeResource(BaseITSIResource):
    METADATA = ResourceMetadata(
        uri="itsi://test/resource",
        name="itsi_test_resource",
        description="A fake ITSI resource used in tests.",
        mime_type="text/markdown",
        category="testing",
        tags=("itsi", "docs"),
    )

    async def read(self, mcp_ctx):  # pragma: no cover - never invoked
        return "ok"


class _FakePrompt(BaseITSIPrompt):
    METADATA = PromptMetadata(
        name="itsi_test_prompt",
        description="A fake ITSI prompt used in tests.",
        category="testing",
        tags=("itsi", "prompt"),
    )

    async def render(self, mcp_ctx, **kwargs):  # pragma: no cover - never invoked
        return "ok"


def _decorator_capture() -> tuple[MagicMock, list[Any]]:
    """Build a MagicMock that mimics fastmcp's decorator-returning .tool/.resource/.prompt."""
    captured: list[Any] = []

    def fake_decorator(*args, **kwargs):
        captured.append((args, kwargs))

        def _identity(fn):
            return fn

        return _identity

    mock = MagicMock(side_effect=fake_decorator)
    return mock, captured


def test_register_tools_forwards_metadata_tags_as_set():
    fake_mcp = MagicMock()
    fake_mcp.tool, captured = _decorator_capture()

    count = register_tools(fake_mcp, [_FakeTool])

    assert count == 1
    args, kwargs = captured[0]
    assert kwargs["name"] == "itsi_test_tool"
    assert "tags" in kwargs, "register_tools must forward tags to mcp.tool"
    assert kwargs["tags"] == {"itsi", "test"}


def test_register_resources_forwards_metadata_tags_as_set():
    fake_mcp = MagicMock()
    fake_mcp.resource, captured = _decorator_capture()

    count = register_resources(fake_mcp, [_FakeResource])

    assert count == 1
    args, kwargs = captured[0]
    assert kwargs["name"] == "itsi_test_resource"
    assert "tags" in kwargs, "register_resources must forward tags to mcp.resource"
    assert kwargs["tags"] == {"itsi", "docs"}


def test_register_prompts_forwards_metadata_tags_as_set():
    fake_mcp = MagicMock()
    fake_mcp.prompt, captured = _decorator_capture()

    count = register_prompts(fake_mcp, [_FakePrompt])

    assert count == 1
    args, kwargs = captured[0]
    assert kwargs["name"] == "itsi_test_prompt"
    assert "tags" in kwargs, "register_prompts must forward tags to mcp.prompt"
    assert kwargs["tags"] == {"itsi", "prompt"}


def test_register_tools_handles_empty_tags_metadata():
    """Empty tag tuple should still produce an empty set (not raise)."""

    class _Untagged(BaseITSITool):
        METADATA = ToolMetadata(
            name="itsi_untagged_tool",
            description="No tags.",
            category="testing",
            tags=(),
        )

        async def execute(self, mcp_ctx, ctx, *args, **kwargs):  # pragma: no cover
            return {"status": "success"}

    fake_mcp = MagicMock()
    fake_mcp.tool, captured = _decorator_capture()

    count = register_tools(fake_mcp, [_Untagged])

    assert count == 1
    _, kwargs = captured[0]
    assert kwargs["tags"] == set()
