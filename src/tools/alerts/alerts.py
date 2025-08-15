"""
Alerts management tools for Splunk MCP Server.

This module provides tools for managing and querying Splunk alerts.
"""

from typing import Any

from fastmcp import Context

from src.core.base import BaseTool, ToolMetadata
from src.core.utils import log_tool_execution


class ListTriggeredAlerts(BaseTool):
    """Tool for listing triggered alerts in Splunk."""

    METADATA = ToolMetadata(
        name="list_triggered_alerts",
        description=(
            "List fired alerts and their details. Use this to review recent triggered alerts, including "
            "saved search name, trigger time, owner/app, and trigger reason. Supports a name filter and a "
            "max results cap. Note: Splunk's fired alerts feed may not strictly filter by time; earliest/" 
            "latest are advisory.\n\n"
            "Args:\n"
            "    count (int, optional): Maximum number of alert groups to return (default: 50)\n"
            "    earliest_time (str, optional): Advisory filter for earliest trigger time (default: '-24h@h')\n"
            "    latest_time (str, optional): Advisory filter for latest trigger time (default: 'now')\n"
            "    search (str, optional): Case-insensitive substring filter applied to alert group name\n\n"
            "Outputs: 'triggered_alerts' array, total counts, and the applied parameters.\n"
            "Security: results are constrained by the authenticated user's permissions."
        ),
        category="alerts",
        tags=["alerts", "monitoring", "troubleshooting", "fired-alerts"],
        requires_connection=True,
    )

    async def execute(
        self,
        ctx: Context,
        count: int = 50,
        earliest_time: str = "-24h@h",
        latest_time: str = "now",
        search: str = "",
    ) -> dict[str, Any]:
        """
        Execute the list triggered alerts tool.

        Args:
            ctx: MCP context containing client connection
            count: Maximum number of alerts to return (default: 50, max: 1000)
            earliest_time: Filter alerts triggered after this time (default: "-24h@h")
            latest_time: Filter alerts triggered before this time (default: "now")
            search: Search filter to apply to alert names or saved search names

        Returns:
            Dict containing list of triggered alerts with their details
        """
        log_tool_execution(
            "list_triggered_alerts",
            count=count,
            earliest_time=earliest_time,
            latest_time=latest_time,
            search=search,
        )

        is_available, service, error_msg = self.check_splunk_available(ctx)

        if not is_available:
            return self.format_error_response(error_msg)

        self.logger.info("Retrieving list of triggered alerts")
        await ctx.info("Retrieving list of triggered alerts")

        try:
            # Validate and use the provided parameters
            search_filter = search

            # Get Splunk service (already retrieved from check_splunk_available)

            # Get fired alerts from Splunk (fired_alerts is a collection, not a method)
            fired_alerts = service.fired_alerts

            alerts_data = []
            processed_count = 0

            for alert_group in fired_alerts:
                # Stop if we've reached the count limit
                if processed_count >= count:
                    break

                try:
                    # Get alert group properties
                    alert_name = getattr(alert_group, "name", "Unknown")
                    alert_count = getattr(alert_group, "count", 0)

                    # Apply search filter if provided
                    if search_filter and search_filter.lower() not in alert_name.lower():
                        continue

                    # Get individual alerts in this group
                    group_alerts = []
                    if hasattr(alert_group, "alerts"):
                        for alert in alert_group.alerts:
                            try:
                                alert_info = {
                                    "trigger_time": getattr(alert, "trigger_time", ""),
                                    "sid": getattr(alert, "sid", ""),
                                    "saved_search_name": getattr(alert, "saved_search_name", ""),
                                    "app": getattr(alert, "app", ""),
                                    "owner": getattr(alert, "owner", ""),
                                    "trigger_reason": getattr(alert, "trigger_reason", ""),
                                    "digest_mode": getattr(alert, "digest_mode", False),
                                }
                                # Add any additional alert properties
                                try:
                                    alert_info.update(
                                        {
                                            "result_count": getattr(alert, "result_count", 0),
                                            "server_host": getattr(alert, "server_host", ""),
                                            "server_uri": getattr(alert, "server_uri", ""),
                                        }
                                    )
                                except Exception:
                                    # Some properties might not be available
                                    pass

                                group_alerts.append(alert_info)
                            except Exception as alert_error:
                                # Log individual alert errors but continue
                                self.logger.warning(
                                    f"Error processing individual alert: {alert_error}"
                                )
                                continue

                    alert_group_data = {
                        "alert_name": alert_name,
                        "alert_count": alert_count,
                        "alerts": group_alerts,
                    }

                    # Add any additional group properties
                    try:
                        alert_group_data.update(
                            {
                                "content": getattr(alert_group, "content", {}),
                                "state": getattr(alert_group, "state", {}),
                                "access": getattr(alert_group, "access", {}),
                            }
                        )
                    except Exception:
                        # Some properties might not be available
                        pass

                    alerts_data.append(alert_group_data)
                    processed_count += 1

                except Exception as e:
                    # Log individual alert processing errors but continue
                    self.logger.warning(
                        f"Error processing alert group {getattr(alert_group, 'name', 'Unknown')}: {e}"
                    )
                    continue

            # Sort alerts by most recent trigger time if available
            try:
                alerts_data.sort(
                    key=lambda x: max(
                        (alert.get("trigger_time", "") for alert in x.get("alerts", [])), default=""
                    ),
                    reverse=True,
                )
            except Exception:
                # If sorting fails, continue with unsorted data
                pass

            await ctx.info(
                f"Found {len(alerts_data)} alert groups with {sum(len(group.get('alerts', [])) for group in alerts_data)} total alerts"
            )

            return self.format_success_response(
                {
                    "triggered_alerts": alerts_data,
                    "total_alert_groups": len(alerts_data),
                    "total_individual_alerts": sum(
                        len(group.get("alerts", [])) for group in alerts_data
                    ),
                    "search_parameters": {
                        "count": count,
                        "earliest_time": earliest_time,
                        "latest_time": latest_time,
                        "search_filter": search_filter or None,
                    },
                }
            )

        except Exception as e:
            self.logger.error(f"Failed to retrieve triggered alerts: {str(e)}")
            await ctx.error(f"Failed to retrieve triggered alerts: {str(e)}")
            return self.format_error_response(f"Failed to retrieve triggered alerts: {str(e)}")
