import pytest

from src.core.list_paging import (
    PaginationError,
    build_paging,
    clamp_search_page_size,
    validate_pagination,
)


def test_validate_defaults() -> None:
    params = validate_pagination()
    assert params.count == 50
    assert params.offset == 0


def test_validate_rejects_zero_and_over_cap() -> None:
    with pytest.raises(PaginationError):
        validate_pagination(count=0)
    with pytest.raises(PaginationError):
        validate_pagination(count=201, max_count=200)
    with pytest.raises(PaginationError):
        validate_pagination(offset=-1)


def test_has_more_and_next_offset() -> None:
    paging = build_paging(returned=50, total_available=184, offset=0, count=50)
    assert paging == {
        "count": 50,
        "total_available": 184,
        "offset": 0,
        "has_more": True,
        "next_offset": 50,
    }


def test_clamp_search_page_size_treats_zero_as_default() -> None:
    assert clamp_search_page_size(0) == 50
    assert clamp_search_page_size(None, 0) == 50
    assert clamp_search_page_size(-5) == 50


def test_clamp_search_page_size_caps_over_max() -> None:
    assert clamp_search_page_size(500, max_count=100) == 100
    assert clamp_search_page_size(25) == 25


def test_last_page_has_no_next() -> None:
    paging = build_paging(returned=34, total_available=84, offset=50, count=50)
    assert paging["has_more"] is False
    assert paging["next_offset"] is None
