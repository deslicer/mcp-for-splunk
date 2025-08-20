import argparse
import asyncio
import dataclasses
import json
import os
from typing import Any

import mcp.types
from fastmcp import Client
from fastmcp.client.messages import MessageHandler
from fastmcp.client.transports import StreamableHttpTransport

INLINE_WORKFLOW_SHOW_CONNECTION_HEALTH: dict[str, Any] = {
    "workflow_id": "show_connection_health",
    "name": "Show Connection Health",
    "description": "Simple workflow that checks Splunk server connectivity and basic health status using get_splunk_health.",
    "tasks": [
        {
            "task_id": "server_health_check",
            "name": "Server Health Check",
            "description": "Check basic Splunk server health and connectivity",
            "instructions": (
                "Execute health check using get_splunk_health tool. Analyze server status, version, "
                "and connectivity source. Report any issues found and provide brief recommendations "
                "if status != 'connected'."
            ),
            "required_tools": ["get_splunk_health"],
            "dependencies": [],
            "context_requirements": []
        }
    ]
}


def get_env_headers() -> dict[str, str]:
    """Build Splunk client headers from env vars defined in env.example.

    Uses SPLUNK_* variables and maps them to X-Splunk-* headers.
    """
    verify_ssl = os.getenv("SPLUNK_VERIFY_SSL", "true").lower()
    default_scheme = "https" if verify_ssl == "true" else "http"

    headers: dict[str, str] = {
        "X-Splunk-Host": os.getenv("SPLUNK_HOST", ""),
        "X-Splunk-Port": os.getenv("SPLUNK_PORT", ""),
        "X-Splunk-Username": os.getenv("SPLUNK_USERNAME", ""),
        "X-Splunk-Password": os.getenv("SPLUNK_PASSWORD", ""),
        "X-Splunk-Scheme": os.getenv("SPLUNK_SCHEME", default_scheme),
        "X-Splunk-Verify-SSL": verify_ssl,
        "X-Session-ID": os.getenv("X_SESSION_ID", "env-splunk-session-workflows"),
        "Accept": os.getenv("HTTP_ACCEPT", "application/json, text/event-stream"),
    }

    # Drop empty values to avoid sending blank headers
    return {k: v for k, v in headers.items() if isinstance(v, str) and v != ""}


def to_jsonable(obj: Any) -> Any:
    """Recursively convert FastMCP content objects to JSON-serializable types."""
    if hasattr(obj, "model_dump") and callable(obj.model_dump):
        try:
            return to_jsonable(obj.model_dump())
        except (TypeError, ValueError, AttributeError):
            pass
    if dataclasses.is_dataclass(obj):
        return to_jsonable(dataclasses.asdict(obj))
    if isinstance(obj, dict):
        return {k: to_jsonable(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple, set)):
        return [to_jsonable(v) for v in obj]
    if isinstance(obj, (str, int, float, bool)) or obj is None:
        return obj
    return str(obj)


def to_plain_dict(obj: Any) -> dict[str, Any]:
    """Best-effort conversion to plain dict for FastMCP responses."""
    if isinstance(obj, dict):
        return obj
    if hasattr(obj, "model_dump") and callable(obj.model_dump):
        return obj.model_dump()  # type: ignore[no-any-return]
    # Fallback: try jsonable, then ensure dict
    val = to_jsonable(obj)
    return val if isinstance(val, dict) else {}


def get_field(obj: Any, key: str, default: Any = None) -> Any:
    data = to_plain_dict(obj)
    return data.get(key, default)


def print_tool_call(tool: str, params: dict[str, Any] | None, result: Any) -> None:
    print(f"\n=== tool: {tool} ===")
    if params:
        print("params:")
        print(json.dumps(params, indent=2))
    print("result:")
    print(json.dumps(to_jsonable(result), indent=2))


class LoggingHandler(MessageHandler):
    # Only print the actual logging message from the server
    async def on_logging_message(self, message: mcp.types.LoggingMessageNotification) -> None:
        message_text = getattr(message, "message", None)
        print(message_text or str(message))


async def progress_logger(progress: float, total: float | None, message: str | None) -> None:
    if total is not None and isinstance(progress, (int, float)) and isinstance(total, (int, float)) and total != 0:
        percentage = (progress / total) * 100.0
        print(f"Progress: {percentage:.1f}% - {message or ''}".rstrip())
    else:
        # No total available; print raw progress and message
        print(f"Progress: {progress} - {message or ''}".rstrip())


