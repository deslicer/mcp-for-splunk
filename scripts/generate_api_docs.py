#!/usr/bin/env python3
"""
API Documentation Generator for MCP Server for Splunk

Generates comprehensive API documentation from tool metadata, method signatures,
and enhanced descriptions. Creates both markdown and OpenAPI specification formats.
"""

import ast
import inspect
import json
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from src.core.discovery import discover_tools
from src.core.registry import tool_registry


class ToolDocumentationExtractor:
    """Extract comprehensive documentation from MCP tools."""
    
    def __init__(self):
        self.tools_metadata = {}
        self.method_signatures = {}
        self.source_code = {}
        
    def discover_and_analyze_tools(self):
        """Discover all tools and analyze their documentation."""
        print("🔍 Discovering tools...")
        discover_tools()
        
        tool_metadata_list = tool_registry.list_tools()
        print(f"📋 Found {len(tool_metadata_list)} tools")
        
        for metadata in tool_metadata_list:
            tool_name = metadata.name
            tool_class = tool_registry._tools.get(tool_name)
            
            if tool_class:
                print(f"  📄 Analyzing: {tool_name}")
                self._analyze_tool(tool_class, metadata)
                
    def _analyze_tool(self, tool_class, metadata):
        """Analyze a single tool for comprehensive documentation."""
        tool_name = metadata.name
        
        # Store metadata
        self.tools_metadata[tool_name] = {
            'metadata': metadata,
            'class_name': tool_class.__name__,
            'module': tool_class.__module__,
            'class_doc': tool_class.__doc__ or "",
        }
        
        # Analyze execute method
        if hasattr(tool_class, 'execute'):
            execute_method = getattr(tool_class, 'execute')
            self._analyze_execute_method(tool_name, execute_method)
            
        # Extract source code for additional context
        self._extract_source_info(tool_name, tool_class)
        
    def _analyze_execute_method(self, tool_name: str, execute_method):
        """Analyze the execute method signature and documentation."""
        try:
            # Get method signature
            sig = inspect.signature(execute_method)
            
            # Get method docstring
            docstring = execute_method.__doc__ or ""
            
            # Parse parameters
            parameters = {}
            for param_name, param in sig.parameters.items():
                if param_name in ['self', 'ctx']:  # Skip self and context
                    continue
                    
                param_info = {
                    'name': param_name,
                    'type': self._format_type_annotation(param.annotation),
                    'default': self._format_default_value(param.default),
                    'required': param.default == inspect.Parameter.empty,
                    'description': self._extract_param_description(docstring, param_name)
                }
                parameters[param_name] = param_info
                
            # Parse return type
            return_type = self._format_type_annotation(sig.return_annotation)
            
            self.method_signatures[tool_name] = {
                'signature': str(sig),
                'parameters': parameters,
                'return_type': return_type,
                'docstring': docstring,
                'parsed_docstring': self._parse_docstring(docstring)
            }
            
        except Exception as e:
            print(f"  ⚠️ Error analyzing {tool_name}: {e}")
            
    def _format_type_annotation(self, annotation) -> str:
        """Format type annotation for documentation."""
        if annotation == inspect.Parameter.empty:
            return "Any"
            
        if hasattr(annotation, '__name__'):
            return annotation.__name__
        elif hasattr(annotation, '__origin__'):
            # Handle generic types like Union, Optional, List, etc.
            origin = annotation.__origin__
            if origin is Union:
                args = annotation.__args__
                if len(args) == 2 and type(None) in args:
                    # This is Optional[Type]
                    non_none = next(arg for arg in args if arg is not type(None))
                    return f"Optional[{self._format_type_annotation(non_none)}]"
                else:
                    # This is Union[Type1, Type2, ...]
                    formatted_args = [self._format_type_annotation(arg) for arg in args]
                    return f"Union[{', '.join(formatted_args)}]"
            elif hasattr(origin, '__name__'):
                if annotation.__args__:
                    args_str = ', '.join(self._format_type_annotation(arg) for arg in annotation.__args__)
                    return f"{origin.__name__}[{args_str}]"
                else:
                    return origin.__name__
        
        return str(annotation)
        
    def _format_default_value(self, default) -> Optional[str]:
        """Format default value for documentation."""
        if default == inspect.Parameter.empty:
            return None
        elif default is None:
            return "None"
        elif isinstance(default, str):
            return f'"{default}"'
        else:
            return str(default)
            
    def _extract_param_description(self, docstring: str, param_name: str) -> str:
        """Extract parameter description from docstring."""
        if not docstring:
            return ""
            
        # Look for Args section
        args_match = re.search(r'Args:\s*\n(.*?)(?:\n\s*\n|\n[A-Z]|\Z)', docstring, re.DOTALL)
        if not args_match:
            return ""
            
        args_section = args_match.group(1)
        
        # Look for parameter description
        param_pattern = rf'{re.escape(param_name)}\s*\([^)]*\)\s*:\s*([^:]*?)(?=\n\s*\w+\s*\(|\Z)'
        param_match = re.search(param_pattern, args_section, re.DOTALL)
        
        if param_match:
            description = param_match.group(1).strip()
            # Clean up the description (remove extra whitespace, etc.)
            description = re.sub(r'\s+', ' ', description)
            return description
            
        return ""
        
    def _parse_docstring(self, docstring: str) -> Dict[str, str]:
        """Parse docstring into sections."""
        if not docstring:
            return {}
            
        sections = {}
        current_section = "description"
        current_content = []
        
        lines = docstring.strip().split('\n')
        
        for line in lines:
            line = line.strip()
            
            # Check for section headers
            if line.endswith(':') and line[:-1] in ['Args', 'Returns', 'Raises', 'Example', 'Examples']:
                # Save previous section
                if current_content:
                    sections[current_section] = '\n'.join(current_content).strip()
                
                # Start new section
                current_section = line[:-1].lower()
                current_content = []
            else:
                current_content.append(line)
                
        # Save last section
        if current_content:
            sections[current_section] = '\n'.join(current_content).strip()
            
        return sections
        
    def _extract_source_info(self, tool_name: str, tool_class):
        """Extract additional information from source code."""
        try:
            source_file = inspect.getfile(tool_class)
            source_lines = inspect.getsourcelines(tool_class)[1]
            
            self.source_code[tool_name] = {
                'file': source_file,
                'start_line': source_lines,
                'module_path': tool_class.__module__
            }
        except Exception as e:
            print(f"  ⚠️ Could not extract source info for {tool_name}: {e}")


