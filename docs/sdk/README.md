# MCP Server for Splunk - Client SDK Development

This directory contains comprehensive resources for developing and using client SDKs for the MCP Server for Splunk.

## Overview

The MCP Server for Splunk provides client SDKs in multiple programming languages, all generated from our OpenAPI 3.0 specification. These SDKs enable developers to integrate Splunk operations seamlessly into their applications.

## Available SDKs

| Language | Status | Package Manager | Installation | Documentation |
|----------|--------|-----------------|--------------|---------------|
| **Python** | ✅ Ready | PyPI | `pip install splunk-mcp-client` | [Python SDK Guide](./python/README.md) |
| **TypeScript** | ✅ Ready | npm | `npm install splunk-mcp-client` | [TypeScript SDK Guide](./typescript/README.md) |
| **JavaScript** | ✅ Ready | npm | `npm install splunk-mcp-client` | [JavaScript SDK Guide](./javascript/README.md) |
| **Go** | ✅ Ready | Go modules | `go get github.com/.../sdk/go` | [Go SDK Guide](./go/README.md) |
| **Java** | ✅ Ready | Maven Central | See Maven/Gradle | [Java SDK Guide](./java/README.md) |
| **C#** | ✅ Ready | NuGet | `dotnet add package` | [C# SDK Guide](./csharp/README.md) |

## Quick Start

### 1. Choose Your Language

Select your preferred programming language from the table above.

### 2. Install the SDK

Follow the installation instructions for your chosen language.

### 3. Configure Connection

```python
# Python example
from splunk_mcp_client import McpClient
from splunk_mcp_client.configuration import Configuration

config = Configuration(host="http://localhost:8001/mcp")
client = McpClient(configuration=config)
```

### 4. Execute Tools

```python
# Check Splunk health
result = client.tools_api.tools_call_post({
    "jsonrpc": "2.0",
    "method": "tools/call",
    "params": {
        "name": "get_splunk_health",
        "arguments": {}
    },
    "id": "1"
})
```

## SDK Features

All SDKs provide consistent functionality:

### Core Features
- ✅ **20+ Splunk Tools** - Complete coverage of all MCP tools
- ✅ **Type Safety** - Strong typing for all API interactions
- ✅ **Error Handling** - Comprehensive error handling and validation
- ✅ **Authentication** - Support for various authentication methods
- ✅ **Async Support** - Non-blocking operations where applicable

### Tool Categories

#### Admin Tools
- `get_configurations` - Retrieve Splunk configuration settings
- `list_apps` - List installed Splunk applications  
- `list_users` - List Splunk users and properties
- `manage_apps` - Enable, disable, or restart applications

#### Health & Monitoring
- `get_splunk_health` - Check server connectivity and status
- `get_latest_feature_health` - Monitor feature health issues

#### Search & Analytics
- `run_oneshot_search` - Execute immediate searches
- `run_splunk_search` - Complex searches with progress tracking
- `list_saved_searches` - Manage saved search inventory
- `create_saved_search` - Create new saved searches
- `execute_saved_search` - Run existing saved searches
- `get_saved_search_details` - Get detailed configurations
- `update_saved_search` - Modify existing searches
- `delete_saved_search` - Remove saved searches

#### Data Discovery
- `list_indexes` - Enumerate accessible data indexes
- `list_sources` - Discover available data sources
- `list_sourcetypes` - List available sourcetypes

#### Storage Management
- `list_kvstore_collections` - List KV Store collections
- `get_kvstore_data` - Retrieve stored data
- `create_kvstore_collection` - Create new collections

## Architecture

### OpenAPI-First Design

All SDKs are generated from a single OpenAPI 3.0 specification:

```
docs/api/openapi.json  →  Code Generation  →  Language SDKs
```

This ensures:
- **Consistency** across all languages
- **Accuracy** with server implementation
- **Automatic Updates** when APIs evolve
- **Type Safety** from specification to code

### SDK Structure

Each generated SDK follows a consistent structure:

```
client-{language}/
├── api/              # API client classes
├── models/           # Data models and DTOs
├── docs/             # Generated documentation
├── examples/         # Usage examples
├── tests/            # Unit tests
└── README.md         # Language-specific guide
```

## Development Workflow

### 1. Specification Updates

When the OpenAPI specification is updated:

```bash
# Regenerate all SDKs
python scripts/generate_client_sdks.py

# Or specific language
python scripts/generate_client_sdks.py --languages python typescript
```

### 2. Testing

Each SDK includes comprehensive testing:

