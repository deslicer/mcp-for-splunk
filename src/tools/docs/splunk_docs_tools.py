"""
Documentation tools that wrap existing resources for agentic frameworks.

These tools provide access to Splunk documentation by wrapping existing resources
and returning embedded resources with actual content, making them compatible
with agentic frameworks that don't yet support MCP resources natively.
"""

import logging
from typing import Any

from fastmcp import Context

from src.core.base import BaseTool, ToolMetadata
from src.core.utils import log_tool_execution
from src.resources.dashboard_studio_docs import (
    DASHBOARD_STUDIO_TOPICS,
    DashboardStudioDiscoveryResource,
    DashboardStudioDocsResource,
)
from src.resources.splunk_cim import (
    CIMDataModelResource,
    CIMDiscoveryResource,
    SplunkCIMResource,
)
from src.resources.splunk_docs import (
    AdminGuideResource,
    DocumentationDiscoveryResource,
    SPLCommandResource,
    SplunkCheatSheetResource,
    SplunkSpecReferenceResource,
    TroubleshootingResource,
)

logger = logging.getLogger(__name__)


# Common Splunk configuration files
COMMON_CONFIG_FILES = {
    "alert_actions.conf": "Alert action definitions and configurations",
    "authentication.conf": "Authentication settings and configurations",
    "authorize.conf": "Role-based access control settings",
    "indexes.conf": "Index definitions and data retention policies",
    "inputs.conf": "Data input definitions and configurations",
    "limits.conf": "Resource limits and search constraints",
    "outputs.conf": "Forwarding and output configurations",
    "props.conf": "Field extraction, transforms, and sourcetype configs",
    "transforms.conf": "Field transformations and lookups",
    "savedsearches.conf": "Saved search and alert definitions",
    "server.conf": "Server-level settings and configurations",
    "web.conf": "Web interface and UI settings",
    "app.conf": "Application metadata and configurations",
    "commands.conf": "Custom search command definitions",
    "datamodels.conf": "Data model configurations",
    "eventtypes.conf": "Event type definitions",
    "fields.conf": "Field definitions and properties",
    "macros.conf": "Search macro definitions",
    "tags.conf": "Event tag definitions",
    "workflow_actions.conf": "Workflow action configurations",
}


class ListAvailableTopics(BaseTool):
    """
    List all available documentation topics for discovery.

    This tool provides comprehensive lists of available topics for troubleshooting,
    admin guides, SPL commands, and URI patterns to help LLMs and agentic frameworks
    understand what documentation is available.
    """

    METADATA = ToolMetadata(
        name="list_available_topics",
        description=(
            "List all available documentation topics and URI patterns for discovery. "
            "This tool helps LLMs and agentic frameworks understand what documentation "
            "topics are available across different categories:\n\n"
            "Returns structured information about:\n"
            "- Available troubleshooting topics with descriptions\n"
            "- Available admin guide topics\n"
            "- Common SPL commands with examples\n"
            "- URI patterns for accessing documentation\n"
            "- Version support information\n\n"
            "Use this tool first to discover what documentation is available before "
            "requesting specific topics."
        ),
        category="documentation",
        tags=["discovery", "topics", "reference", "embedded-resource"],
        requires_connection=False,
    )

    async def execute(self, ctx: Context) -> dict[str, Any]:
        """List all available documentation topics."""
        log_tool_execution(self.name)

        try:
            # Get troubleshooting topics
            troubleshooting_topics = []
            for topic_key, topic_info in TroubleshootingResource.TROUBLESHOOTING_TOPICS.items():
                troubleshooting_topics.append(
                    {
                        "topic": topic_key,
                        "title": topic_info["title"],
                        "description": topic_info["description"],
                        "example_uri": f"splunk-docs://latest/troubleshooting/{topic_key}",
                    }
                )

            # Get admin topics
            admin_topics = [
                {"topic": "indexes", "description": "Index management and configuration"},
                {"topic": "authentication", "description": "Authentication and user management"},
                {"topic": "deployment", "description": "Deployment and installation guides"},
                {"topic": "apps", "description": "Application management and configuration"},
                {"topic": "users", "description": "User and role management"},
                {"topic": "roles", "description": "Role-based access control"},
                {"topic": "monitoring", "description": "System monitoring and health checks"},
                {"topic": "performance", "description": "Performance tuning and optimization"},
                {"topic": "clustering", "description": "Clustering and high availability"},
                {"topic": "distributed-search", "description": "Distributed search configuration"},
                {"topic": "forwarders", "description": "Universal and heavy forwarder setup"},
                {"topic": "inputs", "description": "Data input configuration"},
                {"topic": "outputs", "description": "Data output configuration"},
                {"topic": "licensing", "description": "License management"},
                {"topic": "security", "description": "Security configuration and best practices"},
            ]

            # Get common SPL commands
            spl_commands = [
                {"command": "stats", "description": "Statistical aggregation and analysis"},
                {"command": "eval", "description": "Field calculation and manipulation"},
                {"command": "search", "description": "Search filtering and field extraction"},
                {"command": "timechart", "description": "Time-based charting and visualization"},
                {"command": "chart", "description": "Chart creation and data visualization"},
                {"command": "table", "description": "Table formatting and field display"},
                {"command": "sort", "description": "Sort events by field values"},
                {"command": "head", "description": "Return first N events"},
                {"command": "tail", "description": "Return last N events"},
                {"command": "rex", "description": "Regular expression field extraction"},
                {"command": "lookup", "description": "Data enrichment from lookup tables"},
                {"command": "join", "description": "Join events from multiple sources"},
                {"command": "append", "description": "Append search results"},
                {"command": "dedup", "description": "Remove duplicate events"},
                {"command": "where", "description": "Filter events with boolean expressions"},
                {"command": "bucket", "description": "Group events into time buckets"},
                {"command": "top", "description": "Find most common field values"},
                {"command": "rare", "description": "Find least common field values"},
                {"command": "transaction", "description": "Group events into transactions"},
                {"command": "subsearch", "description": "Use subsearch results in main search"},
            ]

            # URI patterns
            uri_patterns = [
                {
                    "pattern": "splunk-docs://cheat-sheet",
                    "description": "Complete Splunk SPL cheat sheet",
                    "example": "splunk-docs://cheat-sheet",
                },
                {
                    "pattern": "splunk-docs://discovery",
                    "description": "Documentation discovery guide",
                    "example": "splunk-docs://discovery",
                },
                {
                    "pattern": "splunk-docs://{version}/spl-reference/{command}",
                    "description": "SPL command reference documentation",
                    "example": "splunk-docs://latest/spl-reference/stats",
                },
                {
                    "pattern": "splunk-docs://{version}/troubleshooting/{topic}",
                    "description": "Troubleshooting guides for specific topics",
                    "example": "splunk-docs://9.4/troubleshooting/metrics-log",
                },
                {
                    "pattern": "splunk-docs://{version}/admin/{topic}",
                    "description": "Administration guides for specific topics",
                    "example": "splunk-docs://latest/admin/indexes",
                },
            ]

            # Version information
            version_info = {
                "supported_versions": ["9.4", "9.3", "9.2", "9.1", "9.0", "8.2", "latest"],
                "default_version": "latest",
                "auto_detection": "Available when connected to Splunk instance",
            }

            content = f"""# Available Documentation Topics

This reference lists all available documentation topics, commands, and URI patterns for the Splunk MCP server.

## Troubleshooting Topics

{len(troubleshooting_topics)} troubleshooting topics available:

| Topic | Title | Description |
|-------|-------|-------------|
"""

            for topic in troubleshooting_topics:
                content += f"| `{topic['topic']}` | {topic['title']} | {topic['description']} |\n"

            content += f"""

**Usage Examples:**
```
get_troubleshooting_guide("metrics-log")
get_troubleshooting_guide("platform-instrumentation", version="9.4")
get_splunk_documentation("splunk-docs://latest/troubleshooting/indexing-performance")
```

## Admin Guide Topics

{len(admin_topics)} admin topics available:

| Topic | Description |
|-------|-------------|
"""

            for topic in admin_topics:
                content += f"| `{topic['topic']}` | {topic['description']} |\n"

            content += f"""

**Usage Examples:**
```
get_admin_guide("indexes")
get_admin_guide("authentication", version="9.4")
get_splunk_documentation("splunk-docs://latest/admin/clustering")
```

## SPL Commands

{len(spl_commands)} common SPL commands available:

| Command | Description |
|---------|-------------|
"""

            for cmd in spl_commands:
                content += f"| `{cmd['command']}` | {cmd['description']} |\n"

            content += """

**Usage Examples:**
```
get_spl_reference("stats")
get_spl_reference("eval", version="9.4")
get_splunk_documentation("splunk-docs://latest/spl-reference/timechart")
```

## URI Patterns

Available URI patterns for `get_splunk_documentation`:

| Pattern | Description | Example |
|---------|-------------|---------|
"""

            for pattern in uri_patterns:
                content += f"| `{pattern['pattern']}` | {pattern['description']} | `{pattern['example']}` |\n"

            content += f"""

## Version Support

**Supported Versions:** {", ".join(version_info["supported_versions"])}
**Default Version:** {version_info["default_version"]}
**Auto-Detection:** {version_info["auto_detection"]}

## Quick Reference

### Most Common Use Cases

1. **Get cheat sheet:** `get_splunk_cheat_sheet()`
2. **Discover documentation:** `discover_splunk_docs()`
3. **Get SPL command help:** `get_spl_reference("stats")`
4. **Troubleshoot issues:** `get_troubleshooting_guide("metrics-log")`
5. **Admin configuration:** `get_admin_guide("indexes")`

### Tool Selection Guide

- **`list_available_topics`** - Use this first to discover available topics
- **`get_splunk_cheat_sheet`** - For quick SPL syntax reference
- **`discover_splunk_docs`** - For comprehensive documentation overview
- **`get_spl_reference`** - For specific SPL command documentation
- **`get_troubleshooting_guide`** - For troubleshooting specific issues
- **`get_admin_guide`** - For administration configuration help
- **`get_splunk_documentation`** - For flexible URI-based access

### Error Handling

If you specify an invalid topic, the tool will return an error message with available options:
- Troubleshooting: Available topics listed above
- Admin: Available topics listed above
- SPL: Most common commands listed above (supports many more)

### Performance Notes

- All documentation is cached for improved performance
- Version auto-detection requires Splunk connection
- Static resources (cheat sheet, discovery) load fastest
- Dynamic resources fetch from Splunk documentation sites
"""

            return self.format_success_response(
                {
                    "content": [
                        {
                            "type": "resource",
                            "resource": {
                                "uri": "splunk-docs://available-topics",
                                "title": "Available Documentation Topics",
                                "mimeType": "text/markdown",
                                "text": content,
                            },
                        }
                    ]
                }
            )

        except Exception as e:
            error_msg = f"Failed to list available topics: {str(e)}"
            self.logger.error(error_msg)
            return self.format_error_response(error_msg)


