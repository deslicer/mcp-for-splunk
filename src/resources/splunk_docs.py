"""
Splunk documentation resources for MCP server.

Provides version-aware access to Splunk documentation, optimized for LLM consumption.
"""

import logging
from datetime import datetime

from fastmcp import Context

from src.core.base import BaseResource, ResourceMetadata
from src.core.registry import resource_registry
from src.resources.admin_topics import (
    ADMIN_TOPICS,
    build_admin_url,
    build_admin_urls,
    list_admin_topics,
)
from src.resources.docs_http import (
    HAS_HTTPX,
    DocumentationCache,
    fetch_docs_url,
    is_error_doc_content,
)
from src.resources.docs_versions import (
    DEFAULT_DOC_VERSION,
    SUPPORTED_DOC_VERSIONS,
    build_spec_urls,
    build_spl_urls,
    build_troubleshooting_urls,
    parse_requested_version,
    version_mapping,
)

from .processors.html_processor import SplunkDocsProcessor

logger = logging.getLogger(__name__)

# Global documentation cache
_doc_cache = DocumentationCache()


class SplunkDocsResource(BaseResource):
    """Base class for Splunk documentation resources."""

    # SPLUNK_DOCS_BASE = "https://docs.splunk.com"
    SPLUNK_HELP_BASE = "https://help.splunk.com"
    VERSION_MAPPING = version_mapping()

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
        """Convert version to major.minor docs format."""
        return parse_requested_version(version)

    async def fetch_first_doc(self, urls: list[str]) -> tuple[str, str]:
        """Fetch the first live documentation URL and process its HTML."""
        if not urls:
            return await self.fetch_doc_content(""), ""
        last_content = ""
        last_url = urls[0]
        for url in urls:
            content = await self.fetch_doc_content(url)
            last_content = content
            last_url = url
            if not is_error_doc_content(content):
                return content, url
        return last_content, last_url

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

        result = await fetch_docs_url(url)
        if result.ok:
            logger.debug("Successfully fetched documentation from %s", result.final_url)
            return self.processor.process_html(result.text, result.final_url)

        if result.status_code == 404:
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

        return f"""# Documentation Error

Failed to fetch documentation due to HTTP error.

**URL**: {url}
**Status**: {result.status_code or "unavailable"}
**Error**: {result.error or "request failed"}
**Time**: {datetime.now().isoformat()}
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
            urls = build_troubleshooting_urls(topic_info["url_path"], self.version)
            content, url = await self.fetch_first_doc(urls)

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
            urls = build_spl_urls(self.command, self.version)
            content, url = await self.fetch_first_doc(urls)

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

    TOPIC_PATHS = {key: info["path"] for key, info in ADMIN_TOPICS.items()}

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
            help_version = self.format_version_for_help_url(self.version)
            urls = build_admin_urls(self.topic, self.version)
            if not urls:
                return self._unknown_topic_catalog(help_version)

            content, topic_url = await self.fetch_first_doc(urls)
            return f"""# Splunk Administration: {self.topic}

**Version**: Splunk {self.version}
**Category**: Administration Guide
**Source URL**: {topic_url}

{content}

## Administration Context

This documentation covers administrative aspects of Splunk deployment and configuration.

