# Splunk MCP Client Examples (TypeScript)

This guide provides practical examples for using the TypeScript client SDK with the MCP Server for Splunk.

## Quick Start

### Installation

```bash
npm install splunk-mcp-client
# or  
yarn add splunk-mcp-client
```

### Basic Setup

```typescript
import { DefaultApi, Configuration, ToolCallRequest } from 'splunk-mcp-client';

// Configure the client
const configuration = new Configuration({
  basePath: 'http://localhost:8001/mcp'  // Your MCP server endpoint
});

// Create API client
const apiClient = new DefaultApi(configuration);
```

### Helper Function for Tool Calls

```typescript
interface MCPToolResult {
  status: string;
  [key: string]: any;
}

async function callMCPTool(toolName: string, arguments_: Record<string, any> = {}): Promise<MCPToolResult | null> {
  try {
    const toolRequest: ToolCallRequest = {
      jsonrpc: "2.0",
      method: "tools/call",
      params: {
        name: toolName,
        arguments: arguments_
      },
      id: "1"
    };

    const response = await apiClient.toolsCallPost(toolRequest);
    
    // Parse the JSON response
    const result = JSON.parse(response.result.content[0]);
    return result;
  } catch (error) {
    console.error(`Exception when calling ${toolName}:`, error);
    return null;
  }
}
```

## Health & Monitoring

### Check Splunk Health

```typescript
interface HealthStatus {
  status: string;
  version?: string;
  server_name?: string;
  error?: string;
}

async function checkSplunkHealth(): Promise<boolean> {
  const result = await callMCPTool("get_splunk_health") as HealthStatus;
  
  if (result?.status === "connected") {
    console.log("✅ Splunk is healthy");
    console.log(`Version: ${result.version}`);
    console.log(`Server: ${result.server_name}`);
    return true;
  } else {
    console.log("❌ Splunk health check failed");
    if (result?.error) {
      console.log(`Error: ${result.error}`);
    }
    return false;
  }
}

// Usage
checkSplunkHealth();
```

For more comprehensive examples, see the Python examples which can be easily adapted to TypeScript.
