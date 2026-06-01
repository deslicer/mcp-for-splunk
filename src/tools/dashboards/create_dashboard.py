"""
Create a dashboard (Simple XML or Dashboard Studio) via Splunk REST API.
"""

import json
from typing import Any, Literal

from fastmcp import Context

from src.core.base import BaseTool, ToolMetadata
from src.core.utils import log_tool_execution
from src.tools.dashboards.studio_wrapper import (
    DashboardDefinitionPreparer,
    PreparedDashboard,
    ThemeParam,
)


class CreateDashboard(BaseTool):
    """
    Create a new dashboard in Splunk (Classic Simple XML or Dashboard Studio).

    Uses /servicesNS/{owner}/{app}/data/ui/views to create a dashboard with the
    provided definition. Supports optional overwrite and ACL (sharing/permissions).
    """

    METADATA = ToolMetadata(
        name="create_dashboard",
        description=(
            "Create a new dashboard in Splunk. Accepts Classic Simple XML (string) or "
            "Dashboard Studio JSON (object/string) via eai:data. Optionally overwrite "
            "if it exists and set sharing/permissions (ACL).\n\n"
            "Args:\n"
            "    name (str): Dashboard name (required)\n"
            "    definition (dict|str): Studio JSON (dict/string) or Classic XML (string) (required)\n"
            "    owner (str, optional): Dashboard owner. Default: 'nobody'\n"
            "    app (str, optional): App context. Default: 'search'\n"
            "    label (str, optional): Human label shown in UI\n"
            "    description (str, optional): Dashboard description\n"
            "    dashboard_type (str, optional): 'studio'|'classic'|'auto' (default: 'auto')\n"
            "    theme (str, optional): Dashboard Studio UI theme when wrapping JSON: "
            "'light', 'dark', or 'auto' (default: 'auto'). With 'auto', reads "
            "uiSettings.theme / theme from Studio JSON or pre-wrapped XML; falls back to "
            "'dark'. Ignored for Classic Simple XML.\n"
            "    sharing (str, optional): 'user'|'app'|'global'\n"
            "    read_perms (list[str], optional): Roles/users granted read\n"
            "    write_perms (list[str], optional): Roles/users granted write\n"
            "    overwrite (bool, optional): If True, updates existing dashboard of same name\n"
        ),
        category="dashboards",
        tags=["dashboards", "visualization", "ui", "create", "xml", "json"],
        requires_connection=True,
    )

    @staticmethod
    def _build_create_payload(name: str, prepared: PreparedDashboard) -> dict[str, Any]:
        """Splunk create handler accepts name and eai:data only."""
        return {
            "name": name,
            "eai:data": prepared.eai_data,
            "output_mode": "json",
        }

    @staticmethod
    def _should_skip_metadata_post(
        prepared: PreparedDashboard,
        *,
        label: str | None,
        description: str | None,
    ) -> bool:
        """Studio XML wrapper already embeds label/description when provided."""
        if prepared.resolved_type != "studio":
            return False
        data = prepared.eai_data
        if label and "<label>" not in data:
            return False
        if description and "<description>" not in data:
            return False
        return bool(label or description)

    @staticmethod
    def _update_dashboard_metadata(
        service: Any,
        *,
        owner: str,
        app: str,
        name: str,
        label: str | None,
        description: str | None,
    ) -> None:
        endpoint = f"/servicesNS/{owner}/{app}/data/ui/views/{name}"
        meta_payload: dict[str, Any] = {"output_mode": "json"}
        if label:
            meta_payload["label"] = label
        if description:
            meta_payload["description"] = description
        service.post(endpoint, **meta_payload)

    @staticmethod
    def _read_response_entry(response_body: bytes) -> dict[str, Any] | None:
        if not response_body:
            return None
        try:
            response_data = json.loads(response_body)
        except json.JSONDecodeError:
            return None
        if not isinstance(response_data, dict):
            return None
        entries = response_data.get("entry", [])
        if entries and isinstance(entries[0], dict):
            return entries[0]
        return None

    async def execute(
        self,
        ctx: Context,
        name: str,
        definition: Any,
        owner: str = "nobody",
        app: str = "search",
        label: str | None = None,
        description: str | None = None,
        dashboard_type: str = "auto",
        sharing: str | None = None,
        read_perms: list[str] | None = None,
        write_perms: list[str] | None = None,
        overwrite: bool = False,
        theme: ThemeParam = "auto",
    ) -> dict[str, Any]:
        """Create (or overwrite) a dashboard in Splunk."""
        log_tool_execution(
            "create_dashboard",
            name=name,
            owner=owner,
            app=app,
            label=label,
            dashboard_type=dashboard_type,
            theme=theme,
            overwrite=overwrite,
            sharing=sharing,
        )

        is_available, service, error_msg = self.check_splunk_available(ctx)

        if not is_available:
            await ctx.error(f"Create dashboard failed: {error_msg}")
            return self.format_error_response(error_msg)

        try:
            await ctx.report_progress(progress=5, total=100)

            prepared_result = DashboardDefinitionPreparer.prepare(
                definition,
                dashboard_type=dashboard_type,
                label=label,
                description=description,
                theme=theme,
            )
            if isinstance(prepared_result, str):
                return self.format_error_response(prepared_result)

            prepared = prepared_result
            resolved_type = prepared.resolved_type
            resolved_theme = prepared.resolved_theme

            await ctx.report_progress(progress=20, total=100)
            await ctx.info(
                f"Creating dashboard '{name}' (type={resolved_type}, owner={owner}, app={app}"
                + (
                    f", theme={resolved_theme}, size={prepared.definition_size_bytes} bytes"
                    if resolved_type == "studio"
                    else f", size={prepared.definition_size_bytes} bytes"
                )
                + ")"
            )

            splunk_host = getattr(service, "host", "localhost")
            web_scheme = getattr(service, "scheme", "https")
            web_port = 443 if web_scheme == "https" else 8000
            web_base = f"{web_scheme}://{splunk_host}:{web_port}"

            endpoint = f"/servicesNS/{owner}/{app}/data/ui/views"
            create_payload = self._build_create_payload(name, prepared)

            created = False
            entry: dict[str, Any] | None = None

            await ctx.report_progress(progress=35, total=100)
            try:
                response = service.post(endpoint, **create_payload)
                entry = self._read_response_entry(response.body.read())
                created = True
            except Exception as create_err:  # pylint: disable=broad-except
                err_str = str(create_err)
                if overwrite and ("409" in err_str or "exists" in err_str.lower()):
                    await ctx.info(f"Dashboard exists. Overwriting existing dashboard '{name}'")
                    update_endpoint = f"/servicesNS/{owner}/{app}/data/ui/views/{name}"
                    update_payload = {
                        key: value for key, value in create_payload.items() if key != "name"
                    }
                    response = service.post(update_endpoint, **update_payload)
                    entry = self._read_response_entry(response.body.read())
                else:
                    self.logger.error("Create dashboard failed: %s", err_str, exc_info=True)
                    await ctx.error(f"Failed to create dashboard: {err_str}")
                    detail = err_str
                    if "403" in err_str or "Forbidden" in err_str:
                        detail += " (Permission denied - check role/capabilities)"
                    elif "401" in err_str or "Unauthorized" in err_str:
                        detail += " (Authentication failed - check credentials)"
                    elif "404" in err_str or "Not Found" in err_str:
                        detail += " (Endpoint not found - check owner/app)"
                    elif "400" in err_str and "session" in err_str.lower():
                        detail += " (Session error - try reconnecting to Splunk)"
                    return self.format_error_response(detail)

            await ctx.report_progress(progress=75, total=100)

            if (label or description) and not self._should_skip_metadata_post(
                prepared, label=label, description=description
            ):
                try:
                    await self._update_dashboard_metadata(
                        service,
                        owner=owner,
                        app=app,
                        name=name,
                        label=label,
                        description=description,
                    )
                except Exception as meta_err:  # pylint: disable=broad-except
                    await ctx.warning(f"Label/description update failed: {str(meta_err)}")

            if sharing or read_perms or write_perms:
                try:
                    acl_endpoint = f"/servicesNS/{owner}/{app}/data/ui/views/{name}/acl"
                    acl_payload: dict[str, Any] = {"output_mode": "json"}
                    if sharing:
                        acl_payload["sharing"] = sharing
                    if read_perms:
                        acl_payload["perms.read"] = ",".join(read_perms)
                    if write_perms:
                        acl_payload["perms.write"] = ",".join(write_perms)
                    service.post(acl_endpoint, **acl_payload)
                except Exception as acl_err:  # pylint: disable=broad-except
                    await ctx.warning(f"ACL update failed: {str(acl_err)}")

            content = (entry or {}).get("content", {})
            acl = (entry or {}).get("acl", {})
            dashboard_app = acl.get("app", app)
            web_url = f"{web_base}/en-US/app/{dashboard_app}/{name}"

            await ctx.info(
                f"Dashboard '{name}' {'created' if created else 'updated'} (type={resolved_type})"
            )
            await ctx.report_progress(progress=100, total=100)

            response_payload: dict[str, Any] = {
                "name": name,
                "label": content.get("label", label or name),
                "type": resolved_type,
                "app": dashboard_app,
                "owner": acl.get("owner", owner),
                "sharing": acl.get("sharing", sharing or ""),
                "description": content.get("description", description or ""),
                "version": content.get("version", ""),
                "definition_size_bytes": prepared.definition_size_bytes,
                "permissions": {
                    "read": (acl.get("perms", {}) or {}).get("read", []),
                    "write": (acl.get("perms", {}) or {}).get("write", []),
                },
                "web_url": web_url,
                "id": (entry or {}).get("id", ""),
            }
            if resolved_type == "studio" and resolved_theme:
                response_payload["theme"] = resolved_theme
            return self.format_success_response(response_payload)

        except Exception as e:  # pylint: disable=broad-except
            self.logger.error("Failed to create dashboard: %s", str(e), exc_info=True)
            await ctx.error(f"Failed to create dashboard: {str(e)}")

            error_detail = str(e)
            if "403" in error_detail or "Forbidden" in error_detail:
                error_detail += " (Permission denied - check role/capabilities)"
            elif "401" in error_detail or "Unauthorized" in error_detail:
                error_detail += " (Authentication failed - check credentials)"
            elif "404" in error_detail or "Not Found" in error_detail:
                error_detail += " (Endpoint not found - check owner/app)"

            return self.format_error_response(error_detail)
