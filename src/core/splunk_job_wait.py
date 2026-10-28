"""Poll a Splunk search job without holding the MCP request indefinitely."""

import asyncio
import math
import os
import time
from dataclasses import dataclass
from typing import Any

DEFAULT_SEARCH_WAIT_SECONDS = 15.0


@dataclass(frozen=True)
class JobWaitSnapshot:
    is_done: bool
    is_failed: bool
    cancelled: bool
    content: dict[str, Any]


def resolve_search_wait_seconds() -> float:
    raw = (os.getenv("MCP_SEARCH_WAIT_SECONDS") or "").strip()
    if not raw:
        return DEFAULT_SEARCH_WAIT_SECONDS
    try:
        value = float(raw)
        return max(0.0, value) if math.isfinite(value) else DEFAULT_SEARCH_WAIT_SECONDS
    except ValueError:
        return DEFAULT_SEARCH_WAIT_SECONDS


def _read_job(job: Any) -> tuple[bool, bool, dict[str, Any]]:
    done = bool(job.is_done())
    content = dict(getattr(job, "content", {}) or {})
    failed = str(content.get("isFailed", "0")) == "1"
    return done, failed, content


def _cancel_job(job: Any) -> None:
    cancel = getattr(job, "cancel", None)
    if callable(cancel):
        cancel()


async def wait_for_job(
    job: Any,
    *,
    wait_seconds: float,
    poll_interval: float = 2.0,
) -> JobWaitSnapshot:
    deadline = time.monotonic() + max(float(wait_seconds), 0.0)
    content: dict[str, Any] = {}
    while True:
        try:
            done, failed, content = await asyncio.wait_for(
                asyncio.to_thread(_read_job, job),
                timeout=max(0.001, deadline - time.monotonic()),
            )
        except TimeoutError:
            # The SDK socket timeout bounds the worker; return the known SID to
            # the caller instead of waiting for that worker or creating another job.
            return JobWaitSnapshot(is_done=False, is_failed=False, cancelled=False, content=content)
        except asyncio.CancelledError:
            await asyncio.to_thread(_cancel_job, job)
            raise
        if done or failed:
            return JobWaitSnapshot(is_done=done, is_failed=failed, cancelled=False, content=content)
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            return JobWaitSnapshot(
                is_done=False, is_failed=failed, cancelled=False, content=content
            )
        try:
            await asyncio.sleep(min(poll_interval, remaining))
        except asyncio.CancelledError:
            await asyncio.to_thread(_cancel_job, job)
            raise
