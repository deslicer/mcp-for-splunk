"""
Splunk documentation resources for MCP server.

Provides version-aware access to Splunk documentation, optimized for LLM consumption.
"""

import logging
from datetime import datetime, timedelta
from typing import Any, Iterable

from fastmcp import Context

try:
    import httpx

    HAS_HTTPX = True
except ImportError:
    HAS_HTTPX = False

from src.core.base import BaseResource, ResourceMetadata
from src.core.registry import resource_registry

from .processors.html_processor import SplunkDocsProcessor

logger = logging.getLogger(__name__)


class DocumentationCache:
    """Version-aware caching for Splunk documentation."""

    def __init__(self, ttl_hours: int = 24):
        self.cache: dict[str, dict[str, Any]] = {}
        self.ttl_hours = ttl_hours

    def cache_key(self, version: str, category: str, topic: str) -> str:
        return f"docs_{version}_{category}_{topic}"

    def is_expired(self, timestamp: datetime) -> bool:
        return datetime.now() - timestamp > timedelta(hours=self.ttl_hours)

    async def get_or_fetch(self, version: str, category: str, topic: str, fetch_func) -> str:
        key = self.cache_key(version, category, topic)
        if key in self.cache:
            cached_item = self.cache[key]
            if not self.is_expired(cached_item["timestamp"]):
                logger.debug(f"Cache hit for {key}")
                return cached_item["content"]

        logger.debug(f"Cache miss for {key}, fetching")
        content = await fetch_func()
        self.cache[key] = {"content": content, "timestamp": datetime.now(), "version": version}
        return content

    def invalidate_version(self, version: str):
        keys_to_remove = [k for k in self.cache.keys() if k.startswith(f"docs_{version}_")]
        for key in keys_to_remove:
            del self.cache[key]
        logger.info(f"Invalidated {len(keys_to_remove)} cache entries for version {version}")


_doc_cache = DocumentationCache()


class SplunkDocsResource(BaseResource):
    """Base class for Splunk documentation resources."""

    SPLUNK_HELP_BASE = "https://help.splunk.com"
    VERSION_MAPPING = {
        "10.0.0": "10.0",
        "9.4.0": "9.4",
        "9.3.0": "9.3",
        "9.2.1": "9.2",
        "9.1.0": "9.1",
        "latest": "10.0",  # Current latest
    }

    def __init__(self, uri: str, name: str, description: str, mime_type: str = "text/markdown"):
        super().__init__(uri, name, description, mime_type)
        self.processor = SplunkDocsProcessor()

    async def get_splunk_version(self, ctx: Context) -> str:
        try:
            from src.tools.health.status import GetSplunkHealth

            health_tool = GetSplunkHealth("get_splunk_health", "Get Splunk health status")
            health_result = await health_tool.execute(ctx)

            if health_result.get("status") == "connected":
                version = health_result.get("version", "latest")
                logger.debug(f"Detected Splunk version: {version}")
                return version
        except Exception as e:
            logger.warning(f"Failed to detect Splunk version: {e}")

        return "latest"

    def normalize_version(self, version: str) -> str:
        """Convert version to help.splunk.com format (major.minor)."""
        if version == "auto":
            version = "latest"

        if version not in self.VERSION_MAPPING:
            parts = version.split(".")
            if len(parts) >= 2:
                major_minor = f"{parts[0]}.{parts[1]}.0"
                if major_minor in self.VERSION_MAPPING:
                    version = major_minor

        return self.VERSION_MAPPING.get(version, self.VERSION_MAPPING["latest"])

    def format_version_for_help_url(self, version: str) -> str:
        return self.normalize_version(version)

    async def fetch_doc_content(self, url: str) -> str:
        if not HAS_HTTPX:
            return f"""# Documentation Unavailable

HTTP client not available. To enable documentation fetching, install httpx:

```bash
pip install httpx
```

**Requested URL**: {url}
**Time**: {datetime.now().isoformat()}
"""

        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            }

            async with httpx.AsyncClient(timeout=30.0, headers=headers, follow_redirects=True) as client:
                logger.debug(f"Fetching documentation from: {url}")
                response = await client.get(url)
                response.raise_for_status()
                return self.processor.process_html(response.text, url)

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return f"""# Documentation Not Found

The requested Splunk documentation was not found at this URL.

**URL**: {url}
**Status**: 404 Not Found
**Time**: {datetime.now().isoformat()}
"""

            return f"""# Documentation Error

Failed to fetch documentation due to HTTP error.

**URL**: {url}
**Status**: {e.response.status_code}
**Error**: {str(e)}
**Time**: {datetime.now().isoformat()}
"""
        except Exception as e:
            logger.error(f"Error fetching documentation from {url}: {e}")
            return f"""# Documentation Error

Failed to fetch documentation due to an error.

**URL**: {url}
**Error**: {str(e)}
**Time**: {datetime.now().isoformat()}
"""

    async def _fetch_first_working(self, urls: Iterable[str]) -> tuple[str | None, str | None]:
        """Try URLs in order; return the first that doesn't produce a 404 wrapper."""
        last_content = None
        for url in urls:
            content = await self.fetch_doc_content(url)
            last_content = content
            if not content.startswith("# Documentation Not Found"):
                return url, content
        return None, last_content


