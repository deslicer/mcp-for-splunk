# Splunk MCP Client SDKs

This directory contains auto-generated client SDKs for the MCP Server for Splunk in multiple programming languages.

## Available SDKs

### 🐍 Python SDK
- **Location**: `client-python/`
- **Package**: `splunk_mcp_client`
- **Installation**: `pip install ./client-python`
- **Examples**: See `client-python/SPLUNK_MCP_EXAMPLES.md`

### 📘 TypeScript SDK  
- **Location**: `client-typescript/`
- **Package**: `splunk-mcp-client`
- **Installation**: `npm install ./client-typescript`
- **Examples**: See `client-typescript/SPLUNK_MCP_EXAMPLES.md`

## Quick Start

### Python
```python
import splunk_mcp_client
from splunk_mcp_client.rest import ApiException

# Configure client
configuration = splunk_mcp_client.Configuration(
    host="http://localhost:8001/mcp"
)

# Create API client
with splunk_mcp_client.ApiClient(configuration) as api_client:
    api_instance = splunk_mcp_client.DefaultApi(api_client)
    
    # Call MCP tool
    tool_request = splunk_mcp_client.ToolCallRequest(
        jsonrpc="2.0",
        method="tools/call",
        params={"name": "get_splunk_health"},
        id="1"
    )
    
    response = api_instance.tools_call_post(tool_request)
    print(response)
```

### TypeScript
```typescript
import { DefaultApi, Configuration, ToolCallRequest } from 'splunk-mcp-client';

// Configure client
const config = new Configuration({
  basePath: 'http://localhost:8001/mcp'
});

const apiClient = new DefaultApi(config);

// Call MCP tool
const toolRequest: ToolCallRequest = {
  jsonrpc: "2.0",
  method: "tools/call",
  params: { name: "get_splunk_health" },
  id: "1"
};

const response = await apiClient.toolsCallPost(toolRequest);
console.log(response);
```

## Available MCP Tools

The SDKs provide access to all MCP Server for Splunk tools:

### Health & Monitoring
- `get_splunk_health` - Check Splunk server health and connectivity
- `get_latest_feature_health` - Get degraded Splunk features

### Search Operations
- `run_oneshot_search` - Execute one-shot searches
- `run_splunk_search` - Execute search jobs with progress tracking
- `list_saved_searches` - List available saved searches
- `create_saved_search` - Create new saved searches
- `execute_saved_search` - Run existing saved searches
- `update_saved_search` - Modify saved search configurations
- `delete_saved_search` - Remove saved searches

### Administrative Tasks
- `list_apps` - List installed Splunk apps
- `manage_apps` - Enable, disable, or restart apps
- `list_users` - List Splunk users and roles
- `get_configurations` - Access Splunk configuration files

### Data Discovery
- `list_indexes` - Enumerate available indexes
- `list_sources` - Discover data sources
- `list_sourcetypes` - List available sourcetypes

### KV Store Operations
- `list_kvstore_collections` - List KV Store collections
- `create_kvstore_collection` - Create new collections
- `get_kvstore_data` - Query collection data

## SDK Generation

These SDKs are automatically generated from the OpenAPI specification using OpenAPI Generator. To regenerate:

```bash
# From project root
python scripts/generate_client_sdks.py --languages python typescript
```

## Development

### Testing Python SDK
```bash
cd client-python
pip install -e .
python -m pytest test/
```

### Testing TypeScript SDK
```bash
cd client-typescript
npm install
npm test
```

## Integration Examples

See the comprehensive examples in each SDK directory:
- **Python**: `client-python/SPLUNK_MCP_EXAMPLES.md` - Complete examples for Python development
- **TypeScript**: `client-typescript/SPLUNK_MCP_EXAMPLES.md` - Examples for Node.js and React

## API Documentation

For detailed API documentation, see:
- OpenAPI Specification: `../docs/api/openapi.json`
- Tools Reference: `../docs/api/tools.md`
- Main Documentation: `../docs/sdk/README.md`

## Contributing

When adding new tools to the MCP server:
1. Update the server implementation
2. Regenerate OpenAPI specification: `python scripts/generate_api_docs.py`
3. Regenerate SDKs: `python scripts/generate_client_sdks.py`
4. Update examples and documentation
5. Test all SDK languages

## Support

For issues with the SDKs:
- Check the main project documentation in `../docs/`
- Review examples in each SDK directory
- File issues in the main project repository

---

**Note**: These SDKs are auto-generated. Do not edit the generated code directly. Instead, modify the OpenAPI specification and regenerate the SDKs. 