class ListTroubleshootingTopics(BaseTool):
    """
    List available troubleshooting topics specifically.

    This tool provides a focused list of troubleshooting topics for quick reference.
    """

    METADATA = ToolMetadata(
        name="list_troubleshooting_topics",
        description=(
            "List all available troubleshooting topics with descriptions. "
            "Returns a structured list of troubleshooting topics that can be used "
            "with the get_troubleshooting_guide tool. Each topic includes:\n\n"
            "- Topic key for use in API calls\n"
            "- Human-readable title\n"
            "- Description of what the topic covers\n"
            "- Example usage\n\n"
            "Use this tool to discover what troubleshooting documentation is available "
            "before calling get_troubleshooting_guide with specific topics."
        ),
        category="documentation",
        tags=["troubleshooting", "topics", "discovery", "embedded-resource"],
        requires_connection=False,
    )

    async def execute(self, ctx: Context) -> dict[str, Any]:
        """List available troubleshooting topics."""
        log_tool_execution(self.name)

        try:
            topics = []
            for topic_key, topic_info in TroubleshootingResource.TROUBLESHOOTING_TOPICS.items():
                topics.append(
                    {
                        "topic": topic_key,
                        "title": topic_info["title"],
                        "description": topic_info["description"],
                    }
                )

            content = f"""# Available Troubleshooting Topics

{len(topics)} troubleshooting topics available:

"""

            for topic in topics:
                content += f"""## {topic["title"]}
**Topic Key:** `{topic["topic"]}`
**Description:** {topic["description"]}
**Usage:** `get_troubleshooting_guide("{topic["topic"]}")`

"""

            content += """## How to Use

Call `get_troubleshooting_guide(topic, version="latest")` with any of the topic keys above.

Examples:
```python
# Get metrics.log troubleshooting guide
get_troubleshooting_guide("metrics-log")

# Get platform instrumentation guide for specific version
get_troubleshooting_guide("platform-instrumentation", version="9.4")

# Get indexing performance troubleshooting
get_troubleshooting_guide("indexing-performance")
```
"""

            return self.format_success_response(
                {
                    "content": [
                        {
                            "type": "resource",
                            "resource": {
                                "uri": "splunk-docs://troubleshooting-topics",
                                "title": "Available Troubleshooting Topics",
                                "mimeType": "text/markdown",
                                "text": content,
                            },
                        }
                    ]
                }
            )

        except Exception as e:
            error_msg = f"Failed to list troubleshooting topics: {str(e)}"
            self.logger.error(error_msg)
            return self.format_error_response(error_msg)


