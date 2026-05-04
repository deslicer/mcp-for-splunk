"""Prompt: triage an ITSI notable event / episode."""

from __future__ import annotations

from fastmcp import Context

from mcp_itsi.core.base import BaseITSIPrompt, PromptMetadata


class EpisodeTriagePrompt(BaseITSIPrompt):
    METADATA = PromptMetadata(
        name="itsi_episode_triage",
        description=(
            "Triage an ITSI notable event end-to-end: enrich, correlate, "
            "decide on owner, and either acknowledge / close it."
        ),
        category="event-analytics",
        tags=("itsi", "episode", "triage"),
    )

    async def render(
        self,
        mcp_ctx: Context,
        event_id: str = "<event-id>",
    ) -> str:
        return (
            f"You are an on-call engineer. Triage notable event `{event_id}`.\n\n"
            "Run this playbook strictly in order:\n\n"
            "1. **Read the event**: `itsi_get_notable_event event_id=...`.\n"
            "   Note severity, status, owner, affected services, drilldown\n"
            "   info.\n"
            "2. **Correlate**: list other open notable events on the same\n"
            "   service(s) with `itsi_list_notable_events filter=...`.\n"
            "3. **Inspect impacted services**: `itsi_get_service key=...`\n"
            "   for each `service_id`. Highlight any KPIs in WARNING/CRITICAL.\n"
            "4. **Look at the aggregation policy** that produced the event: \n"
            "   `itsi_list_aggregation_policies filter=...`. Confirm the\n"
            "   episode grouping logic is correct.\n"
            "5. **Decide**: acknowledge (`itsi_acknowledge_notable_event`)\n"
            "   if you'll work on it, or close (`itsi_close_notable_event`)\n"
            "   with a comment describing the outcome.\n"
            "6. **Document**: post a concise update with what you did and\n"
            "   any follow-up actions.\n\n"
            "Always confirm with the user before closing critical events."
        )
