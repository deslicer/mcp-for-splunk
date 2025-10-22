"""
Dashboard Studio documentation resources for MCP server.

Provides curated Dashboard Studio (9.4) documentation for LLM-assisted dashboard authoring.
"""

import logging
from pathlib import Path

import httpx
from bs4 import BeautifulSoup
from fastmcp import Context

from src.core.base import BaseResource, ResourceMetadata
from src.core.registry import resource_registry

logger = logging.getLogger(__name__)


# Dashboard Studio documentation topics mapping
DASHBOARD_STUDIO_TOPICS = {
    "cheatsheet": {
        "name": "Dashboard Studio Cheatsheet",
        "description": "Comprehensive cheatsheet with definition schema, examples, and best practices",
        "file": "dashboard_studio_cheatsheet.md",
        "tags": ["cheatsheet", "reference", "quick-reference"],
    },
    "definition": {
        "name": "Dashboard Definition Structure",
        "description": "Complete dashboard definition schema and required fields",
        "url": "https://help.splunk.com/en/splunk-enterprise/create-dashboards-and-reports/dashboard-studio/9.4/source-code-editor/what-is-a-dashboard-definition",
        "tags": ["definition", "schema", "structure"],
    },
    "visualizations": {
        "name": "Visualizations Guide",
        "description": "Adding and formatting visualizations in Dashboard Studio",
        "url": "https://help.splunk.com/en/splunk-enterprise/create-dashboards-and-reports/dashboard-studio/9.4/visualizations/add-and-format-visualizations",
        "tags": ["visualizations", "formatting", "configuration"],
    },
    "configuration": {
        "name": "Visualization Configuration Options",
        "description": "Complete reference of visualization configuration options",
        "url": "https://help.splunk.com/en/splunk-enterprise/create-dashboards-and-reports/dashboard-studio/9.4/configuration-options-reference/visualization-configuration-options",
        "tags": ["configuration", "options", "reference"],
    },
    "datasources": {
        "name": "Data Sources Guide",
        "description": "Using ds.search, ds.savedSearch, and ds.chain data sources",
        "url": "https://help.splunk.com/en/splunk-enterprise/create-dashboards-and-reports/dashboard-studio/9.0/use-data-sources/create-search-based-visualizations-with-ds.search",
        "tags": ["datasources", "search", "data"],
    },
    "framework": {
        "name": "Dashboard Framework Introduction",
        "description": "Introduction to Dashboard Framework concepts and architecture",
        "url": "https://splunkui.splunk.com/Packages/dashboard-docs/Introduction",
        "tags": ["framework", "introduction", "concepts"],
    },
}


