"""Tests for get_search_job_results paging and Splunk Web links."""

from unittest.mock import AsyncMock, Mock

import pytest

from src.tools.search.job_results import GetSearchJobResults


class TestGetSearchJobResults:
    @pytest.fixture
    def tool(self):
        return GetSearchJobResults("get_search_job_results", "page job results")

    @pytest.fixture
    def mock_context(self):
        ctx = Mock()
        ctx.info = AsyncMock()
        ctx.error = AsyncMock()
        ctx.get_state = AsyncMock(return_value=None)
        return ctx

    @pytest.fixture
    def mock_job(self):
        job = Mock()
        job.sid = "scheduler__admin__search__test"
        job.content = {
            "isDone": "1",
            "isFailed": "0",
            "resultCount": "3",
        }
        job.results.return_value = [
            {"_raw": "row-1"},
            {"_raw": "row-2"},
        ]
        job.refresh = Mock()
        job.touch = Mock()
        return job

    @pytest.fixture
    def mock_service(self, mock_job):
        service = Mock()
        service.host = "splunk-b839c1.deslicer.io"
        service.scheme = "https"
        service.port = 8089
        jobs = Mock()
        jobs.__getitem__ = Mock(return_value=mock_job)
        service.jobs = jobs
        return service

    async def test_pages_results_and_job_urls(self, tool, mock_context, mock_service, mock_job):
        tool.check_splunk_available = Mock(return_value=(True, mock_service, None))
        tool.get_client_config_from_context = AsyncMock(
            return_value={"splunk_web_url": "https://splunk-b839c1.deslicer.io"}
        )

        result = await tool.execute(mock_context, job_id=mock_job.sid, count=2, offset=0)

        assert result["status"] == "success"
        assert result["results"] == [{"_raw": "row-1"}, {"_raw": "row-2"}]
        assert result["count"] == 2
        assert result["total_available"] == 3
        assert result["has_more"] is True
        assert result["next_offset"] == 2
        assert result["job_id"] == mock_job.sid
        assert result["job_details_url"] == (
            "https://splunk-b839c1.deslicer.io/en-US/app/search/"
            f"job_details_dashboard?form.sid={mock_job.sid}&tab=layout_1"
        )
        assert result["job_inspector_url"] == (
            "https://splunk-b839c1.deslicer.io/en-US/manager/search/"
            f"job_inspector?sid={mock_job.sid}"
        )
        assert ":8089" not in result["job_details_url"]
        assert ":8000" not in result["job_details_url"]
        mock_job.results.assert_called_once()
        mock_job.touch.assert_called_once()

    async def test_missing_job_id(self, tool, mock_context):
        result = await tool.execute(mock_context, job_id="")
        assert result["status"] == "error"
        assert "job_id" in result["error"]

    async def test_rejects_invalid_count(self, tool, mock_context, mock_service, mock_job):
        tool.check_splunk_available = Mock(return_value=(True, mock_service, None))
        result = await tool.execute(mock_context, job_id=mock_job.sid, count=0)
        assert result["status"] == "error"
        assert "count" in result["error"]
