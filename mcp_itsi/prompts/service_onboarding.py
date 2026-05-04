"""Prompt: onboard a new ITSI service end-to-end."""

from __future__ import annotations

from fastmcp import Context

from mcp_itsi.core.base import BaseITSIPrompt, PromptMetadata


class ServiceOnboardingPrompt(BaseITSIPrompt):
    METADATA = PromptMetadata(
        name="itsi_service_onboarding",
        description=(
            "Walk through onboarding a new ITSI service following Splunk "
            "best practices: discovery → entities → KPIs → templates → "
            "visualisation → episodes."
        ),
        category="service-insights",
        tags=("itsi", "service", "onboarding"),
    )

    async def render(
        self,
        mcp_ctx: Context,
        service_name: str = "<service-name>",
        business_owner: str = "<business-owner>",
        environment: str = "production",
    ) -> str:
        return (
            f"You are an ITSI implementation engineer. Onboard the service "
            f"`{service_name}` (owner: `{business_owner}`, environment: "
            f"`{environment}`) end-to-end.\n\n"
            "Follow this plan and call the matching MCP tools at each step.\n\n"
            "1. **Discover** existing entities and KPI base searches:\n"
            "   - `itsi_get_alias_list` to learn the alias conventions in use.\n"
            '   - `itsi_list_entities filter=\'{"title":{"$regex":"..."}}\'`.\n'
            "   - `itsi_list_kpi_base_searches` and pick reusable searches.\n"
            "2. **Pick or create an entity type** so the new entities have\n"
            "   data drilldowns and vital metrics.\n"
            "3. **Define entities**: build a list of identifier alias values\n"
            "   for the hosts/containers backing the service. Create them with\n"
            "   `itsi_create_entity` (or arrange a recurring import).\n"
            "4. **Design the KPIs**: 2–6 high-signal metrics. Use\n"
            '   `itsi_search_docs query="KPI best practices"` if unsure.\n'
            "5. **Choose a service template**: list templates with\n"
            "   `itsi_list_service_templates`. If a good template exists, set\n"
            "   `base_service_template_id` on the new service.\n"
            "6. **Create the service** with `itsi_create_service` (set\n"
            "   `entity_rules`, `kpis`, `service_tags`, `sec_grp`).\n"
            "7. **Visualise**: confirm a glass table or home view exists,\n"
            "   otherwise propose one.\n"
            "8. **Alerting**: review correlation searches and aggregation\n"
            "   policies that should react to KPI severity for this service.\n"
            "9. **Verify**: re-read the service with `itsi_get_service` and\n"
            "   ensure KPIs report data.\n\n"
            "Always confirm with the user before mutating shared resources."
        )
