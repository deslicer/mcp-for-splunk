"""
Shared context classes for Splunk troubleshooting agents.
"""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional


@dataclass
class SplunkDiagnosticContext:
    """Context for maintaining state across Splunk diagnostic workflows."""
    earliest_time: str = "-24h"
    latest_time: str = "now"
    focus_index: Optional[str] = None
    focus_host: Optional[str] = None
    complexity_level: str = "moderate"
    identified_issues: List[str] = None
    baseline_metrics: Dict[str, Any] = None
    validation_results: Dict[str, Any] = None
    indexes: List[str] = None
    sourcetypes: List[str] = None
    sources: List[str] = None

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
    findings: List[str]
    recommendations: List[str]
    details: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.details is None:
            self.details = {}


@dataclass
class ComponentAnalysisResult:
    """Result from a single component analysis."""
    component: str
    agent_name: str
    analysis_result: str
    execution_time: float
    status: str
    error_message: Optional[str] = None


@dataclass
class ParallelAnalysisContext:
    """Context for coordinating parallel analysis workflows."""
    earliest_time: str = "-24h"
    latest_time: str = "now"
    focus_components: List[str] = None
    analysis_depth: str = "standard"
    enable_cross_validation: bool = True
    parallel_execution_limit: int = 3
    
    def __post_init__(self):
        if self.focus_components is None:
            self.focus_components = ["inputs", "indexing", "search_performance"] 