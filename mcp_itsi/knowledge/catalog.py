"""Catalog of bundled ITSI knowledge documents.

The bundle is intentionally curated rather than scraped: AI agents perform
better with focused, well-structured summaries than with the full HTML of
every help page. Source URLs are tracked in :attr:`KnowledgeEntry.source` so
operators can refresh or expand the corpus over time.
"""

from __future__ import annotations

import logging
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)

_KNOWLEDGE_DIR = Path(__file__).parent / "content"


@dataclass(frozen=True)
class KnowledgeEntry:
    slug: str
    title: str
    description: str
    source: str
    category: str
    tags: tuple[str, ...]
    filename: str

    @property
    def uri(self) -> str:
        return f"itsi://docs/{self.slug}"

    def read(self) -> str:
        path = _KNOWLEDGE_DIR / self.filename
        try:
            return path.read_text(encoding="utf-8")
        except FileNotFoundError:
            logger.warning("Knowledge file missing: %s", path)
            return f"# {self.title}\n\n_(content not yet bundled — see {self.source})_\n"


_CATALOG: tuple[KnowledgeEntry, ...] = (
    KnowledgeEntry(
        slug="overview",
        title="ITSI MCP Knowledge Bundle Overview",
        description="High-level map of every doc shipped with this MCP server.",
        source="bundled",
        category="overview",
        tags=("overview", "index"),
        filename="overview.md",
    ),
    KnowledgeEntry(
        slug="api/reference",
        title="ITSI REST API reference (4.21)",
        description=(
            "Endpoints, base URLs, filter syntax, and CRUD semantics for the "
            "ITOA, Event Management, Maintenance and Backup interfaces."
        ),
        source=(
            "https://help.splunk.com/en/splunk-it-service-intelligence/"
            "splunk-it-service-intelligence/leverage-rest-apis/4.21/"
            "itsi-rest-api-reference/itsi-rest-api-reference"
        ),
        category="api",
        tags=("api", "rest", "reference"),
        filename="api/reference.md",
    ),
    KnowledgeEntry(
        slug="api/schema",
        title="ITSI REST API schema (4.21)",
        description=(
            "JSON shapes for every supported ITSI object type and their " "subordinate documents."
        ),
        source=(
            "https://help.splunk.com/en/splunk-it-service-intelligence/"
            "splunk-it-service-intelligence/leverage-rest-apis/4.21/"
            "itsi-rest-api-schema/itsi-rest-api-schema"
        ),
        category="api",
        tags=("api", "rest", "schema"),
        filename="api/schema.md",
    ),
    KnowledgeEntry(
        slug="service-insights",
        title="Service Insights overview",
        description=(
            "Services, KPIs, health scores, glass tables, deep dives, "
            "adaptive thresholds and anomaly detection."
        ),
        source=(
            "https://help.splunk.com/en/splunk-it-service-intelligence/"
            "splunk-it-service-intelligence/visualize-and-assess-service-health/4.21/overview"
        ),
        category="service-insights",
        tags=("service", "kpi", "health-score", "glass-table"),
        filename="service_insights.md",
    ),
    KnowledgeEntry(
        slug="entity-integrations",
        title="Entity integrations overview",
        description=(
            "What entities are, how to import them, and how built-in entity "
            "integrations populate ITSI from common data sources."
        ),
        source=(
            "https://help.splunk.com/en/splunk-it-service-intelligence/"
            "splunk-it-service-intelligence/discover-and-integrate-it-components/4.21"
        ),
        category="entities",
        tags=("entity", "entity-integration", "csv", "search"),
        filename="entity_integrations.md",
    ),
    KnowledgeEntry(
        slug="event-analytics",
        title="Event Analytics overview",
        description=(
            "Notable events, correlation searches, aggregation policies, "
            "episodes and the recommended event-management workflow."
        ),
        source=(
            "https://help.splunk.com/en/splunk-it-service-intelligence/"
            "splunk-it-service-intelligence/detect-and-act-on-notable-events/4.21/"
        ),
        category="event-analytics",
        tags=("event", "notable", "episode", "aggregation-policy"),
        filename="event_analytics.md",
    ),
    KnowledgeEntry(
        slug="modules",
        title="ITSI modules and the Splunk App for Content Packs",
        description=(
            "Legacy ITSI modules (App Server, Database, EUEM, Load Balancer, "
            "OS, Storage, Virtualization, Web Server) and migration guidance "
            "to the Content Pack framework."
        ),
        source=(
            "https://help.splunk.com/en/splunk-it-service-intelligence/"
            "splunk-it-service-intelligence/reduce-time-to-insights/4.18/introduction"
        ),
        category="modules",
        tags=("module", "content-pack"),
        filename="modules.md",
    ),
    KnowledgeEntry(
        slug="best-practices",
        title="ITSI implementation best practices",
        description=(
            "Distilled best practices for service modelling, KPI design, "
            "thresholding, episodes and operational hygiene."
        ),
        source="bundled",
        category="best-practices",
        tags=("best-practices", "guidance"),
        filename="best_practices.md",
    ),
    KnowledgeEntry(
        slug="cookbook/header-auth",
        title="Header-based authentication recipe",
        description=(
            "How to send credentials to the ITSI MCP server via X-Splunk-* and "
            "X-ITSI-* HTTP headers, mirroring the parent mcp-for-splunk server."
        ),
        source="bundled",
        category="cookbook",
        tags=("auth", "headers", "cookbook"),
        filename="cookbook/header_auth.md",
    ),
)


def list_docs() -> list[KnowledgeEntry]:
    """Return every bundled knowledge entry."""
    return list(_CATALOG)


def get_doc(slug: str) -> KnowledgeEntry | None:
    """Look up a knowledge entry by slug. Slugs are URL-style (`a/b`)."""
    for entry in _CATALOG:
        if entry.slug == slug:
            return entry
    return None


def search(query: str, *, limit: int = 20) -> list[tuple[KnowledgeEntry, int]]:
    """Naive substring search across slug/title/description/tags.

    Returns pairs of ``(entry, hit_count)`` sorted by relevance.
    """
    query = query.strip().lower()
    if not query:
        return []
    scored: list[tuple[KnowledgeEntry, int]] = []
    for entry in _CATALOG:
        haystacks: Iterable[str] = (
            entry.slug.lower(),
            entry.title.lower(),
            entry.description.lower(),
            " ".join(entry.tags).lower(),
        )
        score = sum(h.count(query) for h in haystacks)
        if score:
            scored.append((entry, score))
    scored.sort(key=lambda x: x[1], reverse=True)
    return scored[:limit]
