"""
Filesystem-backed store for executed workflows (latest per session + workflow_id).

Stores one record per (session_id, workflow_id). Each record includes:
- executed_workflow_id (uuid4)
- session_id
- workflow_id
- executed_at (ISO8601 string)
- status (mirrors result.status)
- result (full workflow runner result payload)

Environment variables:
- EXECUTED_WORKFLOWS_DIR (default: ./data/executed_workflows)
- EXECUTED_WORKFLOWS_TTL_SECONDS (default: 86400)
"""

import json
import logging
import os
import time
import uuid
from dataclasses import dataclass
from typing import Any

from fastmcp import Context

logger = logging.getLogger(__name__)


def _now_iso() -> str:
    try:
        from datetime import datetime, timezone

        return datetime.now(timezone.utc).isoformat()
    except Exception:
        return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _get_session_id(ctx: Context) -> str:
    try:
        # Prefer the canonical FastMCP property (see docs)
        # https://gofastmcp.com/servers/context#mcp-request
        if hasattr(ctx, "session_id") and ctx.session_id:
            logger.debug("Resolved session_id from ctx.session_id: %s", ctx.session_id)
            return str(ctx.session_id)

        # Legacy/alternate shapes
        if hasattr(ctx, "session") and ctx.session:
            sid = getattr(ctx.session, "session_id", None)
            if sid:
                logger.debug("Resolved session_id from ctx.session.session_id: %s", sid)
                return str(sid)
        if (
            hasattr(ctx, "request_context")
            and hasattr(ctx.request_context, "request")
            and hasattr(ctx.request_context.request, "headers")
        ):
            headers = ctx.request_context.request.headers
            sid = headers.get("x-session-id") or headers.get("authorization", "")
            if sid:
                logger.debug("Resolved session_id from request headers: %s", sid)
                return sid
    except Exception:
        pass
    # Fallback ephemeral
    logger.warning("Falling back to generated ephemeral session_id (no session present)")
    return uuid.uuid4().hex


@dataclass
class ExecutedWorkflow:
    executed_workflow_id: str
    session_id: str
    workflow_id: str
    executed_at: str
    status: str
    result: dict[str, Any]


