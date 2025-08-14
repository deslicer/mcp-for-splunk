# MCP Server for Splunk - API Documentation

This directory contains comprehensive API documentation automatically generated from the MCP Server for Splunk tools.

## 📚 Generated Documentation

### 1. [**tools.md**](./tools.md) - Complete API Reference
A comprehensive markdown document providing detailed documentation for all 20 MCP tools:

- **Table of Contents** with category organization
- **Overview** with tool statistics and authentication info
- **Tools by Category** with quick reference
- **Detailed Tool Documentation** with parameters, return values, and examples
- **API Schemas** and error handling patterns
- **Usage Examples** for each tool

**Features:**
- ✅ **Complete Parameter Documentation** - Type, required/optional, defaults, descriptions
- ✅ **Return Value Specifications** - Clear documentation of response formats
- ✅ **Usage Examples** - Realistic code examples for each tool
- ✅ **Source Information** - Module paths and line numbers for reference
- ✅ **Cross-References** - Internal linking and navigation

### 2. [**openapi.json**](./openapi.json) - OpenAPI 3.0 Specification
A machine-readable API specification suitable for:

- **SDK Generation** - Generate client libraries for any language
- **API Testing** - Import into Postman, Insomnia, or other API tools
- **Documentation Hosting** - Use with Swagger UI or similar platforms
- **Integration** - API contract for automated testing and validation

**Features:**
- ✅ **Complete MCP Protocol** - All tool call endpoints
- ✅ **Parameter Schemas** - JSON Schema definitions for each tool
- ✅ **Request/Response Models** - Standardized API contracts
- ✅ **Tool Enumeration** - All available tools listed in schemas

## 🔧 Generated Content Overview

### Tool Categories (20 Total)

| Category | Count | Description |
|----------|-------|-------------|
| **Admin** | 4 | Application and user management, configuration access |
| **Health** | 2 | System health monitoring and connectivity checks |
| **KV Store** | 3 | NoSQL data storage operations and collection management |
| **Metadata** | 3 | Data discovery for indexes, sources, and sourcetypes |
| **Search** | 8 | Search execution, saved search management, and results |

### Documentation Quality

- **100% Tool Coverage** - All 20 tools documented
- **Parameter Analysis** - Method signatures automatically extracted
- **Type Information** - Complete type annotations and validation
- **Example Generation** - Realistic usage examples for each tool
- **Source Mapping** - Links back to source code for developers

## 🚀 Usage Guide

### For Developers

1. **Quick Reference** - Use `tools.md` for understanding tool capabilities
2. **Implementation** - Reference parameter tables and examples
3. **Integration** - Use OpenAPI spec for client generation
4. **Debugging** - Source information links to actual implementation

### For API Consumers

1. **Browse Available Tools** - Review categories and descriptions
2. **Understand Parameters** - Check required vs optional parameters
3. **Test API Calls** - Use examples as starting templates
4. **Handle Responses** - Review return value documentation

### For Client SDK Development

1. **Import OpenAPI Spec** - Use `openapi.json` in code generators
2. **Generate Clients** - Create language-specific SDKs
3. **Validate Schemas** - Use JSON schemas for request validation
4. **Test Integration** - Use documented examples for testing

## 🛠️ Integration Examples

### Swagger UI Integration

```bash
# Serve documentation with Swagger UI
docker run -p 8080:8080 -e SWAGGER_JSON=/api/openapi.json \
  -v $(pwd)/docs/api/openapi.json:/api/openapi.json swaggerapi/swagger-ui
```

### Client SDK Generation (Python)

```bash
# Generate Python client from OpenAPI spec
npx @openapitools/openapi-generator-cli generate \
  -i docs/api/openapi.json \
  -g python \
  -o client-sdk-python \
  --additional-properties=packageName=splunk_mcp_client
```

### Client SDK Generation (TypeScript)

```bash
# Generate TypeScript client
npx @openapitools/openapi-generator-cli generate \
  -i docs/api/openapi.json \
  -g typescript-axios \
  -o client-sdk-typescript \
  --additional-properties=npmName=splunk-mcp-client
```

### Postman Collection Import

1. Open Postman
2. Import → Upload Files
3. Select `openapi.json`
4. Configure base URL: `http://localhost:8001/mcp`

## 📊 Documentation Statistics

- **Tools Documented**: 20
- **Categories**: 5 (Admin, Health, KV Store, Metadata, Search)
- **Parameters Analyzed**: 60+ unique parameters across all tools
- **Method Signatures**: Complete type information extracted
- **Examples Generated**: Custom examples for each tool
- **Total Documentation**: 1,251 lines of comprehensive markdown

## 🔄 Regeneration

The documentation is automatically generated from tool metadata and source code. To regenerate:

```bash
# Regenerate all API documentation
uv run python scripts/generate_api_docs.py

# Generated files:
# - docs/api/tools.md (comprehensive markdown)
# - docs/api/openapi.json (OpenAPI specification)
```

### Automation

Consider adding to CI/CD pipeline:

```yaml
# .github/workflows/docs.yml
- name: Generate API Documentation
  run: |
    uv run python scripts/generate_api_docs.py
    git add docs/api/
    git commit -m "docs: update API documentation" || exit 0
```

## 📈 Benefits Achieved

✅ **Professional Documentation** - Enterprise-ready API reference
✅ **Developer Experience** - Clear examples and parameter descriptions
✅ **SDK Generation Ready** - OpenAPI spec for automated client creation
✅ **Maintenance Automation** - Regenerates from source code changes
✅ **Integration Support** - Multiple output formats for different use cases
✅ **Quality Assurance** - Comprehensive validation and type checking

## 🆘 Support

- **Tool Issues**: Reference source information in documentation
- **API Questions**: Check parameter descriptions and examples
- **Integration Help**: Use OpenAPI spec for validation
- **Updates**: Regenerate documentation after tool changes

---

*This documentation was automatically generated from tool metadata and source code analysis on 2025-07-03.*
