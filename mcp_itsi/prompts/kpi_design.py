"""Prompt: design KPIs for an ITSI service."""

from __future__ import annotations

from fastmcp import Context

from mcp_itsi.core.base import BaseITSIPrompt, PromptMetadata


class KpiDesignPrompt(BaseITSIPrompt):
    METADATA = PromptMetadata(
        name="itsi_kpi_design",
        description=(
            "Help an operator pick a small, high-signal set of KPIs for a "
            "service, including base search, statop, urgency and threshold "
            "strategy."
        ),
        category="kpi",
        tags=("itsi", "kpi", "design"),
    )

    async def render(
        self,
        mcp_ctx: Context,
        service_name: str = "<service-name>",
        business_outcome: str = "<business-outcome>",
    ) -> str:
        return (
            f"You are an SRE designing KPIs for the ITSI service "
            f"`{service_name}` whose business outcome is `{business_outcome}`.\n\n"
            "Produce a KPI plan with 4–6 KPIs. For each KPI, specify:\n"
            "- `title` (concise, action-oriented).\n"
            "- `kpi_base_search` reference (reuse if possible — call\n"
            "  `itsi_list_kpi_base_searches`).\n"
            "- `threshold_field` and `entity_statop` / `aggregate_statop`.\n"
            "- `urgency` (0–11). Reserve 10–11 for service-impacting KPIs.\n"
            "- Threshold template (`itsi_list_kpi_threshold_templates`) or\n"
            "  custom thresholds. Prefer adaptive thresholds for time-varying\n"
            "  metrics, static thresholds for SLO/SLI absolutes.\n"
            "- Whether `is_entity_breakdown` should be true (per-entity) or\n"
            "  false (service-wide aggregate).\n\n"
            "Validate the plan against `itsi://docs/best-practices` and call\n"
            "`itsi_search_docs` if you need more guidance. Output the plan as\n"
            "a markdown table, then a JSON snippet ready to drop into the\n"
            "`kpis` array of `itsi_create_service` or\n"
            "`itsi_update_service`."
        )