class MarkdownDocumentationGenerator:
    """Generate comprehensive markdown documentation."""
    
    def __init__(self, extractor: ToolDocumentationExtractor):
        self.extractor = extractor
        
    def generate_full_documentation(self) -> str:
        """Generate complete API documentation."""
        doc_parts = []
        
        # Header
        doc_parts.append(self._generate_header())
        
        # Table of contents
        doc_parts.append(self._generate_toc())
        
        # Overview
        doc_parts.append(self._generate_overview())
        
        # Tools by category
        doc_parts.append(self._generate_tools_by_category())
        
        # Detailed tool documentation
        doc_parts.append(self._generate_detailed_tools())
        
        # API schemas
        doc_parts.append(self._generate_schemas())
        
        # Footer
        doc_parts.append(self._generate_footer())
        
        return '\n\n'.join(doc_parts)
        
    def _generate_header(self) -> str:
        """Generate documentation header."""
        return f"""# MCP Server for Splunk - API Documentation

**Version:** 1.0.0  
**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  
**Protocol:** Model Context Protocol (MCP) 2024-11-05

## Introduction

This document provides comprehensive API documentation for all tools available in the MCP Server for Splunk. Each tool is documented with detailed parameter information, return values, usage examples, and integration guidance.

The MCP Server for Splunk provides {len(self.extractor.tools_metadata)} production-ready tools organized into categories for different use cases including search operations, system administration, data management, and health monitoring."""

    def _generate_toc(self) -> str:
        """Generate table of contents."""
        toc = ["## Table of Contents", ""]
        
        # Group tools by category
        categories = {}
        for tool_name, info in self.extractor.tools_metadata.items():
            category = info['metadata'].category
            if category not in categories:
                categories[category] = []
            categories[category].append(tool_name)
            
        toc.append("### Tools by Category")
        for category in sorted(categories.keys()):
            toc.append(f"- [{category.title()} Tools](#{category.lower()}-tools)")
            
        toc.append("")
        toc.append("### Detailed Tool Documentation")
        for tool_name in sorted(self.extractor.tools_metadata.keys()):
            toc.append(f"- [`{tool_name}`](#{tool_name.replace('_', '-')})")
            
        toc.extend([
            "",
            "### Additional Sections",
            "- [API Schemas](#api-schemas)",
            "- [Error Handling](#error-handling)",
            "- [Authentication](#authentication)",
            "- [Rate Limiting](#rate-limiting)"
        ])
        
        return '\n'.join(toc)
        
    def _generate_overview(self) -> str:
        """Generate overview section."""
        # Count tools by category
        categories = {}
        for tool_name, info in self.extractor.tools_metadata.items():
            category = info['metadata'].category
            categories[category] = categories.get(category, 0) + 1
            
        overview_parts = [
            "## Overview",
            "",
            "The MCP Server for Splunk provides a comprehensive set of tools for interacting with Splunk environments through the Model Context Protocol. All tools are designed for production use with comprehensive error handling, validation, and documentation.",
            "",
            "### Tool Categories",
            ""
        ]
        
        for category, count in sorted(categories.items()):
            overview_parts.append(f"- **{category.title()}** ({count} tools) - {self._get_category_description(category)}")
            
        overview_parts.extend([
            "",
            "### Authentication & Connection",
            "",
            "All tools that require Splunk connectivity (`requires_connection: true`) use the configured Splunk connection from the server context. Connection parameters can be overridden on a per-tool basis where supported.",
            "",
            "### Error Handling",
            "",
            "All tools return standardized response formats:",
            "- **Success responses** include `success: true` and relevant data",
            "- **Error responses** include `success: false`, `error` message, and context",
            "- **Connection errors** are handled gracefully with diagnostic information"
        ])
        
        return '\n'.join(overview_parts)
        
    def _get_category_description(self, category: str) -> str:
        """Get description for a tool category."""
        descriptions = {
            'search': 'Execute Splunk searches, manage saved searches, and retrieve search results',
            'admin': 'Manage Splunk applications, users, and configuration settings',
            'metadata': 'Discover and explore Splunk data sources, indexes, and structure',
            'kvstore': 'Manage KV Store collections and perform data operations',
            'health': 'Monitor Splunk system health and connectivity status'
        }
        return descriptions.get(category, 'Specialized tools for specific Splunk operations')
        
    def _generate_tools_by_category(self) -> str:
        """Generate tools organized by category."""
        # Group tools by category
        categories = {}
        for tool_name, info in self.extractor.tools_metadata.items():
            category = info['metadata'].category
            if category not in categories:
                categories[category] = []
            categories[category].append((tool_name, info))
            
        doc_parts = []
        
        for category in sorted(categories.keys()):
            doc_parts.append(f"## {category.title()} Tools")
            doc_parts.append("")
            
            tools = sorted(categories[category], key=lambda x: x[0])
            
            for tool_name, info in tools:
                metadata = info['metadata']
                
                # Create tool summary
                doc_parts.append(f"### `{tool_name}`")
                doc_parts.append("")
                doc_parts.append(f"**Description:** {metadata.description}")
                doc_parts.append("")
                
                # Add tags and requirements
                if metadata.tags:
                    doc_parts.append(f"**Tags:** {', '.join(metadata.tags)}")
                doc_parts.append(f"**Requires Connection:** {'Yes' if metadata.requires_connection else 'No'}")
                doc_parts.append("")
                
                # Add quick parameter summary
                if tool_name in self.extractor.method_signatures:
                    sig_info = self.extractor.method_signatures[tool_name]
                    params = sig_info['parameters']
                    
                    if params:
                        required_params = [name for name, info in params.items() if info['required']]
                        optional_params = [name for name, info in params.items() if not info['required']]
                        
                        if required_params:
                            doc_parts.append(f"**Required Parameters:** {', '.join(f'`{p}`' for p in required_params)}")
                        if optional_params:
                            doc_parts.append(f"**Optional Parameters:** {', '.join(f'`{p}`' for p in optional_params)}")
                    else:
                        doc_parts.append("**Parameters:** None")
                        
                doc_parts.append("")
                doc_parts.append(f"[→ Detailed Documentation](#{tool_name.replace('_', '-')})")
                doc_parts.append("")
                
        return '\n'.join(doc_parts)
        
    def _generate_detailed_tools(self) -> str:
        """Generate detailed documentation for each tool."""
        doc_parts = ["## Detailed Tool Documentation", ""]
        
        for tool_name in sorted(self.extractor.tools_metadata.keys()):
            doc_parts.append(self._generate_tool_detail(tool_name))
            doc_parts.append("")
            
        return '\n'.join(doc_parts)
        
    def _generate_tool_detail(self, tool_name: str) -> str:
        """Generate detailed documentation for a single tool."""
        info = self.extractor.tools_metadata[tool_name]
        metadata = info['metadata']
        
        parts = [
            f"### {tool_name}",
            "",
            f"**Category:** {metadata.category}  ",
            f"**Version:** {metadata.version}  ",
            f"**Requires Connection:** {'Yes' if metadata.requires_connection else 'No'}  "
        ]
        
        if metadata.tags:
            parts.append(f"**Tags:** {', '.join(metadata.tags)}  ")
            
        parts.extend([
            "",
            "#### Description",
            "",
            metadata.description
        ])
        
        # Add method signature information
        if tool_name in self.extractor.method_signatures:
            sig_info = self.extractor.method_signatures[tool_name]
            
            # Parameters section
            parts.extend([
                "",
                "#### Parameters",
                ""
            ])
            
            params = sig_info['parameters']
            if params:
                parts.append("| Parameter | Type | Required | Default | Description |")
                parts.append("|-----------|------|----------|---------|-------------|")
                
                for param_name, param_info in params.items():
                    required = "✅" if param_info['required'] else "❌"
                    default = param_info['default'] or "None"
                    description = param_info['description'] or "No description available"
                    
                    parts.append(f"| `{param_name}` | `{param_info['type']}` | {required} | `{default}` | {description} |")
            else:
                parts.append("This tool takes no parameters.")
                
            # Return value section
            parts.extend([
                "",
                "#### Returns",
                "",
                f"**Type:** `{sig_info['return_type']}`",
                ""
            ])
            
            # Parse return description from docstring
            parsed_doc = sig_info['parsed_docstring']
            if 'returns' in parsed_doc:
                parts.append(parsed_doc['returns'])
            else:
                parts.append("Returns a dictionary containing the operation result with success status and data.")
                
            # Usage example
            parts.extend([
                "",
                "#### Usage Example",
                "",
                "```python"
            ])
            
            # Generate example based on parameters
            example_call = self._generate_usage_example(tool_name, params)
            parts.append(example_call)
            parts.append("```")
            
            # Add any examples from docstring
            if 'example' in parsed_doc or 'examples' in parsed_doc:
                example_content = parsed_doc.get('example', parsed_doc.get('examples', ''))
                if example_content:
                    parts.extend([
                        "",
                        "#### Additional Examples",
                        "",
                        example_content
                    ])
                    
        # Source information
        if tool_name in self.extractor.source_code:
            source_info = self.extractor.source_code[tool_name]
            parts.extend([
                "",
                "#### Source Information",
                "",
                f"**Module:** `{source_info['module_path']}`  ",
                f"**File:** `{Path(source_info['file']).relative_to(Path.cwd())}`  ",
                f"**Line:** {source_info['start_line']}  "
            ])
            
        return '\n'.join(parts)
        
    def _generate_usage_example(self, tool_name: str, params: Dict) -> str:
        """Generate a usage example for a tool."""
        if not params:
            return f"result = await {tool_name}()"
            
        # Build example with realistic parameter values
        example_params = []
        for param_name, param_info in params.items():
            if param_info['required'] or param_name in ['query', 'search', 'name']:
                example_value = self._get_example_value(param_name, param_info['type'])
                example_params.append(f"{param_name}={example_value}")
                
        params_str = ", ".join(example_params)
        return f"result = await {tool_name}({params_str})"
        
    def _get_example_value(self, param_name: str, param_type: str) -> str:
        """Get an appropriate example value for a parameter."""
        # Special cases based on parameter name
        examples = {
            'query': '"index=main error | stats count"',
            'search': '"index=web_logs status=500 | head 10"',
            'name': '"my_saved_search"',
            'earliest_time': '"-24h"',
            'latest_time': '"now"',
            'max_results': '100',
            'app': '"search"',
            'collection': '"my_collection"',
            'conf_file': '"props"',
            'stanza': '"default"'
        }
        
        if param_name in examples:
            return examples[param_name]
            
        # Type-based defaults
        if 'str' in param_type:
            return '"example_value"'
        elif 'int' in param_type:
            return '100'
        elif 'bool' in param_type:
            return 'True'
        elif 'dict' in param_type:
            return '{}'
        elif 'list' in param_type:
            return '[]'
        else:
            return '"example"'
            
    def _generate_schemas(self) -> str:
        """Generate API schemas section."""
        return """## API Schemas

### Standard Response Format

All tools return responses in a standardized format:

```json
{
  "success": true,
  "data": {
    // Tool-specific response data
  },
  "metadata": {
    "tool": "tool_name",
    "execution_time": "2024-01-01T12:00:00Z",
    "version": "1.0.0"
  }
}
```

### Error Response Format

```json
{
  "success": false,
  "error": "Error description",
  "error_code": "ERROR_CODE",
  "details": {
    // Additional error context
  },
  "metadata": {
    "tool": "tool_name",
    "execution_time": "2024-01-01T12:00:00Z"
  }
}
```

### Connection Parameters

Tools that support connection overrides accept these parameters:

```json
{
  "splunk_host": "splunk.example.com",
  "splunk_port": 8089,
  "splunk_username": "admin",
  "splunk_password": "password",
  "splunk_scheme": "https",
  "splunk_verify_ssl": true
}
```

## Error Handling

### Common Error Codes

- `CONNECTION_ERROR` - Unable to connect to Splunk
- `AUTHENTICATION_ERROR` - Invalid credentials
- `PERMISSION_ERROR` - Insufficient permissions
- `VALIDATION_ERROR` - Invalid parameters
- `TIMEOUT_ERROR` - Operation timed out
- `NOT_FOUND_ERROR` - Resource not found
- `INTERNAL_ERROR` - Server error

### Best Practices

1. **Always check the `success` field** in responses
2. **Handle connection errors gracefully** with retry logic
3. **Validate parameters** before making tool calls
4. **Use appropriate timeouts** for long-running operations
5. **Log errors with context** for debugging

## Authentication

Authentication is handled at the server level. Tools inherit the connection context from the server configuration. Individual tools can override connection parameters where supported.

## Rate Limiting

The server implements connection pooling and request throttling to prevent overwhelming Splunk instances. Consider:

- **Batch operations** when possible
- **Reasonable time ranges** for search operations  
- **Pagination** for large result sets
- **Appropriate delays** between consecutive calls"""

    def _generate_footer(self) -> str:
        """Generate documentation footer."""
        return f"""---

## Support

- **Documentation:** [GitHub Repository](https://github.com/your-org/mcp-server-for-splunk)
- **Issues:** [Report Issues](https://github.com/your-org/mcp-server-for-splunk/issues)
- **Discussions:** [Community Support](https://github.com/your-org/mcp-server-for-splunk/discussions)

---

*This documentation was automatically generated from tool metadata and source code analysis.*  
*Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*"""


