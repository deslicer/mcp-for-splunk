"""
Splunk dashboard tools for listing and viewing dashboards.
"""

from mcp_server_for_splunk.tools.dashboards.get_dashboard_definition import GetDashboardDefinition
from mcp_server_for_splunk.tools.dashboards.list_dashboards import ListDashboards

__all__ = ["ListDashboards", "GetDashboardDefinition"]
