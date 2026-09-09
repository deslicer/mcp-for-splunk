import asyncio

import pytest

from src.core.splunk_job_wait import resolve_search_wait_seconds, wait_for_job


class _Job:
    def __init__(self, snapshots: list[dict]) -> None:
        self._snapshots = list(snapshots)
        self.sid = "job.1"
        self.cancelled = False
        self.content = self._snapshots[0]

    def is_done(self) -> bool:
        self.content = self._snapshots.pop(0) if self._snapshots else self.content
        return self.content.get("isDone") == "1"

    def cancel(self) -> None:
        self.cancelled = True


@pytest.mark.asyncio
async def test_wait_for_job_returns_incomplete_after_budget() -> None:
    job = _Job(
        [
            {"isDone": "0", "isFailed": "0", "doneProgress": "0.2"},
            {"isDone": "0", "isFailed": "0", "doneProgress": "0.4"},
        ]
    )
    snapshot = await wait_for_job(job, wait_seconds=0.05, poll_interval=0.01)
    assert snapshot.is_done is False
    assert snapshot.is_failed is False
    assert snapshot.cancelled is False


@pytest.mark.asyncio
async def test_wait_for_job_returns_when_done() -> None:
    job = _Job([{"isDone": "1", "isFailed": "0", "doneProgress": "1"}])
    snapshot = await wait_for_job(job, wait_seconds=1, poll_interval=0.01)
    assert snapshot.is_done is True


@pytest.mark.asyncio
async def test_wait_for_job_cancels_splunk_job_on_disconnect() -> None:
    job = _Job(
        [{"isDone": "0", "isFailed": "0", "doneProgress": "0.1"}]
        * 20
    )

    async def _run() -> None:
        await wait_for_job(job, wait_seconds=5, poll_interval=0.05)

    task = asyncio.create_task(_run())
    await asyncio.sleep(0.02)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert job.cancelled is True


def test_resolve_search_wait_seconds_reads_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MCP_SEARCH_WAIT_SECONDS", "8")
    assert resolve_search_wait_seconds() == 8.0
    monkeypatch.setenv("MCP_SEARCH_WAIT_SECONDS", "nope")
    assert resolve_search_wait_seconds() == 15.0
