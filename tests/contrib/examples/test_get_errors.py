"""
Tests for GetErrorsTool.
"""

from unittest.mock import MagicMock, patch

import pytest
from fastmcp import Context

from contrib.tools.examples.get_errors import GetErrorsTool


class TestGetErrorsTool:
    """Test cases for GetErrorsTool."""

    @pytest.fixture
    def tool(self):
        """Create a tool instance for testing."""
        return GetErrorsTool(
            name="get_errors",
            description="This tools retrieves any existing errors in a splunk internal index."
        )

    @pytest.fixture
    def mock_context(self):
        """Create a mock context for testing."""
        ctx = MagicMock(spec=Context)
        ctx.info = MagicMock()
        ctx.error = MagicMock()
        return ctx

    @pytest.fixture
    def mock_splunk_service(self):
        """Create a mock Splunk service."""
        service = MagicMock()
        mock_job = MagicMock()
        mock_results = [
            {"field1": "value1", "count": 10},
            {"field1": "value2", "count": 5}
        ]

        with patch('contrib.tools.examples.get_errors.ResultsReader') as mock_reader:
            mock_reader.return_value = iter(mock_results)
            service.jobs.oneshot.return_value = mock_job
            yield service

    @pytest.mark.asyncio
    async def test_execute_success_default_params(self, tool, mock_context, mock_splunk_service):
        """Test successful execution with default parameters."""
        tool.check_splunk_available = MagicMock(return_value=(True, mock_splunk_service, ""))

        with patch('contrib.tools.examples.get_errors.ResultsReader') as mock_reader:
            mock_results = [{"field1": "test", "count": 1}]
            mock_reader.return_value = iter(mock_results)

            result = await tool.execute(mock_context)

        assert result["status"] == "success"
        assert "results" in result
        assert "results_count" in result
        assert "query_executed" in result
        assert "duration" in result
        assert result["results_count"] == 1

    @pytest.mark.asyncio
    async def test_execute_with_custom_parameters(self, tool, mock_context, mock_splunk_service):
        """Test execution with custom time parameters."""
        tool.check_splunk_available = MagicMock(return_value=(True, mock_splunk_service, ""))

        with patch('contrib.tools.examples.get_errors.ResultsReader') as mock_reader:
            mock_reader.return_value = iter([])

            result = await tool.execute(
                mock_context,
                earliest_time="-1h",
                latest_time="-30m",
                max_results=50
            )

        assert result["status"] == "success"

        # Verify search parameters
        call_kwargs = mock_splunk_service.jobs.oneshot.call_args[1]
        assert call_kwargs["earliest_time"] == "-1h"
        assert call_kwargs["latest_time"] == "-30m"
        assert call_kwargs["count"] == 50

    @pytest.mark.asyncio
    async def test_execute_splunk_unavailable(self, tool, mock_context):
        """Test execution when Splunk is unavailable."""
        error_msg = "Splunk service is not available"
        tool.check_splunk_available = MagicMock(return_value=(False, None, error_msg))

        result = await tool.execute(mock_context)

        assert result["status"] == "error"
        assert result["error"] == error_msg

    @pytest.mark.asyncio
    async def test_execute_search_exception(self, tool, mock_context, mock_splunk_service):
        """Test error handling when search fails."""
        tool.check_splunk_available = MagicMock(return_value=(True, mock_splunk_service, ""))
        mock_splunk_service.jobs.oneshot.side_effect = Exception("Search failed")

        result = await tool.execute(mock_context)

        assert result["status"] == "error"
        assert "Search failed" in result["error"]

    def test_metadata(self, tool):
        """Test tool metadata."""
        metadata = GetErrorsTool.METADATA

        assert metadata.name == "get_errors"
        assert metadata.description == "This tools retrieves any existing errors in a splunk internal index."
        assert metadata.category == "examples"
        assert metadata.requires_connection is True
        assert "splunk" in metadata.tags
        assert "search" in metadata.tags
        assert metadata.version == "1.0.0"

    def test_tool_initialization(self, tool):
        """Test tool initialization."""
        assert tool.name == "get_errors"
        assert tool.description == "This tools retrieves any existing errors in a splunk internal index."
        assert hasattr(tool, 'logger')
