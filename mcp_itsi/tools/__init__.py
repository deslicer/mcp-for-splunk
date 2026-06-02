"""ITSI tool implementations.

This module exposes :func:`all_tools` which returns the canonical list of
:class:`BaseITSITool` classes shipped with the server. Adding a new tool is a
two-step process: write the class, then add it here.
"""

from __future__ import annotations

from mcp_itsi.core.base import BaseITSITool
from mcp_itsi.tools.aggregation_policy import (
    CreateAggregationPolicy,
    DeleteAggregationPolicy,
    GetAggregationPolicy,
    UpdateAggregationPolicy,
)
from mcp_itsi.tools.correlation_search import (
    CreateCorrelationSearch,
    DeleteCorrelationSearch,
    GetCorrelationSearch,
    UpdateCorrelationSearch,
)
from mcp_itsi.tools.deep_dive import (
    CreateDeepDive,
    DeleteDeepDive,
    GetDeepDive,
    ListDeepDives,
    UpdateDeepDive,
)
from mcp_itsi.tools.docs import ListDocs, ReadDoc, SearchDocs
from mcp_itsi.tools.entity import (
    CreateEntity,
    DeleteEntity,
    GetEntity,
    ListEntities,
    UpdateEntity,
)
from mcp_itsi.tools.entity_type import (
    CreateEntityType,
    DeleteEntityType,
    GetEntityType,
    ListEntityTypes,
    UpdateEntityType,
)
from mcp_itsi.tools.event_management import (
    AcknowledgeNotableEvent,
    CloseNotableEvent,
    GetNotableEvent,
    ListAggregationPolicies,
    ListCorrelationSearches,
    ListNotableEvents,
)
from mcp_itsi.tools.glass_table import (
    CreateGlassTable,
    DeleteGlassTable,
    GetGlassTable,
    ListGlassTables,
    UpdateGlassTable,
)
from mcp_itsi.tools.home_view import (
    CreateHomeView,
    DeleteHomeView,
    GetHomeView,
    ListHomeViews,
    UpdateHomeView,
)
from mcp_itsi.tools.kpi_base_search import (
    CreateKpiBaseSearch,
    DeleteKpiBaseSearch,
    GetKpiBaseSearch,
    ListKpiBaseSearches,
    UpdateKpiBaseSearch,
)
from mcp_itsi.tools.kpi_threshold_template import (
    CreateKpiThresholdTemplate,
    DeleteKpiThresholdTemplate,
    GetKpiThresholdTemplate,
    ListKpiThresholdTemplates,
    UpdateKpiThresholdTemplate,
)
from mcp_itsi.tools.maintenance import GetMaintenanceWindow, ListMaintenanceWindows
from mcp_itsi.tools.meta import GetAliasList, GetSupportedObjectTypes
from mcp_itsi.tools.schema import (
    GetObjectSchema,
    ListObjectSchemas,
    ValidateObjectPayload,
)
from mcp_itsi.tools.service import (
    CountServices,
    CreateService,
    DeleteService,
    GetService,
    ListServices,
    UpdateService,
)
from mcp_itsi.tools.service_template import (
    CreateServiceTemplate,
    DeleteServiceTemplate,
    GetServiceTemplate,
    ListServiceTemplates,
    TemplatizeService,
    UpdateServiceTemplate,
)
from mcp_itsi.tools.team import GetTeam, ListTeams


def all_tools() -> list[type[BaseITSITool]]:
    """Return every concrete ITSI tool class."""
    return [
        # Meta / discovery
        GetAliasList,
        GetSupportedObjectTypes,
        # Schema / validation
        ListObjectSchemas,
        GetObjectSchema,
        ValidateObjectPayload,
        # Service Insights
        ListServices,
        GetService,
        CreateService,
        UpdateService,
        DeleteService,
        CountServices,
        ListServiceTemplates,
        GetServiceTemplate,
        CreateServiceTemplate,
        UpdateServiceTemplate,
        DeleteServiceTemplate,
        TemplatizeService,
        # Entity & entity types
        ListEntities,
        GetEntity,
        CreateEntity,
        UpdateEntity,
        DeleteEntity,
        ListEntityTypes,
        GetEntityType,
        CreateEntityType,
        UpdateEntityType,
        DeleteEntityType,
        # KPI configuration
        ListKpiBaseSearches,
        GetKpiBaseSearch,
        CreateKpiBaseSearch,
        UpdateKpiBaseSearch,
        DeleteKpiBaseSearch,
        ListKpiThresholdTemplates,
        GetKpiThresholdTemplate,
        CreateKpiThresholdTemplate,
        UpdateKpiThresholdTemplate,
        DeleteKpiThresholdTemplate,
        # Visualisation
        ListGlassTables,
        GetGlassTable,
        CreateGlassTable,
        UpdateGlassTable,
        DeleteGlassTable,
        ListHomeViews,
        GetHomeView,
        CreateHomeView,
        UpdateHomeView,
        DeleteHomeView,
        ListDeepDives,
        GetDeepDive,
        CreateDeepDive,
        UpdateDeepDive,
        DeleteDeepDive,
        # Teams / RBAC
        ListTeams,
        GetTeam,
        # Event Analytics
        ListNotableEvents,
        GetNotableEvent,
        AcknowledgeNotableEvent,
        CloseNotableEvent,
        ListAggregationPolicies,
        GetAggregationPolicy,
        CreateAggregationPolicy,
        UpdateAggregationPolicy,
        DeleteAggregationPolicy,
        ListCorrelationSearches,
        GetCorrelationSearch,
        CreateCorrelationSearch,
        UpdateCorrelationSearch,
        DeleteCorrelationSearch,
        # Maintenance
        ListMaintenanceWindows,
        GetMaintenanceWindow,
        # Documentation as tools
        ListDocs,
        ReadDoc,
        SearchDocs,
    ]


__all__ = ["all_tools"]
