"""Page Splunk metadata searches without unbounded oneshot dumps."""

import re
from dataclasses import dataclass
from typing import Any, Literal

from splunklib.results import JSONResultsReader

from src.core.list_paging import PaginationError, PaginationParams, build_paging, validate_pagination

_INDEX_NAME = re.compile(r"^[A-Za-z0-9_][A-Za-z0-9_\-]*$")
MetadataType = Literal["sources", "sourcetypes", "hosts"]


@dataclass(frozen=True)
class MetadataPage:
    values: list[str]
    params: PaginationParams
    paging: dict[str, int | bool | None]


def validate_index_name(index: str) -> str:
    if not _INDEX_NAME.match(index):
        raise PaginationError("index must be a simple Splunk index name")
    return index


def _index_clause(index: str | None) -> str:
    if not index:
        return "index=* index=_*"
    return f'index="{validate_index_name(index)}"'


def build_metadata_total_query(*, metadata_type: MetadataType, index: str | None = None) -> str:
    return f"| metadata type={metadata_type} {_index_clause(index)} | stats count"


def build_metadata_page_query(
    *,
    metadata_type: MetadataType,
    field: str,
    count: int,
    offset: int,
    index: str | None = None,
    max_count: int = 100,
) -> str:
    params = validate_pagination(count=count, offset=offset, max_count=max_count)
    if field not in {"source", "sourcetype", "host"}:
        raise PaginationError("unsupported metadata field")
    return (
        f"| metadata type={metadata_type} {_index_clause(index)} "
        f"| sort {field} "
        f"| streamstats count as row "
        f"| where row > {params.offset} "
        f"| head {params.count} "
        f"| table {field}"
    )


def _iter_results(stream: Any):
    if isinstance(stream, list):
        return stream
    return JSONResultsReader(stream)


def _read_field_values(stream: Any, field: str) -> list[str]:
    values: list[str] = []
    for result in _iter_results(stream):
        if isinstance(result, dict) and field in result:
            values.append(str(result[field]))
    return values


def _read_count(stream: Any) -> int:
    for result in _iter_results(stream):
        if isinstance(result, dict) and "count" in result:
            return int(float(result["count"]))
    return 0


def fetch_metadata_page(
    service: Any,
    *,
    metadata_type: MetadataType,
    field: str,
    count: int = 50,
    offset: int = 0,
    index: str | None = None,
    max_count: int = 100,
) -> MetadataPage:
    params = validate_pagination(count=count, offset=offset, max_count=max_count)
    total_query = build_metadata_total_query(metadata_type=metadata_type, index=index)
    page_query = build_metadata_page_query(
        metadata_type=metadata_type,
        field=field,
        count=params.count,
        offset=params.offset,
        index=index,
        max_count=max_count,
    )
    total_stream = service.jobs.oneshot(total_query, output_mode="json")
    page_stream = service.jobs.oneshot(page_query, output_mode="json")
    total = _read_count(total_stream)
    values = _read_field_values(page_stream, field)
    return MetadataPage(
        values=values,
        params=params,
        paging=build_paging(
            returned=len(values),
            total_available=total,
            offset=params.offset,
            count=params.count,
        ),
    )
