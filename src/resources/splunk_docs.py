"""
Splunk documentation resources for MCP server.

Provides version-aware access to Splunk documentation, optimized for LLM consumption.
"""

import logging
from datetime import datetime, timedelta
from typing import Any

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
        """Generate cache key for documentation."""
        return f"docs_{version}_{category}_{topic}"

    def is_expired(self, timestamp: datetime) -> bool:
        """Check if cached item is expired."""
        return datetime.now() - timestamp > timedelta(hours=self.ttl_hours)

    async def get_or_fetch(self, version: str, category: str, topic: str, fetch_func) -> str:
        """Get from cache or fetch if expired/missing."""
        key = self.cache_key(version, category, topic)

        if key in self.cache:
            cached_item = self.cache[key]
            if not self.is_expired(cached_item["timestamp"]):
                logger.debug(f"Cache hit for {key}")
                return cached_item["content"]

        # Fetch fresh content
        logger.debug(f"Cache miss for {key}, fetching")
        content = await fetch_func()
        self.cache[key] = {"content": content, "timestamp": datetime.now(), "version": version}

        return content

    def invalidate_version(self, version: str):
        """Invalidate all cached docs for a specific version."""
        keys_to_remove = [k for k in self.cache.keys() if k.startswith(f"docs_{version}_")]
        for key in keys_to_remove:
            del self.cache[key]
        logger.info(f"Invalidated {len(keys_to_remove)} cache entries for version {version}")


# Global documentation cache
_doc_cache = DocumentationCache()


class SplunkDocsResource(BaseResource):
    """Base class for Splunk documentation resources."""

    # SPLUNK_DOCS_BASE = "https://docs.splunk.com"
    SPLUNK_HELP_BASE = "https://help.splunk.com"
    VERSION_MAPPING = {
        "9.4.0": "9.4",
        "9.3.0": "9.3",
        "9.2.1": "9.2",
        "9.1.0": "9.1",
        "latest": "9.4",  # Current latest
    }

    def __init__(self, uri: str, name: str, description: str, mime_type: str = "text/markdown"):
        super().__init__(uri, name, description, mime_type)
        self.processor = SplunkDocsProcessor()

    async def get_splunk_version(self, ctx: Context) -> str:
        """Detect Splunk version from connected instance."""
        try:
            # Import here to avoid circular imports
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
        """Convert version to docs URL format."""
        # Handle auto-detection
        if version == "auto":
            version = "latest"

        # Extract major.minor from full version if needed
        if version not in self.VERSION_MAPPING:
            # Try to match major.minor (e.g., "9.3.1" -> "9.3.0")
            parts = version.split(".")
            if len(parts) >= 2:
                major_minor = f"{parts[0]}.{parts[1]}.0"
                if major_minor in self.VERSION_MAPPING:
                    version = major_minor

        return self.VERSION_MAPPING.get(version, self.VERSION_MAPPING["latest"])

    def format_version_for_help_url(self, version: str) -> str:
        """Convert version to help URL format.

        Takes a version string (e.g., "9.4.0", "latest", "auto") and returns
        the normalized version suitable for help.splunk.com URLs (e.g., "9.4").
        """
        norm_version = self.normalize_version(version)
        return norm_version

    async def fetch_doc_content(self, url: str) -> str:
        """Fetch and process documentation content."""
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
            # Headers to bypass browser detection on help.splunk.com
            headers = {
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            }

            async with httpx.AsyncClient(
                timeout=30.0, headers=headers, follow_redirects=True
            ) as client:
                logger.debug(f"Fetching documentation from: {url}")
                response = await client.get(url)
                response.raise_for_status()

                # Process HTML to LLM-friendly format
                content = self.processor.process_html(response.text, url)
                logger.debug(f"Successfully processed documentation from {url}")
                return content

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return f"""# Documentation Not Found

The requested Splunk documentation was not found at this URL.

**URL**: {url}
**Status**: 404 Not Found
**Time**: {datetime.now().isoformat()}

This may indicate:
- The documentation has moved or been renamed
- The Splunk version doesn't have this specific documentation
- The topic name may be incorrect

Please check the [Splunk Documentation](https://help.splunk.com) for the correct location.
"""
            else:
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

