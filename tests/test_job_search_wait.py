from unittest.mock import AsyncMock, Mock

import pytest

from src.tools.search.job_search import JobSearch


@pytest.fixture
def job_search_tool() -> JobSearch:
    return JobSearch("run_splunk_search", "search")


@pytest.fixture
def mock_context() -> Mock:
    ctx = Mock()
    ctx.info = AsyncMock()
    ctx.error = AsyncMock()
    ctx.report_progress = AsyncMock()
    return ctx


@pytest.mark.asyncio
async def test_run_splunk_search_returns_job_id_when_wait_expires(
    job_search_tool: JobSearch, mock_context: Mock, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("MCP_SEARCH_WAIT_SECONDS", "0")
    service = Mock()
    service.host = "splunk.example"
    service.scheme = "https"
    job = Mock()
    job.sid = "1788882620.1334"
    job.is_done.return_value = False
    job.content = {
        "isDone": "0",
        "isFailed": "0",
        "doneProgress": "0.4",
        "scanCount": "12",
        "eventCount": "3",
        "resultCount": "0",
    }
    service.jobs.create.return_value = job
    job_search_tool.check_splunk_available = Mock(return_value=(True, service, None))
    job_search_tool.get_client_config_from_context = AsyncMock(return_value={})

    result = await job_search_tool.execute(mock_context, query="index=_internal | head 1")

    assert result["status"] == "success"
    assert result["is_done"] is False
    assert result["job_id"] == "1788882620.1334"
    assert result["poll_with"] == "get_search_job_info"
    assert result["results"] == []
    job.results.assert_not_called()


@pytest.mark.asyncio
async def test_run_splunk_search_clamps_zero_count_instead_of_erroring(
    job_search_tool: JobSearch, mock_context: Mock
) -> None:
    service = Mock()
    service.host = "splunk.example"
    service.scheme = "https"
    job = Mock()
    job.sid = "job.done"
    job.is_done.return_value = True
    job.content = {
        "isDone": "1",
        "isFailed": "0",
        "doneProgress": "1",
        "scanCount": "2",
        "eventCount": "2",
        "resultCount": "2",
        "earliestTime": "",
        "latestTime": "",
        "isFinalized": "1",
    }
    job.results.return_value = [{"host": "a"}]
    service.jobs.create.return_value = job
    job_search_tool.check_splunk_available = Mock(return_value=(True, service, None))
    job_search_tool.get_client_config_from_context = AsyncMock(return_value={})

    result = await job_search_tool.execute(
        mock_context, query="index=_internal | head 1", count=0
    )

    assert result["status"] == "success"
    assert result["is_done"] is True
    assert "count must be between" not in str(result)
    job.results.assert_called()
    assert job.results.call_args.kwargs["count"] == 50