class DashboardStudioDocsResource(BaseResource):
    """Base class for Dashboard Studio documentation resources with dynamic topic support."""

    METADATA = ResourceMetadata(
        uri="dashboard-studio://{topic}",
        name="dashboard_studio_docs",
        description="Dashboard Studio documentation (9.4) with multiple topics",
        mime_type="text/markdown",
        category="reference",
        tags=["dashboard-studio", "dashboards", "visualization", "reference"],
    )

    def __init__(self, topic: str):
        self.topic = topic
        topic_info = DASHBOARD_STUDIO_TOPICS.get(topic, {})

        uri = f"dashboard-studio://{topic}"
        name = topic_info.get("name", f"Dashboard Studio - {topic}")
        description = topic_info.get("description", f"Dashboard Studio documentation for {topic}")

        super().__init__(uri, name, description, "text/markdown")

    async def get_content(self, ctx: Context) -> str:
        """Get Dashboard Studio documentation content for the specified topic."""
        topic_info = DASHBOARD_STUDIO_TOPICS.get(self.topic)

        if not topic_info:
            return self._get_topic_index()

        # Check if this is a file-based resource (like cheatsheet)
        if "file" in topic_info:
            return await self._load_file_content(topic_info["file"])

        # Otherwise, fetch content from external URL
        return await self._fetch_external_content(topic_info)

    async def _load_file_content(self, filename: str) -> str:
        """Load content from a file in docs/reference."""
        try:
            file_path = Path(__file__).parent.parent.parent / "docs" / "reference" / filename

            if not file_path.exists():
                return f"""# Dashboard Studio Documentation Not Found

The documentation file was not found at: {file_path}

Please ensure the file exists in the docs/reference directory.
"""

            content = file_path.read_text(encoding="utf-8")
            return content

        except Exception as e:  # pylint: disable=broad-except
            logger.error("Error loading Dashboard Studio documentation file %s: %s", filename, e)
            return f"""# Error Loading Documentation

Failed to load Dashboard Studio documentation: {str(e)}

Please check the file path and permissions.
"""

    async def _fetch_external_content(self, topic_info: dict) -> str:
        """Fetch and format external documentation content."""
        url = topic_info.get("url", "")
        name = topic_info.get("name", self.topic)
        description = topic_info.get("description", "")
        tags = ", ".join(topic_info.get("tags", []))

        try:
            # Use browser-like headers to avoid detection as a bot
            headers = {
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.5",
                "Accept-Encoding": "gzip, deflate, br",
                "DNT": "1",
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1",
            }

            # Fetch the content from the URL
            async with httpx.AsyncClient(
                timeout=30.0, follow_redirects=True, headers=headers
            ) as client:
                response = await client.get(url)
                response.raise_for_status()

                # Parse HTML content
                soup = BeautifulSoup(response.text, "html.parser")

                # Extract main content area (common patterns for Splunk docs)
                main_content = None
                for selector in [
                    "main",
                    "article",
                    ".content",
                    "#content",
                    ".main-content",
                    "[role='main']",
                ]:
                    main_content = soup.select_one(selector)
                    if main_content:
                        break

                if not main_content:
                    # Fallback to body if no main content found
                    main_content = soup.find("body")

                if main_content:
                    # Remove unwanted elements
                    for tag in main_content.select(
                        "script, style, nav, header, footer, .navigation, .sidebar"
                    ):
                        tag.decompose()

                    # Extract text with basic formatting
                    content_text = main_content.get_text(separator="\n", strip=True)

                    # Clean up excessive whitespace
                    lines = [line.strip() for line in content_text.split("\n") if line.strip()]
                    formatted_content = "\n\n".join(lines)
                else:
                    formatted_content = "Content extraction failed - no main content found."

                return f"""# {name}

**Topic**: `{self.topic}`
**Description**: {description}
**Tags**: {tags}
**Source**: {url}

---

## Documentation Content

{formatted_content}

---

## Related Topics

{self._get_related_topics()}

---

**Note**: This content was fetched from Splunk's official documentation. For a comprehensive local reference, see: `dashboard-studio://cheatsheet`
"""

        except httpx.HTTPError as e:
            logger.error("Failed to fetch Dashboard Studio docs from %s: %s", url, e)
            return f"""# {name}

**Topic**: `{self.topic}`
**Description**: {description}
**Tags**: {tags}

## Error Fetching Documentation

Failed to retrieve documentation from: {url}

**Error**: {str(e)}

Please check:
- Network connectivity
- URL availability
- Firewall settings

For offline reference, use: `dashboard-studio://cheatsheet`

## Related Topics

{self._get_related_topics()}

---

**Official URL**: {url}
"""
        except Exception as e:  # pylint: disable=broad-except
            logger.error("Error processing Dashboard Studio docs for %s: %s", self.topic, e)
            return f"""# {name}

**Topic**: `{self.topic}`
**Description**: {description}

## Error Processing Documentation

An error occurred while processing the documentation.

**Error**: {str(e)}

For offline reference, use: `dashboard-studio://cheatsheet`

## Related Topics

{self._get_related_topics()}

---

**Official URL**: {url}
"""

    def _get_related_topics(self) -> str:
        """Get formatted list of related topics."""
        topics = []
        for topic_key, topic_data in DASHBOARD_STUDIO_TOPICS.items():
            if topic_key != self.topic:
                topics.append(f"- **{topic_data['name']}**: `dashboard-studio://{topic_key}`")

        return "\n".join(topics) if topics else "No related topics available."

    def _get_topic_index(self) -> str:
        """Get index of all available Dashboard Studio topics."""
        return f"""# Dashboard Studio Documentation Index

Available documentation topics for Splunk Dashboard Studio (version 9.4).

## Unknown Topic: {self.topic}

The requested topic `{self.topic}` is not available. Please choose from the available topics below.

## Available Topics

{self._format_all_topics()}

## Usage

Access any topic using the URI pattern: `dashboard-studio://{{topic}}`

**Example**: `dashboard-studio://cheatsheet`

---

**Tip**: Start with the cheatsheet for a comprehensive overview!
"""

    def _format_all_topics(self) -> str:
        """Format all available topics for display."""
        topics = []
        for topic_key, topic_data in DASHBOARD_STUDIO_TOPICS.items():
            name = topic_data.get("name", topic_key)
            description = topic_data.get("description", "")
            source = "local file" if "file" in topic_data else "external link"

            topics.append(f"""### {name}
**URI**: `dashboard-studio://{topic_key}`
**Description**: {description}
**Source**: {source}
""")

        return "\n".join(topics)