Please check your internet connection and try again.
"""


class SplunkCheatSheetResource(SplunkDocsResource):
    """Static Splunk cheat sheet resource from Splunk blog."""

    METADATA = ResourceMetadata(
        uri="splunk-docs://cheat-sheet",
        name="splunk_cheat_sheet",
        description="Splunk SPL cheat sheet with commands, regex, and query examples",
        mime_type="text/markdown",
        category="reference",
        tags=["cheat-sheet", "spl", "reference", "commands", "regex"],
    )

    def __init__(
        self,
        uri: str = None,
        name: str = None,
        description: str = None,
        mime_type: str = "text/markdown",
    ):
        # Use metadata defaults if not provided
        uri = uri or self.METADATA.uri
        name = name or self.METADATA.name
        description = description or self.METADATA.description
        super().__init__(uri, name, description, mime_type)

    async def get_content(self, ctx: Context) -> str:
        """Get Splunk cheat sheet content."""

        async def fetch_cheat_sheet():
            # Use the custom processor that returns the complete cheat sheet content
            url = "https://www.splunk.com/en_us/blog/learn/splunk-cheat-sheet-query-spl-regex-commands.html"
            # The processor will handle this URL specially and return comprehensive content
            content = self.processor.process_cheat_sheet_content("", url)
            return content

        return await _doc_cache.get_or_fetch("static", "cheat-sheet", "main", fetch_cheat_sheet)


class TroubleshootingResource(SplunkDocsResource):
    """Version-aware Splunk troubleshooting documentation."""

    METADATA = ResourceMetadata(
        uri="splunk-docs://{version}/troubleshooting/{topic}",
        name="troubleshooting_guide",
        description="Splunk troubleshooting documentation for various topics and versions",
        mime_type="text/markdown",
        category="troubleshooting",
        tags=["troubleshooting", "documentation", "diagnostics", "performance"],
    )

    # Comprehensive troubleshooting topics mapping
    TROUBLESHOOTING_TOPICS = {
        # Log files and internal logging
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
        # Platform instrumentation
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
        # Search and web problems
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
        # Data acquisition and indexing
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
            raise ValueError(
                f"Unknown troubleshooting topic: {topic}. Available topics: {available_topics}"
            )

        topic_info = self.TROUBLESHOOTING_TOPICS[topic]
        uri = f"splunk-docs://{version}/troubleshooting/{topic}"

        super().__init__(
            uri=uri,
            name=f"troubleshooting_{topic}_{version}",
            description=f"Splunk troubleshooting: {topic_info['description']} (version {version})",
        )

    async def get_content(self, ctx: Context) -> str:
        """Get troubleshooting documentation for specific topic."""

        async def fetch_troubleshooting_docs():
            topic_info = self.TROUBLESHOOTING_TOPICS[self.topic]
            help_version = self.format_version_for_help_url(self.version)

            url = f"{self.SPLUNK_HELP_BASE}/en/splunk-enterprise/administer/troubleshoot/{help_version}/{topic_info['url_path']}"

            content = await self.fetch_doc_content(url)

            result = f"""# Splunk Troubleshooting: {topic_info["title"]}

**Version**: Splunk {self.version}
**Category**: Troubleshooting Guide
**Topic**: {topic_info["description"]}
**Source URL**: {url}

{content}

## Troubleshooting Context

This documentation is part of Splunk's comprehensive troubleshooting guide. It helps administrators and users:

- Understand Splunk's internal operations
- Diagnose performance and operational issues
- Monitor system health and metrics
- Resolve common problems

### Related Troubleshooting Topics

"""

            # Add links to related troubleshooting topics
            for topic_key, topic_data in self.TROUBLESHOOTING_TOPICS.items():
                if topic_key != self.topic:
                    result += f"- [{topic_data['title']}](splunk-docs://{self.version}/troubleshooting/{topic_key})\n"

            result += f"""
