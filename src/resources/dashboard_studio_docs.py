"""Dashboard Studio documentation resources. Live Help URLs default to 10.2."""

import logging

from bs4 import BeautifulSoup
from fastmcp import Context

from src.core.base import BaseResource, ResourceMetadata
from src.core.registry import resource_registry
from src.resources.dashboard_studio_content import (
    CHEATSHEET_SOURCE_PATH,
    DashboardStudioContentError,
    load_cheatsheet_markdown,
)
from src.resources.docs_http import fetch_first_ok
from src.resources.docs_versions import DEFAULT_STUDIO_VERSION, parse_requested_version
from src.resources.studio_topics import (
    DASHBOARD_STUDIO_TOPICS,
    build_studio_urls,
    parse_studio_ref,
)

logger = logging.getLogger(__name__)


class DashboardStudioDocsResource(BaseResource):
    """Base class for Dashboard Studio documentation resources with dynamic topic support."""

    METADATA = ResourceMetadata(
        uri="dashboard-studio://{topic}",
        name="dashboard_studio_docs",
        description="Dashboard Studio documentation (default 10.2) with multiple topics",
        mime_type="text/markdown",
        category="reference",
        tags=["dashboard-studio", "dashboards", "visualization", "reference"],
    )

    def __init__(self, topic: str, version: str | None = None):
        self.topic = topic
        self.version = parse_requested_version(version or DEFAULT_STUDIO_VERSION)
        topic_info = DASHBOARD_STUDIO_TOPICS.get(topic, {})

        uri = (
            f"dashboard-studio://{topic}"
            if self.version == DEFAULT_STUDIO_VERSION
            else f"dashboard-studio://{self.version}/{topic}"
        )
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
        """Load bundled or repo-local Dashboard Studio reference content."""
        if filename != "dashboard_studio_cheatsheet.md":
            raise DashboardStudioContentError(
                f"Unknown local Dashboard Studio document '{filename}'. "
                f"Edit cheatsheet content in {CHEATSHEET_SOURCE_PATH}."
            )

        try:
            return load_cheatsheet_markdown()
        except DashboardStudioContentError:
            raise
        except Exception as e:  # pylint: disable=broad-except
            logger.error("Error loading Dashboard Studio documentation file %s: %s", filename, e)
            raise DashboardStudioContentError(
                f"Failed to load Dashboard Studio cheatsheet from {CHEATSHEET_SOURCE_PATH}: {e}"
            ) from e

    async def _fetch_external_content(self, topic_info: dict) -> str:
        """Fetch and format external documentation content."""
        urls = build_studio_urls(self.topic, self.version)
        url = urls[0] if urls else topic_info.get("url", "")
        name = topic_info.get("name", self.topic)
        description = topic_info.get("description", "")
        tags = ", ".join(topic_info.get("tags", []))

        try:
            result = await fetch_first_ok(urls or [url])
            if not result.ok:
                raise DashboardStudioContentError(
                    f"Failed to retrieve documentation from {url}: HTTP {result.status_code}. "
                    "Use dashboard-studio://cheatsheet for the local reference."
                )
            url = result.final_url
            soup = BeautifulSoup(result.text, "html.parser")

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
                main_content = soup.find("body")

            if main_content:
                for tag in main_content.select(
                    "script, style, nav, header, footer, .navigation, .sidebar"
                ):
                    tag.decompose()

                content_text = main_content.get_text(separator="\n", strip=True)
                lines = [line.strip() for line in content_text.split("\n") if line.strip()]
                formatted_content = "\n\n".join(lines)
            else:
                raise DashboardStudioContentError(
                    f"No readable documentation content found at {url}. "
                    "Use dashboard-studio://cheatsheet for the local reference."
                )

            if len(formatted_content.strip()) < 100:
                raise DashboardStudioContentError(
                    f"Documentation at {url} returned insufficient content after parsing. "
                    "Use dashboard-studio://cheatsheet for the local reference."
                )

            return f"""# {name}

**Topic**: `{self.topic}`
**Version**: Splunk {self.version}
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

        except DashboardStudioContentError:
            raise
        except Exception as e:  # pylint: disable=broad-except
            logger.error("Error processing Dashboard Studio docs for %s: %s", self.topic, e)
            raise DashboardStudioContentError(
                f"Failed to process documentation for topic '{self.topic}': {e}"
            ) from e

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

Available documentation topics for Splunk Dashboard Studio (default {DEFAULT_STUDIO_VERSION}).

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

**Version**: Splunk {DEFAULT_STUDIO_VERSION} (default)
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
def create_dashboard_studio_resource(
    topic: str, version: str | None = None
) -> DashboardStudioDocsResource:
    """Create a Dashboard Studio documentation resource for the specified topic.

    Args:
        topic: Topic name (e.g., 'cheatsheet', 'definition', 'visualizations')
        version: Splunk version (default 10.2). Also accepts ``10.5/datasources``.

    Returns:
        DashboardStudioDocsResource instance
    """
    parsed_topic, parsed_version = parse_studio_ref(topic)
    return DashboardStudioDocsResource(parsed_topic, version or parsed_version)


def register_dashboard_studio_resources():
    """Register Dashboard Studio documentation resources with the resource registry."""
    try:
        resource_registry.register(
            DashboardStudioDocsResource, DashboardStudioDocsResource.METADATA
        )
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


register_dashboard_studio_resources()
