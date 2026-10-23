"""
Blocking-job search that waits for completion and returns one result page.
"""

import asyncio
import time
from typing import Any

from fastmcp import Context

from src.core.base import BaseTool, ToolMetadata
from src.core.list_paging import clamp_search_page_size
from src.core.search_errors import SearchStage, search_error_fields
from src.core.splunk_errors import safe_error_message
from src.core.splunk_job_results_page import (
    JOB_TTL_SECONDS,
    SEARCH_PAGE_MAX,
    apply_job_ttl,
    fetch_job_results_page,
)
from src.core.splunk_web_urls import web_links_from_service
from src.core.utils import log_tool_execution, sanitize_search_query


def _resolve_page_size(count: int | None, max_results: int | None) -> int:
    return clamp_search_page_size(count, max_results, max_count=SEARCH_PAGE_MAX)


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
            "    count (int, optional): Page size 1-100 (default 50; 0 uses default)\n"
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
        availability = self.check_splunk_availability(ctx)
        service, error_msg = availability.service, availability.error
        if not availability.available:
            await ctx.error(f"One-shot search failed: {error_msg}")
            return self.format_error_response(
                error_msg,
                results=[],
                count=0,
                query_executed=query,
                **search_error_fields(None, "pre_execution", error_code=availability.error_code),
            )

        query = sanitize_search_query(query)
        await ctx.info(f"Executing blocking search: {query}")
        start_time = time.time()
        stage: SearchStage = "job_creation"
        job_id = None
        try:
            job = await asyncio.to_thread(
                service.jobs.create,
                query,
                earliest_time=earliest_time,
                latest_time=latest_time,
                exec_mode="blocking",
                adhoc_search_level="smart",
            )
            job_id = job.sid
            stage = "job_ttl"
            await asyncio.to_thread(apply_job_ttl, job, JOB_TTL_SECONDS)
            stage = "result_retrieval"
            page = await asyncio.to_thread(
                fetch_job_results_page, job, count=page_size, offset=offset
            )
            stage = "response_formatting"
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
        except Exception as e:
            detail = safe_error_message(e)
            self.logger.error("One-shot search failed: %s", detail)
            await ctx.error(f"One-shot search failed: {detail}")
            return self.format_error_response(
                detail,
                results=[],
                count=0,
                query_executed=query,
                **search_error_fields(e, stage, job_id),
            )