class ListAdminTopics(BaseTool):
    """
    List available admin guide topics specifically.

    This tool provides a focused list of admin topics for quick reference.
    """

    METADATA = ToolMetadata(
        name="list_admin_topics",
        description=(
            "List all available admin guide topics with descriptions. "
            "Returns a structured list of administration topics that can be used "
            "with the get_admin_guide tool. Each topic includes:\n\n"
            "- Topic key for use in API calls\n"
            "- Description of what the topic covers\n"
            "- Example usage\n\n"
            "Use this tool to discover what admin documentation is available "
            "before calling get_admin_guide with specific topics."
        ),
        category="documentation",
        tags=["admin", "topics", "discovery", "embedded-resource"],
        requires_connection=False,
    )

    async def execute(self, ctx: Context) -> dict[str, Any]:
        """List available admin topics."""
        log_tool_execution(self.name)

        try:
            topics = [
                {"topic": "indexes", "description": "Index management and configuration"},
                {"topic": "authentication", "description": "Authentication and user management"},
                {"topic": "deployment", "description": "Deployment and installation guides"},
                {"topic": "apps", "description": "Application management and configuration"},
                {"topic": "users", "description": "User and role management"},
                {"topic": "roles", "description": "Role-based access control"},
                {"topic": "monitoring", "description": "System monitoring and health checks"},
                {"topic": "performance", "description": "Performance tuning and optimization"},
                {"topic": "clustering", "description": "Clustering and high availability"},
                {"topic": "distributed-search", "description": "Distributed search configuration"},
                {"topic": "forwarders", "description": "Universal and heavy forwarder setup"},
                {"topic": "inputs", "description": "Data input configuration"},
                {"topic": "outputs", "description": "Data output configuration"},
                {"topic": "licensing", "description": "License management"},
                {"topic": "security", "description": "Security configuration and best practices"},
            ]

            content = f"""# Available Admin Guide Topics

{len(topics)} admin topics available:

"""

            for topic in topics:
                content += f"""## {topic["topic"].replace("-", " ").title()}
**Topic Key:** `{topic["topic"]}`
**Description:** {topic["description"]}
**Usage:** `get_admin_guide("{topic["topic"]}")`

"""

            content += """## How to Use

Call `get_admin_guide(topic, version="latest")` with any of the topic keys above.

Examples:
```python
# Get index management guide
get_admin_guide("indexes")

# Get authentication guide for specific version
get_admin_guide("authentication", version="9.4")

# Get clustering configuration guide
get_admin_guide("clustering")
```
"""

            return self.format_success_response(
                {
                    "content": [
                        {
                            "type": "resource",
                            "resource": {
                                "uri": "splunk-docs://admin-topics",
                                "title": "Available Admin Guide Topics",
                                "mimeType": "text/markdown",
                                "text": content,
                            },
                        }
                    ]
                }
            )

        except Exception as e:
            error_msg = f"Failed to list admin topics: {str(e)}"
            self.logger.error(error_msg)
            return self.format_error_response(error_msg)


class ListSPLCommands(BaseTool):
    """
    List common SPL commands for reference.

    This tool provides a list of common SPL commands that can be used with get_spl_reference.
    """

    METADATA = ToolMetadata(
        name="list_spl_commands",
        description=(
            "List common SPL (Search Processing Language) commands with descriptions. "
            "Returns a structured list of SPL commands that can be used with the "
            "get_spl_reference tool. Each command includes:\n\n"
            "- Command name for use in API calls\n"
            "- Description of what the command does\n"
            "- Example usage\n\n"
            "Note: This list includes the most common commands, but get_spl_reference "
            "supports many more SPL commands beyond those listed here."
        ),
        category="documentation",
        tags=["spl", "commands", "discovery", "embedded-resource"],
        requires_connection=False,
    )

    async def execute(self, ctx: Context) -> dict[str, Any]:
        """List common SPL commands."""
        log_tool_execution(self.name)

        try:
            commands = [
                {"command": "stats", "description": "Statistical aggregation and analysis"},
                {"command": "eval", "description": "Field calculation and manipulation"},
                {"command": "search", "description": "Search filtering and field extraction"},
                {"command": "timechart", "description": "Time-based charting and visualization"},
                {"command": "chart", "description": "Chart creation and data visualization"},
                {"command": "table", "description": "Table formatting and field display"},
                {"command": "sort", "description": "Sort events by field values"},
                {"command": "head", "description": "Return first N events"},
                {"command": "tail", "description": "Return last N events"},
                {"command": "rex", "description": "Regular expression field extraction"},
                {"command": "lookup", "description": "Data enrichment from lookup tables"},
                {"command": "join", "description": "Join events from multiple sources"},
                {"command": "append", "description": "Append search results"},
                {"command": "dedup", "description": "Remove duplicate events"},
                {"command": "where", "description": "Filter events with boolean expressions"},
                {"command": "bucket", "description": "Group events into time buckets"},
                {"command": "top", "description": "Find most common field values"},
                {"command": "rare", "description": "Find least common field values"},
                {"command": "transaction", "description": "Group events into transactions"},
                {"command": "subsearch", "description": "Use subsearch results in main search"},
            ]

            content = f"""# Common SPL Commands

{len(commands)} common SPL commands available:

"""

            for cmd in commands:
                content += f"""## {cmd["command"]}
**Description:** {cmd["description"]}
**Usage:** `get_spl_reference("{cmd["command"]}")`

"""

            content += """## How to Use

Call `get_spl_reference(command, version="latest")` with any of the command names above.

Examples:
```python
# Get stats command reference
get_spl_reference("stats")

# Get eval command reference for specific version
get_spl_reference("eval", version="9.4")

# Get timechart command reference
get_spl_reference("timechart")
```

## Note

This list includes the most common SPL commands, but `get_spl_reference` supports many more commands beyond those listed here. If you need documentation for a specific SPL command not listed, try calling `get_spl_reference` with the command name anyway - it may still be available.
"""

            return self.format_success_response(
                {
                    "content": [
                        {
                            "type": "resource",
                            "resource": {
                                "uri": "splunk-docs://spl-commands",
                                "title": "Common SPL Commands",
                                "mimeType": "text/markdown",
                                "text": content,
                            },
                        }
                    ]
                }
            )

        except Exception as e:
            error_msg = f"Failed to list SPL commands: {str(e)}"
            self.logger.error(error_msg)
            return self.format_error_response(error_msg)


