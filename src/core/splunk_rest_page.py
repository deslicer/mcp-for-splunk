"""Page a Splunk REST collection using count/offset and paging.total."""

import json
from dataclasses import dataclass
from typing import Any

from src.core.list_paging import PaginationParams, build_paging, validate_pagination


@dataclass(frozen=True)
class RestCollectionPage:
    entries: list[dict[str, Any]]
    total_available: int
    params: PaginationParams
    paging: dict[str, int | bool | None]


def fetch_rest_collection_page(
    service: Any,
    endpoint: str,
    *,
    count: int = 50,
    offset: int = 0,
    search_filter: str = "",
    max_count: int = 200,
    extra_params: dict[str, Any] | None = None,
) -> RestCollectionPage:
    params = validate_pagination(count=count, offset=offset, max_count=max_count)
    query: dict[str, Any] = {
        "output_mode": "json",
        "count": params.count,
        "offset": params.offset,
    }
    if search_filter:
        query["search"] = search_filter
    if extra_params:
        query.update(extra_params)
    response = service.get(endpoint, **query)
    data = json.loads(response.body.read())
    entries = data.get("entry") or []
    total = int(data.get("paging", {}).get("total", len(entries)))
    return RestCollectionPage(
        entries=entries,
        total_available=total,
        params=params,
        paging=build_paging(
            returned=len(entries),
            total_available=total,
            offset=params.offset,
            count=params.count,
        ),
    )
