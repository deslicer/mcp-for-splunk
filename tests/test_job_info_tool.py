"""
Tests for search job info tool.
"""

from unittest.mock import AsyncMock, Mock

import pytest

from src.tools.search.job_info import GetSearchJobInfo


class TestJobInfoTool:
    @pytest.fixture
    def tool(self):
        return GetSearchJobInfo("get_search_job_info", "job info")

    @pytest.fixture
    def mock_context(self):
        ctx = Mock()
        ctx.info = AsyncMock()
        ctx.error = AsyncMock()
        ctx.report_progress = AsyncMock()
        return ctx

    @pytest.fixture
    def mock_service(self):
        service = Mock()
        service.jobs = {}
        return service

    async def test_job_info_not_found(self, tool, mock_context, mock_service):
        tool.check_splunk_available = Mock(return_value=(True, mock_service, None))

        # Simulate Splunk SDK behavior for missing sid
        jobs = Mock()
        jobs.__getitem__ = Mock(side_effect=KeyError("missing"))
        mock_service.jobs = jobs

        result = await tool.execute(mock_context, job_id="nope")
        assert result["status"] == "error"
        assert "not found" in result["error"].lower()

    async def test_job_info_string_messages(self, tool, mock_context, mock_service):
        tool.check_splunk_available = Mock(return_value=(True, mock_service, None))

        mock_job = Mock()
        mock_job.content = {
            "isFailed": "1",
            "isDone": "1",
            "messages": [
                "Error in 'search' command: Unable to parse the search",
                "Search not executed: The search job has failed due to an error.",
            ],
            "doneProgress": "1.0",
        }
        mock_job.refresh = Mock()

        jobs = Mock()
        jobs.__getitem__ = Mock(return_value=mock_job)
        mock_service.jobs = jobs

        result = await tool.execute(mock_context, job_id="sid_123")
        assert result["status"] == "success"
        assert result["errors"]
        assert result["job_status"]["is_failed"] is True
        assert any("Unable to parse" in e for e in result["errors"])

    async def test_job_info_dict_messages(self, tool, mock_context, mock_service):
        tool.check_splunk_available = Mock(return_value=(True, mock_service, None))

        mock_job = Mock()
        mock_job.content = {
            "isFailed": "1",
            "isDone": "1",
            "messages": [
                {"type": "ERROR", "text": "Search syntax error: Invalid command"},
                {"type": "WARN", "text": "This is a warning"},
                {"type": "ERROR", "text": "Another error occurred"},
            ],
            "doneProgress": "1.0",
        }
        mock_job.refresh = Mock()

        jobs = Mock()
        jobs.__getitem__ = Mock(return_value=mock_job)
        mock_service.jobs = jobs

        result = await tool.execute(mock_context, job_id="sid_456")
        assert result["status"] == "success"
        assert "Search syntax error: Invalid command" in result["errors"]
        assert "Another error occurred" in result["errors"]
        assert not any("warning" in e.lower() for e in result["errors"])

    async def test_job_info_mixed_messages(self, tool, mock_context, mock_service):
        tool.check_splunk_available = Mock(return_value=(True, mock_service, None))

        mock_job = Mock()
        mock_job.content = {
            "isFailed": "1",
            "isDone": "1",
            "messages": [
                "String error message: Search failed",
                {"type": "ERROR", "text": "Dictionary error message: Invalid syntax"},
                {"type": "INFO", "text": "Info only"},
            ],
            "doneProgress": "1.0",
        }
        mock_job.refresh = Mock()

        jobs = Mock()
        jobs.__getitem__ = Mock(return_value=mock_job)
        mock_service.jobs = jobs

        result = await tool.execute(mock_context, job_id="sid_789")
        assert result["status"] == "success"
        assert "String error message: Search failed" in result["errors"]
        assert "Dictionary error message: Invalid syntax" in result["errors"]
        assert not any("info only" in e.lower() for e in result["errors"])

    async def test_job_info_include_raw_content(self, tool, mock_context, mock_service):
        tool.check_splunk_available = Mock(return_value=(True, mock_service, None))

        mock_job = Mock()
        mock_job.content = {
            "isFailed": "0",
            "isDone": "0",
            "messages": [{"type": "INFO", "text": "Running"}],
            "doneProgress": "0.25",
            "dispatchState": "RUNNING",
        }
        mock_job.refresh = Mock()

        jobs = Mock()
        jobs.__getitem__ = Mock(return_value=mock_job)
        mock_service.jobs = jobs

        result = await tool.execute(mock_context, job_id="sid_raw", include_raw_content=True)
        assert result["status"] == "success"
        assert "raw_content" in result
        assert result["raw_content"]["dispatchState"] == "RUNNING"
