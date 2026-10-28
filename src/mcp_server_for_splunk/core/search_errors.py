"""Additive search failure fields for retry and job reconciliation."""

from typing import Any, Literal

from mcp_server_for_splunk.core.list_paging import PaginationError
from mcp_server_for_splunk.core.splunk_errors import classify_splunk_error
from mcp_server_for_splunk.core.splunk_job_results_page import JobResultsError

SearchStage = Literal[
    "pre_execution",
    "job_creation",
    "job_ttl",
    "job_wait",
    "result_retrieval",
    "response_formatting",
]


def search_error_fields(
    error: BaseException | None,
    stage: SearchStage,
    job_id: str | None = None,
    *,
    error_code: str | None = None,
) -> dict[str, Any]:
    if error_code is None:
        if isinstance(error, PaginationError):
            error_code = "invalid_pagination"
        elif isinstance(error, JobResultsError):
            error_code = "job_results_error"
        else:
            error_code = classify_splunk_error(error, default="search_failed")
    # A failed create may have reached Splunk even when no SID was returned.
    started = None if stage == "job_creation" else stage != "pre_execution"
    fields: dict[str, Any] = {
        "error_code": error_code,
        "execution_stage": stage,
        "search_started": started,
    }
    if job_id is not None:
        fields["job_id"] = job_id
    return fields