class GetSplunkDocumentation(BaseTool):
    """
    Universal Splunk documentation retrieval tool.

    This tool wraps existing documentation resources and returns embedded resources
    with actual content for use with agentic frameworks.
    """

    METADATA = ToolMetadata(
        name="get_splunk_documentation",
        description=(
            "Retrieve any Splunk documentation by URI pattern. This tool wraps existing "
            "documentation resources and returns embedded resources with actual content, "
            "making them compatible with agentic frameworks that don't support MCP resources "
            "natively. Supports all documentation types including cheat sheets, troubleshooting "
            "guides, SPL references, and admin guides.\n\n"
            "Args:\n"
            "    doc_uri (str): Documentation URI pattern. Use list_available_topics() to see "
            "all available URI patterns and topics. Examples:\n"
            "        - 'splunk-docs://cheat-sheet' - Splunk SPL cheat sheet\n"
            "        - 'splunk-docs://discovery' - Available documentation discovery\n"
            "        - 'splunk-docs://9.4/spl-reference/stats' - SPL stats command\n"
            "        - 'splunk-docs://latest/troubleshooting/metrics-log' - Troubleshooting guide\n"
            "        - 'splunk-docs://9.3/admin/indexes' - Admin guide for indexes\n"
            "        - 'splunk-cim://authentication' - CIM data model (latest version)\n"
            "        - 'splunk-cim://6.1/network-traffic' - CIM data model (specific version)\n"
            "        - 'splunk-cim://discovery' - CIM discovery index\n"
            "        - 'dashboard-studio://cheatsheet' - Dashboard Studio cheatsheet\n"
            "        - 'dashboard-studio://discovery' - Dashboard Studio discovery\n"
            "        - 'splunk-spec://props.conf' - Config file specification\n"
            "    auto_detect_version (bool, optional): Whether to auto-detect Splunk version "
            "for dynamic resources. Defaults to True.\n\n"
            "Returns embedded resource with actual documentation content in markdown format.\n\n"
            "💡 Tip: Use list_available_topics() to discover all available URI patterns and topics."
        ),
        category="documentation",
        tags=["documentation", "embedded-resource", "splunk", "agentic"],
        requires_connection=False,
    )

    async def execute(
        self, ctx: Context, doc_uri: str, auto_detect_version: bool = True
    ) -> dict[str, Any]:
        """Execute documentation retrieval and return embedded resource."""
        log_tool_execution(self.name, doc_uri=doc_uri, auto_detect_version=auto_detect_version)

        try:
            # Parse the URI to determine resource type
            content = await self._get_documentation_content(ctx, doc_uri, auto_detect_version)

            # Return as embedded resource according to MCP specification
            return self.format_success_response(
                {
                    "content": [
                        {
                            "type": "resource",
                            "resource": {
                                "uri": doc_uri,
                                "title": self._get_doc_title(doc_uri),
                                "mimeType": "text/markdown",
                                "text": content,
                            },
                        }
                    ]
                }
            )

        except Exception as e:
            error_msg = f"Failed to retrieve documentation for URI '{doc_uri}': {str(e)}"
            self.logger.error(error_msg)
            return self.format_error_response(error_msg)

    async def _get_documentation_content(
        self, ctx: Context, doc_uri: str, auto_detect_version: bool
    ) -> str:
        """Get documentation content from appropriate resource."""

        # Static resources
        if doc_uri == "splunk-docs://cheat-sheet":
            resource = SplunkCheatSheetResource()
            return await resource.get_content(ctx)

        elif doc_uri == "splunk-docs://discovery":
            resource = DocumentationDiscoveryResource()
            return await resource.get_content(ctx)

        # Dynamic resources - parse URI components
        elif doc_uri.startswith("splunk-docs://"):
            parts = doc_uri.replace("splunk-docs://", "").split("/")

            if len(parts) >= 3:
                version = parts[0]
                doc_type = parts[1]
                topic = "/".join(parts[2:])

                # Auto-detect version if requested
                if auto_detect_version and version in ["auto", "latest"]:
                    version = await self._detect_splunk_version(ctx)

                # Route to appropriate resource
                if doc_type == "spl-reference":
                    resource = SPLCommandResource(version, topic)
                    return await resource.get_content(ctx)

                elif doc_type == "troubleshooting":
                    resource = TroubleshootingResource(version, topic)
                    return await resource.get_content(ctx)

                elif doc_type == "admin":
                    resource = AdminGuideResource(version, topic)
                    return await resource.get_content(ctx)

        # CIM resources
        elif doc_uri.startswith("splunk-cim://"):
            parts = doc_uri.replace("splunk-cim://", "").split("/")
            if parts[0] == "discovery":
                resource = CIMDiscoveryResource()
                return await resource.get_content(ctx)
            elif len(parts) == 1:
                # splunk-cim://model (use latest version)
                resource = CIMDataModelResource("latest", parts[0])
                return await resource.get_content(ctx)
            elif len(parts) == 2:
                # splunk-cim://version/model
                resource = CIMDataModelResource(parts[0], parts[1])
                return await resource.get_content(ctx)

        # Dashboard Studio resources
        elif doc_uri.startswith("dashboard-studio://"):
            topic = doc_uri.replace("dashboard-studio://", "")
            if topic == "discovery":
                resource = DashboardStudioDiscoveryResource()
                return await resource.get_content(ctx)
            else:
                resource = DashboardStudioDocsResource(topic)
                return await resource.get_content(ctx)

        # Config spec resources
        elif doc_uri.startswith("splunk-spec://"):
            config = doc_uri.replace("splunk-spec://", "")
            resource = SplunkSpecReferenceResource(config)
            return await resource.get_content(ctx)

        raise ValueError(f"Unsupported documentation URI: {doc_uri}")

    async def _detect_splunk_version(self, ctx: Context) -> str:
        """Detect Splunk version from connected instance."""
        try:
            from src.tools.health.status import GetSplunkHealth

            health_tool = GetSplunkHealth("get_splunk_health", "Get Splunk health status")
            health_result = await health_tool.execute(ctx)

            if (
                health_result.get("status") == "success"
                and health_result.get("data", {}).get("status") == "connected"
            ):
                return health_result["data"].get("version", "latest")
        except Exception as e:
            logger.warning(f"Failed to detect Splunk version: {e}")

        return "latest"

    def _get_doc_title(self, doc_uri: str) -> str:
        """Generate appropriate title for documentation resource."""
        if doc_uri == "splunk-docs://cheat-sheet":
            return "Splunk SPL Cheat Sheet"
        elif doc_uri == "splunk-docs://discovery":
            return "Splunk Documentation Discovery"
        elif "/spl-reference/" in doc_uri:
            parts = doc_uri.split("/")
            return f"SPL Reference: {parts[-1]}"
        elif "/troubleshooting/" in doc_uri:
            parts = doc_uri.split("/")
            return f"Troubleshooting: {parts[-1]}"
        elif "/admin/" in doc_uri:
            parts = doc_uri.split("/")
            return f"Admin Guide: {parts[-1]}"
        elif doc_uri.startswith("splunk-cim://"):
            if "discovery" in doc_uri:
                return "CIM Data Models Discovery"
            parts = doc_uri.split("/")
            return f"CIM Data Model: {parts[-1]}"
        elif doc_uri.startswith("dashboard-studio://"):
            if "discovery" in doc_uri:
                return "Dashboard Studio Documentation Discovery"
            topic = doc_uri.replace("dashboard-studio://", "")
            return f"Dashboard Studio: {topic}"
        elif doc_uri.startswith("splunk-spec://"):
            config = doc_uri.replace("splunk-spec://", "")
            return f"Config Spec: {config}"
        else:
            return "Splunk Documentation"


class GetSplunkCheatSheet(BaseTool):
    """
    Quick access to Splunk SPL cheat sheet.

    Returns the complete Splunk cheat sheet as an embedded resource.
    """

    METADATA = ToolMetadata(
        name="get_splunk_cheat_sheet",
        description=(
            "Get the comprehensive Splunk SPL cheat sheet with commands, regex patterns, "
            "and usage examples. Returns the complete cheat sheet as an embedded resource "
            "with actual markdown content, perfect for quick reference during SPL query "
            "development and troubleshooting.\n\n"
            "Returns embedded resource with complete SPL reference content including:\n"
            "- Core SPL commands and syntax\n"
            "- Regular expression patterns\n"
            "- Statistical functions\n"
            "- Time modifiers and formatting\n"
            "- Search optimization tips\n"
            "- Common use cases and examples"
        ),
        category="documentation",
        tags=["cheat-sheet", "spl", "reference", "embedded-resource"],
        requires_connection=False,
    )

    async def execute(self, ctx: Context) -> dict[str, Any]:
        """Execute cheat sheet retrieval and return embedded resource."""
        log_tool_execution(self.name)

        try:
            resource = SplunkCheatSheetResource()
            content = await resource.get_content(ctx)

            return self.format_success_response(
                {
                    "content": [
                        {
                            "type": "resource",
                            "resource": {
                                "uri": "splunk-docs://cheat-sheet",
                                "title": "Splunk SPL Cheat Sheet",
                                "mimeType": "text/markdown",
                                "text": content,
                            },
                        }
                    ]
                }
            )

        except Exception as e:
            error_msg = f"Failed to retrieve Splunk cheat sheet: {str(e)}"
            self.logger.error(error_msg)
            return self.format_error_response(error_msg)


