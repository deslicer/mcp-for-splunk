import json
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest

from src.core.list_paging import PaginationError
from src.tools.admin.apps import ListApps
from src.tools.admin.users import ListUsers
from src.tools.metadata.indexes import ListIndexes


class _Body:
    def __init__(self, payload: dict) -> None:
        self._payload = payload

    def read(self) -> bytes:
        return json.dumps(self._payload).encode()


def _collection_service(entries: list[dict], total: int | None = None) -> Mock:
    captured: dict = {}

    def fake_get(endpoint: str, **params):
        captured["endpoint"] = endpoint
        captured["params"] = params
        payload = {
            "entry": entries,
            "paging": {"total": total if total is not None else len(entries), "offset": params.get("offset", 0)},
        }
        return SimpleNamespace(body=_Body(payload))

    service = Mock()
    service.get.side_effect = fake_get
    service._captured = captured
    return service


@pytest.mark.asyncio
async def test_list_indexes_pages_and_excludes_internal() -> None:
    service = _collection_service(
        [{"name": "main", "content": {}, "acl": {}}],
        total=12,
    )
    tool = ListIndexes("list_indexes", "list")
    tool.get_splunk_service = AsyncMock(return_value=service)
    ctx = SimpleNamespace(info=AsyncMock(), error=AsyncMock())

    result = await tool.execute(ctx, count=1, offset=0)
    assert result["status"] == "success"
    assert result["indexes"] == ["main"]
    assert result["has_more"] is True
    assert result["next_offset"] == 1
    assert result["total_available"] == 12
    assert "NOT name=_*" in service._captured["params"]["search"]
    service.get.assert_called_once()


@pytest.mark.asyncio
async def test_list_indexes_clamps_oversize_count() -> None:
    service = _collection_service(
        [{"name": "main", "content": {}, "acl": {}}],
        total=1,
    )
    tool = ListIndexes("list_indexes", "list")
    tool.get_splunk_service = AsyncMock(return_value=service)
    ctx = SimpleNamespace(info=AsyncMock(), error=AsyncMock())
    result = await tool.execute(ctx, count=500, offset=0)
    assert result["status"] == "success"
    assert service._captured["params"]["count"] == 200


@pytest.mark.asyncio
async def test_list_apps_pages() -> None:
    service = _collection_service(
        [{"name": "search", "content": {"label": "Search", "version": "1.0"}, "acl": {}}],
        total=54,
    )
    tool = ListApps("list_apps", "list")
    tool.check_splunk_available = Mock(return_value=(True, service, ""))
    ctx = SimpleNamespace(info=AsyncMock(), error=AsyncMock())
    result = await tool.execute(ctx, count=1)
    assert result["apps"][0]["name"] == "search"
    assert result["has_more"] is True
    assert result["total_available"] == 54


@pytest.mark.asyncio
async def test_list_users_pages() -> None:
    service = _collection_service(
        [{"name": "admin", "content": {"roles": ["admin"], "email": "a@b.c"}, "acl": {}}],
        total=3,
    )
    tool = ListUsers("list_users", "list")
    tool.check_splunk_available = Mock(return_value=(True, service, ""))
    ctx = SimpleNamespace(info=AsyncMock(), error=AsyncMock())
    result = await tool.execute(ctx, count=1)
    assert result["users"][0]["username"] == "admin"
    assert result["has_more"] is True


def test_pagination_error_type() -> None:
    with pytest.raises(PaginationError):
        raise PaginationError("offset must be >= 0")


def test_list_indexes_description_states_count_cap() -> None:
    description = ListIndexes.METADATA.description
    assert "Maximum 200" in description
    assert "Do not send a count larger than 200" in description
