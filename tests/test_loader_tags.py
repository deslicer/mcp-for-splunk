"""Verify that ``ToolLoader`` tags every host tool with ``{"splunk"}``.

The host registers core Splunk tools through
:class:`src.core.loader.ToolLoader`. Tagging is done at registration
time so the host doesn't have to retro-fit ``tags`` on every
``BaseTool`` subclass. Per-tool ``ToolMetadata.tags`` (if any) merges
in alongside the default ``"splunk"`` tag.
"""

from __future__ import annotations

from unittest.mock import MagicMock

from src.core.base import BaseTool, ToolMetadata
from src.core.loader import ToolLoader


class _FakeTool(BaseTool):
    """Minimal host tool used as a fixture; never executed in these tests."""

    async def execute(self, ctx, *args, **kwargs):  # pragma: no cover - never called
        return {"status": "success"}


def _patch_registry(monkeypatch, name: str, extra_tags: list[str] | None) -> None:
    """Replace ``tool_registry`` and ``discover_tools`` so the loader sees
    a single fake tool with the requested metadata."""
    metadata = ToolMetadata(
        name=name,
        description="fake",
        category="test",
        tags=extra_tags,
    )

    fake_registry = MagicMock()
    fake_registry.list_tools.return_value = [metadata]
    fake_registry._tools = {name: _FakeTool}
    fake_registry.get_metadata.return_value = metadata

    monkeypatch.setattr("src.core.loader.tool_registry", fake_registry)
    monkeypatch.setattr("src.core.loader.discover_tools", lambda: None)


def _decorator_capture():
    captured: list = []

    def fake_decorator(*args, **kwargs):
        captured.append((args, kwargs))

        def _identity(fn):
            return fn

        return _identity

    return MagicMock(side_effect=fake_decorator), captured


def test_loader_adds_splunk_tag_to_every_tool(monkeypatch):
    fake_mcp = MagicMock()
    fake_mcp.tool, captured = _decorator_capture()

    _patch_registry(monkeypatch, "fake_tool", extra_tags=None)

    loader = ToolLoader(fake_mcp)
    loaded = loader.load_tools()

    assert loaded == 1
    _, kwargs = captured[0]
    assert "tags" in kwargs, "loader must forward tags"
    assert "splunk" in kwargs["tags"]


def test_loader_merges_metadata_tags_with_splunk(monkeypatch):
    fake_mcp = MagicMock()
    fake_mcp.tool, captured = _decorator_capture()

    _patch_registry(monkeypatch, "fake_tool", extra_tags=["search", "metadata"])

    loader = ToolLoader(fake_mcp)
    loader.load_tools()

    _, kwargs = captured[0]
    assert kwargs["tags"] == {"splunk", "search", "metadata"}


def test_loader_uses_set_type_for_tags(monkeypatch):
    """FastMCP expects a set; ensure we don't accidentally pass a list."""
    fake_mcp = MagicMock()
    fake_mcp.tool, captured = _decorator_capture()

    _patch_registry(monkeypatch, "fake_tool", extra_tags=["search"])

    loader = ToolLoader(fake_mcp)
    loader.load_tools()

    _, kwargs = captured[0]
    assert isinstance(kwargs["tags"], set), f"tags must be a set, got {type(kwargs['tags'])}"