class OpenAPIGenerator:
    """Generate OpenAPI specification from tools."""
    
    def __init__(self, extractor: ToolDocumentationExtractor):
        self.extractor = extractor
        
    def generate_openapi_spec(self) -> Dict[str, Any]:
        """Generate OpenAPI 3.0 specification."""
        spec = {
            "openapi": "3.0.0",
            "info": {
                "title": "MCP Server for Splunk API",
                "version": "1.0.0",
                "description": "Model Context Protocol server providing Splunk integration tools",
                "contact": {
                    "name": "API Support",
                    "url": "https://github.com/your-org/mcp-server-for-splunk"
                },
                "license": {
                    "name": "MIT",
                    "url": "https://opensource.org/licenses/MIT"
                }
            },
            "servers": [
                {
                    "url": "http://localhost:8001/mcp",
                    "description": "Development server"
                }
            ],
            "paths": {
                "/tools/call": {
                    "post": {
                        "summary": "Execute MCP Tool",
                        "description": "Execute any available MCP tool with parameters",
                        "requestBody": {
                            "required": True,
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "$ref": "#/components/schemas/ToolCallRequest"
                                    }
                                }
                            }
                        },
                        "responses": {
                            "200": {
                                "description": "Tool execution result",
                                "content": {
                                    "application/json": {
                                        "schema": {
                                            "$ref": "#/components/schemas/ToolCallResponse"
                                        }
                                    }
                                }
                            }
                        }
                    }
                },
                "/tools/list": {
                    "post": {
                        "summary": "List Available Tools",
                        "description": "Get list of all available tools",
                        "responses": {
                            "200": {
                                "description": "List of available tools",
                                "content": {
                                    "application/json": {
                                        "schema": {
                                            "$ref": "#/components/schemas/ToolListResponse"
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            },
            "components": {
                "schemas": self._generate_schemas()
            }
        }
        
        return spec
        
    def _generate_schemas(self) -> Dict[str, Any]:
        """Generate OpenAPI schemas."""
        schemas = {
            "ToolCallRequest": {
                "type": "object",
                "required": ["jsonrpc", "method", "params"],
                "properties": {
                    "jsonrpc": {"type": "string", "enum": ["2.0"]},
                    "method": {"type": "string", "enum": ["tools/call"]},
                    "params": {
                        "type": "object",
                        "required": ["name"],
                        "properties": {
                            "name": {
                                "type": "string",
                                "enum": list(self.extractor.tools_metadata.keys())
                            },
                            "arguments": {"type": "object"}
                        }
                    },
                    "id": {"type": "string"}
                }
            },
            "ToolCallResponse": {
                "type": "object",
                "properties": {
                    "jsonrpc": {"type": "string"},
                    "result": {
                        "type": "object",
                        "properties": {
                            "content": {"type": "array"},
                            "isError": {"type": "boolean"}
                        }
                    },
                    "id": {"type": "string"}
                }
            },
            "ToolListResponse": {
                "type": "object",
                "properties": {
                    "jsonrpc": {"type": "string"},
                    "result": {
                        "type": "object",
                        "properties": {
                            "tools": {
                                "type": "array",
                                "items": {"$ref": "#/components/schemas/ToolMetadata"}
                            }
                        }
                    }
                }
            },
            "ToolMetadata": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "description": {"type": "string"},
                    "inputSchema": {"type": "object"}
                }
            }
        }
        
        # Add parameter schemas for each tool
        for tool_name, sig_info in self.extractor.method_signatures.items():
            schema_name = f"{self._to_pascal_case(tool_name)}Parameters"
            schemas[schema_name] = self._generate_parameter_schema(sig_info['parameters'])
            
        return schemas
        
    def _generate_parameter_schema(self, parameters: Dict) -> Dict[str, Any]:
        """Generate JSON schema for tool parameters."""
        if not parameters:
            return {"type": "object", "properties": {}}
            
        schema = {
            "type": "object",
            "properties": {},
            "required": []
        }
        
        for param_name, param_info in parameters.items():
            # Convert Python type to JSON schema type
            json_type = self._python_type_to_json_type(param_info['type'])
            
            param_schema = {"type": json_type}
            if param_info['description']:
                param_schema["description"] = param_info['description']
                
            if param_info['default'] is not None:
                param_schema["default"] = param_info['default']
                
            schema["properties"][param_name] = param_schema
            
            if param_info['required']:
                schema["required"].append(param_name)
                
        return schema
        
    def _python_type_to_json_type(self, python_type: str) -> str:
        """Convert Python type annotation to JSON schema type."""
        type_mapping = {
            'str': 'string',
            'int': 'integer', 
            'float': 'number',
            'bool': 'boolean',
            'list': 'array',
            'dict': 'object',
            'Any': 'string'  # Default to string for Any type
        }
        
        # Handle complex types
        if 'Optional' in python_type or 'Union' in python_type:
            # Extract the base type from Optional[Type] or Union[Type, None]
            base_type = python_type.replace('Optional[', '').replace(']', '').replace('Union[', '').split(',')[0].strip()
            return type_mapping.get(base_type, 'string')
            
        return type_mapping.get(python_type, 'string')
        
    def _to_pascal_case(self, snake_str: str) -> str:
        """Convert snake_case to PascalCase."""
        return ''.join(word.capitalize() for word in snake_str.split('_'))


def main():
    """Generate API documentation."""
    print("🚀 Starting API Documentation Generation...")
    
    # Create output directory
    output_dir = Path("docs/api")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Extract tool information
    extractor = ToolDocumentationExtractor()
    extractor.discover_and_analyze_tools()
    
    # Generate markdown documentation
    print("📝 Generating Markdown documentation...")
    markdown_gen = MarkdownDocumentationGenerator(extractor)
    markdown_content = markdown_gen.generate_full_documentation()
    
    # Write markdown file
    markdown_file = output_dir / "tools.md"
    with open(markdown_file, 'w', encoding='utf-8') as f:
        f.write(markdown_content)
    print(f"✅ Markdown documentation saved to: {markdown_file}")
    
    # Generate OpenAPI specification
    print("🔧 Generating OpenAPI specification...")
    openapi_gen = OpenAPIGenerator(extractor)
    openapi_spec = openapi_gen.generate_openapi_spec()
    
    # Write OpenAPI file
    openapi_file = output_dir / "openapi.json"
    with open(openapi_file, 'w', encoding='utf-8') as f:
        json.dump(openapi_spec, f, indent=2)
    print(f"✅ OpenAPI specification saved to: {openapi_file}")
    
    # Generate summary
    tool_count = len(extractor.tools_metadata)
    categories = set(info['metadata'].category for info in extractor.tools_metadata.values())
    
    print(f"""
📊 Documentation Generation Complete!

📈 Statistics:
   • {tool_count} tools documented
   • {len(categories)} categories: {', '.join(sorted(categories))}
   • Files generated: {markdown_file.name}, {openapi_file.name}

🎯 Next Steps:
   1. Review generated documentation at: {markdown_file}
   2. Use OpenAPI spec for client SDK generation: {openapi_file}
   3. Integrate with documentation website or API portal
   4. Set up automated regeneration in CI/CD pipeline

💡 Usage:
   • Host markdown on GitHub Pages or documentation platform
   • Import OpenAPI spec into Swagger UI, Postman, or API tools
   • Generate client SDKs using OpenAPI generators
   • Use for integration guides and developer onboarding
""")


if __name__ == "__main__":
    main()