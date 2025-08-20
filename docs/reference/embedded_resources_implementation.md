# Embedded Resources Implementation

## Overview

This document describes the implementation of embedded resources for the MCP Splunk server, specifically focusing on embedded Splunk documentation resources and the tools to access them.

## Architecture

### Embedded Resources System

The embedded resources system consists of several key components:

1. **Base Embedded Resource Classes** (`src/resources/embedded.py`)
   - `EmbeddedResource`: Base class for embedded content
   - `SplunkEmbeddedResource`: Splunk-specific embedded resource
   - `FileEmbeddedResource`: File-based embedded resource
   - `TemplateEmbeddedResource`: Template-based embedded resource

2. **Splunk Documentation Resources** (`src/resources/embedded_splunk_docs.py`)
   - `SplunkCheatSheetEmbeddedResource`: Comprehensive Splunk cheat sheet
   - `SPLReferenceEmbeddedResource`: SPL syntax and command reference
   - `SplunkTroubleshootingEmbeddedResource`: Troubleshooting guide
   - `SplunkAdminGuideEmbeddedResource`: Administration guide

3. **Tools for Accessing Embedded Resources** (`src/tools/resources/embedded_docs_tools.py`)
   - `ListEmbeddedDocsTool`: List all available embedded documentation
   - `GetEmbeddedDocTool`: Get specific documentation by name or URI
   - `SearchEmbeddedDocsTool`: Search within documentation content
   - Specific tools for each documentation type

## Embedded Splunk Documentation Resources

### 1. Splunk Cheat Sheet

**URI**: `embedded://splunk/docs/cheat-sheet`

**Content**: Comprehensive Splunk cheat sheet including:
- Search commands (basic, statistical, data manipulation, output)
- SPL syntax and examples
- Common search patterns
- Time modifiers
- Field extraction techniques
- Statistical functions
- Performance tips
- Best practices

**Usage**:
```python
from src.resources.embedded_splunk_docs import embedded_splunk_docs_registry

cheat_sheet = embedded_splunk_docs_registry["cheat_sheet"]
content = await cheat_sheet.get_content(ctx)
```

### 2. SPL Reference

**URI**: `embedded://splunk/docs/spl-reference`

**Content**: Comprehensive SPL (Search Processing Language) reference including:
- Command categories and overview
- Generating commands (search, multisearch, append, join)
- Transforming commands (eval, rex, spath, rename, replace)
- Filtering commands (where, head, tail, dedup, sort)
- Statistical commands (stats, chart, timechart, top, rare)
- Output commands (table, list, fields, outputcsv)
- Statistical functions (count, sum, avg, min, max, etc.)
- String functions (len, lower, upper, substr, etc.)
- Mathematical functions (abs, ceil, floor, round, etc.)
- Time functions (strptime, strftime, now, etc.)
- Conditional functions (if, case)
- Regular expressions
- Best practices and examples

### 3. Troubleshooting Guide

**URI**: `embedded://splunk/docs/troubleshooting`

**Content**: Comprehensive troubleshooting guide including:
- Search issues (no results, slow performance, memory errors)
- Data issues (missing fields, incorrect data types)
- Performance issues (high CPU/memory usage)
- Index issues (not found, corruption)
- Forwarder issues (data not reaching indexer, disconnection)
- Authentication issues (login failures, permission errors)
- Configuration issues (not applied, errors)
- Diagnostic commands
- Log analysis techniques
- Performance monitoring
- Best practices

### 4. Administration Guide

**URI**: `embedded://splunk/docs/admin-guide`

**Content**: Comprehensive administration guide including:
- Installation and setup
- Index management
- User management
- Forwarder management
- Monitoring and alerting
- Security configuration
- Backup and recovery
- Performance optimization
- Troubleshooting
- Best practices

## Tools for Accessing Embedded Resources

### 1. ListEmbeddedDocsTool

Lists all available embedded Splunk documentation resources.

**Parameters**:
- `include_content` (boolean, optional): Whether to include content preview

**Example Response**:
```json
{
  "success": true,
  "count": 4,
  "documentation": [
    {
      "name": "cheat_sheet",
      "uri": "embedded://splunk/docs/cheat-sheet",
      "title": "Splunk Cheat Sheet",
      "description": "Comprehensive Splunk cheat sheet with search commands, SPL syntax, and common patterns"
    }
  ],
  "message": "Found 4 embedded documentation resources"
}
```

### 2. GetEmbeddedDocTool

Get specific embedded Splunk documentation by name or URI.

**Parameters**:
- `name` (string, optional): Name of the documentation
- `uri` (string, optional): URI of the documentation resource
- `include_metadata` (boolean, optional): Whether to include metadata

**Example Response**:
```json
{
  "success": true,
  "content": "# Splunk Cheat Sheet\n\n## Search Commands...",
  "metadata": {
    "name": "Splunk Cheat Sheet",
    "uri": "embedded://splunk/docs/cheat-sheet",
    "description": "Comprehensive Splunk cheat sheet...",
    "mime_type": "text/markdown",
    "cache_ttl": 86400
  },
  "message": "Successfully retrieved Splunk Cheat Sheet"
}
```

### 3. SearchEmbeddedDocsTool

Search within embedded Splunk documentation content.

**Parameters**:
- `query` (string, required): Search query to find in documentation content
- `docs` (array, optional): Specific documentation names to search in
- `case_sensitive` (boolean, optional): Whether search should be case sensitive
- `max_results` (integer, optional): Maximum number of results to return