For related administration topics, see `list_admin_topics`.
"""

        return await _doc_cache.get_or_fetch(self.version, "admin", self.topic, fetch_admin_docs)

    def _build_topic_url(self, help_version: str) -> str | None:
        """Build a verified Splunk Help URL, or None if the topic is not catalogued."""
        return build_admin_url(self.topic, help_version)

    def _unknown_topic_catalog(self, help_version: str) -> str:
        """Return a stable catalog instead of guessing a 404 URL."""
        lines = [
            f"# Administration Topic Not Catalogued: {self.topic}",
            "",
            f"No verified help.splunk.com path exists for `{self.topic}` ",
            f"on Splunk {help_version}. Use one of these live topics instead:",
            "",
        ]
        for row in list_admin_topics():
            lines.append(f"- `{row['topic']}` — {row['description']}")
        lines.append("")
        lines.append("Call `list_admin_topics` or `get_admin_guide(\"<topic>\")`.")
        return "\n".join(lines)


class SplunkSpecReferenceResource(SplunkDocsResource):
    """Splunk configuration specification file reference documentation."""

    VERSION_PREFIXES = {"latest", "auto"}

    METADATA = ResourceMetadata(
        uri="splunk-spec://{config}",
        name="splunk_spec_reference",
        description="Splunk configuration specification reference (auto-detects version)",
        mime_type="text/markdown",
        category="reference",
        tags=["spec", "configuration", "reference", "admin"],
    )

    def __init__(self, config: str, version: str | None = None):
        parsed_version, parsed_config = self._split_versioned_config_reference(config)
        self.config = parsed_config
        self.version = version or parsed_version
        # Version will be detected dynamically in get_content()
        self._cached_version = None

        uri_path = f"{self.version}/{self.config}" if self.version else self.config
        uri = f"splunk-spec://{uri_path}"
        # Normalize config name for display
        display_config = self._normalize_config_name(self.config)
        super().__init__(
            uri=uri,
            name=f"spec_{uri_path.replace('/', '_').replace('.', '_')}",
            description=f"Splunk configuration spec for {display_config} (auto-detected version)",
        )

    def _split_versioned_config_reference(self, config: str) -> tuple[str | None, str]:
        """Split optional version prefixes from config references."""
        if "/" not in config:
            return None, config

        version, config_name = config.split("/", 1)
        if self._is_version_reference(version) and config_name:
            return version, config_name

        return None, config

    def _is_version_reference(self, value: str) -> bool:
        """Return whether a URI path segment is a Splunk version selector."""
        if value in self.VERSION_PREFIXES:
            return True

        parts = value.split(".")
        return len(parts) in {2, 3} and all(part.isdigit() for part in parts)

    def _parse_version_components(self, version: str) -> tuple[str, str]:
        """Parse version into minor (X.Y) and full (X.Y.Z) components.

        Args:
            version: Version string like "10.0", "9.4.0", "latest", "auto"

        Returns:
            Tuple of (minor, full) version strings
        """
        # Handle auto-detection
        if version == "auto":
            version = "latest"

        # Normalize using existing method to get minor version
        minor = self.normalize_version(version)

        # Now construct full version
        # If input was already X.Y.Z, try to preserve it
        parts = version.split(".")
        if len(parts) >= 3:
            # Has patch version already
            full = f"{parts[0]}.{parts[1]}.{parts[2]}"
        elif len(parts) == 2:
            # Only has major.minor, add .0 for patch
            full = f"{parts[0]}.{parts[1]}.0"
        else:
            # Single component or "latest" - use minor + .0
            full = f"{minor}.0"

        return minor, full

    def _normalize_config_name(self, config: str) -> str:
        """Normalize configuration file name to ensure .conf extension.

        Args:
            config: Config file name (with or without .conf)

        Returns:
            Config name with .conf extension
        """
        _, config = self._split_versioned_config_reference(config)

        # Always use .conf (not .conf.spec)
        if config.endswith(".conf.spec"):
            # Strip .spec suffix if present
            return config[:-5]  # Remove ".spec"
        elif config.endswith(".conf"):
            return config
        else:
            return f"{config}.conf"

    async def get_content(self, ctx: Context) -> str:
        """Get configuration specification documentation for specific file."""

        # Detect version once before caching unless the URI supplied one explicitly.
        version = self.version or await self.get_splunk_version(ctx)
        logger.info(f"Auto-detected Splunk version: {version}")

        async def fetch_spec_docs():
            # Version already detected above
            minor, full = self._parse_version_components(version)
            config = self._normalize_config_name(self.config)
            urls = build_spec_urls(config, version)
            content, used_url = await self.fetch_first_doc(urls)

            if content.startswith("# Documentation Not Found"):
                attempted = "\n".join(f"{i}. {url}" for i, url in enumerate(urls, start=1))
                return f"""# Configuration Spec Not Found

The requested Splunk configuration specification was not found.

**Config File**: {config}
**Version**: {version} (minor: {minor}, full: {full})
**Time**: {datetime.now().isoformat()}

**Attempted URLs**:
{attempted}

This may indicate:
- The configuration file name is incorrect or has a typo
- This Splunk version doesn't document this configuration file
- The documentation structure has changed

