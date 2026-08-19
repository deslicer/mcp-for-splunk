"""Create a Splunk alert (scheduled saved search with trigger and actions)."""

from dataclasses import dataclass
from typing import Any, Literal

from fastmcp import Context

from src.core.base import BaseTool, ToolMetadata
from src.core.utils import log_tool_execution
from src.tools.alerts.alert_action_settings import AlertActionSettings
from src.tools.alerts.alert_saved_search import (
    create_alert_config,
    default_alert_app,
    find_alert_saved_search,
    namespace_for_create,
)
from src.tools.alerts.alert_tool_context import AlertContextMixin
from src.tools.search.saved_search_acl import get_saved_search_acl

SharingLevel = Literal["user", "app", "global"]


@dataclass(frozen=True)
class CreatedAlertNamespace:
    """Result of creating a saved search in a Splunk namespace."""

    app: str
    owner: str
    error: str | None = None


class CreateAlert(AlertContextMixin, BaseTool):
    """Create a scheduled Splunk alert with optional built-in or custom actions."""

    METADATA = ToolMetadata(
        name="create_alert",
        description=(
            "Create a Splunk alert (a scheduled saved search with trigger conditions). "
            "Actions can be any installed alert action, including custom ones, and more than "
            "one action is allowed. Call list_alert_actions first for custom action names and "
            "param keys.\n\n"
            "Args:\n"
            "    name (str): Unique alert name (required)\n"
            "    search (str): SPL query (required)\n"
            "    cron_schedule (str): Cron schedule, e.g. '*/5 * * * *' (required)\n"
            "    description (str, optional): Description\n"
            "    earliest_time (str, optional): Dispatch earliest time, e.g. '-15m'\n"
            "    latest_time (str, optional): Dispatch latest time, e.g. 'now'\n"
            "    app (str, optional): App context (default: search)\n"
            "    sharing (str, optional): user|app|global (default: user)\n"
            "    alert_type (str, optional): always|number of events|number of hosts|"
            "number of sources|custom (default: number of events)\n"
            "    alert_comparator (str, optional): greater than|less than|equal to|"
            "not equal to (default: greater than)\n"
            "    alert_threshold (str, optional): Threshold value (default: 0)\n"
            "    alert_condition (str, optional): Required when alert_type is custom\n"
            "    alert_track (bool, optional): Show in Triggered Alerts (default: true)\n"
            "    alert_severity (int, optional): 1-5 (default: 3)\n"
            "    actions (list, optional): [{name, params, enabled}]. Empty means track-only. "
            "Custom action params use keys from list_alert_actions.\n\n"
            "Outputs: created name, trigger, schedule, and applied action fields.\n"
            "Security: visibility and execution follow the chosen sharing level and user ACL."
        ),
        category="alerts",
        tags=["alerts", "create", "saved_searches", "alert-actions"],
        requires_connection=True,
    )

    async def execute(
        self,
        ctx: Context,
        name: str,
        search: str,
        cron_schedule: str,
        description: str = "",
        earliest_time: str = "-15m",
        latest_time: str = "now",
        app: str | None = None,
        sharing: SharingLevel = "user",
        is_visible: bool = True,
        alert_type: str = "number of events",
        alert_comparator: str = "greater than",
        alert_threshold: str = "0",
        alert_condition: str = "",
        alert_track: bool = True,
        alert_severity: int = 3,
        alert_digest_mode: bool = True,
        actions: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        log_tool_execution("create_alert", name=name, search=search[:50] + "...")
        is_available, service, error_msg = self.check_splunk_available(ctx)
        if not is_available:
            return await self.fail(ctx, error_msg, name=name, created=False)

        try:
            await self.notify_progress(ctx, 0, 100, f"Validating alert '{name}'")
            parsed_actions = AlertActionSettings().parse_actions(actions)
            validation_error = self._validate(
                name, search, cron_schedule, alert_type, alert_condition, alert_severity
            )
            if validation_error:
                return await self.fail(ctx, validation_error, name=name, created=False)
            unknown = await self.unknown_actions_message(ctx, service, parsed_actions)
            if unknown:
                return await self.fail(ctx, unknown, name=name, created=False)
            return await self._create(
                ctx,
                service,
                name=name,
                search=search,
                cron_schedule=cron_schedule,
                description=description,
                earliest_time=earliest_time,
                latest_time=latest_time,
                app=app,
                sharing=sharing,
                is_visible=is_visible,
                alert_type=alert_type,
                alert_comparator=alert_comparator,
                alert_threshold=alert_threshold,
                alert_condition=alert_condition,
                alert_track=alert_track,
                alert_severity=alert_severity,
                alert_digest_mode=alert_digest_mode,
                parsed_actions=parsed_actions,
            )
        except Exception as exc:
            self.logger.error("Failed to create alert '%s': %s", name, exc)
            return await self.fail(
                ctx, f"Failed to create alert '{name}': {exc}", name=name, created=False
            )

    def _validate(
        self,
        name: str,
        search: str,
        cron_schedule: str,
        alert_type: str,
        alert_condition: str,
        alert_severity: int,
    ) -> str | None:
        if not name.strip():
            return "Alert name cannot be empty"
        if not search.strip():
            return "Search query cannot be empty"
        if not cron_schedule.strip():
            return "cron_schedule is required"
        if alert_type.strip().lower() == "custom" and not alert_condition.strip():
            return "alert_condition is required when alert_type is custom"
        if alert_severity < 1 or alert_severity > 5:
            return "alert_severity must be between 1 and 5"
        return None

    async def _create(
        self,
        ctx: Context,
        service: Any,
        **kwargs: Any,
    ) -> dict[str, Any]:
        name = kwargs["name"]
        mapper = AlertActionSettings()
        config = create_alert_config(
            search=kwargs["search"],
            description=kwargs["description"],
            earliest_time=kwargs["earliest_time"],
            latest_time=kwargs["latest_time"],
            cron_schedule=kwargs["cron_schedule"],
            is_visible=kwargs["is_visible"],
            alert_type=kwargs["alert_type"],
            alert_comparator=kwargs["alert_comparator"],
            alert_threshold=str(kwargs["alert_threshold"]),
            alert_condition=kwargs["alert_condition"],
            alert_track=kwargs["alert_track"],
            alert_severity=kwargs["alert_severity"],
            alert_digest_mode=kwargs["alert_digest_mode"],
        )
        action_fields = mapper.splunk_fields(kwargs["parsed_actions"])
        config.update(action_fields)
        await ctx.info(f"Creating alert '{name}'")
        await self.notify_progress(ctx, 50, 100, f"Submitting alert '{name}'")
        created = self._create_in_namespace(
            service, name, config, kwargs["app"], kwargs["sharing"]
        )
        if created.error:
            return await self.fail(ctx, created.error, name=name, created=False)
        target_app, create_owner = created.app, created.owner
        saved_search = find_alert_saved_search(
            service, name, app=target_app, owner=create_owner if kwargs["sharing"] == "user" else None
        )
        if not saved_search:
            return await self.fail(
                ctx,
                f"Alert '{name}' was submitted but is not accessible after creation",
                name=name,
                created=False,
            )
        await self.notify_progress(ctx, 100, 100, f"Created alert '{name}'")
        acl = get_saved_search_acl(saved_search)
        return self.format_success_response(
            {
                "name": name,
                "created": True,
                "app": acl.get("app") or target_app,
                "owner": acl.get("owner") or create_owner,
                "sharing": kwargs["sharing"],
                "configuration": {
                    "search": config["search"],
                    "cron_schedule": kwargs["cron_schedule"],
                    "alert_type": kwargs["alert_type"],
                    "alert_comparator": kwargs["alert_comparator"],
                    "alert_threshold": str(kwargs["alert_threshold"]),
                    "alert_track": kwargs["alert_track"],
                    "actions": kwargs["parsed_actions"],
                    "applied_action_fields": action_fields,
                },
            }
        )

    def _create_in_namespace(
        self,
        service: Any,
        name: str,
        config: dict[str, str],
        app: str | None,
        sharing: SharingLevel,
    ) -> CreatedAlertNamespace:
        original_namespace = getattr(service, "namespace", None)
        create_owner = getattr(service, "username", None) or "admin"
        target_app = (app or default_alert_app()).strip()
        try:
            service.namespace = namespace_for_create(
                app=target_app, owner=create_owner, sharing=sharing
            )
            try:
                service.saved_searches[name]
            except KeyError:
                # Splunklib raises KeyError when this name is unused in the
                # create namespace. Continue with create.
                service.saved_searches.create(name, **config)
                return CreatedAlertNamespace(app=target_app, owner=create_owner)
            return CreatedAlertNamespace(
                app=target_app,
                owner=create_owner,
                error=f"Alert '{name}' already exists",
            )
        finally:
            service.namespace = original_namespace
