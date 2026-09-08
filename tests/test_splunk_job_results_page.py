from types import SimpleNamespace

import pytest

from src.core.splunk_job_results_page import JobResultsError, fetch_job_results_page


def test_pages_completed_job(monkeypatch) -> None:
    rows = [{"host": "a"}, {"host": "b"}]

    class FakeReader:
        def __init__(self, _stream):
            self._rows = list(rows)

        def __iter__(self):
            return iter(self._rows)

    monkeypatch.setattr(
        "src.core.splunk_job_results_page.JSONResultsReader",
        FakeReader,
    )
    job = SimpleNamespace(
        content={"isDone": "1", "isFailed": "0", "resultCount": "80"},
        results=lambda **kwargs: object(),
        touch=lambda: None,
        refresh=lambda: None,
    )
    page = fetch_job_results_page(job, count=2, offset=0)
    assert len(page.results) == 2
    assert page.paging["total_available"] == 80
    assert page.paging["has_more"] is True


def test_rejects_unfinished_job() -> None:
    job = SimpleNamespace(
        content={"isDone": "0", "isFailed": "0", "resultCount": "0"},
        refresh=lambda: None,
    )
    with pytest.raises(JobResultsError, match="not done"):
        fetch_job_results_page(job, count=10, offset=0)


def test_rejects_failed_job() -> None:
    job = SimpleNamespace(
        content={"isDone": "1", "isFailed": "1", "resultCount": "0"},
        refresh=lambda: None,
    )
    with pytest.raises(JobResultsError, match="failed"):
        fetch_job_results_page(job, count=10, offset=0)
