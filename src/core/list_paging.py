"""Shared MCP list/search paging contract."""

from dataclasses import dataclass
from typing import Annotated

from pydantic import Field


class PaginationError(ValueError):
    """Invalid count or offset supplied by a tool caller."""


@dataclass(frozen=True)
class PaginationParams:
    count: int
    offset: int


LIST_PAGE_DEFAULT = 50
LIST_PAGE_MAX = 200
METADATA_PAGE_MAX = 100


def count_arg_help(*, default: int = LIST_PAGE_DEFAULT, max_count: int = LIST_PAGE_MAX) -> str:
    return (
        f"    count (int, optional): Page size. Default {default}. Maximum {max_count}. "
        f"Values above {max_count} are capped to {max_count}; 0 uses {default}. "
        f"Do not send a count larger than {max_count}.\n"
    )


ListPageCount = Annotated[
    int,
    Field(
        description=(
            "Page size. Default 50. Maximum 200; larger values are capped to 200. "
            "Do not send a count above 200."
        )
    ),
]
MetadataPageCount = Annotated[
    int,
    Field(
        description=(
            "Page size. Default 50. Maximum 100; larger values are capped to 100. "
            "Do not send a count above 100."
        )
    ),
]


def clamp_search_page_size(
    count: int | None,
    max_results: int | None = None,
    *,
    default: int = 50,
    max_count: int = 100,
) -> int:
    """Coerce agent-supplied page sizes. 0/negative become default; over max is capped."""
    raw = default
    if count is not None:
        raw = count
    elif max_results is not None:
        raw = max_results
    if raw < 1:
        return default
    if raw > max_count:
        return max_count
    return raw


def validate_pagination(
    count: int = LIST_PAGE_DEFAULT,
    offset: int = 0,
    max_count: int = LIST_PAGE_MAX,
) -> PaginationParams:
    if offset < 0:
        raise PaginationError("offset must be >= 0")
    return PaginationParams(
        count=clamp_search_page_size(count, default=LIST_PAGE_DEFAULT, max_count=max_count),
        offset=offset,
    )


def build_paging(
    *,
    returned: int,
    total_available: int,
    offset: int,
    count: int,
) -> dict[str, int | bool | None]:
    has_more = (offset + returned) < total_available
    return {
        "count": returned,
        "total_available": total_available,
        "offset": offset,
        "has_more": has_more,
        "next_offset": (offset + returned) if has_more else None,
    }