class SplunkCheatSheetResource(SplunkDocsResource):
    METADATA = ResourceMetadata(
        uri="splunk-docs://cheat-sheet",
        name="splunk_cheat_sheet",
        description="Splunk SPL cheat sheet with commands, regex, and query examples",
        mime_type="text/markdown",
        category="reference",
        tags=["cheat-sheet", "spl", "reference", "commands", "regex"],
    )

    def __init__(self, uri: str = None, name: str = None, description: str = None, mime_type: str = "text/markdown"):
        uri = uri or self.METADATA.uri
        name = name or self.METADATA.name
        description = description or self.METADATA.description
        super().__init__(uri, name, description, mime_type)

    async def get_content(self, ctx: Context) -> str:
        async def fetch_cheat_sheet():
            url = "https://www.splunk.com/en_us/blog/learn/splunk-cheat-sheet-query-spl-regex-commands.html"
            return self.processor.process_cheat_sheet_content("", url)

        return await _doc_cache.get_or_fetch("static", "cheat-sheet", "main", fetch_cheat_sheet)


class TroubleshootingResource(SplunkDocsResource):
    METADATA = ResourceMetadata(
        uri="splunk-docs://{version}/troubleshooting/{topic}",
        name="troubleshooting_guide",
        description="Splunk troubleshooting documentation for various topics and versions",
        mime_type="text/markdown",
        category="troubleshooting",
        tags=["troubleshooting", "documentation", "diagnostics", "performance"],
    )

    TROUBLESHOOTING_TOPICS = {
        "splunk-logs": {
            "title": "What Splunk Logs about Itself",
            "description": "Understanding Splunk's internal logging and log files",
            "url_path": "splunk-enterprise-log-files/what-splunk-software-logs-about-itself",
        },
        "metrics-log": {
            "title": "About metrics.log",
            "description": "Understanding Splunk's metrics.log file for performance monitoring",
            "url_path": "splunk-enterprise-log-files/about-metrics.log",
        },
        "troubleshoot-inputs": {
            "title": "Troubleshooting Inputs with metrics.log",
            "description": "Using metrics.log to diagnose input-related issues",
            "url_path": "splunk-enterprise-log-files/troubleshoot-inputs-with-metrics.log",
        },
        "platform-instrumentation": {
            "title": "About Platform Instrumentation",
            "description": "Understanding Splunk Enterprise platform instrumentation",
            "url_path": "platform-instrumentation/about-splunk-enterprise-platform-instrumentation",
        },
        "platform-instrumentation-logs": {
            "title": "What Platform Instrumentation Logs",
            "description": "Understanding what platform instrumentation logs in Splunk",
            "url_path": "platform-instrumentation/what-does-platform-instrumentation-log",
        },
        "platform-instrumentation-searches": {
            "title": "Sample Platform Instrumentation Searches",
            "description": "Example searches for monitoring platform instrumentation",
            "url_path": "platform-instrumentation/sample-platform-instrumentation-searches",
        },
        "search-problems": {
            "title": "Splunk Web and Search Problems",
            "description": "Troubleshooting Splunk web interface and search issues",
            "url_path": "splunk-web-and-search-problems/i-cant-find-my-data",
        },
        "authentication-timeouts": {
            "title": "Intermittent Authentication Timeouts on Search Peers",
            "description": "Resolving authentication timeout issues between search head and peers",
            "url_path": "splunk-web-and-search-problems/intermittent-authentication-timeouts-on-search-peers",
        },
        "indexing-performance": {
            "title": "Identify and Triage Indexing Performance Issues",
            "description": "Diagnosing and resolving indexing performance problems",
            "url_path": "data-acquisition-problems/identify-and-triage-indexing-performance-problems",
        },
        "indexing-delay": {
            "title": "Event Indexing Delay",
            "description": "Understanding and resolving event indexing delays",
            "url_path": "data-acquisition-problems/event-indexing-delay",
        },
    }

    def __init__(self, version: str, topic: str):
        self.version = version
        self.topic = topic

        if topic not in self.TROUBLESHOOTING_TOPICS:
            available_topics = ", ".join(self.TROUBLESHOOTING_TOPICS.keys())
            raise ValueError(f"Unknown troubleshooting topic: {topic}. Available topics: {available_topics}")

        topic_info = self.TROUBLESHOOTING_TOPICS[topic]
        uri = f"splunk-docs://{version}/troubleshooting/{topic}"
        super().__init__(
            uri=uri,
            name=f"troubleshooting_{topic}_{version}",
            description=f"Splunk troubleshooting: {topic_info['description']} (version {version})",
        )

    async def get_content(self, ctx: Context) -> str:
        async def fetch_troubleshooting_docs():
            topic_info = self.TROUBLESHOOTING_TOPICS[self.topic]
            help_version = self.format_version_for_help_url(self.version)
            url = f"{self.SPLUNK_HELP_BASE}/en/splunk-enterprise/administer/troubleshoot/{help_version}/{topic_info['url_path']}"
            content = await self.fetch_doc_content(url)
            return f"""# Splunk Troubleshooting: {topic_info['title']}

**Version**: Splunk {self.version}
**Category**: Troubleshooting Guide
**Topic**: {topic_info['description']}
**Source URL**: {url}

{content}
"""

        return await _doc_cache.get_or_fetch(self.version, "troubleshooting", self.topic, fetch_troubleshooting_docs)


