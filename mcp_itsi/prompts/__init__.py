"""ITSI MCP prompts."""

from __future__ import annotations

from mcp_itsi.core.base import BaseITSIPrompt
from mcp_itsi.prompts.episode_triage import EpisodeTriagePrompt
from mcp_itsi.prompts.kpi_design import KpiDesignPrompt
from mcp_itsi.prompts.service_onboarding import ServiceOnboardingPrompt


def all_prompts() -> list[type[BaseITSIPrompt]]:
    return [ServiceOnboardingPrompt, KpiDesignPrompt, EpisodeTriagePrompt]


__all__ = ["all_prompts"]
