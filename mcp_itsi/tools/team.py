"""Tools for ITSI teams (RBAC scoping)."""

from __future__ import annotations

from typing import Any

from fastmcp import Context

from mcp_itsi.core.base import BaseITSITool, ToolMetadata
from mcp_itsi.core.context import ITSICallContext
from mcp_itsi.core.responses import error_response, success_response
from mcp_itsi.tools import _itoa_ops as ops

_OBJECT_TYPE = "team"


class ListTeams(BaseITSITool):
    METADATA = ToolMetadata(
        name="itsi_list_teams",
        description=(
            "List ITSI teams (security groups). Use this to discover the "
            "`sec_grp` value for service / template creation."
        ),
        category="rbac",
        tags=("itsi", "team", "list"),
    )

    async def execute(
        self,
        mcp_ctx: Context,
        ctx: ITSICallContext,
        filter_query: dict[str, Any] | str | None = None,
        fields: str | None = "title,_key,description,acl",
        limit: int = 100,
        offset: int = 0,
    ) -> dict[str, Any]:
        items = await ops.list_objects(
            ctx,
            _OBJECT_TYPE,
            filter_query=filter_query,
            fields=fields,
            limit=limit,
            offset=offset,
        )
        return success_response(count=len(items), teams=items)


class GetTeam(BaseITSITool):
    METADATA = ToolMetadata(
        name="itsi_get_team",
        description="Fetch a single ITSI team document including ACL.",
        category="rbac",
        tags=("itsi", "team", "get"),
    )

    async def execute(self, mcp_ctx: Context, ctx: ITSICallContext, key: str) -> dict[str, Any]:
        if not key:
            return error_response("`key` is required")
        item = await ops.get_object(ctx, _OBJECT_TYPE, key)
        if item is None:
            return error_response("team not found", key=key)
        return success_response(team=item)
