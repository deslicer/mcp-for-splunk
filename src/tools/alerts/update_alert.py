"""Update an existing Splunk alert, including patch or override of actions."""

from typing import Any, Literal

from fastmcp import Context

from src.core.base import BaseTool, ToolMetadata
from src.core.utils import log_tool_execution, sanitize_search_query
from src.tools.alerts.alert_action_settings import AlertActionSettings
from src.tools.alerts.alert_saved_search import (
    apply_saved_search_namespace,
    find_alert_saved_search,
)
from src.tools.alerts.alert_tool_context import AlertContextMixin
from src.tools.search.saved_search_acl import get_saved_search_acl

ActionsMode = Literal["patch", "override"]


class UpdateAlert(AlertContextMixin, BaseTool):
    """Partially update an alert, with patch or override for actions."""

    METADATA = ToolMetadata(
        name="update_alert",
        description=(
            "Update an existing Splunk alert (a scheduled saved search with trigger conditions "
            "and optional actions). Omit any field you do not want to change. Search, schedule, "
            "trigger, and tracking fields are always patched.\n\n"
            "actions_mode (only applies when actions is sent):\n"
            "    patch (default): Change only the listed actions and params. Other actions and "
            "unspecified params on those actions stay as they are. Use this to change one setting "
            "(for example only email.to). Set enabled=false on an action to turn that action off "
            "without touching the others.\n"
            "    override: The actions list becomes the full set. Listed actions are enabled with "
            "the given params; any action currently on the alert but missing from the list is "
            "disabled. Use this when you want the alert to have exactly these actions.\n\n"
            "Call list_alert_actions first for custom actions and their param names.\n\n"
            "Args:\n"
            "    name (str): Alert name (required)\n"
            "    app (str, optional): App context for lookup\n"
            "    owner (str, optional): Owner context for lookup\n"
            "    search (str, optional): New SPL query\n"
            "    description (str, optional): New description\n"
            "    cron_schedule (str, optional): New cron schedule\n"
            "    earliest_time (str, optional): New dispatch earliest time\n"
            "    latest_time (str, optional): New dispatch latest time\n"
            "    alert_type (str, optional): Trigger type\n"
            "    alert_comparator (str, optional): Comparator\n"
            "    alert_threshold (str, optional): Threshold\n"
            "    alert_condition (str, optional): Custom trigger search\n"
            "    alert_track (bool, optional): Show in Triggered Alerts\n"
            "    alert_severity (int, optional): 1-5\n"
            "    actions_mode (str, optional): patch|override (default: patch)\n"
            "    actions (list, optional): [{name, params, enabled}]\n"
        ),
        category="alerts",
        tags=["alerts", "update", "saved_searches", "alert-actions"],
        requires_connection=True,
    )

    async def execute(
        self,
        ctx: Context,
        name: str,
        app: str | None = None,
        owner: str | None = None,
        search: str | None = None,
        description: str | None = None,
        cron_schedule: str | None = None,
        earliest_time: str | None = None,
        latest_time: str | None = None,
        is_visible: bool | None = None,
        alert_type: str | None = None,
        alert_comparator: str | None = None,
        alert_threshold: str | None = None,
        alert_condition: str | None = None,
        alert_track: bool | None = None,
        alert_severity: int | None = None,
        alert_digest_mode: bool | None = None,
        actions_mode: ActionsMode = "patch",
        actions: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        log_tool_execution("update_alert", name=name, actions_mode=actions_mode)
        is_available, service, error_msg = self.check_splunk_available(ctx)
        if not is_available:
            return await self.fail(ctx, error_msg, name=name, updated=False)

        try:
            if not name.strip():
                return await self.fail(
                    ctx, "Alert name cannot be empty", name=name, updated=False
                )
            if actions_mode not in ("patch", "override"):
                return await self.fail(
                    ctx,
                    "actions_mode must be 'patch' or 'override'",
                    name=name,
                    updated=False,
                )
            mapper = AlertActionSettings()
            parsed_actions = mapper.parse_actions(actions) if actions is not None else None
            if parsed_actions is not None and not parsed_actions:
                if actions_mode == "override":
                    return await self.fail(
                        ctx,
                        "actions_mode=override requires a non-empty actions list. "
                        "Omit actions to leave them unchanged, or use patch with "
                        "enabled=false to disable one action.",
                        name=name,
                        updated=False,
                    )
                parsed_actions = None
            unknown = await self.unknown_actions_message(ctx, service, parsed_actions)
            if unknown:
                return await self.fail(ctx, unknown, name=name, updated=False)
            return await self._update(
                ctx,
                service,
                mapper,
                name=name,
                app=app,
                owner=owner,
                search=search,
                description=description,
                cron_schedule=cron_schedule,
                earliest_time=earliest_time,
                latest_time=latest_time,
                is_visible=is_visible,
                alert_type=alert_type,
                alert_comparator=alert_comparator,
                alert_threshold=alert_threshold,
                alert_condition=alert_condition,
                alert_track=alert_track,
                alert_severity=alert_severity,
                alert_digest_mode=alert_digest_mode,
                actions_mode=actions_mode,
                parsed_actions=parsed_actions,
            )
        except Exception as exc:
            self.logger.error("Failed to update alert '%s': %s", name, exc)
            return await self.fail(
                ctx, f"Failed to update alert '{name}': {exc}", name=name, updated=False
            )

    async def _update(
        self,
        ctx: Context,
        service: Any,
        mapper: AlertActionSettings,
        **kwargs: Any,
    ) -> dict[str, Any]:
        name = kwargs["name"]
        saved_search = find_alert_saved_search(
            service, name, kwargs["app"], kwargs["owner"]
        )
        if not saved_search:
            return await self.fail(
                ctx, f"Alert '{name}' not found", name=name, updated=False
            )
        update_config = self._scalar_updates(kwargs)
        if kwargs["parsed_actions"] is not None:
            content = dict(getattr(saved_search, "content", None) or {})
            if kwargs["actions_mode"] == "override":
                update_config.update(mapper.override_fields(content, kwargs["parsed_actions"]))
            else:
                update_config.update(mapper.patch_fields(content, kwargs["parsed_actions"]))
        if not update_config:
            return await self.fail(
                ctx, "No updates provided", name=name, updated=False
            )
        await ctx.info(f"Updating alert '{name}' ({kwargs['actions_mode']})")
        await self.notify_progress(ctx, 50, 100, f"Updating alert '{name}'")
        original_namespace = apply_saved_search_namespace(service, saved_search)
        try:
            saved_search = service.saved_searches[saved_search.name]
            saved_search.update(**update_config).refresh()
        finally:
            service.namespace = original_namespace
        await self.notify_progress(ctx, 100, 100, f"Updated alert '{name}'")
        acl = get_saved_search_acl(saved_search)
        return self.format_success_response(
            {
                "name": name,
                "updated": True,
                "actions_mode": kwargs["actions_mode"] if kwargs["parsed_actions"] is not None else None,
                "changes": sorted(update_config.keys()),
                "app": acl.get("app", ""),
                "owner": acl.get("owner", ""),
            }
        )

    def _scalar_updates(self, kwargs: dict[str, Any]) -> dict[str, str]:
        config: dict[str, str] = {}
        if kwargs["search"] is not None:
            config["search"] = sanitize_search_query(kwargs["search"])
        if kwargs["description"] is not None:
            config["description"] = kwargs["description"]
        if kwargs["cron_schedule"] is not None:
            config["cron_schedule"] = kwargs["cron_schedule"]
            config["is_scheduled"] = "1"
        if kwargs["earliest_time"] is not None:
            config["dispatch.earliest_time"] = kwargs["earliest_time"]
        if kwargs["latest_time"] is not None:
            config["dispatch.latest_time"] = kwargs["latest_time"]
        if kwargs["is_visible"] is not None:
            config["is_visible"] = "1" if kwargs["is_visible"] else "0"
        if kwargs["alert_type"] is not None:
            config["alert_type"] = kwargs["alert_type"]
        if kwargs["alert_comparator"] is not None:
            config["alert_comparator"] = kwargs["alert_comparator"]
        if kwargs["alert_threshold"] is not None:
            config["alert_threshold"] = str(kwargs["alert_threshold"])
        if kwargs["alert_condition"] is not None:
            config["alert_condition"] = kwargs["alert_condition"]
        if kwargs["alert_track"] is not None:
            config["alert.track"] = "1" if kwargs["alert_track"] else "0"
        if kwargs["alert_severity"] is not None:
            config["alert.severity"] = str(kwargs["alert_severity"])
        if kwargs["alert_digest_mode"] is not None:
            config["alert.digest_mode"] = "1" if kwargs["alert_digest_mode"] else "0"
        return config
