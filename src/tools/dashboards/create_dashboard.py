"""
Create a dashboard (Simple XML or Dashboard Studio) via Splunk REST API.
"""

import json
from typing import Any

from fastmcp import Context

from src.core.base import BaseTool, ToolMetadata
from src.core.utils import log_tool_execution


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
            "    sharing (str, optional): 'user'|'app'|'global'\n"
            "    read_perms (list[str], optional): Roles/users granted read\n"
            "    write_perms (list[str], optional): Roles/users granted write\n"
            "    overwrite (bool, optional): If True, updates existing dashboard of same name\n"
        ),
        category="dashboards",
        tags=["dashboards", "visualization", "ui", "create", "xml", "json"],
        requires_connection=True,
    )

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
    ) -> dict[str, Any]:
        """
        Create (or overwrite) a dashboard in Splunk.
        """
        log_tool_execution(
            "create_dashboard",
            name=name,
            owner=owner,
            app=app,
            label=label,
            dashboard_type=dashboard_type,
            overwrite=overwrite,
            sharing=sharing,
        )

        is_available, service, error_msg = self.check_splunk_available(ctx)

        if not is_available:
            await ctx.error(f"Create dashboard failed: {error_msg}")
            return self.format_error_response(error_msg)

        try:
            # Determine Studio vs Classic and prepare eai:data
            resolved_type = dashboard_type
            eai_data: str

            if resolved_type not in ("studio", "classic", "auto"):
                resolved_type = "auto"

            if resolved_type == "auto":
                if isinstance(definition, dict):
                    resolved_type = "studio"
                    eai_data = json.dumps(definition)
                elif isinstance(definition, str):
                    # Heuristics: Studio hybrid (<definition>) or pure JSON
                    if "<definition>" in definition:
                        resolved_type = "studio"
                        eai_data = definition
                    else:
                        try:
                            json.loads(definition)
                            resolved_type = "studio"
                            eai_data = definition
                        except (json.JSONDecodeError, TypeError):
                            resolved_type = "classic"
                            eai_data = definition
                else:
                    return self.format_error_response(
                        "Invalid 'definition' type. Expect dict or str"
                    )
            elif resolved_type == "studio":
                if isinstance(definition, dict):
                    eai_data = json.dumps(definition)
                elif isinstance(definition, str):
                    eai_data = definition
                else:
                    return self.format_error_response(
                        "Studio dashboards require JSON (dict) or JSON string"
                    )
            else:  # classic
                if not isinstance(definition, str):
                    return self.format_error_response(
                        "Classic dashboards require XML string definition"
                    )
                eai_data = definition

            await ctx.info(
                f"Creating dashboard '{name}' (type={resolved_type}, owner={owner}, app={app})"
            )

            # Web URL for response (use Splunk Web port 8000, not management port)
            splunk_host = service.host
            web_port = 8000  # Splunk Web UI port (management API is on service.port which is 8089)
            web_scheme = "https"
            web_base = f"{web_scheme}://{splunk_host}:{web_port}"

            # Create first; on conflict and overwrite=True, update existing
            created = False
            response_data: dict[str, Any] | None = None
            try:
                # Initial create: only name and eai:data
                # Use full path like list_dashboards does
                endpoint = f"/servicesNS/{owner}/{app}/data/ui/views"

                # Don't pass owner/app as separate params - they're in the path
                response = service.post(
                    endpoint,
                    name=name,
                    **{"eai:data": eai_data, "output_mode": "json"},
                )
                response_body = response.body.read()
                response_data = json.loads(response_body) if response_body else {}
                created = True
            except Exception as create_err:  # pylint: disable=broad-except
                err_str = str(create_err)
                if overwrite and ("409" in err_str or "exists" in err_str.lower()):
                    await ctx.info(f"Dashboard exists. Overwriting existing dashboard '{name}'")
                    # Update allows eai:data only (no name parameter)
                    endpoint = f"/servicesNS/{owner}/{app}/data/ui/views/{name}"
                    response = service.post(
                        endpoint, **{"eai:data": eai_data, "output_mode": "json"}
                    )
                    response_body = response.body.read()
                    response_data = json.loads(response_body) if response_body else {}
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

            # Optional: Update label/description if provided (separate API call)
            if label or description:
                try:
                    endpoint = f"/servicesNS/{owner}/{app}/data/ui/views/{name}"
                    meta_payload: dict[str, Any] = {"output_mode": "json"}
                    if label:
                        meta_payload["label"] = label
                    if description:
                        meta_payload["description"] = description
                    service.post(endpoint, **meta_payload)
                except Exception as meta_err:  # pylint: disable=broad-except
                    # Non-fatal: dashboard was created, just label/description update failed
                    await ctx.warning(f"Label/description update failed: {str(meta_err)}")

            # Optional ACL update (sharing/perms)
            if sharing or read_perms or write_perms:
                try:
                    endpoint = f"/servicesNS/{owner}/{app}/data/ui/views/{name}/acl"
                    acl_payload: dict[str, Any] = {"output_mode": "json"}
                    if sharing:
                        acl_payload["sharing"] = sharing
                    if read_perms:
                        acl_payload["perms.read"] = ",".join(read_perms)
                    if write_perms:
                        acl_payload["perms.write"] = ",".join(write_perms)
                    service.post(endpoint, **acl_payload)
                except Exception as acl_err:  # pylint: disable=broad-except
                    # Non-fatal: include warning in response
                    await ctx.warning(f"ACL update failed: {str(acl_err)}")

            # Parse response entry (best-effort)
            entry = None
            if isinstance(response_data, dict):
                entries = response_data.get("entry", [])
                if entries:
                    entry = entries[0]

            # Fallbacks if server didn't echo entry
            content = (entry or {}).get("content", {}) if entry else {}
            acl = (entry or {}).get("acl", {}) if entry else {}

            # Determine dashboard app for web URL
            dashboard_app = acl.get("app", app)
            web_url = f"{web_base}/en-US/app/{dashboard_app}/{name}"

            # Determine type (reuse read logic heuristics)
            eai_data_from_resp = content.get("eai:data", eai_data)
            detected_type = "classic"
            if eai_data_from_resp:
                if "<definition>" in str(eai_data_from_resp):
                    detected_type = "studio"
                else:
                    try:
                        json.loads(eai_data_from_resp)
                        detected_type = "studio"
                    except Exception:  # noqa: BLE001
                        detected_type = "classic"

            await ctx.info(
                f"Dashboard '{name}' {'created' if created else 'updated'} (type={detected_type})"
            )

            return self.format_success_response(
                {
                    "name": name,
                    "label": content.get("label", label or name),
                    "type": detected_type,
                    "app": dashboard_app,
                    "owner": acl.get("owner", owner),
                    "sharing": acl.get("sharing", sharing or ""),
                    "description": content.get("description", description or ""),
                    "version": content.get("version", ""),
                    "permissions": {
                        "read": (acl.get("perms", {}) or {}).get("read", []),
                        "write": (acl.get("perms", {}) or {}).get("write", []),
                    },
                    "web_url": web_url,
                    "id": (entry or {}).get("id", ""),
                }
            )

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
