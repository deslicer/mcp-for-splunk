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
from src.resources.splunk_docs import (
    AdminGuideResource,
    DocumentationDiscoveryResource,
    SPLCommandResource,
    SplunkCheatSheetResource,
    TroubleshootingResource,
)

logger = logging.getLogger(__name__)


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
                troubleshooting_topics.append({
                    "topic": topic_key,
                    "title": topic_info["title"],
                    "description": topic_info["description"],
                    "example_uri": f"splunk-docs://latest/troubleshooting/{topic_key}"
                })

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
                    "example": "splunk-docs://cheat-sheet"
                },
                {
                    "pattern": "splunk-docs://discovery",
                    "description": "Documentation discovery guide",
                    "example": "splunk-docs://discovery"
                },
                {
                    "pattern": "splunk-docs://{version}/spl-reference/{command}",
                    "description": "SPL command reference documentation",
                    "example": "splunk-docs://latest/spl-reference/stats"
                },
                {
                    "pattern": "splunk-docs://{version}/troubleshooting/{topic}",
                    "description": "Troubleshooting guides for specific topics",
                    "example": "splunk-docs://9.4/troubleshooting/metrics-log"
                },
                {
                    "pattern": "splunk-docs://{version}/admin/{topic}",
                    "description": "Administration guides for specific topics",
                    "example": "splunk-docs://latest/admin/indexes"
                }
            ]

            # Version information
            version_info = {
                "supported_versions": ["9.4", "9.3", "9.2", "9.1", "9.0", "8.2", "latest"],
                "default_version": "latest",
                "auto_detection": "Available when connected to Splunk instance"
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

**Supported Versions:** {', '.join(version_info['supported_versions'])}
**Default Version:** {version_info['default_version']}
**Auto-Detection:** {version_info['auto_detection']}

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

            return self.format_success_response({
                "content": [
                    {
                        "type": "resource",
                        "resource": {
                            "uri": "splunk-docs://available-topics",
                            "title": "Available Documentation Topics",
                            "mimeType": "text/markdown",
                            "text": content
                        }
                    }
                ]
            })

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
                topics.append({
                    "topic": topic_key,
                    "title": topic_info["title"],
                    "description": topic_info["description"]
                })

            content = f"""# Available Troubleshooting Topics

{len(topics)} troubleshooting topics available:

"""

            for topic in topics:
                content += f"""## {topic['title']}
**Topic Key:** `{topic['topic']}`
**Description:** {topic['description']}
**Usage:** `get_troubleshooting_guide("{topic['topic']}")`

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

            return self.format_success_response({
                "content": [
                    {
                        "type": "resource",
                        "resource": {
                            "uri": "splunk-docs://troubleshooting-topics",
                            "title": "Available Troubleshooting Topics",
                            "mimeType": "text/markdown",
                            "text": content
                        }
                    }
                ]
            })

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
                content += f"""## {topic['topic'].replace('-', ' ').title()}
**Topic Key:** `{topic['topic']}`
**Description:** {topic['description']}
**Usage:** `get_admin_guide("{topic['topic']}")`

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

            return self.format_success_response({
                "content": [
                    {
                        "type": "resource",
                        "resource": {
                            "uri": "splunk-docs://admin-topics",
                            "title": "Available Admin Guide Topics",
                            "mimeType": "text/markdown",
                            "text": content
                        }
                    }
                ]
            })

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
                content += f"""## {cmd['command']}
**Description:** {cmd['description']}
**Usage:** `get_spl_reference("{cmd['command']}")`

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

            return self.format_success_response({
                "content": [
                    {
                        "type": "resource",
                        "resource": {
                            "uri": "splunk-docs://spl-commands",
                            "title": "Common SPL Commands",
                            "mimeType": "text/markdown",
                            "text": content
                        }
                    }
                ]
            })

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
            "    auto_detect_version (bool, optional): Whether to auto-detect Splunk version "
            "for dynamic resources. Defaults to True.\n\n"
            "Returns embedded resource with actual documentation content in markdown format.\n\n"
            "💡 Tip: Use list_available_topics() to discover all available URI patterns and topics."
        ),
        category="documentation",
        tags=["documentation", "embedded-resource", "splunk", "agentic"],
        requires_connection=False,
    )

    async def execute(self, ctx: Context, doc_uri: str, auto_detect_version: bool = True) -> dict[str, Any]:
        """Execute documentation retrieval and return embedded resource."""
        log_tool_execution(self.name, doc_uri=doc_uri, auto_detect_version=auto_detect_version)

        try:
            # Parse the URI to determine resource type
            content = await self._get_documentation_content(ctx, doc_uri, auto_detect_version)

            # Return as embedded resource according to MCP specification
            return self.format_success_response({
                "content": [
                    {
                        "type": "resource",
                        "resource": {
                            "uri": doc_uri,
                            "title": self._get_doc_title(doc_uri),
                            "mimeType": "text/markdown",
                            "text": content
                        }
                    }
                ]
            })

        except Exception as e:
            error_msg = f"Failed to retrieve documentation for URI '{doc_uri}': {str(e)}"
            self.logger.error(error_msg)
            return self.format_error_response(error_msg)

    async def _get_documentation_content(self, ctx: Context, doc_uri: str, auto_detect_version: bool) -> str:
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

        raise ValueError(f"Unsupported documentation URI: {doc_uri}")

    async def _detect_splunk_version(self, ctx: Context) -> str:
        """Detect Splunk version from connected instance."""
        try:
            from src.tools.health.status import GetSplunkHealth

            health_tool = GetSplunkHealth("get_splunk_health", "Get Splunk health status")
            health_result = await health_tool.execute(ctx)

            if health_result.get("status") == "success" and health_result.get("data", {}).get("status") == "connected":
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

            return self.format_success_response({
                "content": [
                    {
                        "type": "resource",
                        "resource": {
                            "uri": "splunk-docs://cheat-sheet",
                            "title": "Splunk SPL Cheat Sheet",
                            "mimeType": "text/markdown",
                            "text": content
                        }
                    }
                ]
            })

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

            return self.format_success_response({
                "content": [
                    {
                        "type": "resource",
                        "resource": {
                            "uri": "splunk-docs://discovery",
                            "title": "Splunk Documentation Discovery",
                            "mimeType": "text/markdown",
                            "text": content
                        }
                    }
                ]
            })

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
        self,
        ctx: Context,
        command: str,
        version: str = "latest",
        auto_detect_version: bool = True
    ) -> dict[str, Any]:
        """Execute SPL reference retrieval and return embedded resource."""
        log_tool_execution(self.name, command=command, version=version, auto_detect_version=auto_detect_version)

        try:
            # Auto-detect version if requested
            if auto_detect_version and version in ["auto", "latest"]:
                version = await self._detect_splunk_version(ctx)

            resource = SPLCommandResource(version, command)
            content = await resource.get_content(ctx)

            uri = f"splunk-docs://{version}/spl-reference/{command}"

            return self.format_success_response({
                "content": [
                    {
                        "type": "resource",
                        "resource": {
                            "uri": uri,
                            "title": f"SPL Reference: {command}",
                            "mimeType": "text/markdown",
                            "text": content
                        }
                    }
                ]
            })

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

            if health_result.get("status") == "success" and health_result.get("data", {}).get("status") == "connected":
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
        self,
        ctx: Context,
        topic: str,
        version: str = "latest",
        auto_detect_version: bool = True
    ) -> dict[str, Any]:
        """Execute troubleshooting guide retrieval and return embedded resource."""
        log_tool_execution(self.name, topic=topic, version=version, auto_detect_version=auto_detect_version)

        try:
            # Auto-detect version if requested
            if auto_detect_version and version in ["auto", "latest"]:
                version = await self._detect_splunk_version(ctx)

            resource = TroubleshootingResource(version, topic)
            content = await resource.get_content(ctx)

            uri = f"splunk-docs://{version}/troubleshooting/{topic}"

            return self.format_success_response({
                "content": [
                    {
                        "type": "resource",
                        "resource": {
                            "uri": uri,
                            "title": f"Troubleshooting: {topic}",
                            "mimeType": "text/markdown",
                            "text": content
                        }
                    }
                ]
            })

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

            if health_result.get("status") == "success" and health_result.get("data", {}).get("status") == "connected":
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
        self,
        ctx: Context,
        topic: str,
        version: str = "latest",
        auto_detect_version: bool = True
    ) -> dict[str, Any]:
        """Execute admin guide retrieval and return embedded resource."""
        log_tool_execution(self.name, topic=topic, version=version, auto_detect_version=auto_detect_version)

        try:
            # Auto-detect version if requested
            if auto_detect_version and version in ["auto", "latest"]:
                version = await self._detect_splunk_version(ctx)

            resource = AdminGuideResource(version, topic)
            content = await resource.get_content(ctx)

            uri = f"splunk-docs://{version}/admin/{topic}"

            return self.format_success_response({
                "content": [
                    {
                        "type": "resource",
                        "resource": {
                            "uri": uri,
                            "title": f"Admin Guide: {topic}",
                            "mimeType": "text/markdown",
                            "text": content
                        }
                    }
                ]
            })

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

            if health_result.get("status") == "success" and health_result.get("data", {}).get("status") == "connected":
                return health_result["data"].get("version", "latest")
        except Exception as e:
            logger.warning(f"Failed to detect Splunk version: {e}")

        return "latest"
