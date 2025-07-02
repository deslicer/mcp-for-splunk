# Splunk Documentation Resources Implementation Plan

## Overview

This document outlines the strategy for implementing Splunk documentation resources in the MCP server to help LLMs better interact with Splunk. The approach balances LLM-optimized content delivery with version-aware, dynamic documentation access.

## Architecture Strategy

### 1. Resource URI Scheme

```
splunk-docs://{version}/{category}/{topic}
splunk-docs://{version}/search-reference/eval-functions
splunk-docs://{version}/admin-guide/indexes
splunk-docs://{version}/knowledge-manager/data-models
splunk-docs://latest/api-reference/search-api
```

### 2. Version Management Strategy

**Version Detection:**
- Auto-detect Splunk version from connected instance
- Support explicit version specification
- Default to "latest" for current documentation
- Maintain compatibility matrix

**Version Mapping:**
```python
VERSION_MAPPING = {
    "9.3.0": "93",
    "9.2.1": "92", 
    "9.1.0": "91",
    "latest": "93"  # Current latest
}
```

### 3. Content Categories

**Core Categories:**
- `search-reference` - SPL commands, functions, syntax
- `admin-guide` - Configuration, deployment, management
- `knowledge-manager` - Data models, field extractions, lookups
- `api-reference` - REST API endpoints and usage
- `getting-data-in` - Data ingestion and sourcetypes
- `alerting` - Alerts, saved searches, reports
- `security` - Authentication, authorization, encryption
- `troubleshooting` - Common issues and solutions

## Implementation Design

### Phase 1: Core Infrastructure

#### A. Base Documentation Resource Class

```python
# src/resources/splunk_docs.py

from src.core.base import BaseResource, ResourceMetadata
from fastmcp import Context
import httpx
from typing import Optional, Dict, List
from dataclasses import dataclass

@dataclass
class DocSection:
    title: str
    content: str
    url: str
    version: str
    category: str
    tags: List[str]

class SplunkDocsResource(BaseResource):
    """Base class for Splunk documentation resources."""
    
    SPLUNK_DOCS_BASE = "https://docs.splunk.com"
    VERSION_MAPPING = {
        "9.3.0": "93",
        "9.2.1": "92", 
        "9.1.0": "91",
        "latest": "93"
    }
    
    def __init__(self):
        super().__init__()
        self._cache = {}
        self._version_cache = {}
    
    async def get_splunk_version(self, ctx: Context) -> str:
        """Detect Splunk version from connected instance."""
        try:
            # Use existing health tool to get version
            health_result = await self.call_tool("get_splunk_health", {})
            return health_result.get("version", "latest")
        except:
            return "latest"
    
    def normalize_version(self, version: str) -> str:
        """Convert version to docs URL format."""
        return self.VERSION_MAPPING.get(version, self.VERSION_MAPPING["latest"])
    
    async def fetch_doc_content(self, url: str) -> str:
        """Fetch and process documentation content."""
        cache_key = f"doc_{hash(url)}"
        if cache_key in self._cache:
            return self._cache[cache_key]
        
        async with httpx.AsyncClient() as client:
            response = await client.get(url, timeout=30.0)
            response.raise_for_status()
            
            # Process HTML to LLM-friendly format
            content = self.process_html_to_llm_format(response.text)
            self._cache[cache_key] = content
            return content
    
    def process_html_to_llm_format(self, html: str) -> str:
        """Convert HTML documentation to LLM-optimized format."""
        # Use BeautifulSoup or similar to extract clean content
        # Follow llms.txt principles for structure
        pass
```

#### B. Specific Documentation Resources

```python
# src/resources/splunk_docs.py (continued)

class SPLReferenceResource(SplunkDocsResource):
    """SPL (Search Processing Language) reference documentation."""
    
    METADATA = ResourceMetadata(
        name="spl_reference",
        description="Splunk SPL command and function reference",
        category="documentation",
        tags={"spl", "search", "reference", "commands"}
    )
    
    @register_resource("splunk-docs://{version}/spl-reference/{command}")
    async def get_spl_command_docs(self, ctx: Context, version: str, command: str) -> str:
        """Get documentation for specific SPL command."""
        norm_version = self.normalize_version(version)
        url = f"{self.SPLUNK_DOCS_BASE}/Documentation/Splunk/{norm_version}/SearchReference/{command}"
        
        content = await self.fetch_doc_content(url)
        
        # Format for LLM consumption
        return f"""# SPL Command: {command}

**Version**: Splunk {version}
**Category**: Search Processing Language Reference

## Overview
{content}

## Usage Context
This command is used in Splunk search queries (SPL). It can be combined with other SPL commands using the pipe (|) operator.

## Related Commands
[This would include related command suggestions]

**Source**: {url}
"""

class AdminGuideResource(SplunkDocsResource):
    """Splunk administration documentation."""
    
    METADATA = ResourceMetadata(
        name="admin_guide",
        description="Splunk administration and configuration guide",
        category="documentation", 
        tags={"admin", "configuration", "deployment"}
    )
    
    @register_resource("splunk-docs://{version}/admin/{topic}")
    async def get_admin_docs(self, ctx: Context, version: str, topic: str) -> str:
        """Get administration documentation for specific topic."""
        # Implementation similar to SPL reference
        pass
```

