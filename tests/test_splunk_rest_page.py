import json
from types import SimpleNamespace

from src.core.splunk_rest_page import fetch_rest_collection_page


class _Body:
    def __init__(self, payload: dict) -> None:
        self._payload = payload

    def read(self) -> bytes:
        return json.dumps(self._payload).encode()


def test_parses_entries_and_paging() -> None:
    payload = {
        "entry": [
            {"name": "main", "content": {"maxTotalDataSizeMB": "500000"}, "acl": {}},
        ],
        "paging": {"total": 12, "perPage": 1, "offset": 0},
    }
    service = SimpleNamespace(get=lambda endpoint, **params: SimpleNamespace(body=_Body(payload)))
    page = fetch_rest_collection_page(
        service,
        "/services/data/indexes",
        count=1,
        offset=0,
    )
    assert page.entries[0]["name"] == "main"
    assert page.total_available == 12
    assert page.params.count == 1
    assert page.paging["has_more"] is True
    assert page.paging["next_offset"] == 1
