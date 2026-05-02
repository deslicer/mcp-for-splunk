"""ITSI tool implementations.

This module exposes :func:`all_tools` which returns the canonical list of
:class:`BaseITSITool` classes shipped with the server. Adding a new tool is a
two-step process: write the class, then add it here.
"""

from __future__ import annotations

from mcp_itsi.core.base import BaseITSITool
from mcp_itsi.tools.deep_dive import GetDeepDive, ListDeepDives
from mcp_itsi.tools.docs import ListDocs, ReadDoc, SearchDocs
from mcp_itsi.tools.entity import (
    CreateEntity,
    DeleteEntity,
    GetEntity,
    ListEntities,
    UpdateEntity,
)
from mcp_itsi.tools.entity_type import GetEntityType, ListEntityTypes
from mcp_itsi.tools.event_management import (
    AcknowledgeNotableEvent,
    CloseNotableEvent,
    GetNotableEvent,
    ListAggregationPolicies,
    ListCorrelationSearches,
    ListNotableEvents,
)
from mcp_itsi.tools.glass_table import GetGlassTable, ListGlassTables
from mcp_itsi.tools.home_view import GetHomeView, ListHomeViews
from mcp_itsi.tools.kpi_base_search import GetKpiBaseSearch, ListKpiBaseSearches
from mcp_itsi.tools.kpi_threshold_template import (
    GetKpiThresholdTemplate,
    ListKpiThresholdTemplates,
)
from mcp_itsi.tools.maintenance import GetMaintenanceWindow, ListMaintenanceWindows
from mcp_itsi.tools.meta import GetAliasList, GetSupportedObjectTypes
from mcp_itsi.tools.service import (
    CountServices,
    CreateService,
    DeleteService,
    GetService,
    ListServices,
    UpdateService,
)
from mcp_itsi.tools.service_template import (
    GetServiceTemplate,
    ListServiceTemplates,
    TemplatizeService,
)
from mcp_itsi.tools.team import GetTeam, ListTeams


def all_tools() -> list[type[BaseITSITool]]:
    """Return every concrete ITSI tool class."""
    return [
        # Meta / discovery
        GetAliasList,
        GetSupportedObjectTypes,
        # Service Insights
        ListServices,
        GetService,
        CreateService,
        UpdateService,
        DeleteService,
        CountServices,
        ListServiceTemplates,
        GetServiceTemplate,
        TemplatizeService,
        # Entity & entity types
        ListEntities,
        GetEntity,
        CreateEntity,
        UpdateEntity,
        DeleteEntity,
        ListEntityTypes,
        GetEntityType,
        # KPI configuration
        ListKpiBaseSearches,
        GetKpiBaseSearch,
        ListKpiThresholdTemplates,
        GetKpiThresholdTemplate,
        # Visualisation
        ListGlassTables,
        GetGlassTable,
        ListHomeViews,
        GetHomeView,
        ListDeepDives,
        GetDeepDive,
        # Teams / RBAC
        ListTeams,
        GetTeam,
        # Event Analytics
        ListNotableEvents,
        GetNotableEvent,
        AcknowledgeNotableEvent,
        CloseNotableEvent,
        ListAggregationPolicies,
        ListCorrelationSearches,
        # Maintenance
        ListMaintenanceWindows,
        GetMaintenanceWindow,
        # Documentation as tools
        ListDocs,
        ReadDoc,
        SearchDocs,
    ]


__all__ = ["all_tools"]