### Phase 2: Content Processing Pipeline

#### A. HTML to LLM Format Processor

```python
# src/resources/processors/html_processor.py

from bs4 import BeautifulSoup
from typing import Dict, List
import re

class SplunkDocsProcessor:
    """Process Splunk HTML documentation into LLM-optimized format."""
    
    def __init__(self):
        self.section_hierarchy = []
        
    def process_html(self, html: str, url: str) -> str:
        """Main processing pipeline."""
        soup = BeautifulSoup(html, 'html.parser')
        
        # Extract main content area
        content_area = self.extract_main_content(soup)
        
        # Process sections hierarchically  
        sections = self.extract_sections(content_area)
        
        # Generate LLM-optimized markdown
        return self.generate_llm_markdown(sections, url)
    
    def extract_main_content(self, soup: BeautifulSoup) -> BeautifulSoup:
        """Extract the main documentation content, removing navigation/footer."""
        # Splunk docs typically have main content in specific containers
        main_content = (
            soup.find('div', class_='main-content') or
            soup.find('article') or
            soup.find('div', class_='content') or
            soup.find('main')
        )
        return main_content or soup
    
    def extract_sections(self, content: BeautifulSoup) -> List[Dict]:
        """Extract hierarchical sections from documentation."""
        sections = []
        current_section = None
        
        for element in content.find_all(['h1', 'h2', 'h3', 'h4', 'p', 'pre', 'code', 'ul', 'ol', 'table']):
            if element.name in ['h1', 'h2', 'h3', 'h4']:
                if current_section:
                    sections.append(current_section)
                
                current_section = {
                    'level': int(element.name[1]),
                    'title': element.get_text().strip(),
                    'content': []
                }
            elif current_section:
                current_section['content'].append(self.process_element(element))
        
        if current_section:
            sections.append(current_section)
            
        return sections
    
    def process_element(self, element) -> str:
        """Process individual HTML elements."""
        if element.name == 'pre':
            # Code blocks
            return f"```\n{element.get_text()}\n```"
        elif element.name == 'code':
            # Inline code
            return f"`{element.get_text()}`"
        elif element.name in ['ul', 'ol']:
            # Lists
            items = [f"- {li.get_text().strip()}" for li in element.find_all('li')]
            return '\n'.join(items)
        elif element.name == 'table':
            # Tables - convert to markdown
            return self.table_to_markdown(element)
        else:
            # Regular text
            return element.get_text().strip()
    
    def generate_llm_markdown(self, sections: List[Dict], url: str) -> str:
        """Generate final LLM-optimized markdown."""
        output = []
        
        for section in sections:
            # Add section header
            header_prefix = '#' * section['level']
            output.append(f"{header_prefix} {section['title']}")
            output.append("")
            
            # Add section content
            for content_item in section['content']:
                if content_item.strip():
                    output.append(content_item)
                    output.append("")
        
        # Add metadata footer
        output.extend([
            "---",
            f"**Source**: {url}",
            f"**Processed**: {datetime.now().isoformat()}",
            "**Format**: Optimized for LLM consumption"
        ])
        
        return '\n'.join(output)
```

### Phase 3: Resource Registration and Discovery

#### A. Automatic Resource Registration

```python
# src/resources/__init__.py

from .splunk_docs import SPLReferenceResource, AdminGuideResource, APIReferenceResource
from src.core.registry import resource_registry

def register_documentation_resources():
    """Register all Splunk documentation resources."""
    
    resources = [
        SPLReferenceResource(),
        AdminGuideResource(), 
        APIReferenceResource(),
        KnowledgeManagerResource(),
        DataIngestionResource(),
        SecurityGuideResource(),
        TroubleshootingResource()
    ]
    
    for resource in resources:
        resource_registry.register(resource)

# Auto-register when module is imported
register_documentation_resources()
```

#### B. Documentation Discovery Resource

