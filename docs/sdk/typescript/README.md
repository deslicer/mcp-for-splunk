# Splunk MCP Client - TypeScript SDK

Official TypeScript client SDK for the MCP Server for Splunk.

## Installation

```bash
npm install splunk-mcp-client
# or
yarn add splunk-mcp-client
```

## Quick Start

```typescript
import { Configuration, ToolsApi } from 'splunk-mcp-client';

// Configure the client
const config = new Configuration({
    basePath: 'http://localhost:8001/mcp'
});

// Create client instance
const toolsApi = new ToolsApi(config);

// Check Splunk health
const health = await toolsApi.toolsCallPost({
    jsonrpc: "2.0",
    method: "tools/call",
    params: {
        name: "get_splunk_health",
        arguments: {}
    },
    id: "1"
});

console.log('Splunk health:', health.result);
```

## Configuration

### Basic Configuration

```typescript
import { Configuration } from 'splunk-mcp-client';

const config = new Configuration({
    basePath: 'http://localhost:8001/mcp',
    fetchApi: fetch, // Custom fetch implementation
});
```

### With Authentication

```typescript
const config = new Configuration({
    basePath: 'http://localhost:8001/mcp',
    headers: {
        'X-Splunk-Host': process.env.SPLUNK_HOST,
        'X-Splunk-Username': process.env.SPLUNK_USERNAME,
        'X-Splunk-Password': process.env.SPLUNK_PASSWORD
    }
});
```

## API Examples

### Search Operations

```typescript
import { ToolsApi, ToolCallRequest } from 'splunk-mcp-client';

class SplunkSearchService {
    constructor(private toolsApi: ToolsApi) {}

    async runOneshotSearch(query: string, earliestTime: string = '-15m'): Promise<any> {
        const request: ToolCallRequest = {
            jsonrpc: "2.0",
            method: "tools/call",
            params: {
                name: "run_oneshot_search",
                arguments: {
                    query,
                    earliest_time: earliestTime,
                    latest_time: "now",
                    max_results: 100
                }
            },
            id: `search_${Date.now()}`
        };

        const response = await this.toolsApi.toolsCallPost(request);
        
        if (response.result.isError) {
            throw new Error(`Search failed: ${response.result.content}`);
        }
        
        return JSON.parse(response.result.content[0].text);
    }

    async listSavedSearches(): Promise<any> {
        const request: ToolCallRequest = {
            jsonrpc: "2.0",
            method: "tools/call",
            params: {
                name: "list_saved_searches",
                arguments: {}
            },
            id: "list_searches"
        };

        const response = await this.toolsApi.toolsCallPost(request);
        return JSON.parse(response.result.content[0].text);
    }
}
```

### Admin Operations

```typescript
class SplunkAdminService {
    constructor(private toolsApi: ToolsApi) {}

    async getApps(): Promise<any> {
        const response = await this.toolsApi.toolsCallPost({
            jsonrpc: "2.0",
            method: "tools/call",
            params: {
                name: "list_apps",
                arguments: {}
            },
            id: "get_apps"
        });

        return JSON.parse(response.result.content[0].text);
    }

    async getConfiguration(confFile: string, stanza?: string): Promise<any> {
        const response = await this.toolsApi.toolsCallPost({
            jsonrpc: "2.0",
            method: "tools/call",
            params: {
                name: "get_configurations",
                arguments: {
                    conf_file: confFile,
                    stanza
                }
            },
            id: "get_config"
        });

        return JSON.parse(response.result.content[0].text);
    }
}
```

## Error Handling

```typescript
import { ResponseError } from 'splunk-mcp-client';

try {
    const result = await toolsApi.toolsCallPost(request);
    
    if (result.result.isError) {
        console.error('Tool execution failed:', result.result.content);
    } else {
        console.log('Success:', result.result.content);
    }
} catch (error) {
    if (error instanceof ResponseError) {
        console.error('HTTP error:', error.response.status, error.response.statusText);
    } else {
        console.error('Unexpected error:', error);
    }
}
```