### Additional Resources

For more troubleshooting information, see:
- [Splunk Documentation](splunk-docs://{self.version}/admin/monitoring)
- [SPL Reference](splunk-docs://{self.version}/spl-reference)
- [Splunk Cheat Sheet](splunk-docs://cheat-sheet)

---
**Generated**: {datetime.now().isoformat()}
"""

            return result

        return await _doc_cache.get_or_fetch(
            self.version, "troubleshooting", self.topic, fetch_troubleshooting_docs
        )


class SPLReferenceResource(SplunkDocsResource):
    """SPL (Search Processing Language) reference documentation."""

    METADATA = ResourceMetadata(
        uri="splunk-docs://spl-reference",
        name="spl_reference",
        description="Splunk SPL command and function reference documentation",
        mime_type="text/markdown",
        category="reference",
        tags=["spl", "search", "commands", "reference"],
    )

    def __init__(
        self,
        uri: str = None,
        name: str = None,
        description: str = None,
        mime_type: str = "text/markdown",
    ):
        # Use metadata defaults if not provided
        uri = uri or self.METADATA.uri
        name = name or self.METADATA.name
        description = description or self.METADATA.description
        super().__init__(uri, name, description, mime_type)

    async def get_content(self, ctx: Context) -> str:
        """Get SPL reference documentation content."""
        # This is a template resource - actual content comes from parameterized URIs
        return """# SPL Reference Documentation

This resource provides access to Splunk's Search Processing Language (SPL) documentation.

## Available Resources

Use these URI patterns to access specific SPL documentation:

- `splunk-docs://{version}/spl-reference/{command}` - Specific SPL command documentation
- `splunk-docs://latest/spl-reference/search` - Search command documentation
- `splunk-docs://latest/spl-reference/stats` - Stats command documentation
- `splunk-docs://latest/spl-reference/eval` - Eval command documentation

## Examples

- `splunk-docs://9.3.0/spl-reference/chart` - Chart command for Splunk 9.3.0
- `splunk-docs://latest/spl-reference/timechart` - Timechart command (latest version)

Replace `{version}` with a specific Splunk version (e.g., "9.3.0") or use "latest" for the current version.
Replace `{command}` with the SPL command name you want to learn about.
"""


class SPLCommandResource(SplunkDocsResource):
    """Specific SPL command documentation resource."""

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
        super().__init__(
            uri=uri,
            name=f"spl_command_{command}_{version}",
            description=f"SPL {command} command documentation for Splunk {version}",
        )

    async def get_content(self, ctx: Context) -> str:
        """Get documentation for specific SPL command."""

        async def fetch_command_docs():
            norm_version = self.normalize_version(self.version)
            # help.splunk.com uses lowercase command names and different URL structure
            command_lower = self.command.lower()
            url = f"{self.SPLUNK_HELP_BASE}/en/splunk-enterprise/search/spl-search-reference/{norm_version}/search-commands/{command_lower}"

            content = await self.fetch_doc_content(url)

            # Add SPL-specific context
            return f"""# SPL Command: {self.command}

**Version**: Splunk {self.version}
**Category**: Search Processing Language Reference

{content}

## Usage Context

The `{self.command}` command is part of Splunk's Search Processing Language (SPL). It can be used in search queries and combined with other SPL commands using the pipe (|) operator.

### Common Usage Patterns

```spl
index=main | {self.command} ...
```

For more SPL commands, see the complete [SPL Reference](splunk-docs://{self.version}/spl-reference).
"""

        return await _doc_cache.get_or_fetch(
            self.version, "spl-reference", self.command, fetch_command_docs
        )


class AdminGuideResource(SplunkDocsResource):
    """Splunk administration documentation."""

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
        super().__init__(
            uri=uri,
            name=f"admin_{topic}_{version}",
            description=f"Splunk administration guide: {topic} (version {version})",
        )

    async def get_content(self, ctx: Context) -> str:
        """Get administration documentation for specific topic."""

        async def fetch_admin_docs():
            # help.splunk.com uses hyphenated topic names and different URL structure
            topic_url = self.topic.replace("_", "-").lower()
            url = f"{self.SPLUNK_HELP_BASE}/en/splunk-enterprise/administer/{topic_url}"

            content = await self.fetch_doc_content(url)

            return f"""# Splunk Administration: {self.topic}

**Version**: Splunk {self.version}
**Category**: Administration Guide

{content}

## Administration Context

This documentation covers administrative aspects of Splunk deployment and configuration.

For related administration topics, see the complete [Admin Guide](splunk-docs://{self.version}/admin).
"""

        return await _doc_cache.get_or_fetch(self.version, "admin", self.topic, fetch_admin_docs)


class DocumentationDiscoveryResource(SplunkDocsResource):
    """Resource for discovering available Splunk documentation."""

    METADATA = ResourceMetadata(
        uri="splunk-docs://discovery",
        name="documentation_discovery",
        description="Discover available Splunk documentation resources",
        mime_type="text/markdown",
        category="discovery",
        tags=["discovery", "documentation", "reference"],
    )

    def __init__(
        self,
        uri: str = None,
        name: str = None,
        description: str = None,
        mime_type: str = "text/markdown",
    ):
        # Use metadata defaults if not provided
        uri = uri or self.METADATA.uri
        name = name or self.METADATA.name
        description = description or self.METADATA.description
        super().__init__(uri, name, description, mime_type)

    async def get_content(self, ctx: Context) -> str:
        """Discover available Splunk documentation resources."""

        # Try to get actual Splunk version
        try:
            detected_version = await self.get_splunk_version(ctx)
        except Exception:
            detected_version = "latest"

        # Common SPL commands for quick reference
        common_spl_commands = [
            "search",
            "stats",
            "eval",
            "chart",
            "timechart",
            "table",
            "sort",
            "where",
            "join",
            "append",
            "lookup",
            "rex",
            "fieldsfor",
            "top",
            "rare",
            "transaction",
            "streamstats",
            "eventstats",
            "bucket",
            "dedup",
            "head",
            "tail",
            "regex",
            "replace",
            "convert",
            "makemv",
            "mvexpand",
            "spath",
            "xmlkv",
            "kvform",
        ]

        # Common admin topics
        admin_topics = [
            "indexes",
            "authentication",
            "deployment",
            "apps",
            "users",
            "roles",
            "monitoring",
            "performance",
            "clustering",
            "distributed-search",
            "forwarders",
            "inputs",
            "outputs",
            "licensing",
            "security",
        ]

        # All available troubleshooting topics
        troubleshooting_topics = list(TroubleshootingResource.TROUBLESHOOTING_TOPICS.keys())

        content = f"""# Splunk Documentation Discovery

**Detected Splunk Version**: {detected_version}
**Discovery Time**: {datetime.now().isoformat()}

This resource helps you discover and access Splunk documentation through the MCP server.

## Static Resources

### 📋 Splunk Cheat Sheet
- **URI**: `splunk-docs://cheat-sheet`
- **Description**: Complete SPL command reference, regex patterns, and quick examples
- **Source**: Official Splunk blog

## Dynamic Resources

### 🔍 SPL Command Reference
Access documentation for specific SPL commands:

**Pattern**: `splunk-docs://{{version}}/spl-reference/{{command}}`

**Common Commands**:
"""

        # Add SPL commands in columns
        for i, cmd in enumerate(common_spl_commands):
            if i % 4 == 0:
                content += "\n"
            content += f"- [`{cmd}`](splunk-docs://{detected_version}/spl-reference/{cmd})  "

        content += """

### 🛠️ Troubleshooting Documentation
Access version-specific troubleshooting guides:

**Pattern**: `splunk-docs://{version}/troubleshooting/{topic}`

**Available Topics**:
"""

        # Add troubleshooting topics with descriptions
        for topic in troubleshooting_topics:
            topic_info = TroubleshootingResource.TROUBLESHOOTING_TOPICS[topic]
            content += f"- [`{topic}`](splunk-docs://{detected_version}/troubleshooting/{topic}) - {topic_info['description']}\n"

        content += """

### ⚙️ Administration Guides
Access administration documentation:

**Pattern**: `splunk-docs://{version}/admin/{topic}`

**Common Topics**:
"""

        # Add admin topics in columns
        for i, topic in enumerate(admin_topics):
            if i % 3 == 0:
                content += "\n"
            content += f"- [`{topic}`](splunk-docs://{detected_version}/admin/{topic})  "

        content += f"""

## Version Support

**Supported Versions**: 9.1.0, 9.2.1, 9.3.0, 9.4.0, latest
**Default Version**: latest (currently 9.4.0)

### Examples

```
# Static resources (no version needed)
splunk-docs://cheat-sheet

# Dynamic resources with version
splunk-docs://9.4/troubleshooting/metrics-log
splunk-docs://latest/spl-reference/stats
splunk-docs://9.3.0/admin/indexes

# Auto-detect version (uses detected: {detected_version})
splunk-docs://auto/troubleshooting/platform-instrumentation
```

## Quick Access Links

### Most Useful Resources
- [📋 Splunk Cheat Sheet](splunk-docs://cheat-sheet) - Essential SPL reference
- [🔧 Metrics Log Troubleshooting](splunk-docs://{detected_version}/troubleshooting/metrics-log) - Performance monitoring
- [📊 Platform Instrumentation](splunk-docs://{detected_version}/troubleshooting/platform-instrumentation) - System monitoring
- [🔍 Search Problems](splunk-docs://{detected_version}/troubleshooting/search-problems) - Search troubleshooting
- [📈 Indexing Performance](splunk-docs://{detected_version}/troubleshooting/indexing-performance) - Index optimization

### For Administrators
- [👥 User Management](splunk-docs://{detected_version}/admin/users) - User administration
- [🏗️ Index Management](splunk-docs://{detected_version}/admin/indexes) - Index configuration
- [🔐 Authentication](splunk-docs://{detected_version}/admin/authentication) - Security setup
- [📡 Distributed Search](splunk-docs://{detected_version}/admin/distributed-search) - Multi-instance setup

---

**Note**: All documentation is cached for 24 hours for optimal performance. URLs are automatically validated and content is processed for LLM consumption.
"""

        return content


# Registry and factory functions
def register_all_resources():
    """Register all documentation resources with the resource registry."""
    try:
        # Register static resources that have METADATA defined
        resource_registry.register(SplunkCheatSheetResource, SplunkCheatSheetResource.METADATA)

        resource_registry.register(
            DocumentationDiscoveryResource, DocumentationDiscoveryResource.METADATA
        )

        resource_registry.register(SPLReferenceResource, SPLReferenceResource.METADATA)

        # Register dynamic/parameterized resources using their class METADATA
        resource_registry.register(TroubleshootingResource, TroubleshootingResource.METADATA)
        resource_registry.register(SPLCommandResource, SPLCommandResource.METADATA)
        resource_registry.register(AdminGuideResource, AdminGuideResource.METADATA)

        logger.info(
            "Successfully registered 6 Splunk documentation resources (3 static, 3 dynamic templates)"
        )

    except Exception as e:
        logger.error(f"Failed to register documentation resources: {e}")


def create_spl_command_resource(version: str, command: str) -> SPLCommandResource:
    """Factory function to create SPL command documentation resources."""
    return SPLCommandResource(version, command)


def create_admin_guide_resource(version: str, topic: str) -> AdminGuideResource:
    """Factory function to create admin guide documentation resources."""
    return AdminGuideResource(version, topic)


def create_troubleshooting_resource(version: str, topic: str) -> TroubleshootingResource:
    """Factory function to create troubleshooting documentation resources."""
    return TroubleshootingResource(version, topic)


# Auto-register resources when module is imported
register_all_resources()