**Common configuration files**:
- alert_actions.conf
- limits.conf
- indexes.conf
- inputs.conf
- outputs.conf
- props.conf
- transforms.conf
- server.conf
- web.conf
- authentication.conf

Please verify the configuration file name and version, or check the [Splunk Documentation](https://help.splunk.com) directly.
"""

            # Wrap successful content with metadata
            result = f"""# Splunk Configuration Spec: {config}

**Version**: Splunk {version}
**Category**: Configuration File Reference
**Source URL**: {used_url}

{content}

## Configuration Context

This documentation describes the configuration specification for `{config}`. Configuration files in Splunk Enterprise:

- Control behavior and features of the Splunk platform
- Use INI-style stanza format with key-value pairs
- Follow precedence rules (system → local → app → user)
- Can be validated using `btool check`

### Related Resources

- [Configuration File Precedence](splunk-docs://{version}/admin/configuration-file-precedence)
- [List of Configuration Files](splunk-docs://{version}/admin/list-of-configuration-files)
- [Admin Guide](splunk-docs://{version}/admin)

---
**Generated**: {datetime.now().isoformat()}
"""
            return result

        return await _doc_cache.get_or_fetch(
            version, "spec-reference", self.config, fetch_spec_docs
        )


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

        admin_topics = [row["topic"] for row in list_admin_topics()]

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

        # Common configuration files for spec reference
        common_config_files = [
            "alert_actions.conf",
            "limits.conf",
            "indexes.conf",
            "inputs.conf",
            "outputs.conf",
            "props.conf",
            "transforms.conf",
            "server.conf",
            "web.conf",
            "authentication.conf",
            "authorize.conf",
            "savedsearches.conf",
        ]

        content += """

### 🧩 Configuration Spec Reference
Access configuration file specifications:

**Pattern**: `splunk-spec://{config}`

**💡 Pro Tip**: Version is automatically detected from your connected Splunk instance!

**Common Configuration Files**:
"""

        # Add config files in columns
        for i, config in enumerate(common_config_files):
            if i % 3 == 0:
                content += "\n"
            content += f"- [`{config}`](splunk-spec://{config})  "

        content += f"""

## Version Support

**Supported Versions**: {", ".join(SUPPORTED_DOC_VERSIONS)}, latest
**Default Version**: latest (currently {DEFAULT_DOC_VERSION})
**Auto-Detection**: Version automatically detected from your connected Splunk instance

### Examples

```
# Static resources (no version needed)
splunk-docs://cheat-sheet

# Dynamic resources with version
splunk-docs://9.4/troubleshooting/metrics-log
splunk-docs://latest/spl-reference/stats
splunk-docs://9.3.0/admin/indexes

# Configuration spec references (version auto-detected)
splunk-spec://alert_actions.conf
splunk-spec://limits.conf
splunk-spec://inputs.conf
splunk-spec://props.conf
splunk-spec://transforms.conf

# Auto-detect version for other resources (uses detected: {detected_version})
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

### Configuration References
- [🔧 Alert Actions Spec](splunk-spec://{detected_version}/alert_actions.conf) - Alert configuration
- [⚡ Limits Spec](splunk-spec://{detected_version}/limits.conf) - Performance tuning
- [📊 Indexes Spec](splunk-spec://{detected_version}/indexes.conf) - Index configuration
- [📥 Inputs Spec](splunk-spec://{detected_version}/inputs.conf) - Data input configuration

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
        resource_registry.register(
            SplunkSpecReferenceResource, SplunkSpecReferenceResource.METADATA
        )

        logger.info(
            "Successfully registered 7 Splunk documentation resources (3 static, 4 dynamic templates)"
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


def create_spec_reference_resource(
    config: str, version: str | None = None
) -> SplunkSpecReferenceResource:
    """Factory function to create configuration spec reference resources.

    Args:
        config: Configuration file name (e.g., "alert_actions.conf", "limits.conf")
        version: Optional Splunk version selector from versioned resource URIs

    Returns:
        SplunkSpecReferenceResource instance (version auto-detected from Splunk instance)
    """
    return SplunkSpecReferenceResource(config, version=version)


# Auto-register resources when module is imported
register_all_resources()
