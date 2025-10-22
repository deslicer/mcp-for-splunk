"""
Dashboard Studio documentation resources for MCP server.

Provides curated Dashboard Studio (9.4) documentation for LLM-assisted dashboard authoring.
"""

import logging
from pathlib import Path

from fastmcp import Context

from src.core.base import BaseResource, ResourceMetadata
from src.core.registry import resource_registry

logger = logging.getLogger(__name__)


class DashboardStudioCheatsheetResource(BaseResource):
    """Curated Dashboard Studio cheatsheet resource."""

    METADATA = ResourceMetadata(
        uri="dashboard-studio://cheatsheet",
        name="dashboard_studio_cheatsheet",
        description="Dashboard Studio (9.4) cheatsheet with definition schema, examples, and authoring tips",
        mime_type="text/markdown",
        category="reference",
        tags=["dashboard-studio", "dashboards", "visualization", "reference", "cheatsheet"],
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
        """Get Dashboard Studio cheatsheet content."""
        try:
            # Load cheatsheet from file
            cheatsheet_path = (
                Path(__file__).parent.parent.parent
                / "docs"
                / "reference"
                / "dashboard_studio_cheatsheet.md"
            )

            if not cheatsheet_path.exists():
                return f"""# Dashboard Studio Cheatsheet Not Found

The cheatsheet file was not found at: {cheatsheet_path}

Please ensure the file exists in the docs/reference directory.
"""

            content = cheatsheet_path.read_text(encoding="utf-8")
            return content

        except Exception as e:  # pylint: disable=broad-except
            logger.error("Error loading Dashboard Studio cheatsheet: %s", e)
            return f"""# Error Loading Cheatsheet

Failed to load Dashboard Studio cheatsheet: {str(e)}

Please check the file path and permissions.
"""


class DashboardStudioLinksResource(BaseResource):
    """Dashboard Studio canonical documentation links index."""

    METADATA = ResourceMetadata(
        uri="dashboard-studio://links",
        name="dashboard_studio_links",
        description="Canonical Dashboard Studio documentation links with titles and summaries",
        mime_type="text/markdown",
        category="reference",
        tags=["dashboard-studio", "dashboards", "documentation", "links", "reference"],
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
        """Get Dashboard Studio documentation links index."""
        return """# Dashboard Studio Documentation Links

Canonical documentation for Splunk Dashboard Studio (version 9.4).

## Core Concepts

### Dashboard Framework Introduction
**URL**: https://splunkui.splunk.com/Packages/dashboard-docs/Introduction

**Summary**: Explains what Dashboard Framework is - a set of UI components that render dashboards. Covers key concepts: Dashboard Definition (JSON object), Visualizations (React components), Layout (positioning), DataSource (data providers), Inputs, Tokens, EventHandlers, and Presets. Essential for understanding the architecture.

### Dashboard Docs Package Index
**URL**: https://splunkui.splunk.com/Packages/dashboard-docs/

**Summary**: Main entry point for Splunk Dashboard Framework documentation. Links to all packages, components, and guides for building dashboards programmatically.

## Definition and Structure

### What is a Dashboard Definition?
**URL**: https://help.splunk.com/en/splunk-enterprise/create-dashboards-and-reports/dashboard-studio/9.4/source-code-editor/what-is-a-dashboard-definition

**Summary**: Comprehensive explanation of dashboard definition structure. Covers JSON schema, required fields, optional components, and how definitions are used in Dashboard Studio. Critical for understanding the definition format for REST API creation.

## Visualizations

### Add and Format Visualizations
**URL**: https://help.splunk.com/en/splunk-enterprise/create-dashboards-and-reports/dashboard-studio/9.4/visualizations/add-and-format-visualizations

**Summary**: Guide to adding visualizations to dashboards, configuring properties, connecting to data sources, and formatting appearance. Includes examples of common visualization types and configuration patterns.

### Visualization Configuration Options
**URL**: https://help.splunk.com/en/splunk-enterprise/create-dashboards-and-reports/dashboard-studio/9.4/configuration-options-reference/visualization-configuration-options

**Summary**: Complete reference of configuration options available for each visualization type. Details field mappings, display options, interaction settings, and type-specific properties. Use this for accurate `options` object construction.

## Quick Reference

### Most Used Links
1. **Cheatsheet** (local): `dashboard-studio://cheatsheet` - Quick reference with examples
2. **Definition Structure**: What is a Dashboard Definition? (above)
3. **Viz Configuration**: Visualization Configuration Options (above)

### Common Workflows
- **Planning**: Review Framework Introduction → understand components
- **Authoring**: Use Cheatsheet → reference Definition Structure for schema
- **Configuring Viz**: Check Add/Format guide → lookup specific options in Configuration reference
- **Troubleshooting**: Validate JSON structure → check field names in Configuration reference

## Version Information

**Target Version**: Splunk Enterprise 9.4
**Framework**: Dashboard Studio (JSON-based)
**REST Endpoint**: `/servicesNS/{owner}/{app}/data/ui/views`

---

**Note**: All links are versioned to 9.4 for consistency. For other versions, update the version segment in URLs.
"""


# Registry and factory functions
def register_dashboard_studio_resources():
    """Register Dashboard Studio documentation resources with the resource registry."""
    try:
        # Register static resources
        resource_registry.register(
            DashboardStudioCheatsheetResource, DashboardStudioCheatsheetResource.METADATA
        )

        resource_registry.register(
            DashboardStudioLinksResource, DashboardStudioLinksResource.METADATA
        )

        logger.info("Successfully registered 2 Dashboard Studio documentation resources")

    except Exception as e:  # pylint: disable=broad-except
        logger.error("Failed to register Dashboard Studio resources: %s", e)


# Auto-register resources when module is imported
register_dashboard_studio_resources()