class DiscoverSplunkDocs(BaseTool):
    """
    Discover available Splunk documentation resources.

    Returns a comprehensive guide to all available documentation resources.
    """

    METADATA = ToolMetadata(
        name="discover_splunk_docs",
        description=(
            "Discover all available Splunk documentation resources with examples and usage patterns. "
            "Returns a comprehensive guide showing available documentation types, URI patterns, "
            "and quick access links. Perfect for understanding what documentation is available "
            "and how to access it through the documentation tools.\n\n"
            "Returns embedded resource with discovery guide including:\n"
            "- Static documentation resources (cheat sheet, etc.)\n"
            "- Dynamic documentation patterns (SPL reference, troubleshooting, admin guides)\n"
            "- Version support information\n"
            "- Quick access examples for common documentation needs\n"
            "- Usage patterns for agentic frameworks"
        ),
        category="documentation",
        tags=["discovery", "documentation", "reference", "embedded-resource"],
        requires_connection=False,
    )

    async def execute(self, ctx: Context) -> dict[str, Any]:
        """Execute documentation discovery and return embedded resource."""
        log_tool_execution(self.name)

        try:
            resource = DocumentationDiscoveryResource()
            content = await resource.get_content(ctx)

            return self.format_success_response(
                {
                    "content": [
                        {
                            "type": "resource",
                            "resource": {
                                "uri": "splunk-docs://discovery",
                                "title": "Splunk Documentation Discovery",
                                "mimeType": "text/markdown",
                                "text": content,
                            },
                        }
                    ]
                }
            )

        except Exception as e:
            error_msg = f"Failed to discover documentation: {str(e)}"
            self.logger.error(error_msg)
            return self.format_error_response(error_msg)


class GetSPLReference(BaseTool):
    """
    Get SPL (Search Processing Language) command reference.

    Returns detailed documentation for specific SPL commands.
    """

    METADATA = ToolMetadata(
        name="get_spl_reference",
        description=(
            "Get detailed reference documentation for specific SPL (Search Processing Language) "
            "commands. Returns comprehensive documentation with syntax, examples, and usage "
            "patterns as an embedded resource.\n\n"
            "Args:\n"
            "    command (str): SPL command name. Use list_spl_commands() to see common "
            "commands. Examples:\n"
            "        - 'stats' - Statistical aggregation command\n"
            "        - 'eval' - Field calculation and manipulation\n"
            "        - 'search' - Search filtering command\n"
            "        - 'timechart' - Time-based charting\n"
            "        - 'rex' - Regular expression field extraction\n"
            "        - 'lookup' - Data enrichment from lookups\n"
            "    version (str, optional): Splunk version for documentation. Examples:\n"
            "        - '9.4' - Splunk 9.4 documentation\n"
            "        - '9.3' - Splunk 9.3 documentation\n"
            "        - 'latest' - Latest version (default)\n"
            "    auto_detect_version (bool, optional): Whether to auto-detect Splunk version "
            "from connected instance. Defaults to True.\n\n"
            "Returns embedded resource with detailed SPL command documentation.\n\n"
            "💡 Tip: Use list_spl_commands() to see common commands, but this tool supports "
            "many more SPL commands beyond the common ones listed."
        ),
        category="documentation",
        tags=["spl", "reference", "commands", "embedded-resource"],
        requires_connection=False,
    )

    async def execute(
        self, ctx: Context, command: str, version: str = "latest", auto_detect_version: bool = True
    ) -> dict[str, Any]:
        """Execute SPL reference retrieval and return embedded resource."""
        log_tool_execution(
            self.name, command=command, version=version, auto_detect_version=auto_detect_version
        )

        try:
            # Auto-detect version if requested
            if auto_detect_version and version in ["auto", "latest"]:
                version = await self._detect_splunk_version(ctx)

            resource = SPLCommandResource(version, command)
            content = await resource.get_content(ctx)

            uri = f"splunk-docs://{version}/spl-reference/{command}"

            return self.format_success_response(
                {
                    "content": [
                        {
                            "type": "resource",
                            "resource": {
                                "uri": uri,
                                "title": f"SPL Reference: {command}",
                                "mimeType": "text/markdown",
                                "text": content,
                            },
                        }
                    ]
                }
            )

        except Exception as e:
            error_msg = f"Failed to retrieve SPL reference for command '{command}': {str(e)}"
            self.logger.error(error_msg)
            return self.format_error_response(error_msg)

    async def _detect_splunk_version(self, ctx: Context) -> str:
        """Detect Splunk version from connected instance."""
        try:
            from src.tools.health.status import GetSplunkHealth

            health_tool = GetSplunkHealth("get_splunk_health", "Get Splunk health status")
            health_result = await health_tool.execute(ctx)

            if (
                health_result.get("status") == "success"
                and health_result.get("data", {}).get("status") == "connected"
            ):
                return health_result["data"].get("version", "latest")
        except Exception as e:
            logger.warning(f"Failed to detect Splunk version: {e}")

        return "latest"


class GetTroubleshootingGuide(BaseTool):
    """
    Get Splunk troubleshooting documentation.

    Returns detailed troubleshooting guides for specific topics.
    """

    METADATA = ToolMetadata(
        name="get_troubleshooting_guide",
        description=(
            "Get detailed Splunk troubleshooting documentation for specific topics. "
            "Returns comprehensive troubleshooting guides with diagnostics, solutions, "
            "and best practices as an embedded resource.\n\n"
            "Args:\n"
            "    topic (str): Troubleshooting topic. Use list_troubleshooting_topics() to see "
            "all available topics. Common topics include:\n"
            "        - 'metrics-log' - About metrics.log for performance monitoring\n"
            "        - 'splunk-logs' - What Splunk logs about itself\n"
            "        - 'platform-instrumentation' - Platform instrumentation overview\n"
            "        - 'search-problems' - Splunk web and search problems\n"
            "        - 'indexing-performance' - Indexing performance issues\n"
            "        - 'indexing-delay' - Event indexing delays\n"
            "        - 'authentication-timeouts' - Authentication timeout issues\n"
            "    version (str, optional): Splunk version for documentation. Examples:\n"
            "        - '9.4' - Splunk 9.4 documentation\n"
            "        - '9.3' - Splunk 9.3 documentation\n"
            "        - 'latest' - Latest version (default)\n"
            "    auto_detect_version (bool, optional): Whether to auto-detect Splunk version "
            "from connected instance. Defaults to True.\n\n"
            "Returns embedded resource with detailed troubleshooting guide.\n\n"
            "💡 Tip: Use list_troubleshooting_topics() to discover all available topics."
        ),
        category="documentation",
        tags=["troubleshooting", "diagnostics", "guides", "embedded-resource"],
        requires_connection=False,
    )

    async def execute(
        self, ctx: Context, topic: str, version: str = "latest", auto_detect_version: bool = True
    ) -> dict[str, Any]:
        """Execute troubleshooting guide retrieval and return embedded resource."""
        log_tool_execution(
            self.name, topic=topic, version=version, auto_detect_version=auto_detect_version
        )

        try:
            # Auto-detect version if requested
            if auto_detect_version and version in ["auto", "latest"]:
                version = await self._detect_splunk_version(ctx)

            resource = TroubleshootingResource(version, topic)
            content = await resource.get_content(ctx)

            uri = f"splunk-docs://{version}/troubleshooting/{topic}"

            return self.format_success_response(
                {
                    "content": [
                        {
                            "type": "resource",
                            "resource": {
                                "uri": uri,
                                "title": f"Troubleshooting: {topic}",
                                "mimeType": "text/markdown",
                                "text": content,
                            },
                        }
                    ]
                }
            )

        except Exception as e:
            error_msg = f"Failed to retrieve troubleshooting guide for topic '{topic}': {str(e)}"
            self.logger.error(error_msg)
            return self.format_error_response(error_msg)

    async def _detect_splunk_version(self, ctx: Context) -> str:
        """Detect Splunk version from connected instance."""
        try:
            from src.tools.health.status import GetSplunkHealth

            health_tool = GetSplunkHealth("get_splunk_health", "Get Splunk health status")
            health_result = await health_tool.execute(ctx)

            if (
                health_result.get("status") == "success"
                and health_result.get("data", {}).get("status") == "connected"
            ):
                return health_result["data"].get("version", "latest")
        except Exception as e:
            logger.warning(f"Failed to detect Splunk version: {e}")

        return "latest"


