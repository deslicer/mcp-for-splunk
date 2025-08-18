"""
Tool for retrieving Splunk configurations.
"""

from typing import Any

try:
    from splunklib import client as splunk_client  # type: ignore
except Exception:  # splunklib may not be available in some test contexts
    splunk_client = None  # type: ignore

from fastmcp import Context

from src.core.base import BaseTool, ToolMetadata
from src.core.utils import log_tool_execution


class GetConfigurations(BaseTool):
    """
    Get Splunk configurations.
    """

    METADATA = ToolMetadata(
        name="get_configurations",
        description=(
            "Retrieves Splunk configuration settings from specified .conf files. "
            "Use this tool when you need to access or inspect Splunk configurations, "
            "such as for troubleshooting, auditing, or understanding settings in files like props.conf or inputs.conf. "
            "Access settings from any Splunk configuration file (props.conf, transforms.conf, "
            "inputs.conf, outputs.conf, etc.) either by entire file or specific stanza. "
            "Returns structured configuration data showing all settings and their values.\n\n"
            "Args:\n"
            "    conf_file (str): Configuration file name without .conf extension "
            "(e.g., 'props', 'transforms', 'inputs', 'outputs', 'server', 'web')\n"
            "    stanza (str, optional): Specific stanza name within the conf file to retrieve. "
            "If not provided, returns all stanzas in the file.\n"
            "    app (str, optional): Filter results to stanzas owned by this app (namespace).\n"
            "    owner (str, optional): Filter results to stanzas owned by this owner (user)."
        ),
        category="admin",
        tags=["configuration", "settings", "administration"],
        requires_connection=True,
    )

    async def execute(
        self, ctx: Context, conf_file: str, stanza: str = "", app: str = "", owner: str = ""
    ) -> dict[str, Any]:
        """
        Get Splunk configurations from specific configuration files.

        Args:
            conf_file (str): Configuration file name without .conf extension
                           (e.g., 'props', 'transforms', 'inputs', 'outputs', 'server', 'web')
            stanza (str, optional): Specific stanza name within the conf file to retrieve.
                                  If not provided, returns all stanzas in the file.

        Returns:
            Dict containing configuration settings with status, file name, and configuration data
        """
        log_tool_execution(
            "get_configurations", conf_file=conf_file, stanza=stanza, app=app, owner=owner
        )

        is_available, service, error_msg = self.check_splunk_available(ctx)

        if not is_available:
            return self.format_error_response(error_msg)

        # Normalize inputs to avoid SDK url-encoding issues (e.g., stray newlines)
        normalized_conf = (conf_file or "").strip()
        if normalized_conf.endswith(".conf"):
            normalized_conf = normalized_conf[: -len(".conf")]

        normalized_stanza = (stanza or "").strip()
        normalized_app = (app or "").strip()
        normalized_owner = (owner or "").strip()

        if not normalized_conf:
            return self.format_error_response("conf_file is required")

        # Debug the normalized parameters
        self.logger.debug(
            "GetConfigurations called with conf_file=%r, stanza=%r, app=%r, owner=%r",
            conf_file,
            stanza,
            app,
            owner,
        )
        self.logger.debug(
            "Normalized conf=%r, stanza=%r, app=%r, owner=%r",
            normalized_conf,
            normalized_stanza,
            normalized_app,
            normalized_owner,
        )

        self.logger.info("Retrieving configurations from %s", normalized_conf)
        await ctx.info(f"Retrieving configurations from {normalized_conf}")

        try:
            # Use REST API endpoint first to avoid url-encoding issues with certain configs
            import json

            def parse_stanzas_from_json(json_bytes: bytes) -> dict[str, dict[str, Any]]:
                stanzas: dict[str, dict[str, Any]] = {}
                try:
                    data = json.loads(json_bytes.decode("utf-8"))
                except Exception:
                    return stanzas
                entries = data.get("entry", []) if isinstance(data, dict) else []
                for entry in entries:
                    stanza_name = entry.get("name")
                    if not stanza_name:
                        continue
                    content = entry.get("content", {}) or {}
                    acl = entry.get("acl", {}) or {}
                    # Keep values as-is from Splunk JSON
                    stanza_settings: dict[str, Any] = {k: v for k, v in content.items()}
                    stanzas[stanza_name] = {
                        "settings": stanza_settings,
                        "app": acl.get("app"),
                        "owner": acl.get("owner"),
                    }
                return stanzas

            endpoint = f"/services/configs/conf-{normalized_conf}"
            # Build namespace attempts, prioritizing provided filters if set
            attempts: list[tuple[str | None, str | None]] = []
            if normalized_app or normalized_owner:
                attempts.append((normalized_owner or None, normalized_app or None))
            # Default fallbacks
            attempts.extend([(None, None), ("nobody", "search"), ("nobody", "system")])
            # Deduplicate while preserving order
            seen = set()
            dedup_attempts: list[tuple[str | None, str | None]] = []
            for t in attempts:
                if t not in seen:
                    dedup_attempts.append(t)
                    seen.add(t)
            attempts = dedup_attempts

            if normalized_stanza:
                self.logger.info("Retrieving configuration for stanza: %s", normalized_stanza)
                await ctx.info(f"Retrieving configuration for stanza: {normalized_stanza}")
                for ns_owner, ns_app in attempts:
                    try:
                        stanza_endpoint = f"{endpoint}/{normalized_stanza}"
                        self.logger.debug(
                            "REST GET %s (owner=%s, app=%s)", stanza_endpoint, ns_owner, ns_app
                        )
                        resp = service.get(
                            stanza_endpoint, owner=ns_owner, app=ns_app, output_mode="json"
                        )
                        parsed = parse_stanzas_from_json(resp.body.read())
                        if parsed:
                            stanza_info = parsed.get(
                                normalized_stanza, next(iter(parsed.values()), {})
                            )
                            # Apply optional filters on app/owner
                            acl_app = stanza_info.get("app")
                            acl_owner = stanza_info.get("owner")
                            if (normalized_app and acl_app != normalized_app) or (
                                normalized_owner and acl_owner != normalized_owner
                            ):
                                self.logger.debug(
                                    "Stanza found but filtered out by app/user (app=%s, owner=%s)",
                                    acl_app,
                                    acl_owner,
                                )
                                # continue searching
                                continue
                            result = {
                                "stanza": normalized_stanza,
                                "app": stanza_info.get("app"),
                                "owner": stanza_info.get("owner"),
                                "settings": stanza_info.get("settings", {}),
                            }
                            await ctx.info(
                                f"Retrieved configuration for stanza: {normalized_stanza}"
                            )
                            return self.format_success_response(result)
                    except Exception as rest_err:
                        self.logger.debug(
                            "REST stanza attempt failed (owner=%s, app=%s): %s",
                            ns_owner,
                            ns_app,
                            repr(rest_err),
                        )

                # Fallback to SDK confs access with namespace fallbacks
                try:
                    confs = service.confs[normalized_conf]
                    stanza_obj = confs[normalized_stanza]
                    result = {"stanza": normalized_stanza, "settings": dict(stanza_obj.content)}
                    await ctx.info(f"Retrieved configuration for stanza: {normalized_stanza}")
                    return self.format_success_response(result)
                except Exception:
                    if splunk_client is not None:
                        for fb_owner, fb_app in attempts[1:]:
                            try:
                                fb_service = splunk_client.Service(
                                    scheme=getattr(service, "scheme", "https"),
                                    host=getattr(service, "host", "localhost"),
                                    port=getattr(service, "port", 8089),
                                    token=getattr(service, "token", None),
                                    owner=fb_owner,
                                    app=fb_app,
                                )
                                stanza_obj = fb_service.confs[normalized_conf][normalized_stanza]
                                result = {
                                    "stanza": normalized_stanza,
                                    "settings": dict(stanza_obj.content),
                                }
                                await ctx.info(
                                    f"Retrieved configuration for stanza: {normalized_stanza}"
                                )
                                return self.format_success_response(result)
                            except Exception:
                                continue
                msg = f"Stanza '{normalized_stanza}' not found in {normalized_conf}."
                self.logger.error("%s", msg)
                await ctx.error(msg)
                return self.format_error_response(msg)

            # All stanzas via REST first
            all_stanzas: dict[str, dict[str, Any]] = {}
            for ns_owner, ns_app in attempts:
                try:
                    self.logger.debug("REST GET %s (owner=%s, app=%s)", endpoint, ns_owner, ns_app)
                    resp = service.get(
                        endpoint, owner=ns_owner, app=ns_app, output_mode="json", count=0
                    )
                    stanzas = parse_stanzas_from_json(resp.body.read())
                    if stanzas:
                        # Apply optional filters by app/owner
                        if normalized_app or normalized_owner:
                            filtered: dict[str, dict[str, Any]] = {}
                            for name, info in stanzas.items():
                                acl_app = info.get("app")
                                acl_owner = info.get("owner")
                                if normalized_app and acl_app != normalized_app:
                                    continue
                                if normalized_owner and acl_owner != normalized_owner:
                                    continue
                                filtered[name] = info
                            stanzas = filtered
                        if stanzas:
                            all_stanzas.update(stanzas)
                        break
                except Exception as rest_err:
                    self.logger.debug(
                        "REST list attempt failed (owner=%s, app=%s): %s",
                        ns_owner,
                        ns_app,
                        repr(rest_err),
                    )

            if not all_stanzas:
                # Fallback to SDK confs iteration with namespace fallback
                try:
                    confs = service.confs[normalized_conf]
                    for stanza_obj in confs:
                        all_stanzas[stanza_obj.name] = dict(stanza_obj.content)
                except Exception:
                    if splunk_client is not None:
                        for fb_owner, fb_app in attempts[1:]:
                            try:
                                fb_service = splunk_client.Service(
                                    scheme=getattr(service, "scheme", "https"),
                                    host=getattr(service, "host", "localhost"),
                                    port=getattr(service, "port", 8089),
                                    token=getattr(service, "token", None),
                                    owner=fb_owner,
                                    app=fb_app,
                                )
                                confs = fb_service.confs[normalized_conf]
                                for stanza_obj in confs:
                                    all_stanzas[stanza_obj.name] = dict(stanza_obj.content)
                                if all_stanzas:
                                    break
                            except Exception:
                                continue

            self.logger.debug(
                "Collected %d stanzas: %s", len(all_stanzas), list(all_stanzas.keys())[:10]
            )
            await ctx.info(f"Retrieved {len(all_stanzas)} stanzas from {normalized_conf}")
            return self.format_success_response({"file": normalized_conf, "stanzas": all_stanzas})
        except Exception as e:
            # Log full stack trace for diagnostics
            self.logger.exception("Failed to get configurations")
            await ctx.error(f"Failed to get configurations: {str(e)}")
            return self.format_error_response(str(e))
