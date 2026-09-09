"""Shared MCP list/search paging contract."""

from dataclasses import dataclass


class PaginationError(ValueError):
    """Invalid count or offset supplied by a tool caller."""


@dataclass(frozen=True)
class PaginationParams:
    count: int
    offset: int


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
    count: int = 50,
    offset: int = 0,
    max_count: int = 200,
) -> PaginationParams:
    if offset < 0:
        raise PaginationError("offset must be >= 0")
    if count < 1 or count > max_count:
        raise PaginationError(f"count must be between 1 and {max_count}")
    return PaginationParams(count=count, offset=offset)


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