class DashboardStudioDiscoveryResource(BaseResource):
    """Dashboard Studio documentation discovery resource - comprehensive index of all topics and resources."""

    METADATA = ResourceMetadata(
        uri="dashboard-studio://discovery",
        name="dashboard_studio_discovery",
        description="Discovery index of all Dashboard Studio documentation topics and resource templates",
        mime_type="text/markdown",
        category="discovery",
        tags=["dashboard-studio", "dashboards", "documentation", "index", "discovery"],
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
        """Get comprehensive discovery index of all Dashboard Studio documentation topics and resources."""
        local_topics = []
        external_topics = []

        # Separate topics by type
        for topic_key, topic_data in DASHBOARD_STUDIO_TOPICS.items():
            name = topic_data.get("name", topic_key)
            description = topic_data.get("description", "")
            uri = f"`dashboard-studio://{topic_key}`"

            entry = f"""### {name}
**URI**: {uri}
**Description**: {description}
"""

            if "file" in topic_data:
                entry += "**Type**: Local file (embedded content)\n"
                local_topics.append(entry)
            else:
                url = topic_data.get("url", "")
                entry += f"**Type**: External documentation\n**URL**: {url}\n"
                external_topics.append(entry)

        return f"""# Dashboard Studio Documentation - Discovery Index

This discovery resource provides comprehensive access to all Dashboard Studio documentation topics, resource templates, and reference materials through the MCP resource system.

## 🚀 Quick Start

**Most useful resource**: `dashboard-studio://cheatsheet`

The cheatsheet provides a comprehensive, local reference with examples, schema, and best practices for creating Dashboard Studio dashboards via the `create_dashboard` tool.

---

## 📋 Resource Template Pattern

All Dashboard Studio documentation is accessible through the resource template pattern:

**Pattern**: `dashboard-studio://{{topic}}`

**Available Topics**: {len(DASHBOARD_STUDIO_TOPICS)} topics ({len([t for t in DASHBOARD_STUDIO_TOPICS.values() if "file" in t])} local, {len([t for t in DASHBOARD_STUDIO_TOPICS.values() if "url" in t])} external)

---

## 📚 Local Documentation Resources

These resources provide embedded content that's always available offline:

{chr(10).join(local_topics)}

---

## 🔗 External Documentation Resources

These resources provide links and summaries of official Splunk documentation:

{chr(10).join(external_topics)}

---

## 🎯 Common Use Cases

### 1. Building a New Dashboard
**Step-by-step workflow:**
1. **Get reference**: `dashboard-studio://cheatsheet` - Structure and examples
2. **Review schema**: `dashboard-studio://definition` - Definition schema details
3. **Configure viz**: `dashboard-studio://configuration` - Visualization options
4. **Build definition**: Create your JSON dashboard definition
5. **Create dashboard**: Call `create_dashboard` tool with your definition

### 2. Working with Data Sources
**Data source workflow:**
1. **Primary guide**: `dashboard-studio://datasources` - ds.search, ds.savedSearch, ds.chain
2. **Quick reference**: `dashboard-studio://cheatsheet` - Data Sources section
3. **Best practices**: Prefer saved searches for reliability and performance

### 3. Understanding the Framework
**Learning path:**
1. **Concepts**: `dashboard-studio://framework` - Framework introduction
2. **Practical guide**: `dashboard-studio://cheatsheet` - Hands-on examples
3. **Deep dive**: Use specific topic resources as needed

---

## 📖 Resource Template Routes

Access any topic using the URI pattern: `dashboard-studio://{{topic}}`

**Complete Topic List**:
{self._format_topic_list()}

**Invalid topics**: Requesting an unknown topic (e.g., `dashboard-studio://unknown`) returns this discovery index with available options.

---

## 🔧 Integration with create_dashboard Tool

These resources are designed to work seamlessly with the `create_dashboard` tool for programmatic dashboard creation:

### Workflow Example

```python
# Step 1: Get reference documentation
cheatsheet = await client.read_resource("dashboard-studio://cheatsheet")

# Step 2: Review datasources guide
datasources = await client.read_resource("dashboard-studio://datasources")

# Step 3: Build your dashboard definition
definition = {{
    "version": "1.0",
    "title": "System Performance Dashboard",
    "dataSources": {{
        "ds_cpu": {{
            "type": "ds.search",
            "options": {{
                "query": "index=_internal | stats avg(cpu_pct) as avg_cpu by host",
                "queryParameters": {{"earliest": "-24h", "latest": "now"}}
            }}
        }}
    }},
    "visualizations": {{
        "viz_cpu": {{
            "type": "viz.line",
            "dataSources": {{"primary": "ds_cpu"}},
            "title": "CPU Usage by Host"
        }}
    }},
    "layout": {{
        "type": "absolute",
        "options": {{}},
        "structure": [
            {{"item": "viz_cpu", "position": {{"x": 0, "y": 0, "w": 1200, "h": 400}}}}
        ]
    }}
}}

# Step 4: Create the dashboard in Splunk
result = await client.call_tool("create_dashboard", {{
    "name": "system_performance",
    "definition": definition,
    "dashboard_type": "studio",
    "app": "search",
    "sharing": "app"
}})
```

---

## 🎓 Best Practices

### For Dashboard Authors
- **Start with discovery**: Use this resource to understand all available topics
- **Use the cheatsheet**: Most comprehensive offline reference
- **Validate structure**: Ensure JSON is valid before calling `create_dashboard`
- **Test incrementally**: Build simple dashboards first, then add complexity

### For Developers
- **Resource pattern**: Always use `dashboard-studio://{{topic}}` format
- **Error handling**: Invalid topics return this discovery index
- **Caching**: Local resources (cheatsheet) are always available
- **External docs**: External link resources provide up-to-date official documentation

---

## 📊 Resource Statistics

- **Total Topics**: {len(DASHBOARD_STUDIO_TOPICS)}
- **Local Resources**: {len([t for t in DASHBOARD_STUDIO_TOPICS.values() if "file" in t])}
- **External Links**: {len([t for t in DASHBOARD_STUDIO_TOPICS.values() if "url" in t])}
- **Resource Template**: `dashboard-studio://{{topic}}`
- **Discovery URI**: `dashboard-studio://discovery` (this resource)

---

## 🔍 Discovery URI

**This Resource**: `dashboard-studio://discovery`

Use this URI whenever you need to:
- Discover available Dashboard Studio documentation topics
- Understand the resource template pattern
- Find the right resource for your use case
- Get integration examples with `create_dashboard`

---

**Version**: Splunk Enterprise 9.4
**Framework**: Dashboard Studio (JSON-based)
**REST Endpoint**: `/servicesNS/{{owner}}/{{app}}/data/ui/views`
**Tool Integration**: `create_dashboard` with `dashboard_type="studio"`
"""

    def _format_topic_list(self) -> str:
        """Format a simple bulleted list of all topics."""
        topics = []
        for topic_key, topic_data in DASHBOARD_STUDIO_TOPICS.items():
            name = topic_data.get("name", topic_key)
            topics.append(f"- `{topic_key}` - {name}")

        return "\n".join(topics)


# Factory function for creating Dashboard Studio resources
def create_dashboard_studio_resource(topic: str) -> DashboardStudioDocsResource:
    """Create a Dashboard Studio documentation resource for the specified topic.

    Args:
        topic: Topic name (e.g., 'cheatsheet', 'definition', 'visualizations')

    Returns:
        DashboardStudioDocsResource instance
    """
    return DashboardStudioDocsResource(topic)


# Registry and factory functions
def register_dashboard_studio_resources():
    """Register Dashboard Studio documentation resources with the resource registry."""
    try:
        # Register the dynamic resource class with template URI
        resource_registry.register(
            DashboardStudioDocsResource, DashboardStudioDocsResource.METADATA
        )

        # Register the static discovery resource
        resource_registry.register(
            DashboardStudioDiscoveryResource, DashboardStudioDiscoveryResource.METADATA
        )

        logger.info(
            "Successfully registered Dashboard Studio documentation resources "
            "(1 dynamic template with %d topics, 1 static discovery)",
            len(DASHBOARD_STUDIO_TOPICS),
        )

    except Exception as e:  # pylint: disable=broad-except
        logger.error("Failed to register Dashboard Studio resources: %s", e)


# Auto-register resources when module is imported
register_dashboard_studio_resources()