class GetAdminGuide(BaseTool):
    """
    Get Splunk administration documentation.

    Returns detailed administration guides for specific topics.
    """

    METADATA = ToolMetadata(
        name="get_admin_guide",
        description=(
            "Get detailed Splunk administration documentation for specific topics. "
            "Returns comprehensive administration guides with configuration, management, "
            "and best practices as an embedded resource.\n\n"
            "Args:\n"
            "    topic (str): Administration topic. Use list_admin_topics() to see all "
            "available topics. Common topics include:\n"
            "        - 'indexes' - Index management and configuration\n"
            "        - 'authentication' - User authentication setup\n"
            "        - 'users' - User management and roles\n"
            "        - 'apps' - Application management\n"
            "        - 'deployment' - Deployment configuration\n"
            "        - 'monitoring' - System monitoring setup\n"
            "        - 'performance' - Performance optimization\n"
            "        - 'security' - Security configuration\n"
            "        - 'forwarders' - Forwarder configuration\n"
            "        - 'clustering' - Clustering setup\n"
            "    version (str, optional): Splunk version for documentation. Examples:\n"
            "        - '9.4' - Splunk 9.4 documentation\n"
            "        - '9.3' - Splunk 9.3 documentation\n"
            "        - 'latest' - Latest version (default)\n"
            "    auto_detect_version (bool, optional): Whether to auto-detect Splunk version "
            "from connected instance. Defaults to True.\n\n"
            "Returns embedded resource with detailed administration guide.\n\n"
            "💡 Tip: Use list_admin_topics() to discover all available topics."
        ),
        category="documentation",
        tags=["administration", "configuration", "guides", "embedded-resource"],
        requires_connection=False,
    )

    async def execute(
        self, ctx: Context, topic: str, version: str = "latest", auto_detect_version: bool = True
    ) -> dict[str, Any]:
        """Execute admin guide retrieval and return embedded resource."""
        log_tool_execution(
            self.name, topic=topic, version=version, auto_detect_version=auto_detect_version
        )

        try:
            # Auto-detect version if requested
            if auto_detect_version and version in ["auto", "latest"]:
                version = await self._detect_splunk_version(ctx)

            resource = AdminGuideResource(version, topic)
            content = await resource.get_content(ctx)

            uri = f"splunk-docs://{version}/admin/{topic}"

            return self.format_success_response(
                {
                    "content": [
                        {
                            "type": "resource",
                            "resource": {
                                "uri": uri,
                                "title": f"Admin Guide: {topic}",
                                "mimeType": "text/markdown",
                                "text": content,
                            },
                        }
                    ]
                }
            )

        except Exception as e:
            error_msg = f"Failed to retrieve admin guide for topic '{topic}': {str(e)}"
            self.logger.error(error_msg)
            return self.format_error_response(error_msg)

    async def _detect_splunk_version(self, ctx: Context) -> str:
        """Detect Splunk version from connected instance."""
        try:
            from src.tools.health.status import GetSplunkHealth

            health_tool = GetSplunkHealth("get_splunk_health", "Get Splunk health status")
            health_result = await health_tool.execute(ctx)

            if (
                health_result.get("status") == "success"
                and health_result.get("data", {}).get("status") == "connected"
            ):
                return health_result["data"].get("version", "latest")
        except Exception as e:
            logger.warning(f"Failed to detect Splunk version: {e}")

        return "latest"


class ListCIMDataModels(BaseTool):
    """
    List all available CIM data models with descriptions and use cases.

    This tool provides a comprehensive list of all 26 Splunk Common Information Model
    data models for data normalization and onboarding.
    """

    METADATA = ToolMetadata(
        name="list_cim_data_models",
        description=(
            "List all available Splunk Common Information Model (CIM) data models. "
            "Returns structured information about all 26 CIM data models including name, "
            "description, use cases, required tags, and deprecation status. Use this to "
            "discover what CIM models are available before calling get_cim_reference."
        ),
        category="documentation",
        tags=["cim", "data-model", "discovery", "embedded-resource"],
        requires_connection=False,
    )

    async def execute(self, ctx: Context) -> dict[str, Any]:
        """List all available CIM data models."""
        log_tool_execution(self.name)

        try:
            # Get CIM data models from the resource
            cim_models = SplunkCIMResource.CIM_DATA_MODELS

            # Categorize models
            security_models = []
            network_models = []
            app_system_models = []
            alert_mgmt_models = []
            infra_asset_models = []
            monitoring_models = []
            splunk_internal_models = []
            deprecated_models = []

            for model_key, model_info in cim_models.items():
                model_entry = {
                    "key": model_key,
                    "name": model_info["name"],
                    "description": model_info["description"],
                    "use_case": model_info["use_case"],
                    "tags": model_info["tags"],
                }

                if model_info.get("deprecated", False):
                    deprecated_models.append(model_entry)
                    continue

                # Categorize by tags and name
                tags = model_info["tags"]

                if any(
                    t in ["authentication", "malware", "ids", "ips", "dlp", "vulnerability"]
                    for t in tags
                ):
                    security_models.append(model_entry)
                elif any(t in ["network", "dns", "traffic", "session"] for t in tags):
                    network_models.append(model_entry)
                elif any(t in ["alert", "ticket", "update"] for t in tags):
                    alert_mgmt_models.append(model_entry)
                elif any(t in ["inventory", "certificate"] for t in tags):
                    infra_asset_models.append(model_entry)
                elif any(t in ["signature", "messaging"] for t in tags):
                    monitoring_models.append(model_entry)
                elif "audit" in tags:
                    splunk_internal_models.append(model_entry)
                else:
                    app_system_models.append(model_entry)

            content = f"""# Splunk Common Information Model (CIM) Data Models

{len(cim_models)} CIM data models available ({len(deprecated_models)} deprecated).

## Security Data Models ({len(security_models)} models)

"""

            for model in security_models:
                content += f"""### {model["name"]}
**Model Key**: `{model["key"]}`
**Required Tags**: {", ".join(f"`{tag}`" for tag in model["tags"])}
**Description**: {model["description"]}
**Use Case**: {model["use_case"]}
**Usage**: `get_cim_reference("{model["key"]}")`

"""

            content += f"""## Network Data Models ({len(network_models)} models)

"""

            for model in network_models:
                content += f"""### {model["name"]}
**Model Key**: `{model["key"]}`
**Required Tags**: {", ".join(f"`{tag}`" for tag in model["tags"])}
**Description**: {model["description"]}
**Use Case**: {model["use_case"]}
**Usage**: `get_cim_reference("{model["key"]}")`

"""

            content += f"""## Application & System Data Models ({len(app_system_models)} models)

"""

            for model in app_system_models:
                content += f"""### {model["name"]}
**Model Key**: `{model["key"]}`
**Required Tags**: {", ".join(f"`{tag}`" for tag in model["tags"])}
**Description**: {model["description"]}
**Use Case**: {model["use_case"]}
**Usage**: `get_cim_reference("{model["key"]}")`

"""

            content += f"""## Alerting & Management Data Models ({len(alert_mgmt_models)} models)

"""

            for model in alert_mgmt_models:
                content += f"""### {model["name"]}
**Model Key**: `{model["key"]}`
**Required Tags**: {", ".join(f"`{tag}`" for tag in model["tags"])}
**Description**: {model["description"]}
**Use Case**: {model["use_case"]}
**Usage**: `get_cim_reference("{model["key"]}")`

"""

            content += f"""## Infrastructure & Asset Data Models ({len(infra_asset_models)} models)

"""

            for model in infra_asset_models:
                content += f"""### {model["name"]}
**Model Key**: `{model["key"]}`
**Required Tags**: {", ".join(f"`{tag}`" for tag in model["tags"])}
**Description**: {model["description"]}
**Use Case**: {model["use_case"]}
**Usage**: `get_cim_reference("{model["key"]}")`

"""

            if monitoring_models:
                content += f"""## Monitoring & Detection Data Models ({len(monitoring_models)} models)

"""

                for model in monitoring_models:
                    content += f"""### {model["name"]}
**Model Key**: `{model["key"]}`
**Required Tags**: {", ".join(f"`{tag}`" for tag in model["tags"])}
**Description**: {model["description"]}
**Use Case**: {model["use_case"]}
**Usage**: `get_cim_reference("{model["key"]}")`

"""

            if splunk_internal_models:
                content += f"""## Splunk Internal Data Models ({len(splunk_internal_models)} models)

"""

                for model in splunk_internal_models:
                    content += f"""### {model["name"]}
**Model Key**: `{model["key"]}`
**Required Tags**: {", ".join(f"`{tag}`" for tag in model["tags"])}
**Description**: {model["description"]}
**Use Case**: {model["use_case"]}
**Usage**: `get_cim_reference("{model["key"]}")`

"""

            if deprecated_models:
                content += f"""## Deprecated Data Models ({len(deprecated_models)} models)

These models are deprecated in CIM 6.0+ and should not be used for new implementations:

"""

                for model in deprecated_models:
                    content += f"""### {model["name"]}
**Model Key**: `{model["key"]}`
**Status**: DEPRECATED
**Description**: {model["description"]}

"""

            content += """## How to Use

Call `get_cim_reference(model, version="latest")` with any of the model keys above.

Examples:
```python
# Get authentication CIM model
get_cim_reference("authentication")

# Get network-traffic model for specific version
get_cim_reference("network-traffic", version="6.1")

# Get malware detection model
get_cim_reference("malware")
```

## URI Patterns

You can also use the universal documentation tool:
```python
get_splunk_documentation("splunk-cim://authentication")
get_splunk_documentation("splunk-cim://6.1/network-traffic")
get_splunk_documentation("splunk-cim://discovery")
```
"""

            return self.format_success_response(
                {
                    "content": [
                        {
                            "type": "resource",
                            "resource": {
                                "uri": "splunk-cim://models-list",
                                "title": "CIM Data Models List",
                                "mimeType": "text/markdown",
                                "text": content,
                            },
                        }
                    ]
                }
            )

        except Exception as e:
            error_msg = f"Failed to list CIM data models: {str(e)}"
            self.logger.error(error_msg)
            return self.format_error_response(error_msg)


