"""
Tests for HelloWorldTool.
"""

from unittest.mock import MagicMock

import pytest
from fastmcp import Context

from contrib.tools.examples.hello_world import HelloWorldTool


class TestHelloWorldTool:
    """Test cases for HelloWorldTool."""

    @pytest.fixture
    def tool(self):
        """Create a tool instance for testing."""
        return HelloWorldTool(name="hello_world", description="A simple hello world example tool")

    @pytest.fixture
    def mock_context(self):
        """Create a mock context for testing."""
        ctx = MagicMock(spec=Context)
        ctx.info = MagicMock()
        ctx.error = MagicMock()
        return ctx

    @pytest.mark.asyncio
    async def test_execute_hello_world(self, tool, mock_context):
        """Test execution of parameter-less hello world."""
        result = await tool.execute(mock_context)

        assert result["status"] == "success"
        assert result["message"] == "Hello, World!"
        assert result["greeted"] == "World"
        assert result["tool"] == "hello_world"

    def test_metadata(self, tool):
        """Test tool metadata."""
        metadata = HelloWorldTool.METADATA

        assert metadata.name == "hello_world"
        assert (
            metadata.description
            == "A simple hello world example tool for demonstrating contributions"
        )
        assert metadata.category == "examples"
        assert not metadata.requires_connection
        assert "example" in metadata.tags
        assert "tutorial" in metadata.tags
        assert metadata.version == "1.0.0"

    def test_tool_initialization(self, tool):
        """Test tool initialization."""
        assert tool.name == "hello_world"
        assert tool.description == "A simple hello world example tool"
        assert hasattr(tool, "logger")

    @pytest.mark.asyncio
    async def test_context_logging(self, tool, mock_context):
        """Test that the tool properly logs to context."""
        await tool.execute(mock_context)

        # Verify context logging was called
        mock_context.info.assert_called_with("Saying hello to World")
