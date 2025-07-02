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

    SPLUNK_DOCS_BASE = "https://docs.splunk.com"
    SPLUNK_HELP_BASE = "https://help.splunk.com"
    VERSION_MAPPING = {
        "9.4.0": "94",
        "9.3.0": "93",
        "9.2.1": "92",
        "9.1.0": "91",
        "latest": "94",  # Current latest
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

            if health_result.get("status") == "success":
                version = health_result.get("splunk_info", {}).get("version", "latest")
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
            async with httpx.AsyncClient(timeout=30.0) as client:
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

Please check the [Splunk Documentation](https://docs.splunk.com) for the correct location.
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

    def __init__(self):
        super().__init__(
            uri="splunk-docs://cheat-sheet",
            name="splunk_cheat_sheet",
            description="Splunk SPL cheat sheet with commands, regex, and query examples",
        )

    async def get_content(self, ctx: Context) -> str:
        """Get Splunk cheat sheet content."""

        async def fetch_cheat_sheet():
            url = "https://www.splunk.com/en_us/blog/learn/splunk-cheat-sheet-query-spl-regex-commands.html"
            content = await self.fetch_doc_content(url)

            return f"""# Splunk Cheat Sheet: Query, SPL, RegEx, & Commands

**Source**: Splunk Official Blog
**Category**: Quick Reference Guide
**Updated**: {datetime.now().strftime('%Y-%m-%d')}

{content}

## Quick Reference Summary

This cheat sheet covers essential Splunk concepts and commands for both Splunk Cloud and Splunk Enterprise:

### Key Areas Covered
- **Events and Metrics** - Understanding Splunk data structure
- **SPL Commands** - Search Processing Language reference
- **Regular Expressions** - Pattern matching in searches
- **Common Functions** - eval, stats, and other built-in functions
- **Date/Time Formatting** - Timestamp manipulation
- **Field Operations** - Working with multivalue fields

### Usage Context
This resource is invaluable for:
- Quick command lookup during search development
- Learning SPL syntax and patterns
- Reference for regular expressions in Splunk
- Understanding data formatting options

For specific command details, see also: [SPL Reference](splunk-docs://latest/spl-reference)
"""

        return await _doc_cache.get_or_fetch("static", "cheat-sheet", "main", fetch_cheat_sheet)


class TroubleshootingResource(SplunkDocsResource):
    """Version-aware Splunk troubleshooting documentation."""

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
    }

    def __init__(self, version: str, topic: str):
        self.version = version
        self.topic = topic

        if topic not in self.TROUBLESHOOTING_TOPICS:
            raise ValueError(f"Unknown troubleshooting topic: {topic}")

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
            norm_version = self.normalize_version(self.version)
            
            # Convert version format for help URLs (9.4 instead of 94)
            help_version = f"{norm_version[0]}.{norm_version[1]}"
            
            url = f"{self.SPLUNK_HELP_BASE}/en/splunk-enterprise/administer/troubleshoot/{help_version}/{topic_info['url_path']}"

            content = await self.fetch_doc_content(url)

            return f"""# Splunk Troubleshooting: {topic_info['title']}

**Version**: Splunk {self.version}
**Category**: Troubleshooting Guide
**Topic**: {topic_info['description']}

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
                    content += f"- [{topic_data['title']}](splunk-docs://{self.version}/troubleshooting/{topic_key})\n"

            content += f"""
### Additional Resources

For more troubleshooting information, see:
- [Splunk Documentation](splunk-docs://{self.version}/admin/monitoring)
- [SPL Reference](splunk-docs://{self.version}/spl-reference)

---
**Generated**: {datetime.now().isoformat()}
"""

            return content

        return await _doc_cache.get_or_fetch(
            self.version, "troubleshooting", self.topic, fetch_troubleshooting_docs
        )


class SPLReferenceResource(SplunkDocsResource):
    """SPL (Search Processing Language) reference documentation."""

    def __init__(self):
        super().__init__(
            uri="splunk-docs://spl-reference",
            name="spl_reference",
            description="Splunk SPL command and function reference documentation",
        )

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
            # Splunk docs URLs use title case for commands
            command_title = self.command.title()
            url = f"{self.SPLUNK_DOCS_BASE}/Documentation/Splunk/{norm_version}/SearchReference/{command_title}"

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
            norm_version = self.normalize_version(self.version)
            # Map topic to likely URL structure
            topic_url = self.topic.replace("-", "").replace("_", "")
            url = f"{self.SPLUNK_DOCS_BASE}/Documentation/Splunk/{norm_version}/Admin/{topic_url}"

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

    def __init__(self):
        super().__init__(
            uri="splunk-docs://discovery",
            name="documentation_discovery",
            description="Discover available Splunk documentation resources",
        )

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
        ]

        # Common admin topics
        admin_topics = [
            "indexes",
            "authentication",
            "deployment",
            "apps",
            "users",
            "data-inputs",
            "forwarders",
            "clustering",
            "security",
            "monitoring",
        ]

        # Troubleshooting topics
        troubleshooting_topics = list(TroubleshootingResource.TROUBLESHOOTING_TOPICS.keys())

        discovery_content = f"""# Splunk Documentation Discovery

**Detected Splunk Version**: {detected_version}
**Available Documentation Categories**: SPL Reference, Administration Guide, Troubleshooting, Quick Reference

## Quick Access - Cheat Sheet

- [**Splunk Cheat Sheet**](splunk-docs://cheat-sheet) - SPL commands, regex, and quick reference

## SPL Command Reference

The following SPL command documentation is readily available:

"""

        for cmd in common_spl_commands:
            discovery_content += (
                f"- [`{cmd}`](splunk-docs://{detected_version}/spl-reference/{cmd})\n"
            )

        discovery_content += """
## Administration Topics

Common administration documentation:

"""

        for topic in admin_topics:
            discovery_content += (
                f"- [{topic.title()}](splunk-docs://{detected_version}/admin/{topic})\n"
            )

        discovery_content += """
## Troubleshooting Documentation

Splunk troubleshooting and diagnostic resources:

"""

        for topic in troubleshooting_topics:
            topic_info = TroubleshootingResource.TROUBLESHOOTING_TOPICS[topic]
            discovery_content += (
                f"- [{topic_info['title']}](splunk-docs://{detected_version}/troubleshooting/{topic})\n"
            )

        discovery_content += f"""

## Usage Patterns

### SPL Reference
```
splunk-docs://{{version}}/spl-reference/{{command}}
```

### Administration Guide
```
splunk-docs://{{version}}/admin/{{topic}}
```

### Troubleshooting
```
splunk-docs://{{version}}/troubleshooting/{{topic}}
```

### Static Resources
```
splunk-docs://cheat-sheet
```

## Examples
- `splunk-docs://latest/spl-reference/stats` - Stats command documentation
- `splunk-docs://9.4.0/admin/indexes` - Index administration for Splunk 9.4.0
- `splunk-docs://{detected_version}/troubleshooting/splunk-logs` - Splunk logging documentation
- `splunk-docs://cheat-sheet` - Quick reference guide

## Available Versions

{", ".join(self.VERSION_MAPPING.keys())}

**Note**: Use "latest" for the most current documentation, or specify a version like "9.4.0" for version-specific docs.

---
**Generated**: {datetime.now().isoformat()}
**For**: Splunk {detected_version}
"""

        return discovery_content


def register_documentation_resources():
    """Register all Splunk documentation resources."""

    # Register discovery resource
    discovery_resource = DocumentationDiscoveryResource()
    resource_registry.register(
        DocumentationDiscoveryResource,
        ResourceMetadata(
            uri=discovery_resource.uri,
            name=discovery_resource.name,
            description=discovery_resource.description,
            mime_type="text/markdown",
            category="documentation",
            tags=["splunk", "documentation", "discovery"],
        ),
    )

    # Register base SPL reference resource
    spl_resource = SPLReferenceResource()
    resource_registry.register(
        SPLReferenceResource,
        ResourceMetadata(
            uri=spl_resource.uri,
            name=spl_resource.name,
            description=spl_resource.description,
            mime_type="text/markdown",
            category="documentation",
            tags=["splunk", "spl", "reference", "commands"],
        ),
    )

    # Register static cheat sheet resource
    cheat_sheet_resource = SplunkCheatSheetResource()
    resource_registry.register(
        SplunkCheatSheetResource,
        ResourceMetadata(
            uri=cheat_sheet_resource.uri,
            name=cheat_sheet_resource.name,
            description=cheat_sheet_resource.description,
            mime_type="text/markdown",
            category="documentation",
            tags=["splunk", "cheat-sheet", "reference", "quick-guide", "spl"],
        ),
    )

    logger.info("Registered Splunk documentation resources")


# Helper function to create dynamic resources
def create_spl_command_resource(version: str, command: str) -> SPLCommandResource:
    """Create a dynamic SPL command resource."""
    return SPLCommandResource(version, command)


def create_admin_guide_resource(version: str, topic: str) -> AdminGuideResource:
    """Create a dynamic admin guide resource."""
    return AdminGuideResource(version, topic)


def create_troubleshooting_resource(version: str, topic: str) -> TroubleshootingResource:
    """Create a dynamic troubleshooting resource."""
    return TroubleshootingResource(version, topic)