class GetCIMReference(BaseTool):
    """
    Get CIM data model documentation with field specs and configuration examples.

    Returns detailed documentation for specific Splunk CIM data models.
    """

    METADATA = ToolMetadata(
        name="get_cim_reference",
        description=(
            "Get detailed Splunk CIM data model documentation with field specifications "
            "and configuration examples. Returns comprehensive reference including field "
            "mappings, tagging requirements, and implementation guidance.\n\n"
            "Args:\n"
            "    model (str): CIM data model name. Use list_cim_data_models() to see all "
            "available models. Examples: 'authentication', 'network-traffic', 'malware'\n"
            "    version (str, optional): CIM version (default: 'latest'). Options: "
            "'6.1', '6.0', '5.3', '5.2', '5.1', 'latest'"
        ),
        category="documentation",
        tags=["cim", "data-model", "reference", "embedded-resource"],
        requires_connection=False,
    )

    async def execute(self, ctx: Context, model: str, version: str = "latest") -> dict[str, Any]:
        """Execute CIM reference retrieval and return embedded resource."""
        log_tool_execution(self.name, model=model, version=version)

        try:
            resource = CIMDataModelResource(version, model)
            content = await resource.get_content(ctx)

            uri = f"splunk-cim://{version}/{model}"

            return self.format_success_response(
                {
                    "content": [
                        {
                            "type": "resource",
                            "resource": {
                                "uri": uri,
                                "title": f"CIM Data Model: {model}",
                                "mimeType": "text/markdown",
                                "text": content,
                            },
                        }
                    ]
                }
            )

        except Exception as e:
            error_msg = f"Failed to retrieve CIM reference for model '{model}': {str(e)}"
            self.logger.error(error_msg)
            return self.format_error_response(error_msg)


class ListDashboardStudioTopics(BaseTool):
    """
    List all available Dashboard Studio documentation topics.

    This tool provides a comprehensive list of Dashboard Studio documentation
    topics including cheatsheet, schema, and configuration guides.
    """

    METADATA = ToolMetadata(
        name="list_dashboard_studio_topics",
        description=(
            "List all available Dashboard Studio documentation topics. Returns structured "
            "information about available topics including cheatsheet, definition schema, "
            "visualizations guide, and configuration options. Use this to discover what "
            "Dashboard Studio documentation is available."
        ),
        category="documentation",
        tags=["dashboard-studio", "topics", "discovery", "embedded-resource"],
        requires_connection=False,
    )

    async def execute(self, ctx: Context) -> dict[str, Any]:
        """List all available Dashboard Studio topics."""
        log_tool_execution(self.name)

        try:
            local_topics = []
            external_topics = []

            # Separate topics by type
            for topic_key, topic_data in DASHBOARD_STUDIO_TOPICS.items():
                topic_entry = {
                    "key": topic_key,
                    "name": topic_data.get("name", topic_key),
                    "description": topic_data.get("description", ""),
                    "tags": topic_data.get("tags", []),
                    "is_local": "file" in topic_data,
                    "url": topic_data.get("url", ""),
                }

                if topic_entry["is_local"]:
                    local_topics.append(topic_entry)
                else:
                    external_topics.append(topic_entry)

            content = f"""# Dashboard Studio Documentation Topics

{len(DASHBOARD_STUDIO_TOPICS)} documentation topics available ({len(local_topics)} local, {len(external_topics)} external).

## Local Documentation Resources

These resources provide embedded content that's always available offline:

"""

            for topic in local_topics:
                content += f"""### {topic["name"]}
**Topic Key**: `{topic["key"]}`
**Description**: {topic["description"]}
**Tags**: {", ".join(f"`{tag}`" for tag in topic["tags"])}
**Type**: Local file (embedded content)
**Usage**: `get_studio_topic("{topic["key"]}")`

"""

            content += """## External Documentation Resources

These resources provide links and summaries of official Splunk documentation:

"""

            for topic in external_topics:
                content += f"""### {topic["name"]}
**Topic Key**: `{topic["key"]}`
**Description**: {topic["description"]}
**Tags**: {", ".join(f"`{tag}`" for tag in topic["tags"])}
**Type**: External documentation
**URL**: {topic["url"]}
**Usage**: `get_studio_topic("{topic["key"]}")`

"""

            content += """## How to Use

Call `get_studio_topic(topic)` with any of the topic keys above.

Examples:
```python
# Get comprehensive Dashboard Studio cheatsheet
get_studio_topic("cheatsheet")

# Get dashboard definition structure guide
get_studio_topic("definition")

# Get visualizations configuration guide
get_studio_topic("visualizations")
```

## URI Patterns

You can also use the universal documentation tool:
```python
get_splunk_documentation("dashboard-studio://cheatsheet")
get_splunk_documentation("dashboard-studio://definition")
get_splunk_documentation("dashboard-studio://discovery")
```

## Quick Start

**Most useful resource**: `get_studio_topic("cheatsheet")`

The cheatsheet provides a comprehensive, local reference with examples, schema, and best practices for creating Dashboard Studio dashboards via the `create_dashboard` tool.
"""

            return self.format_success_response(
                {
                    "content": [
                        {
                            "type": "resource",
                            "resource": {
                                "uri": "dashboard-studio://topics-list",
                                "title": "Dashboard Studio Topics List",
                                "mimeType": "text/markdown",
                                "text": content,
                            },
                        }
                    ]
                }
            )

        except Exception as e:
            error_msg = f"Failed to list Dashboard Studio topics: {str(e)}"
            self.logger.error(error_msg)
            return self.format_error_response(error_msg)