```python
@register_resource("splunk-docs://discovery")
async def discover_documentation(ctx: Context, version: str = "latest") -> dict:
    """Discover available Splunk documentation resources."""
    
    splunk_version = version if version != "auto" else await get_splunk_version(ctx)
    
    categories = {
        "search-reference": {
            "description": "SPL commands, functions, and syntax reference",
            "resources": [
                "splunk-docs://{version}/spl-reference/search",
                "splunk-docs://{version}/spl-reference/eval", 
                "splunk-docs://{version}/spl-reference/stats",
                "splunk-docs://{version}/spl-reference/chart"
            ]
        },
        "admin-guide": {
            "description": "System administration and configuration",
            "resources": [
                "splunk-docs://{version}/admin/indexes",
                "splunk-docs://{version}/admin/authentication",
                "splunk-docs://{version}/admin/deployment"
            ]
        },
        "api-reference": {
            "description": "REST API endpoints and usage",
            "resources": [
                "splunk-docs://{version}/api/search",
                "splunk-docs://{version}/api/saved-searches",
                "splunk-docs://{version}/api/apps"
            ]
        }
    }
    
    # Replace version placeholders
    formatted_categories = {}
    for category, info in categories.items():
        formatted_resources = [
            resource.format(version=splunk_version) 
            for resource in info["resources"]
        ]
        formatted_categories[category] = {
            **info,
            "resources": formatted_resources
        }
    
    return {
        "splunk_version": splunk_version,
        "categories": formatted_categories,
        "total_resources": sum(len(cat["resources"]) for cat in formatted_categories.values())
    }
```

### Phase 4: Smart Caching and Updates

#### A. Version-Aware Caching

```python
# src/resources/cache.py

class DocumentationCache:
    """Version-aware caching for Splunk documentation."""
    
    def __init__(self, ttl_hours: int = 24):
        self.cache = {}
        self.version_mapping = {}
        self.ttl_hours = ttl_hours
    
    def cache_key(self, version: str, category: str, topic: str) -> str:
        """Generate cache key for documentation."""
        return f"docs_{version}_{category}_{topic}"
    
    async def get_or_fetch(self, version: str, category: str, topic: str, fetch_func) -> str:
        """Get from cache or fetch if expired/missing."""
        key = self.cache_key(version, category, topic)
        
        if key in self.cache:
            cached_item = self.cache[key]
            if not self.is_expired(cached_item['timestamp']):
                return cached_item['content']
        
        # Fetch fresh content
        content = await fetch_func()
        self.cache[key] = {
            'content': content,
            'timestamp': datetime.now(),
            'version': version
        }
        
        return content
    
    def invalidate_version(self, version: str):
        """Invalidate all cached docs for a specific version."""
        keys_to_remove = [k for k in self.cache.keys() if k.startswith(f"docs_{version}_")]
        for key in keys_to_remove:
            del self.cache[key]
```

## Integration with Existing MCP Server

### A. Add to Core Resource Registry

```python
# src/core/registry.py (modification)

class ResourceRegistry:
    def register_documentation_resources(self):
        """Register Splunk documentation resources."""
        from src.resources.splunk_docs import register_documentation_resources
        register_documentation_resources()
```

### B. Update Server Initialization

```python
# src/server.py (modification)

async def main():
    # ... existing code ...
    
    # Register documentation resources
    registry.register_documentation_resources()
    
    # ... rest of server setup ...
```

## Usage Examples

### A. LLM Prompt for Documentation Access

```
To help you with Splunk queries, I have access to Splunk documentation resources. 

Available documentation categories:
- splunk-docs://latest/spl-reference/{command} - SPL command reference
- splunk-docs://latest/admin/{topic} - Administration guides  
- splunk-docs://latest/api/{endpoint} - REST API reference

I can access specific documentation by topic. For example:
- "Show me documentation for the stats command"
- "How do I configure authentication in Splunk?"
- "What are the search API endpoints?"
```

### B. Client Usage

```python
# MCP client usage example
resources = await client.list_resources()
spl_docs = await client.read_resource("splunk-docs://9.3.0/spl-reference/stats")
print(spl_docs.content[0].text)
```

## Benefits of This Approach

1. **Version-Aware**: Automatic version detection and explicit version support
2. **LLM-Optimized**: Content processed for optimal LLM consumption
3. **Modular**: Easy to extend with new documentation categories
4. **Cacheable**: Efficient caching with TTL and version invalidation
5. **Discoverable**: Built-in discovery mechanism for available docs
6. **Flexible**: Support for both latest and version-specific documentation
7. **Maintainable**: Clear separation between processing and serving logic

## Next Steps

1. **Phase 1**: Implement base infrastructure and SPL reference
2. **Phase 2**: Add content processing pipeline  
3. **Phase 3**: Implement remaining documentation categories
4. **Phase 4**: Add smart caching and optimization
5. **Testing**: Comprehensive testing with different Splunk versions
6. **Documentation**: Update MCP server docs with usage examples

This approach provides a robust, scalable foundation for serving Splunk documentation to LLMs while maintaining version awareness and optimal content formatting. 