import json
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest

from src.tools.lookups.list_lookup_files import ListLookupFiles
from src.tools.search.list_saved_searches import ListSavedSearches


class _Body:
    def __init__(self, payload: dict) -> None:
        self._payload = payload

    def read(self) -> bytes:
        return json.dumps(self._payload).encode()


@pytest.mark.asyncio
async def test_list_saved_searches_uses_rest_paging() -> None:
    long_spl = "index=main " + ("error " * 80)
    payload = {
        "entry": [
            {
                "name": "Alerts",
                "content": {"search": long_spl, "disabled": "0"},
                "acl": {"owner": "admin", "app": "search", "sharing": "app", "perms": {}},
            }
        ],
        "paging": {"total": 9, "offset": 0},
    }
    service = Mock()
    service.get.return_value = SimpleNamespace(body=_Body(payload))
    tool = ListSavedSearches("list_saved_searches", "list")
    tool.check_splunk_available = Mock(return_value=(True, service, ""))
    ctx = SimpleNamespace(info=AsyncMock(), error=AsyncMock())

    result = await tool.execute(ctx, count=1)
    assert result["status"] == "success"
    assert result["has_more"] is True
    assert result["saved_searches"][0]["has_full_search"] is True
    assert len(result["saved_searches"][0]["search"]) == 200
    assert service.get.call_args.args[0] == "/servicesNS/-/-/saved/searches"


@pytest.mark.asyncio
async def test_list_lookup_files_rejects_count_zero() -> None:
    tool = ListLookupFiles("list_lookup_files", "list")
    tool.check_splunk_available = Mock(return_value=(True, Mock(), ""))
    ctx = SimpleNamespace(info=AsyncMock(), error=AsyncMock())
    result = await tool.execute(ctx, count=0)
    assert result["status"] == "error"
    assert "count" in result["error"]