class SPLReferenceResource(SplunkDocsResource):
    METADATA = ResourceMetadata(
        uri="splunk-docs://spl-reference",
        name="spl_reference",
        description="Splunk SPL command and function reference documentation",
        mime_type="text/markdown",
        category="reference",
        tags=["spl", "search", "commands", "reference"],
    )

    def __init__(self, uri: str = None, name: str = None, description: str = None, mime_type: str = "text/markdown"):
        uri = uri or self.METADATA.uri
        name = name or self.METADATA.name
        description = description or self.METADATA.description
        super().__init__(uri, name, description, mime_type)

    async def get_content(self, ctx: Context) -> str:
        return """# SPL Reference Documentation

Use `splunk-docs://{version}/spl-reference/{command}` to fetch a specific SPL command page.
"""


class SPLCommandResource(SplunkDocsResource):
    METADATA = ResourceMetadata(
        uri="splunk-docs://{version}/spl-reference/{command}",
        name="spl_command_reference",
        description="Splunk SPL command documentation for specific commands and versions",
        mime_type="text/markdown",
        category="reference",
        tags=["spl", "commands", "reference", "search"],
    )

    def __init__(self, version: str, command: str):
        self.version = version
        self.command = command
        uri = f"splunk-docs://{version}/spl-reference/{command}"
        super().__init__(uri=uri, name=f"spl_command_{command}_{version}", description=f"SPL {command} command documentation for Splunk {version}")

    async def get_content(self, ctx: Context) -> str:
        async def fetch_command_docs():
            norm_version = self.normalize_version(self.version)
            command_lower = self.command.lower()
            url = f"{self.SPLUNK_HELP_BASE}/en/splunk-enterprise/search/spl-search-reference/{norm_version}/search-commands/{command_lower}"
            content = await self.fetch_doc_content(url)
            return f"""# SPL Command: {self.command}

**Version**: Splunk {self.version}
**Category**: Search Processing Language Reference

{content}
"""

        return await _doc_cache.get_or_fetch(self.version, "spl-reference", self.command, fetch_command_docs)