async def run_workflow_sequence(
    *,
    url: str,
    headers: dict[str, str],
    workflow_id: str,
    earliest_time: str,
    latest_time: str,
    focus_index: str | None,
    complexity_level: str,
    output_level: str,
) -> None:
    transport = StreamableHttpTransport(url=url, headers=headers)
    client = Client(transport, message_handler=LoggingHandler(), progress_handler=progress_logger)

    async with client:
        # Aggregate concise context of tool calls
        call_log: list[dict[str, Any]] = []
        # 1) List available workflows (summary + ids)
        lw_summary_params = {"format_type": "summary"}
        wf_summary = await client.call_tool("list_workflows", lw_summary_params)
        # Friendly, concise line
        print("Called list_workflows with format_type=summary")
        call_log.append({"tool": "list_workflows", "params": lw_summary_params})

        lw_ids_params = {"format_type": "ids_only"}
        wf_ids = await client.call_tool("list_workflows", lw_ids_params)
        # Print only the workflow IDs per request (top-level per format_success_response)
        ids_result = get_field(wf_ids, "all_workflow_ids", [])
        if not isinstance(ids_result, list):
            ids_result = []
        print(f"list_workflows(ids_only) -> all_workflow_ids: {ids_result}")
        call_log.append({
            "tool": "list_workflows",
            "params": lw_ids_params,
            "all_workflow_ids": ids_result,
        })

        # 2) Fetch workflow requirements (quick reference)
        wr_params = {"format_type": "quick"}
        requirements = await client.call_tool("workflow_requirements", wr_params)
        # Only print that it was called and success status
        wr_status = get_field(requirements, "status")
        print(f"workflow_requirements(format_type=quick) -> status: {wr_status}")
        call_log.append({
            "tool": "workflow_requirements",
            "params": wr_params,
            "status": wr_status,
        })

        # 3) Create a minimal workflow template using workflow_builder (example)
        wb_template_params = {"mode": "template", "template_type": "minimal"}
        template_resp = await client.call_tool("workflow_builder", wb_template_params)
        if output_level == "all":
            print_tool_call("workflow_builder", wb_template_params, template_resp)
        else:
            status_template = get_field(template_resp, "status")
            print(f"workflow_builder(template minimal) -> status: {status_template}")
        call_log.append({
            "tool": "workflow_builder",
            "params": wb_template_params,
            "status": get_field(template_resp, "status"),
        })

        # Additionally, process our inline custom workflow definition (kept in this script)
        wb_process_params = {"mode": "process", "workflow_data": INLINE_WORKFLOW_SHOW_CONNECTION_HEALTH}
        inline_processed = await client.call_tool("workflow_builder", wb_process_params)
        # Initialize variable for later summary output regardless of verbosity
        valid = get_field(inline_processed, "validation", {}).get("valid")
        if output_level == "all":
            print_tool_call("workflow_builder", {**wb_process_params, "workflow_data": "<inlined>"}, inline_processed)
        else:
            print(f"workflow_builder(process <inlined>) -> validation.valid: {valid}")
        call_log.append({
            "tool": "workflow_builder",
            "params": {"mode": "process", "workflow_data": "<inlined>"},
            "validation_valid": valid,
        })

        # 3b) Edit/update the inline workflow (adds an extra task per the edit mode)
        wb_edit_params = {"mode": "edit", "workflow_data": INLINE_WORKFLOW_SHOW_CONNECTION_HEALTH}
        inline_edited = await client.call_tool("workflow_builder", wb_edit_params)
        # Initialize edited_task_count for later summary output
        ewf = get_field(inline_edited, "edited_workflow", {})
        tasks = ewf.get("tasks") if isinstance(ewf, dict) else None
        edited_task_count = len(tasks) if isinstance(tasks, list) else None
        if output_level == "all":
            print_tool_call("workflow_builder", {**wb_edit_params, "workflow_data": "<inlined>"}, inline_edited)
        else:
            print(f"workflow_builder(edit <inlined>) -> edited_task_count: {edited_task_count}")
        call_log.append({
            "tool": "workflow_builder",
            "params": {"mode": "edit", "workflow_data": "<inlined>"},
            "edited_task_count": edited_task_count,
        })

        # 4) Run a workflow via workflow_runner (default to an existing workflow id)
        # Decide which workflow_id to run: prefer requested id, fallback to simple_health_check if unavailable
        available_ids = get_field(wf_ids, "all_workflow_ids", [])
        if not isinstance(available_ids, list):
            available_ids = []

        decided_workflow_id = workflow_id
        if decided_workflow_id not in available_ids:
            decided_workflow_id = "simple_health_check"

        run_params: dict[str, Any] = {
            "workflow_id": decided_workflow_id,
            "earliest_time": earliest_time,
            "latest_time": latest_time,
            "complexity_level": complexity_level,
            "enable_summarization": False,
        }
        if focus_index:
            run_params["focus_index"] = focus_index

        runner_result = await client.call_tool("workflow_runner", run_params, progress_handler=progress_logger)
        if output_level == "all":
            print_tool_call("workflow_runner", run_params, runner_result)
        else:
            runner_status = get_field(runner_result, "status")
            print(f"workflow_runner({decided_workflow_id}) -> status: {runner_status}")
        call_log.append({
            "tool": "workflow_runner",
            "params": run_params,
            "status": get_field(runner_result, "status"),
        })

        # Print concise, JSON-serializable outputs
        output = {
            "profile": "show",
            "server": {
                "url": url,
                "session_id": headers.get("X-Session-ID"),
            },
            "decided_workflow_id": decided_workflow_id,
            "list_workflows_ids": ids_result,
            "workflow_requirements_status": wr_status,
            "workflow_builder_processed_inline_valid": valid,
            "workflow_builder_edited_task_count": edited_task_count,
            "workflow_runner_status": get_field(runner_result, "status"),
            "calls": call_log,
        }
        # Final summary vs full output
        if output_level == "all":
            # Enrich with full objects as well
            output_full = {
                **output,
                "list_workflows_summary": to_jsonable(wf_summary),
                "workflow_builder_template_minimal": to_jsonable(template_resp),
                "workflow_builder_processed_inline": to_jsonable(inline_processed),
                "workflow_builder_inline_edited": to_jsonable(inline_edited),
                "workflow_runner_result": to_jsonable(runner_result),
            }
            print(json.dumps(output_full, indent=2))
        else:
            print(json.dumps(output, indent=2))


