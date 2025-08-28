"""
Shared context classes for Splunk troubleshooting agents.
"""

from dataclasses import dataclass
from typing import Any


@dataclass
class SplunkDiagnosticContext:
    """Context for maintaining state across Splunk diagnostic workflows."""

    earliest_time: str = "-24h"
    latest_time: str = "now"
    focus_index: str | None = None
    focus_host: str | None = None
    focus_sourcetype: str | None = None  # Added: Specific sourcetype to focus analysis on
    complexity_level: str = "moderate"
    problem_description: str | None = None  # Added: Original problem description for context
    workflow_type: str | None = None  # Added: Workflow type being executed
    identified_issues: list[str] = None
    baseline_metrics: dict[str, Any] = None
    validation_results: dict[str, Any] = None
    indexes: list[str] = None
    sourcetypes: list[str] = None
    sources: list[str] = None

    def __post_init__(self):
        if self.identified_issues is None:
            self.identified_issues = []
        if self.baseline_metrics is None:
            self.baseline_metrics = {}
        if self.validation_results is None:
            self.validation_results = {}
        if self.indexes is None:
            self.indexes = []
        if self.sourcetypes is None:
            self.sourcetypes = []
        if self.sources is None:
            self.sources = []


@dataclass
class DiagnosticResult:
    """Result from a diagnostic step or micro-agent."""

    step: str
    status: str  # "healthy", "warning", "critical", "error"
    findings: list[str]
    recommendations: list[str]
    details: dict[str, Any] = None
    # Extended fields for reliability scoring
    severity: str | None = None  # Explicit severity, defaults from status
    success_score: float | None = None  # 0.0-1.0 assessment of instruction fulfillment
    success: bool | None = None  # Derived true/false indicator of success
    # Optional tracing/telemetry fields (may be populated by agents/runners)
    trace_url: str | None = None
    trace_name: str | None = None
    trace_timestamp: int | None = None
    correlation_id: str | None = None

    def __post_init__(self):
        if self.details is None:
            self.details = {}
        # Normalize and backfill extended fields
        if not self.severity:
            # Default severity mirrors status
            self.severity = self.status
        # Clamp/derive success score if provided; else infer from status
        if self.success_score is not None:
            try:
                self.success_score = max(0.0, min(1.0, float(self.success_score)))
            except Exception:
                self.success_score = None
        if self.success_score is None:
            # Heuristic mapping from status to score
            mapping = {"healthy": 1.0, "warning": 0.6, "critical": 0.2, "error": 0.0}
            self.success_score = mapping.get(self.status, 0.5)
        if self.success is None:
            self.success = self.status in ("healthy", "warning") and self.success_score >= 0.5


@dataclass
class ComponentAnalysisResult:
    """Result from a single component analysis."""

    component: str
    agent_name: str
    analysis_result: str
    execution_time: float
    status: str
    error_message: str | None = None


@dataclass
class ParallelAnalysisContext:
    """Context for coordinating parallel analysis workflows."""

    earliest_time: str = "-24h"
    latest_time: str = "now"
    focus_components: list[str] = None
    analysis_depth: str = "standard"
    enable_cross_validation: bool = True
    parallel_execution_limit: int = 3

    def __post_init__(self):
        if self.focus_components is None:
            self.focus_components = ["inputs", "indexing", "search_performance"]
