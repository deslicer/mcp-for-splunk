"""
Test for job search error handling with string messages.

This test verifies the fix for the bug where job.content["messages"] 
can contain strings instead of dictionaries, causing AttributeError 
when trying to call .get() method on strings.
"""

import pytest
from unittest.mock import Mock, AsyncMock
from src.tools.search.job_search import JobSearch


class TestJobSearchErrorHandling:
    """Test job search error handling for different message formats."""

    @pytest.fixture
    def job_search_tool(self):
        """Create a JobSearch tool instance for testing."""
        return JobSearch("run_splunk_search", "search")

    @pytest.fixture
    def mock_context(self):
        """Create a mock context for testing."""
        ctx = Mock()
        ctx.info = AsyncMock()
        ctx.error = AsyncMock()
        ctx.report_progress = AsyncMock()
        return ctx

    @pytest.fixture
    def mock_service(self):
        """Create a mock Splunk service for testing."""
        service = Mock()
        return service

    async def test_job_search_with_string_messages(self, job_search_tool, mock_context, mock_service):
        """Test that job search handles string messages without crashing."""
        
        # Mock the check_splunk_available method to return success
        job_search_tool.check_splunk_available = Mock(return_value=(True, mock_service, None))
        
        # Create a mock job that fails with string messages
        mock_job = Mock()
        mock_job.sid = "test_job_123"
        mock_job.is_done.return_value = True
        
        # This simulates the bug condition: messages are strings, not dictionaries
        mock_job.content = {
            "isFailed": "1",
            "isDone": "1", 
            "messages": [
                "Error in 'search' command: Unable to parse the search: Encountered the following error while compiling the search: Error in 'search' command: The following search head has one or more missing search peers",
                "Search not executed: The search job has failed due to an error. Review search syntax."
            ]
        }
        
        # Mock the service.jobs.create to return our mock job
        mock_service.jobs.create.return_value = mock_job
        
        # Mock the format_error_response method
        job_search_tool.format_error_response = Mock(return_value={
            "status": "error",
            "error": "Test error"
        })
        
        # Execute the search - this should not crash
        result = await job_search_tool.execute(
            mock_context,
            query="| rest /services/authorization/roles | search title=<your_role> | table title",
            earliest_time="-1h",
            latest_time="now"
        )
        
        # Verify that the tool handled the error gracefully
        assert result is not None
        assert isinstance(result, dict)
        
        # Verify that format_error_response was called (indicating error was handled)
        job_search_tool.format_error_response.assert_called()
        
        # Verify that the error contained the string messages
        call_args = job_search_tool.format_error_response.call_args[0][0]
        assert "Error in 'search' command" in call_args
        assert "Search not executed" in call_args

    async def test_job_search_with_dict_messages(self, job_search_tool, mock_context, mock_service):
        """Test that job search still handles dictionary messages correctly."""
        
        # Mock the check_splunk_available method to return success
        job_search_tool.check_splunk_available = Mock(return_value=(True, mock_service, None))
        
        # Create a mock job that fails with dictionary messages (normal case)
        mock_job = Mock()
        mock_job.sid = "test_job_456"
        mock_job.is_done.return_value = True
        
        # This simulates the normal case: messages are dictionaries
        mock_job.content = {
            "isFailed": "1",
            "isDone": "1",
            "messages": [
                {
                    "type": "ERROR",
                    "text": "Search syntax error: Invalid command"
                },
                {
                    "type": "WARN", 
                    "text": "This is a warning"
                },
                {
                    "type": "ERROR",
                    "text": "Another error occurred"
                }
            ]
        }
        
        # Mock the service.jobs.create to return our mock job
        mock_service.jobs.create.return_value = mock_job
        
        # Mock the format_error_response method
        job_search_tool.format_error_response = Mock(return_value={
            "status": "error", 
            "error": "Test error"
        })
        
        # Execute the search - this should not crash
        result = await job_search_tool.execute(
            mock_context,
            query="index=main | invalid_command",
            earliest_time="-1h",
            latest_time="now"
        )
        
        # Verify that the tool handled the error gracefully
        assert result is not None
        assert isinstance(result, dict)
        
        # Verify that format_error_response was called
        job_search_tool.format_error_response.assert_called()
        
        # Verify that only ERROR messages were included
        call_args = job_search_tool.format_error_response.call_args[0][0]
        assert "Search syntax error: Invalid command" in call_args
        assert "Another error occurred" in call_args
        assert "This is a warning" not in call_args  # WARN messages should be filtered out

    async def test_job_search_with_mixed_messages(self, job_search_tool, mock_context, mock_service):
        """Test that job search handles mixed string and dictionary messages."""
        
        # Mock the check_splunk_available method to return success
        job_search_tool.check_splunk_available = Mock(return_value=(True, mock_service, None))
        
        # Create a mock job that fails with mixed message types
        mock_job = Mock()
        mock_job.sid = "test_job_789"
        mock_job.is_done.return_value = True
        
        # This simulates a mixed case: some messages are strings, some are dictionaries
        mock_job.content = {
            "isFailed": "1",
            "isDone": "1",
            "messages": [
                "String error message: Search failed",
                {
                    "type": "ERROR",
                    "text": "Dictionary error message: Invalid syntax"
                },
                "Another string error: Connection timeout",
                {
                    "type": "INFO",
                    "text": "This is just info"
                }
            ]
        }
        
        # Mock the service.jobs.create to return our mock job
        mock_service.jobs.create.return_value = mock_job
        
        # Mock the format_error_response method
        job_search_tool.format_error_response = Mock(return_value={
            "status": "error",
            "error": "Test error"
        })
        
        # Execute the search - this should not crash
        result = await job_search_tool.execute(
            mock_context,
            query="index=main | some_query",
            earliest_time="-1h", 
            latest_time="now"
        )
        
        # Verify that the tool handled the error gracefully
        assert result is not None
        assert isinstance(result, dict)
        
        # Verify that format_error_response was called
        job_search_tool.format_error_response.assert_called()
        
        # Verify that both string messages and ERROR dictionary messages were included
        call_args = job_search_tool.format_error_response.call_args[0][0]
        assert "String error message: Search failed" in call_args
        assert "Dictionary error message: Invalid syntax" in call_args
        assert "Another string error: Connection timeout" in call_args
        assert "This is just info" not in call_args  # INFO messages should be filtered out

    async def test_job_search_no_messages_field(self, job_search_tool, mock_context, mock_service):
        """Test that job search handles missing messages field gracefully."""
        
        # Mock the check_splunk_available method to return success
        job_search_tool.check_splunk_available = Mock(return_value=(True, mock_service, None))
        
        # Create a mock job that fails without messages field
        mock_job = Mock()
        mock_job.sid = "test_job_no_messages"
        mock_job.is_done.return_value = True
        
        # This simulates a case where there's no messages field
        mock_job.content = {
            "isFailed": "1",
            "isDone": "1"
            # No messages field
        }
        
        # Mock the service.jobs.create to return our mock job
        mock_service.jobs.create.return_value = mock_job
        
        # Mock the format_error_response method
        job_search_tool.format_error_response = Mock(return_value={
            "status": "error",
            "error": "Test error"
        })
        
        # Execute the search - this should not crash
        result = await job_search_tool.execute(
            mock_context,
            query="index=main | some_query",
            earliest_time="-1h",
            latest_time="now"
        )
        
        # Verify that the tool handled the error gracefully
        assert result is not None
        assert isinstance(result, dict)
        
        # Verify that format_error_response was called with generic message
        job_search_tool.format_error_response.assert_called()
        call_args = job_search_tool.format_error_response.call_args[0][0]
        assert "Job failed with no specific error message" in call_args 