async def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Test workflow tooling against the Splunk MCP server: list → requirements → "
            "builder(template) → runner (execute chosen workflow)."
        )
    )
    parser.add_argument(
        "--workflow-id",
        default=os.getenv("WORKFLOW_ID", "show_connection_health"),
        help="Workflow ID to run with workflow_runner (default: show_connection_health)",
    )
    parser.add_argument(
        "--earliest",
        default=os.getenv("SPLUNK_EARLIEST", "-15m"),
        help="Earliest time for workflow context (default: -15m)",
    )
    parser.add_argument(
        "--latest",
        default=os.getenv("SPLUNK_LATEST", "now"),
        help="Latest time for workflow context (default: now)",
    )
    parser.add_argument(
        "--focus-index",
        default=os.getenv("SPLUNK_FOCUS_INDEX", ""),
        help="Optional focus index for workflows that use it",
    )
    parser.add_argument(
        "--complexity",
        choices=["basic", "moderate", "advanced"],
        default=os.getenv("WORKFLOW_COMPLEXITY", "moderate"),
        help="Workflow analysis complexity (default: moderate)",
    )
    parser.add_argument(
        "--output-level",
        choices=["summary", "all"],
        default=os.getenv("WORKFLOW_OUTPUT_LEVEL", "summary"),
        help="Control verbosity of printed results (default: summary)",
    )
    args = parser.parse_args()

    url = os.getenv("MCP_URL", "http://localhost:8002/mcp/")
    headers = get_env_headers()

    await run_workflow_sequence(
        url=url,
        headers=headers,
        workflow_id=args.workflow_id,
        earliest_time=args.earliest,
        latest_time=args.latest,
        focus_index=(args.focus_index or None),
        complexity_level=args.complexity,
        output_level=args.output_level,
    )


if __name__ == "__main__":
    asyncio.run(main())


