"""Oneshot search keeps a job sid and returns a result page."""

from unittest.mock import AsyncMock, Mock

import pytest

from src.tools.search.oneshot_search import OneshotSearch


class TestOneshotSearchPaging:
    @pytest.fixture
    def tool(self):
        return OneshotSearch("run_oneshot_search", "oneshot")

    @pytest.fixture
    def mock_context(self):
        ctx = Mock()
        ctx.info = AsyncMock()
        ctx.error = AsyncMock()
        return ctx

    async def test_returns_job_id_and_has_more(self, tool, mock_context):
        job = Mock()
        job.sid = "oneshot_sid_1"
        job.content = {"isDone": "1", "isFailed": "0", "resultCount": "60"}
        job.results.return_value = [{"_raw": f"r{i}"} for i in range(50)]
        job.set_ttl = Mock()

        service = Mock()
        service.host = "splunk-b839c1.deslicer.io"
        service.scheme = "https"
        service.port = 8089
        service.jobs.create.return_value = job

        tool.check_splunk_available = Mock(return_value=(True, service, None))
        tool.get_client_config_from_context = AsyncMock(
            return_value={"splunk_web_url": "https://splunk-b839c1.deslicer.io"}
        )

        result = await tool.execute(mock_context, query="index=main", count=50)
        assert result["status"] == "success"
        assert result["job_id"] == "oneshot_sid_1"
        assert result["has_more"] is True
        assert result["next_offset"] == 50
        assert result["total_available"] == 60
        assert len(result["results"]) == 50
        assert "job_details_url" in result
        service.jobs.create.assert_called_once()
        assert service.jobs.create.call_args.kwargs.get("exec_mode") == "blocking"
        service.jobs.oneshot.assert_not_called()
