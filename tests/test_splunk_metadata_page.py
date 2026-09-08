import pytest

from src.core.list_paging import PaginationError
from src.core.splunk_metadata_page import (
    build_metadata_page_query,
    build_metadata_total_query,
)


def test_page_query_uses_validated_ints() -> None:
    query = build_metadata_page_query(
        metadata_type="sources",
        field="source",
        count=50,
        offset=0,
    )
    assert "| head 50" in query
    assert "where row > 0" in query
    assert "type=sources" in query


def test_index_filter_is_quoted() -> None:
    query = build_metadata_page_query(
        metadata_type="sourcetypes",
        field="sourcetype",
        count=10,
        offset=20,
        index="main",
    )
    assert 'index="main"' in query
    assert "where row > 20" in query
    assert "| head 10" in query


def test_total_query_has_no_user_offset() -> None:
    query = build_metadata_total_query(metadata_type="sources", index=None)
    assert "stats count" in query
    assert "streamstats" not in query


def test_rejects_bad_index_characters() -> None:
    with pytest.raises(PaginationError):
        build_metadata_page_query(
            metadata_type="sources",
            field="source",
            count=10,
            offset=0,
            index='main" | delete',
        )
