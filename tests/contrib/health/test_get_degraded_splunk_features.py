"""
Tests for GetLatestFeatureHealthTool.
"""

from unittest.mock import MagicMock, patch

import pytest
from fastmcp import Context

from contrib.tools.health.get_degraded_splunk_features import GetLatestFeatureHealthTool


class TestGetLatestFeatureHealthTool:
    """Test cases for GetLatestFeatureHealthTool."""

    @pytest.fixture
    def tool(self):
        """Create a tool instance for testing."""
        return GetLatestFeatureHealthTool(
            name="get_latest_feature_health",
            description="This tool identifies Splunk features with health issues (warning/critical status) requiring attention"
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

        # Mock job and results
        mock_job = MagicMock()
        mock_results = [
            {"feature": "indexing", "status": "healthy"},
            {"feature": "searching", "status": "warning"},
            {"feature": "forwarder", "status": "critical"}
        ]

        # Mock ResultsReader to return our test data
        with patch('contrib.tools.health.get_degraded_splunk_features.ResultsReader') as mock_reader:
            mock_reader.return_value = iter(mock_results)
            service.jobs.oneshot.return_value = mock_job
            yield service

    @pytest.mark.asyncio
    async def test_execute_success_default_params(self, tool, mock_context, mock_splunk_service):
        """Test successful tool execution with default parameters."""
        # Mock check_splunk_available to return success
        tool.check_splunk_available = MagicMock(return_value=(True, mock_splunk_service, ""))

        with patch('contrib.tools.health.get_degraded_splunk_features.ResultsReader') as mock_reader:
            mock_results = [
                {"feature": "indexing", "status": "healthy"},
                {"feature": "searching", "status": "warning"}
            ]
            mock_reader.return_value = iter(mock_results)

            result = await tool.execute(mock_context)

        assert result["status"] == "success"
        assert "results" in result
        assert "results_count" in result
        assert "query_executed" in result
        assert "duration" in result
        assert result["results_count"] == 2
        assert len(result["results"]) == 2
        assert "index=_internal component=PeriodicHealthReporter" in result["query_executed"]
        assert "\"green\"" in result["query_executed"]  # Verify double quotes are used

        # Verify static time parameters are used
        call_kwargs = mock_splunk_service.jobs.oneshot.call_args[1]
        assert call_kwargs["earliest_time"] == "-15m"
        assert call_kwargs["latest_time"] == "now"

    @pytest.mark.asyncio
    async def test_execute_with_custom_max_results(self, tool, mock_context, mock_splunk_service):
        """Test tool execution with custom max_results parameter."""
        tool.check_splunk_available = MagicMock(return_value=(True, mock_splunk_service, ""))

        with patch('contrib.tools.health.get_degraded_splunk_features.ResultsReader') as mock_reader:
            mock_results = [{"feature": "test", "status": "healthy"}]
            mock_reader.return_value = iter(mock_results)

            result = await tool.execute(
                mock_context,
                max_results=50
            )

        assert result["status"] == "success"
        assert result["results_count"] == 1

        # Verify that oneshot was called with correct parameters
        mock_splunk_service.jobs.oneshot.assert_called_once()
        call_args = mock_splunk_service.jobs.oneshot.call_args
        # Time parameters should be static
        assert call_args[1]["earliest_time"] == "-15m"
        assert call_args[1]["latest_time"] == "now"
        assert call_args[1]["count"] == 50

    @pytest.mark.asyncio
    async def test_execute_splunk_unavailable(self, tool, mock_context):
        """Test tool execution when Splunk is unavailable."""
        # Mock check_splunk_available to return failure
        error_msg = "Splunk service is not available. MCP server is running in degraded mode."
        tool.check_splunk_available = MagicMock(return_value=(False, None, error_msg))

        result = await tool.execute(mock_context)

        assert result["status"] == "error"
        assert result["error"] == error_msg

    @pytest.mark.asyncio
    async def test_execute_max_results_limit(self, tool, mock_context, mock_splunk_service):
        """Test that max_results parameter limits the number of results."""
        tool.check_splunk_available = MagicMock(return_value=(True, mock_splunk_service, ""))

        # Create more results than the limit
        mock_results = [
            {"feature": f"test_{i}", "status": "healthy"} for i in range(10)
        ]

        with patch('contrib.tools.health.get_degraded_splunk_features.ResultsReader') as mock_reader:
            mock_reader.return_value = iter(mock_results)

            result = await tool.execute(mock_context, max_results=5)

        assert result["status"] == "success"
        assert result["results_count"] == 5
        assert len(result["results"]) == 5

    @pytest.mark.asyncio
    async def test_execute_search_exception(self, tool, mock_context, mock_splunk_service):
        """Test error handling when search execution fails."""
        tool.check_splunk_available = MagicMock(return_value=(True, mock_splunk_service, ""))

        # Mock oneshot to raise an exception
        mock_splunk_service.jobs.oneshot.side_effect = Exception("Search failed")

        result = await tool.execute(mock_context)

        assert result["status"] == "error"
        assert "Search failed" in result["error"]

    @pytest.mark.asyncio
    async def test_execute_empty_results(self, tool, mock_context, mock_splunk_service):
        """Test tool execution with empty search results."""
        tool.check_splunk_available = MagicMock(return_value=(True, mock_splunk_service, ""))

        with patch('contrib.tools.health.get_degraded_splunk_features.ResultsReader') as mock_reader:
            mock_reader.return_value = iter([])  # Empty results

            result = await tool.execute(mock_context)

        assert result["status"] == "success"
        assert result["results_count"] == 0
        assert len(result["results"]) == 0
        assert "query_executed" in result
        assert "duration" in result

    @pytest.mark.asyncio
    async def test_context_logging(self, tool, mock_context, mock_splunk_service):
        """Test that the tool properly logs to context."""
        tool.check_splunk_available = MagicMock(return_value=(True, mock_splunk_service, ""))

        with patch('contrib.tools.health.get_degraded_splunk_features.ResultsReader') as mock_reader:
            mock_reader.return_value = iter([])

            await tool.execute(mock_context, max_results=25)

        # Verify context logging was called
        mock_context.info.assert_called()
        # Check that parameters were logged
        call_args = [call.args[0] for call in mock_context.info.call_args_list]
        assert any("get-latest-feature-health operation" in arg for arg in call_args)
        assert any("Get-latest-feature-health parameters" in arg for arg in call_args)

    def test_metadata(self, tool):
        """Test tool metadata."""
        metadata = GetLatestFeatureHealthTool.METADATA

        assert metadata.name == "get_latest_feature_health"
        assert metadata.description == "This tool identifies Splunk features with health issues (warning/critical status) requiring attention"
        assert metadata.category == "health"
        assert metadata.requires_connection is True
        assert "health" in metadata.tags
        assert "monitoring" in metadata.tags
        assert metadata.version == "1.0.0"

    def test_tool_initialization(self, tool):
        """Test tool initialization."""
        assert tool.name == "get_latest_feature_health"
        assert tool.description == "This tool identifies Splunk features with health issues (warning/critical status) requiring attention"
        assert hasattr(tool, 'logger')

    @pytest.mark.asyncio
    async def test_health_status_mapping(self, tool, mock_context, mock_splunk_service):
        """Test that health status mapping uses correct terminology."""
        tool.check_splunk_available = MagicMock(return_value=(True, mock_splunk_service, ""))

        with patch('contrib.tools.health.get_degraded_splunk_features.ResultsReader') as mock_reader:
            mock_reader.return_value = iter([])

            result = await tool.execute(mock_context)

        assert result["status"] == "success"

        # Verify the query contains the updated health status mapping
        query = result["query_executed"]
        assert "\"healthy\"" in query  # green -> healthy
        assert "\"warning\"" in query  # yellow -> warning
        assert "\"critical\"" in query  # red -> critical

    @pytest.mark.asyncio
    async def test_static_time_range(self, tool, mock_context, mock_splunk_service):
        """Test that the tool uses static time range values."""
        tool.check_splunk_available = MagicMock(return_value=(True, mock_splunk_service, ""))

        with patch('contrib.tools.health.get_degraded_splunk_features.ResultsReader') as mock_reader:
            mock_reader.return_value = iter([])

            await tool.execute(mock_context, max_results=100)

        # Verify static time parameters are always used
        call_kwargs = mock_splunk_service.jobs.oneshot.call_args[1]
        assert call_kwargs["earliest_time"] == "-15m"
        assert call_kwargs["latest_time"] == "now"
        assert call_kwargs["count"] == 100
