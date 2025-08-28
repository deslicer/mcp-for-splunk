"""MCP Tool: GetExecutedWorkflows

Returns executed workflows for the caller's current session.

Parameters:
- id (optional): executed_workflow_id to retrieve a specific record
- workflow_id (optional): filter results by workflow id
- limit (optional): max records to return (default 50)
- offset (optional): pagination offset (default 0)
"""

import logging
from typing import Any

from fastmcp import Context

from src.core.base import BaseTool, ToolMetadata

from .shared.executed_store import get_executed_store


class GetExecutedWorkflowsTool(BaseTool):
    METADATA = ToolMetadata(
        name="get_executed_workflows",
        description=(
            "Retrieve executed workflows for the current session. "
            "If 'id' is provided, returns that single record (if it belongs to this session). "
            "If 'workflow_id' is provided, filters the list to that workflow. "
            "Otherwise returns a paginated list of latest results per workflow for this session."
        ),
        category="workflows",
    )

    def __init__(self, name: str, category: str):
        super().__init__(name, self.METADATA.description)
        self.category = category
        self._logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    async def execute(
        self,
        ctx: Context,
        id: str | None = None,
        workflow_id: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> dict[str, Any]:
        store = get_executed_store()

        # Log incoming filters and pagination for troubleshooting
        self._logger.info(
            "get_executed_workflows called with id=%s, workflow_id=%s, limit=%s, offset=%s",
            id,
            workflow_id,
            limit,
            offset,
        )

        if id:
            rec = store.get_by_id(ctx, id)
            if not rec:
                self._logger.info(
                    "No executed workflow found for id=%s in current session or it expired.", id
                )
                return {"status": "not_found", "message": "No record found for this session"}
            self._logger.info(
                "Found executed workflow id=%s workflow_id=%s executed_at=%s status=%s",
                rec.executed_workflow_id,
                rec.workflow_id,
                rec.executed_at,
                rec.status,
            )
            return {
                "status": "ok",
                "executed_workflow": {
                    "executed_workflow_id": rec.executed_workflow_id,
                    "session_id": rec.session_id,
                    "workflow_id": rec.workflow_id,
                    "executed_at": rec.executed_at,
                    "status": rec.status,
                    "result": rec.result,
                },
            }

        items = store.list_for_session(ctx, workflow_id=workflow_id, limit=limit, offset=offset)
        self._logger.info(
            "Listed %s executed workflows for current session (workflow_id filter=%s)",
            len(items),
            workflow_id,
        )
        if not items:
            # Provide additional hints to troubleshoot empty results
            try:
                self._logger.info(
                    "Executed store base_dir=%s ttl_seconds=%s",
                    getattr(store, "base_dir", "unknown"),
                    getattr(store, "ttl_seconds", "unknown"),
                )
            except Exception:
                pass
        return {
            "status": "ok",
            "count": len(items),
            "executed_workflows": [
                {
                    "executed_workflow_id": rec.executed_workflow_id,
                    "session_id": rec.session_id,
                    "workflow_id": rec.workflow_id,
                    "executed_at": rec.executed_at,
                    "status": rec.status,
                }
                for rec in items
            ],
        }