## Node.js Integration

```typescript
// server.ts
import express from 'express';
import { Configuration, ToolsApi } from 'splunk-mcp-client';

const app = express();
const config = new Configuration({
    basePath: process.env.MCP_HOST || 'http://localhost:8001/mcp'
});
const toolsApi = new ToolsApi(config);

app.get('/health', async (req, res) => {
    try {
        const health = await toolsApi.toolsCallPost({
            jsonrpc: "2.0",
            method: "tools/call",
            params: {
                name: "get_splunk_health",
                arguments: {}
            },
            id: "health_check"
        });

        res.json(JSON.parse(health.result.content[0].text));
    } catch (error) {
        res.status(500).json({ error: error.message });
    }
});

app.listen(3000, () => {
    console.log('Server running on port 3000');
});
```

## React Integration

```tsx
// hooks/useSplunkMCP.ts
import { useState, useEffect } from 'react';
import { Configuration, ToolsApi } from 'splunk-mcp-client';

export const useSplunkMCP = (host: string) => {
    const [toolsApi, setToolsApi] = useState<ToolsApi | null>(null);
    const [isConnected, setIsConnected] = useState(false);

    useEffect(() => {
        const config = new Configuration({ basePath: host });
        const api = new ToolsApi(config);
        setToolsApi(api);

        // Test connection
        api.toolsCallPost({
            jsonrpc: "2.0",
            method: "tools/call",
            params: {
                name: "get_splunk_health",
                arguments: {}
            },
            id: "connection_test"
        })
        .then(() => setIsConnected(true))
        .catch(() => setIsConnected(false));
    }, [host]);

    return { toolsApi, isConnected };
};

// components/SplunkDashboard.tsx
import React from 'react';
import { useSplunkMCP } from '../hooks/useSplunkMCP';

export const SplunkDashboard: React.FC = () => {
    const { toolsApi, isConnected } = useSplunkMCP('http://localhost:8001/mcp');
    const [apps, setApps] = useState([]);

    useEffect(() => {
        if (toolsApi && isConnected) {
            toolsApi.toolsCallPost({
                jsonrpc: "2.0",
                method: "tools/call",
                params: {
                    name: "list_apps",
                    arguments: {}
                },
                id: "get_apps"
            })
            .then(response => {
                const appData = JSON.parse(response.result.content[0].text);
                setApps(appData.apps);
            });
        }
    }, [toolsApi, isConnected]);

    return (
        <div>
            <h1>Splunk Dashboard</h1>
            <p>Status: {isConnected ? 'Connected' : 'Disconnected'}</p>
            <ul>
                {apps.map(app => (
                    <li key={app.name}>{app.label}</li>
                ))}
            </ul>
        </div>
    );
};
```

## Testing

```typescript
// tests/splunk-client.test.ts
import { Configuration, ToolsApi } from 'splunk-mcp-client';

describe('SplunkMCPClient', () => {
    let toolsApi: ToolsApi;

    beforeEach(() => {
        const config = new Configuration({
            basePath: 'http://localhost:8001/mcp'
        });
        toolsApi = new ToolsApi(config);
    });

    it('should check Splunk health', async () => {
        const response = await toolsApi.toolsCallPost({
            jsonrpc: "2.0",
            method: "tools/call",
            params: {
                name: "get_splunk_health",
                arguments: {}
            },
            id: "test_health"
        });

        expect(response.result.isError).toBe(false);
        const health = JSON.parse(response.result.content[0].text);
        expect(health).toHaveProperty('status');
    });

    it('should list available tools', async () => {
        const response = await toolsApi.toolsListPost();
        
        expect(response.result.tools).toBeDefined();
        expect(response.result.tools.length).toBeGreaterThan(0);
    });
});
```

## Contributing

See the main project [Contributing Guide](../../../CONTRIBUTING.md) for details.

## License

MIT License - see [LICENSE](../../../LICENSE) for details. 