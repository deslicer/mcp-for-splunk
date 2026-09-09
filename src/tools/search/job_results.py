"""Fetch one page of results from a completed Splunk search job."""

import asyncio
from typing import Any

from fastmcp import Context

from src.core.base import BaseTool, ToolMetadata
from src.core.list_paging import PaginationError, clamp_search_page_size
from src.core.splunk_job_results_page import (
    SEARCH_PAGE_MAX,
    JobResultsError,
    fetch_job_results_page,
)
from src.core.splunk_web_urls import web_links_from_service
from src.core.utils import log_tool_execution


class GetSearchJobResults(BaseTool):
    """Page results from a completed search job."""

    METADATA = ToolMetadata(
        name="get_search_job_results",
        description=(
            "Fetch one page of results from a completed Splunk search job. "
            "Use after run_oneshot_search, run_splunk_search, or execute_saved_search "
            "when has_more is true. Pass job_id and offset=next_offset.\n\n"
            "Args:\n"
            "    job_id (str): Splunk search job id (sid)\n"
            "    count (int, optional): Page size 1-100 (default 50; 0 uses default)\n"
            "    offset (int, optional): Result offset (default 0)\n"
        ),
        category="search",
        tags=["search", "job", "results", "pagination"],
        requires_connection=True,
    )

    async def execute(
        self,
        ctx: Context,
        job_id: str,
        count: int = 50,
        offset: int = 0,
    ) -> dict[str, Any]:
        count = clamp_search_page_size(count, max_count=SEARCH_PAGE_MAX)
        log_tool_execution("get_search_job_results", job_id=job_id, count=count, offset=offset)
        if not job_id or not job_id.strip():
            return self.format_error_response("job_id is required", job_id=job_id)

        is_available, service, error_msg = self.check_splunk_available(ctx)
        if not is_available:
            return self.format_error_response(error_msg, job_id=job_id)

        try:
            job = service.jobs[job_id]
            page = await asyncio.to_thread(fetch_job_results_page, job, count=count, offset=offset)
            client_config = await self.get_client_config_from_context(ctx)
            links = web_links_from_service(service, client_config)
            return self.format_success_response(
                {
                    "results": page.results,
                    **page.paging,
                    **links.job_links(job_id),
                }
            )
        except (PaginationError, JobResultsError, KeyError) as e:
            return self.format_error_response(str(e), job_id=job_id)
        except Exception as e:
            self.logger.error("Failed to page search job %s: %s", job_id, e)
            return self.format_error_response(str(e), job_id=job_id)