class GetStudioTopic(BaseTool):
    """
    Get Dashboard Studio documentation for specific topics.

    Returns detailed Dashboard Studio documentation with examples and best practices.
    """

    METADATA = ToolMetadata(
        name="get_studio_topic",
        description=(
            "Get Dashboard Studio documentation for a specific topic. Returns comprehensive "
            "documentation with examples, schema details, and best practices.\n\n"
            "Args:\n"
            "    topic (str): Documentation topic. Use list_dashboard_studio_topics() to see "
            "available topics. Examples: 'cheatsheet', 'definition', 'visualizations', "
            "'configuration', 'datasources', 'framework'"
        ),
        category="documentation",
        tags=["dashboard-studio", "documentation", "embedded-resource"],
        requires_connection=False,
    )

    async def execute(self, ctx: Context, topic: str) -> dict[str, Any]:
        """Execute Dashboard Studio topic retrieval and return embedded resource."""
        log_tool_execution(self.name, topic=topic)

        try:
            resource = DashboardStudioDocsResource(topic)
            content = await resource.get_content(ctx)

            uri = f"dashboard-studio://{topic}"

            return self.format_success_response(
                {
                    "content": [
                        {
                            "type": "resource",
                            "resource": {
                                "uri": uri,
                                "title": f"Dashboard Studio: {topic}",
                                "mimeType": "text/markdown",
                                "text": content,
                            },
                        }
                    ]
                }
            )

        except Exception as e:
            error_msg = f"Failed to retrieve Dashboard Studio topic '{topic}': {str(e)}"
            self.logger.error(error_msg)
            return self.format_error_response(error_msg)


class ListConfigFiles(BaseTool):
    """
    List common Splunk configuration files with descriptions.

    This tool provides a comprehensive list of common Splunk .conf files
    for configuration and administration.
    """

    METADATA = ToolMetadata(
        name="list_config_files",
        description=(
            "List common Splunk configuration files (.conf) with descriptions. Returns "
            "structured information about configuration files that can be used with "
            "get_config_spec() to retrieve detailed specification documentation."
        ),
        category="documentation",
        tags=["config", "spec", "discovery", "embedded-resource"],
        requires_connection=False,
    )

    async def execute(self, ctx: Context) -> dict[str, Any]:
        """List all common Splunk configuration files."""
        log_tool_execution(self.name)

        try:
            content = f"""# Splunk Configuration Files

{len(COMMON_CONFIG_FILES)} common Splunk configuration files available.

## Configuration Files Reference

| Configuration File | Description |
|--------------------|-------------|
"""

            for config_file, description in sorted(COMMON_CONFIG_FILES.items()):
                content += f"| `{config_file}` | {description} |\n"

            content += """

## How to Use

Call `get_config_spec(config)` with any of the configuration file names above (with or without .conf extension).

Examples:
```python
# Get props.conf specification
get_config_spec("props.conf")

# Get indexes.conf specification (extension optional)
get_config_spec("indexes")

# Get transforms.conf specification
get_config_spec("transforms.conf")
```

## URI Patterns

You can also use the universal documentation tool:
```python
get_splunk_documentation("splunk-spec://props.conf")
get_splunk_documentation("splunk-spec://indexes.conf")
get_splunk_documentation("splunk-spec://transforms.conf")
```

## Categories

### Data Input & Processing
- `inputs.conf` - Data input definitions
- `props.conf` - Field extraction and sourcetype configs
- `transforms.conf` - Field transformations and lookups

### Index Management
- `indexes.conf` - Index definitions and retention
- `outputs.conf` - Forwarding configurations

### Search & Knowledge
- `savedsearches.conf` - Saved searches and alerts
- `macros.conf` - Search macro definitions
- `eventtypes.conf` - Event type definitions
- `tags.conf` - Event tag definitions

### Security & Access
- `authentication.conf` - Authentication settings
- `authorize.conf` - Role-based access control

### System Configuration
- `server.conf` - Server-level settings
- `limits.conf` - Resource limits and constraints
- `web.conf` - Web interface settings

### Application Configuration
- `app.conf` - Application metadata
- `alert_actions.conf` - Alert action definitions
- `commands.conf` - Custom search commands

## Note

This list includes the most common configuration files. The `get_config_spec()` tool supports many more configuration files beyond those listed here. If you need documentation for a specific configuration file not listed, try calling `get_config_spec()` with the file name anyway - it may still be available.
"""

            return self.format_success_response(
                {
                    "content": [
                        {
                            "type": "resource",
                            "resource": {
                                "uri": "splunk-spec://config-files-list",
                                "title": "Splunk Configuration Files List",
                                "mimeType": "text/markdown",
                                "text": content,
                            },
                        }
                    ]
                }
            )

        except Exception as e:
            error_msg = f"Failed to list configuration files: {str(e)}"
            self.logger.error(error_msg)
            return self.format_error_response(error_msg)


class GetConfigSpec(BaseTool):
    """
    Get Splunk configuration file specification documentation.

    Returns detailed specification documentation for Splunk configuration files.
    """

    METADATA = ToolMetadata(
        name="get_config_spec",
        description=(
            "Get detailed Splunk configuration file specification documentation. Returns "
            "comprehensive reference with all configuration options, syntax, and examples.\n\n"
            "Args:\n"
            "    config (str): Configuration file name (with or without .conf extension). "
            "Use list_config_files() to see common files. Examples: 'props.conf', "
            "'transforms', 'indexes.conf'"
        ),
        category="documentation",
        tags=["config", "spec", "reference", "embedded-resource"],
        requires_connection=False,
    )

    async def execute(self, ctx: Context, config: str) -> dict[str, Any]:
        """Execute config spec retrieval and return embedded resource."""
        log_tool_execution(self.name, config=config)

        try:
            resource = SplunkSpecReferenceResource(config)
            content = await resource.get_content(ctx)

            uri = f"splunk-spec://{config}"

            return self.format_success_response(
                {
                    "content": [
                        {
                            "type": "resource",
                            "resource": {
                                "uri": uri,
                                "title": f"Config Spec: {config}",
                                "mimeType": "text/markdown",
                                "text": content,
                            },
                        }
                    ]
                }
            )

        except Exception as e:
            error_msg = f"Failed to retrieve config spec for '{config}': {str(e)}"
            self.logger.error(error_msg)
            return self.format_error_response(error_msg)