class AdminGuideResource(SplunkDocsResource):
    METADATA = ResourceMetadata(
        uri="splunk-docs://{version}/admin/{topic}",
        name="admin_guide",
        description="Splunk administration documentation for various topics and versions",
        mime_type="text/markdown",
        category="administration",
        tags=["administration", "configuration", "management", "deployment"],
    )

    def __init__(self, version: str, topic: str):
        self.version = version
        self.topic = topic
        uri = f"splunk-docs://{version}/admin/{topic}"
        super().__init__(uri=uri, name=f"admin_{topic}_{version}", description=f"Splunk administration guide: {topic} (version {version})")

    async def get_content(self, ctx: Context) -> str:
        async def fetch_admin_docs():
            topic_url = self.topic.replace("_", "-").lower()
            help_version = self.format_version_for_help_url(self.version)

            legacy = f"{self.SPLUNK_HELP_BASE}/en/splunk-enterprise/administer/{topic_url}"

            # Minimal pragmatic fallback for the specific failing topic we observed.
            # (Further topic-specific mapping can be extended later.)
            candidates = [legacy]
            if topic_url == "indexes":
                candidates += [
                    f"{self.SPLUNK_HELP_BASE}/en/splunk-enterprise/administer-splunk-enterprise/{help_version}/manage-indexes",
                ]

            used_url, content = await self._fetch_first_working(candidates)
            used_url = used_url or legacy
            return f"""# Splunk Administration: {self.topic}

**Version**: Splunk {self.version}
**Category**: Administration Guide
**Source URL**: {used_url}

{content}
"""

        return await _doc_cache.get_or_fetch(self.version, "admin", self.topic, fetch_admin_docs)


