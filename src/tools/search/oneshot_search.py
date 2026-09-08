"""
Blocking-job search that waits for completion and returns one result page.
"""

import asyncio
import time
from typing import Any

from fastmcp import Context

from src.core.base import BaseTool, ToolMetadata
from src.core.list_paging import PaginationError
from src.core.splunk_job_results_page import (
    JOB_TTL_SECONDS,
    JobResultsError,
    apply_job_ttl,
    fetch_job_results_page,
)
from src.core.splunk_web_urls import web_links_from_service
from src.core.utils import log_tool_execution, sanitize_search_query


def _resolve_page_size(count: int | None, max_results: int | None) -> int:
    if count is not None:
        return count
    if max_results is not None:
        return max_results
    return 50


def _create_blocking_job(
    service: Any, query: str, earliest_time: str, latest_time: str
) -> Any:
    job = service.jobs.create(
        query,
        earliest_time=earliest_time,
        latest_time=latest_time,
        exec_mode="blocking",
        adhoc_search_level="smart",
    )
    apply_job_ttl(job, JOB_TTL_SECONDS)
    return job


class OneshotSearch(BaseTool):
    """
    Run a Splunk search, wait for it to finish, and return the first result page.
    """

    METADATA = ToolMetadata(
        name="run_oneshot_search",
        description=(
            "Run a Splunk search, wait for completion, and return one page of results. "
            "A job is kept so later pages can be fetched with get_search_job_results. "
            "Prefer run_splunk_search for long-running queries.\n\n"
            "If has_more is true, call get_search_job_results with job_id and offset=next_offset.\n\n"
            "Args:\n"
            "    query (str): SPL to execute\n"
            "    earliest_time (str, optional): Start time (default '-15m')\n"
            "    latest_time (str, optional): End time (default 'now')\n"
            "    count (int, optional): Page size 1-100 (default 50)\n"
            "    max_results (int, optional): Deprecated alias for count\n"
            "    offset (int, optional): Result offset (default 0)"
        ),
        category="search",
        tags=["search", "oneshot", "quick"],
        requires_connection=True,
    )

    async def execute(
        self,
        ctx: Context,
        query: str,
        earliest_time: str = "-15m",
        latest_time: str = "now",
        count: int | None = None,
        max_results: int | None = None,
        offset: int = 0,
    ) -> dict[str, Any]:
        page_size = _resolve_page_size(count, max_results)
        log_tool_execution(
            "run_oneshot_search",
            query=query,
            earliest_time=earliest_time,
            latest_time=latest_time,
            count=page_size,
            offset=offset,
        )
        is_available, service, error_msg = self.check_splunk_available(ctx)
        if not is_available:
            await ctx.error(f"One-shot search failed: {error_msg}")
            return self.format_error_response(
                error_msg, results=[], count=0, query_executed=query
            )

        query = sanitize_search_query(query)
        await ctx.info(f"Executing blocking search: {query}")
        start_time = time.time()
        try:
            job = await asyncio.to_thread(
                _create_blocking_job, service, query, earliest_time, latest_time
            )
            page = await asyncio.to_thread(
                fetch_job_results_page, job, count=page_size, offset=offset
            )
            client_config = await self.get_client_config_from_context(ctx)
            links = web_links_from_service(service, client_config)
            duration = time.time() - start_time
            return self.format_success_response(
                {
                    "results": page.results,
                    "results_count": page.paging["count"],
                    "query_executed": query,
                    "duration": round(duration, 3),
                    **page.paging,
                    **links.job_links(job.sid),
                }
            )
        except (PaginationError, JobResultsError) as e:
            return self.format_error_response(
                str(e), results=[], count=0, query_executed=query
            )
        except Exception as e:
            self.logger.error("One-shot search failed: %s", e)
            await ctx.error(f"One-shot search failed: {e}")
            return self.format_error_response(
                str(e), results=[], count=0, query_executed=query
            )
