"""Reusable CRUD operations against the ITSI ITOA interface.

The functions in this module deliberately return plain Python data so each
public tool module can decorate the result with its own response shape.
"""

from __future__ import annotations

import logging
from typing import Any

from mcp_itsi.client.endpoints import (
    itoa_collection,
    itoa_count,
    itoa_item,
    itoa_templatize,
)
from mcp_itsi.core.context import ITSICallContext

logger = logging.getLogger(__name__)


def _build_filter_params(
    filter_query: dict[str, Any] | str | None,
    *,
    fields: str | None = None,
    sort_key: str | None = None,
    sort_dir: int | None = None,
    limit: int | None = None,
    offset: int | None = None,
) -> dict[str, Any]:
    params: dict[str, Any] = {}
    if filter_query is not None:
        params["filter"] = filter_query
    if fields:
        params["fields"] = fields
    if sort_key:
        params["sort_key"] = sort_key
    if sort_dir is not None:
        params["sort_dir"] = sort_dir
    if limit is not None:
        params["limit"] = limit
    if offset is not None:
        params["offset"] = offset
    return params


async def list_objects(
    ctx: ITSICallContext,
    object_type: str,
    *,
    filter_query: dict[str, Any] | str | None = None,
    fields: str | None = None,
    sort_key: str | None = None,
    sort_dir: int | None = None,
    limit: int | None = None,
    offset: int | None = None,
) -> list[dict[str, Any]]:
    params = _build_filter_params(
        filter_query,
        fields=fields,
        sort_key=sort_key,
        sort_dir=sort_dir,
        limit=limit,
        offset=offset,
    )
    async with ctx.client() as client:
        result = await client.get_json(itoa_collection(object_type), params=params)
    return result if isinstance(result, list) else []


async def count_objects(
    ctx: ITSICallContext,
    object_type: str,
    filter_query: dict[str, Any] | str | None = None,
) -> int:
    params: dict[str, Any] = {}
    if filter_query is not None:
        params["filter"] = filter_query
    async with ctx.client() as client:
        result = await client.get_json(itoa_count(object_type), params=params)
    if isinstance(result, dict) and "count" in result:
        try:
            return int(result["count"])
        except (TypeError, ValueError):
            return 0
    return 0


async def get_object(ctx: ITSICallContext, object_type: str, key: str) -> dict[str, Any] | None:
    async with ctx.client() as client:
        result = await client.get_json(itoa_item(object_type, key))
    if isinstance(result, list):
        return result[0] if result else None
    return result if isinstance(result, dict) else None


async def create_object(
    ctx: ITSICallContext, object_type: str, payload: dict[str, Any]
) -> dict[str, Any]:
    async with ctx.client() as client:
        result = await client.post_json(itoa_collection(object_type), body=payload)
    return result if isinstance(result, dict) else {"raw": result}


async def update_object(
    ctx: ITSICallContext,
    object_type: str,
    key: str,
    payload: dict[str, Any],
    *,
    is_partial: bool = True,
) -> dict[str, Any]:
    params = {"is_partial_data": 1 if is_partial else 0}
    async with ctx.client() as client:
        result = await client.post_json(itoa_item(object_type, key), body=payload, params=params)
    return result if isinstance(result, dict) else {"raw": result}


async def delete_object(ctx: ITSICallContext, object_type: str, key: str) -> dict[str, Any]:
    async with ctx.client() as client:
        return await client.delete(itoa_item(object_type, key))


async def templatize_object(ctx: ITSICallContext, object_type: str, key: str) -> dict[str, Any]:
    async with ctx.client() as client:
        result = await client.get_json(itoa_templatize(object_type, key))
    return result if isinstance(result, dict) else {"raw": result}