**Example Response**:
```json
{
  "success": true,
  "query": "stats",
  "results": [
    {
      "doc_name": "cheat_sheet",
      "doc_title": "Splunk Cheat Sheet",
      "doc_uri": "embedded://splunk/docs/cheat-sheet",
      "matches": [
        {
          "line_number": 45,
          "line": "- `stats` - Calculate statistics",
          "context": "### Statistical Commands\n- `stats` - Calculate statistics\n- `chart` - Create charts"
        }
      ]
    }
  ],
  "total_docs_searched": 4,
  "total_matches": 12,
  "message": "Found 12 matches across 3 documents"
}
```

### 4. Specific Documentation Tools

#### GetSplunkCheatSheetTool
Get the comprehensive Splunk cheat sheet.

#### GetSPLReferenceTool
Get the comprehensive SPL reference.

#### GetTroubleshootingGuideTool
Get the comprehensive troubleshooting guide.

#### GetAdminGuideTool
Get the comprehensive administration guide.

## Registration and Discovery

### Automatic Registration

The embedded resources are automatically registered through the following process:

1. **Resource Registration** (`src/resources/__init__.py`):
   ```python
   from .embedded_splunk_docs import register_embedded_splunk_docs
   register_embedded_splunk_docs()
   ```

2. **Tool Registration** (`src/tools/__init__.py`):
   ```python
   from .resources import *
   ```

3. **Automatic Discovery** (`src/core/loader.py`):
   The ComponentLoader automatically discovers and registers all tools and resources.

### Registry System

The embedded resources use a registry system for easy access:

```python
from src.resources.embedded_splunk_docs import embedded_splunk_docs_registry

# Access by name
cheat_sheet = embedded_splunk_docs_registry["cheat_sheet"]

# Access by URI
resource = get_embedded_splunk_doc("embedded://splunk/docs/cheat-sheet")

# List all available docs
docs = list_embedded_splunk_docs()
```

## Benefits of Embedded Resources

### 1. Performance
- **Fast Access**: No network requests required
- **Caching**: Built-in caching with configurable TTL
- **Reliability**: No dependency on external services

### 2. Availability
- **Offline Access**: Available even without internet connection
- **Consistent Content**: Version-controlled and tested content
- **No External Dependencies**: Self-contained within the MCP server

### 3. Security
- **No External Requests**: Eliminates security risks from external API calls
- **Controlled Content**: All content is reviewed and approved
- **No Credentials Required**: No need for external authentication

### 4. Developer Experience
- **Immediate Access**: Instant response times
- **Rich Content**: Comprehensive, well-structured documentation
- **Search Capability**: Full-text search across all documentation
- **Structured Access**: Consistent API for all documentation types

## Usage Examples

### 1. Getting the Splunk Cheat Sheet

```python
# Using the specific tool
result = await get_splunk_cheat_sheet_tool.execute(ctx)

# Using the generic tool
result = await get_embedded_doc_tool.execute(ctx, name="cheat_sheet")

# Direct resource access
cheat_sheet = embedded_splunk_docs_registry["cheat_sheet"]
content = await cheat_sheet.get_content(ctx)
```

### 2. Searching Documentation

```python
# Search for "stats" across all documentation
result = await search_embedded_docs_tool.execute(ctx, query="stats")

# Search only in cheat sheet and SPL reference
result = await search_embedded_docs_tool.execute(
    ctx, 
    query="timechart", 
    docs=["cheat_sheet", "spl_reference"]
)
```

### 3. Listing Available Documentation

```python
# List all documentation
result = await list_embedded_docs_tool.execute(ctx)

# List with content previews
result = await list_embedded_docs_tool.execute(ctx, include_content=True)
```

## Testing

### Test Script

A test script is provided to verify the embedded resources:

```bash
python test_embedded_resources.py
```

The test script verifies:
1. Listing all embedded documentation
2. Testing each individual resource
3. Testing content retrieval
4. Testing the registry functions

### Expected Output

```
🧪 Testing Embedded Splunk Documentation Resources
============================================================

1. Testing list_embedded_splunk_docs()...
✅ Found 4 embedded documentation resources:
   - cheat_sheet: Splunk Cheat Sheet
     URI: embedded://splunk/docs/cheat-sheet
     Description: Comprehensive Splunk cheat sheet with search commands, SPL syntax, and common patterns

2. Testing individual embedded resources...
   Testing cheat_sheet...
     Name: Splunk Cheat Sheet
     URI: embedded://splunk/docs/cheat-sheet
     Description: Comprehensive Splunk cheat sheet with search commands, SPL syntax, and common patterns
     MIME Type: text/markdown
     Content length: 15420 characters
     Content preview: # Splunk Cheat Sheet

## Search Commands

### Basic Search Commands
- `search` - Start a search (optional, implied)...
   ✅ cheat_sheet - PASSED

3. Testing get_embedded_splunk_doc() function...
✅ Found resource by URI: Splunk Cheat Sheet
✅ Found resource by name: Splunk Cheat Sheet

============================================================
🎉 Embedded documentation resources test completed!
```

## Future Enhancements

### 1. Additional Documentation Types
- Splunk Enterprise Security documentation
- Splunk IT Service Intelligence documentation
- Splunk Cloud documentation
- Version-specific documentation

### 2. Enhanced Search Capabilities
- Fuzzy search
- Semantic search
- Search result ranking
- Search history

### 3. Content Management
- Dynamic content updates
- User-contributed content
- Content versioning
- Content validation

### 4. Integration Features
- Export to different formats
- Integration with external documentation
- Content synchronization
- Usage analytics

## Conclusion

The embedded resources system provides a robust, performant, and secure way to access Splunk documentation within the MCP server. The comprehensive documentation resources and tools make it easy for users to access the information they need quickly and reliably.

The system is designed to be extensible, allowing for easy addition of new documentation types and enhanced functionality in the future.