class ExecutedWorkflowStore:
    def __init__(self):
        self.base_dir = os.getenv("EXECUTED_WORKFLOWS_DIR", "./data/executed_workflows")
        self.ttl_seconds = int(os.getenv("EXECUTED_WORKFLOWS_TTL_SECONDS", "86400"))
        self.index_path = os.path.join(self.base_dir, "index.json")
        os.makedirs(self.base_dir, exist_ok=True)
        # Initialize index if missing
        if not os.path.exists(self.index_path):
            self._write_json(self.index_path, {})

    def _read_json(self, path: str) -> Any:
        try:
            with open(path, encoding="utf-8") as f:
                return json.load(f)
        except FileNotFoundError:
            return None
        except Exception as e:
            logger.warning("Failed reading %s: %s", path, e)
            return None

    def _write_json(self, path: str, data: Any) -> None:
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)
        os.replace(tmp, path)

    def _load_index(self) -> dict[str, Any]:
        idx = self._read_json(self.index_path)
        if isinstance(idx, dict):
            return idx
        return {}

    def _save_index(self, idx: dict[str, Any]) -> None:
        self._write_json(self.index_path, idx)

    def _record_path(self, executed_workflow_id: str) -> str:
        return os.path.join(self.base_dir, f"{executed_workflow_id}.json")

    def _composite_key(self, session_id: str, workflow_id: str) -> str:
        return f"{session_id}::{workflow_id}"

    def _is_expired(self, executed_at_iso: str) -> bool:
        try:
            from datetime import datetime, timezone

            executed_at = datetime.fromisoformat(executed_at_iso.replace("Z", "+00:00"))
            now = datetime.now(timezone.utc)
            age = (now - executed_at).total_seconds()
            return age > self.ttl_seconds
        except Exception:
            # Fallback: never expire on parse failure
            return False

    def _prune_expired(self) -> None:
        idx = self._load_index()
        updated = False
        for comp_key, rec_id in list(idx.items()):
            path = self._record_path(rec_id)
            data = self._read_json(path)
            if not data:
                # missing file; remove index entry
                idx.pop(comp_key, None)
                updated = True
                continue
            executed_at = data.get("executed_at")
            if executed_at and self._is_expired(executed_at):
                try:
                    os.remove(path)
                except Exception:
                    pass
                idx.pop(comp_key, None)
                updated = True
        if updated:
            self._save_index(idx)

    def upsert_latest(
        self,
        ctx: Context,
        workflow_id: str,
        result: dict[str, Any],
    ) -> ExecutedWorkflow:
        session_id = _get_session_id(ctx)
        executed_workflow_id = uuid.uuid4().hex
        executed_at = _now_iso()
        status = str(result.get("status", "unknown"))

        record = {
            "executed_workflow_id": executed_workflow_id,
            "session_id": session_id,
            "workflow_id": workflow_id,
            "executed_at": executed_at,
            "status": status,
            "result": result,
        }

        # Write record
        path = self._record_path(executed_workflow_id)
        self._write_json(path, record)

        # Update index to point latest for (session, workflow)
        idx = self._load_index()
        idx[self._composite_key(session_id, workflow_id)] = executed_workflow_id
        self._save_index(idx)

        # Prune expired entries opportunistically
        self._prune_expired()

        return ExecutedWorkflow(
            executed_workflow_id=executed_workflow_id,
            session_id=session_id,
            workflow_id=workflow_id,
            executed_at=executed_at,
            status=status,
            result=result,
        )

    def get_by_id(self, ctx: Context, executed_workflow_id: str) -> ExecutedWorkflow | None:
        session_id = _get_session_id(ctx)
        data = self._read_json(self._record_path(executed_workflow_id))
        if not data:
            return None
        if data.get("session_id") != session_id:
            return None
        if data.get("executed_at") and self._is_expired(data["executed_at"]):
            return None
        return ExecutedWorkflow(
            executed_workflow_id=data["executed_workflow_id"],
            session_id=data["session_id"],
            workflow_id=data["workflow_id"],
            executed_at=data["executed_at"],
            status=data.get("status", "unknown"),
            result=data.get("result", {}),
        )

    def list_for_session(
        self, ctx: Context, workflow_id: str | None = None, limit: int = 50, offset: int = 0
    ) -> list[ExecutedWorkflow]:
        self._prune_expired()
        session_id = _get_session_id(ctx)
        logger.info(f"Listing executed workflows for session {session_id}")
        idx = self._load_index()
        # Collect latest ids for this session
        rec_ids: list[str] = []
        for comp_key, rec_id in idx.items():
            if comp_key.startswith(f"{session_id}::"):
                if workflow_id is None or comp_key.endswith(f"::{workflow_id}"):
                    rec_ids.append(rec_id)

        # Load records and filter expired
        records: list[ExecutedWorkflow] = []
        for rid in rec_ids:
            data = self._read_json(self._record_path(rid))
            if not data:
                continue
            if data.get("session_id") != session_id:
                continue
            if data.get("executed_at") and self._is_expired(data["executed_at"]):
                continue
            records.append(
                ExecutedWorkflow(
                    executed_workflow_id=data["executed_workflow_id"],
                    session_id=data["session_id"],
                    workflow_id=data["workflow_id"],
                    executed_at=data["executed_at"],
                    status=data.get("status", "unknown"),
                    result=data.get("result", {}),
                )
            )

        # Sort newest-first by executed_at
        try:
            from datetime import datetime

            records.sort(
                key=lambda r: datetime.fromisoformat(r.executed_at.replace("Z", "+00:00")),
                reverse=True,
            )
        except Exception:
            pass

        # Apply pagination
        return records[offset : offset + limit]


# Singleton store
_executed_store = ExecutedWorkflowStore()


def get_executed_store() -> ExecutedWorkflowStore:
    return _executed_store
