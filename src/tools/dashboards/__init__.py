"""
Splunk dashboard tools for listing and viewing dashboards.
"""

from src.tools.dashboards.get_dashboard_definition import GetDashboardDefinition
from src.tools.dashboards.list_dashboards import ListDashboards

__all__ = ["ListDashboards", "GetDashboardDefinition"]
