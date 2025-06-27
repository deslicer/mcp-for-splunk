"""
Tests for SplunkSearchTool.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from fastmcp import Context
from contrib.tools.examples.splunk_search import SplunkSearchTool


class TestSplunkSearchTool:
    """Test cases for SplunkSearchTool."""
    
    @pytest.fixture
    def tool(self):
        """Create a tool instance for testing."""
        return SplunkSearchTool(
            name="splunk_search",
            description="This tool searches splunk health reporter to get infrastructure health indicators"
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
            {"feature": "searching", "status": "degraded"},
            {"feature": "forwarder", "status": "issues"}
        ]
        
        # Mock ResultsReader to return our test data
        with patch('contrib.tools.examples.splunk_search.ResultsReader') as mock_reader:
            mock_reader.return_value = iter(mock_results)
            service.jobs.oneshot.return_value = mock_job
            yield service
    
    @pytest.mark.asyncio
    async def test_execute_success_default_params(self, tool, mock_context, mock_splunk_service):
        """Test successful tool execution with default parameters."""
        # Mock check_splunk_available to return success
        tool.check_splunk_available = MagicMock(return_value=(True, mock_splunk_service, ""))
        
        with patch('contrib.tools.examples.splunk_search.ResultsReader') as mock_reader:
            mock_results = [
                {"feature": "indexing", "status": "healthy"},
                {"feature": "searching", "status": "degraded"}
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
    
    @pytest.mark.asyncio
    async def test_execute_with_custom_parameters(self, tool, mock_context, mock_splunk_service):
        """Test tool execution with custom parameters."""
        tool.check_splunk_available = MagicMock(return_value=(True, mock_splunk_service, ""))
        
        with patch('contrib.tools.examples.splunk_search.ResultsReader') as mock_reader:
            mock_results = [{"feature": "test", "status": "healthy"}]
            mock_reader.return_value = iter(mock_results)
            
            result = await tool.execute(
                mock_context,
                earliest_time="-1h",
                latest_time="-30m",
                max_results=50
            )
        
        assert result["status"] == "success"
        assert result["results_count"] == 1
        
        # Verify that oneshot was called with correct parameters
        mock_splunk_service.jobs.oneshot.assert_called_once()
        call_args = mock_splunk_service.jobs.oneshot.call_args
        assert call_args[1]["earliest_time"] == "-1h"
        assert call_args[1]["latest_time"] == "-30m"
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
        
        with patch('contrib.tools.examples.splunk_search.ResultsReader') as mock_reader:
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
        
        with patch('contrib.tools.examples.splunk_search.ResultsReader') as mock_reader:
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
        
        with patch('contrib.tools.examples.splunk_search.ResultsReader') as mock_reader:
            mock_reader.return_value = iter([])
            
            await tool.execute(mock_context, earliest_time="-2h", max_results=25)
        
        # Verify context logging was called
        mock_context.info.assert_called()
        # Check that parameters were logged
        call_args = [call.args[0] for call in mock_context.info.call_args_list]
        assert any("splunk-search operation" in arg for arg in call_args)
        assert any("earliest_time" in arg for arg in call_args)
    
    def test_metadata(self, tool):
        """Test tool metadata."""
        metadata = SplunkSearchTool.METADATA
        
        assert metadata.name == "splunk_search"
        assert metadata.description == "This tool searches splunk health reporter to get infrastructure health indicators"
        assert metadata.category == "examples"
        assert metadata.requires_connection is True
        assert "example" in metadata.tags
        assert "tutorial" in metadata.tags
        assert metadata.version == "1.0.0"
    
    def test_tool_initialization(self, tool):
        """Test tool initialization."""
        assert tool.name == "splunk_search"
        assert tool.description == "This tool searches splunk health reporter to get infrastructure health indicators"
        assert hasattr(tool, 'logger')
    
    @pytest.mark.asyncio
    async def test_parameter_validation(self, tool, mock_context, mock_splunk_service):
        """Test parameter handling and validation."""
        tool.check_splunk_available = MagicMock(return_value=(True, mock_splunk_service, ""))
        
        with patch('contrib.tools.examples.splunk_search.ResultsReader') as mock_reader:
            mock_reader.return_value = iter([])
            
            # Test with various parameter types
            result = await tool.execute(
                mock_context,
                earliest_time="-24h",
                latest_time="now",
                max_results=1000
            )
        
        assert result["status"] == "success"
        
        # Verify parameters were passed correctly to Splunk
        call_kwargs = mock_splunk_service.jobs.oneshot.call_args[1]
        assert call_kwargs["earliest_time"] == "-24h"
        assert call_kwargs["latest_time"] == "now"
        assert call_kwargs["count"] == 1000