class SplunkSpecReferenceResource(SplunkDocsResource):
    METADATA = ResourceMetadata(
        uri="splunk-spec://{config}",
        name="splunk_spec_reference",
        description="Splunk configuration specification reference (auto-detects version)",
        mime_type="text/markdown",
        category="reference",
        tags=["spec", "configuration", "reference", "admin"],
    )

    def __init__(self, config: str):
        self.config = config
        uri = f"splunk-spec://{config}"
        display_config = self._normalize_config_name(config)
        super().__init__(uri=uri, name=f"spec_{config.replace('.', '_')}", description=f"Splunk configuration spec for {display_config} (auto-detected version)")

    def _parse_version_components(self, version: str) -> tuple[str, str]:
        if version == "auto":
            version = "latest"

        minor = self.normalize_version(version)

        parts = version.split(".")
        if len(parts) >= 3:
            full = f"{parts[0]}.{parts[1]}.{parts[2]}"
        elif len(parts) == 2:
            full = f"{parts[0]}.{parts[1]}.0"
        else:
            full = f"{minor}.0"

        return minor, full

    def _normalize_config_name(self, config: str) -> str:
        if config.endswith(".conf.spec"):
            return config[:-5]
        if config.endswith(".conf"):
            return config
        return f"{config}.conf"

    async def get_content(self, ctx: Context) -> str:
        version = await self.get_splunk_version(ctx)
        logger.info(f"Auto-detected Splunk version: {version}")

        async def fetch_spec_docs():
            minor, full = self._parse_version_components(version)
            config = self._normalize_config_name(self.config)

            candidates = [
                f"{self.SPLUNK_HELP_BASE}/en/splunk-enterprise/administer/admin-manual/{minor}/configuration-file-reference/{full}-configuration-file-reference/{config}",
                f"{self.SPLUNK_HELP_BASE}/en/data-management/splunk-enterprise-admin-manual/{minor}/configuration-file-reference/{full}-configuration-file-reference/{config}",
                # Try a minor-based folder (X.Y.0-configuration-file-reference)
                f"{self.SPLUNK_HELP_BASE}/en/splunk-enterprise/administer/admin-manual/{minor}/configuration-file-reference/{minor}.0-configuration-file-reference/{config}",
                f"{self.SPLUNK_HELP_BASE}/en/data-management/splunk-enterprise-admin-manual/{minor}/configuration-file-reference/{minor}.0-configuration-file-reference/{config}",
            ]

            used_url, content = await self._fetch_first_working(candidates)
            if used_url is None:
                return f"""# Configuration Spec Not Found

**Config File**: {config}
**Version**: {version} (minor: {minor}, full: {full})
**Time**: {datetime.now().isoformat()}

**Attempted URLs**:\n""" + "\n".join([f"- {u}" for u in candidates])

            return f"""# Splunk Configuration Spec: {config}

**Version**: Splunk {version}
**Category**: Configuration File Reference
**Source URL**: {used_url}

{content}
"""

        return await _doc_cache.get_or_fetch(version, "spec-reference", self.config, fetch_spec_docs)


class DocumentationDiscoveryResource(SplunkDocsResource):
    METADATA = ResourceMetadata(
        uri="splunk-docs://discovery",
        name="documentation_discovery",
        description="Discover available Splunk documentation resources",
        mime_type="text/markdown",
        category="discovery",
        tags=["discovery", "documentation", "reference"],
    )

    def __init__(self, uri: str = None, name: str = None, description: str = None, mime_type: str = "text/markdown"):
        uri = uri or self.METADATA.uri
        name = name or self.METADATA.name
        description = description or self.METADATA.description
        super().__init__(uri, name, description, mime_type)

    async def get_content(self, ctx: Context) -> str:
        return "# Splunk Documentation Discovery\n"


def register_all_resources():
    try:
        resource_registry.register(SplunkCheatSheetResource, SplunkCheatSheetResource.METADATA)
        resource_registry.register(DocumentationDiscoveryResource, DocumentationDiscoveryResource.METADATA)
        resource_registry.register(SPLReferenceResource, SPLReferenceResource.METADATA)
        resource_registry.register(TroubleshootingResource, TroubleshootingResource.METADATA)
        resource_registry.register(SPLCommandResource, SPLCommandResource.METADATA)
        resource_registry.register(AdminGuideResource, AdminGuideResource.METADATA)
        resource_registry.register(SplunkSpecReferenceResource, SplunkSpecReferenceResource.METADATA)
    except Exception as e:
        logger.error(f"Failed to register documentation resources: {e}")


def create_admin_guide_resource(version: str, topic: str) -> AdminGuideResource:
    return AdminGuideResource(version, topic)


def create_troubleshooting_resource(version: str, topic: str) -> TroubleshootingResource:
    return TroubleshootingResource(version, topic)


def create_spl_command_resource(version: str, command: str) -> SPLCommandResource:
    return SPLCommandResource(version, command)


def create_spec_reference_resource(config: str) -> SplunkSpecReferenceResource:
    return SplunkSpecReferenceResource(config)


register_all_resources()