```bash
# Python
cd sdk/client-python && python -m pytest

# TypeScript
cd sdk/client-typescript && npm test

# Go
cd sdk/client-go && go test ./...
```

### 3. Publishing

SDKs are published to their respective package managers:

- **Python**: PyPI
- **TypeScript/JavaScript**: npm
- **Go**: Go modules
- **Java**: Maven Central
- **C#**: NuGet

## Integration Examples

### Enterprise Integration

```python
# Enterprise monitoring dashboard
from splunk_mcp_client import McpClient

class SplunkMonitor:
    def __init__(self, mcp_host):
        self.client = McpClient(host=mcp_host)
    
    def get_system_health(self):
        health = self.client.get_splunk_health()
        features = self.client.get_latest_feature_health()
        return {
            "server": health,
            "features": features
        }
    
    def run_analytics(self, query):
        return self.client.run_oneshot_search(
            query=query,
            earliest_time="-24h",
            max_results=1000
        )
```

### CI/CD Integration

```yaml
# GitHub Actions example
- name: Splunk Health Check
  run: |
    python -c "
    from splunk_mcp_client import McpClient
    client = McpClient(host='${{ secrets.MCP_HOST }}')
    health = client.get_splunk_health()
    assert health['status'] == 'connected'
    "
```

### Microservices Integration

```typescript
// Node.js microservice
import { McpClient } from 'splunk-mcp-client';

export class SplunkService {
    private client: McpClient;
    
    constructor(mcpHost: string) {
        this.client = new McpClient({ host: mcpHost });
    }
    
    async searchLogs(query: string, timeRange: string = "-1h") {
        return await this.client.runOneshotSearch({
            query,
            earliest_time: timeRange,
            latest_time: "now"
        });
    }
}
```

## Best Practices

### Error Handling

```python
try:
    result = client.tools_api.tools_call_post(request)
    if result.result.is_error:
        # Handle tool-level errors
        logger.error(f"Tool failed: {result.result.content}")
    else:
        # Process successful result
        return result.result.content
except ApiException as e:
    # Handle API-level errors
    logger.error(f"API call failed: {e}")
except Exception as e:
    # Handle unexpected errors
    logger.error(f"Unexpected error: {e}")
```

### Connection Management

```python
# Connection pooling and retry logic
from tenacity import retry, stop_after_attempt, wait_exponential

class SplunkClient:
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10)
    )
    def robust_call(self, tool_name, arguments):
        return self.client.tools_api.tools_call_post({
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": arguments
            },
            "id": str(uuid.uuid4())
        })
```

### Authentication

```python
# With authentication headers
config = Configuration(
    host="http://localhost:8001/mcp",
    api_key={
        'X-Splunk-Host': os.getenv('SPLUNK_HOST'),
        'X-Splunk-Username': os.getenv('SPLUNK_USERNAME'),
        'X-Splunk-Password': os.getenv('SPLUNK_PASSWORD')
    }
)
```

## Support & Contributing

### Getting Help

1. **Documentation**: Language-specific guides in `sdk/{language}/`
2. **Examples**: Comprehensive examples in each SDK
3. **Issues**: GitHub Issues for bug reports and feature requests
4. **Community**: Discussion forums and chat channels

### Contributing

1. **Fork** the repository
2. **Create** a feature branch
3. **Update** the OpenAPI specification if needed
4. **Regenerate** SDKs using the generation script
5. **Test** your changes across relevant languages
6. **Submit** a pull request

### Development Setup

```bash
# Clone repository
git clone https://github.com/your-org/mcp-server-for-splunk.git
cd mcp-server-for-splunk

# Install OpenAPI Generator
npm install @openapitools/openapi-generator-cli -g

# Generate SDKs
python scripts/generate_client_sdks.py

# Test specific SDK
cd sdk/client-python && python -m pytest
```

## Roadmap

### Current Status
- ✅ Core SDK generation framework
- ✅ Python, TypeScript, JavaScript SDKs
- ✅ Go, Java, C# SDKs
- ✅ Comprehensive documentation
- ✅ Testing frameworks

### Upcoming Features
- 🔄 Auto-publishing to package managers
- 🔄 SDK versioning and changelog automation
- 🔄 Advanced authentication methods
- 🔄 Streaming API support
- 🔄 SDK performance optimization

### Future Enhancements
- 📋 Additional language support (Rust, Swift, Kotlin)
- 📋 GraphQL API integration
- 📋 Real-time notifications
- 📋 Advanced caching mechanisms
- 📋 SDK analytics and telemetry

## License

All SDKs are released under the MIT License. See [LICENSE](../../LICENSE) for details. 