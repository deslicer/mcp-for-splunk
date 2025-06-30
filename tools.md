# MCP Tools Best Practices Guide

## Table of Contents
- [Overview](#overview)
- [Tool Definition Best Practices](#tool-definition-best-practices)
- [Input Schema Design](#input-schema-design)
- [Output and Content Types](#output-and-content-types)
- [Error Handling](#error-handling)
- [Tool Annotations](#tool-annotations)
- [Security Considerations](#security-considerations)
- [Performance Optimization](#performance-optimization)
- [Testing and Validation](#testing-and-validation)
- [Documentation Standards](#documentation-standards)
- [Implementation Examples](#implementation-examples)

## Overview

Tools are a core primitive in the Model Context Protocol (MCP) that allow servers to expose executable functionality to clients and LLMs. Unlike resources which are application-controlled, tools are **model-controlled**, meaning the LLM can decide when and how to invoke them during conversations.

### Key Characteristics
- Tools are invoked via JSON-RPC `tools/call` requests
- Each tool has a unique name, description, and input schema
- Tools return structured content with optional error handling
- Tools support various content types: text, images, audio, and embedded resources

## Tool Definition Best Practices

### 1. Naming Conventions
- **Use clear, descriptive names**: Choose names that immediately convey the tool's purpose
- **Follow consistent patterns**: Use verb-noun patterns like `get_weather`, `create_file`, `analyze_data`
- **Avoid abbreviations**: Prefer `calculate_sum` over `calc_sum`
- **Use snake_case**: Follow the convention established in MCP specifications

```json
// Good
{
  "name": "get_weather_forecast",
  "description": "Get detailed weather forecast for a specific location"
}

// Avoid
{
  "name": "weather",
  "description": "Weather stuff"
}
```

### 2. Comprehensive Descriptions
- **Be specific and actionable**: Clearly explain what the tool does and when to use it
- **Include context about limitations**: Mention any constraints or requirements
- **Specify expected outcomes**: Describe what type of data will be returned

```json
{
  "name": "analyze_csv",
  "description": "Analyze a CSV file and perform statistical operations like sum, average, and count on specified columns. Supports files up to 100MB with standard CSV formatting."
}
```

### 3. Tool Structure Template

```json
{
  "name": "tool_name",
  "title": "Human-Readable Tool Title",
  "description": "Detailed description of functionality and use cases",
  "inputSchema": {
    "type": "object",
    "properties": {
      // Parameter definitions
    },
    "required": ["param1", "param2"]
  },
  "outputSchema": {
    "type": "object",
    "properties": {
      // Expected output structure
    }
  },
  "annotations": {
    "title": "Tool Display Name",
    "readOnlyHint": false,
    "destructiveHint": false,
    "idempotentHint": false,
    "openWorldHint": true
  }
}
```

## Input Schema Design

### 1. Use Proper JSON Schema Types
- **String validation**: Include patterns, formats, and length constraints
- **Number validation**: Set minimum, maximum, and type constraints
- **Array handling**: Define item types and length limits
- **Object nesting**: Keep complexity manageable

```json
{
  "inputSchema": {
    "type": "object",
    "properties": {
      "location": {
        "type": "string",
        "description": "City name or coordinates (lat,lng)",
        "pattern": "^[a-zA-Z\\s,.-]+$|^-?\\d+\\.\\d+,-?\\d+\\.\\d+$",
        "minLength": 2,
        "maxLength": 100
      },
      "days": {
        "type": "integer",
        "description": "Number of forecast days",
        "minimum": 1,
        "maximum": 14,
        "default": 7
      },
      "units": {
        "type": "string",
        "enum": ["metric", "imperial", "kelvin"],
        "description": "Temperature units",
        "default": "metric"
      }
    },
    "required": ["location"]
  }
}
```

### 2. Parameter Best Practices
- **Provide clear descriptions**: Each parameter should have a meaningful description
- **Set reasonable defaults**: Include default values where appropriate
- **Use enums for limited options**: Constrain choices with enum values
- **Validate input ranges**: Set min/max values for numeric inputs

### 3. Required vs Optional Parameters
- **Minimize required parameters**: Only mark truly essential parameters as required
- **Provide sensible defaults**: Optional parameters should have reasonable defaults
- **Document parameter interactions**: Explain how parameters work together

## Output and Content Types

### 1. Content Type Selection

#### Text Content
```json
{
  "type": "text",
  "text": "Structured text response with clear formatting"
}
```

#### Image Content (Base64)
```json
{
  "type": "image",
  "data": "base64-encoded-image-data",
  "mimeType": "image/png"
}
```

#### Audio Content (Base64)
```json
{
  "type": "audio",
  "data": "base64-encoded-audio-data",
  "mimeType": "audio/wav"
}
```

#### Embedded Resources
```json
{
  "type": "resource",
  "resource": {
    "uri": "file:///path/to/resource",
    "title": "Resource Title",
    "mimeType": "text/plain",
    "text": "Resource content"
  }
}
```

#### Resource Links
```json
{
  "type": "resource_link",
  "uri": "file:///path/to/resource",
  "name": "resource.txt",
  "description": "Link to external resource",
  "mimeType": "text/plain"
}
```

### 2. Structured Content with Output Schemas
Use output schemas to validate and structure returned data:

```json
{
  "outputSchema": {
    "type": "object",
    "properties": {
      "temperature": {
        "type": "number",
        "description": "Temperature in specified units"
      },
      "conditions": {
        "type": "string",
        "description": "Weather conditions description"
      },
      "humidity": {
        "type": "number",
        "minimum": 0,
        "maximum": 100,
        "description": "Humidity percentage"
      }
    },
    "required": ["temperature", "conditions"]
  }
}
```

### 3. Return Multiple Content Types
Tools can return multiple content items in a single response:

```json
{
  "content": [
    {
      "type": "text",
      "text": "Analysis complete. Temperature: 22°C, Humidity: 65%"
    },
    {
      "type": "image",
      "data": "base64-weather-chart",
      "mimeType": "image/png"
    }
  ],
  "structuredContent": {
    "temperature": 22,
    "humidity": 65,
    "conditions": "partly cloudy"
  }
}
```

## Error Handling

### 1. Proper Error Response Structure
Always include the `isError` flag when tool execution fails:

```typescript
try {
  const result = await performOperation();
  return {
    content: [
      {
        type: "text",
        text: `Operation successful: ${result}`
      }
    ]
  };
} catch (error) {
  return {
    isError: true,
    content: [
      {
        type: "text",
        text: `Error: ${error.message}`
      }
    ]
  };
}
```

### 2. Error Types and Handling

#### Input Validation Errors
```json
{
  "isError": true,
  "content": [
    {
      "type": "text",
      "text": "Invalid input: 'location' parameter is required and must be a non-empty string"
    }
  ]
}
```

#### External Service Errors
```json
{
  "isError": true,
  "content": [
    {
      "type": "text",
      "text": "Failed to fetch weather data: API rate limit exceeded. Please try again in 60 seconds."
    }
  ]
}
```

#### Business Logic Errors
```json
{
  "isError": true,
  "content": [
    {
      "type": "text",
      "text": "Cannot delete file: File is currently in use by another process"
    }
  ]
}
```

### 3. Error Recovery Guidance
Provide actionable error messages that help users understand how to fix issues:

```typescript
if (!fs.existsSync(filePath)) {
  return {
    isError: true,
    content: [
      {
        type: "text",
        text: `File not found: ${filePath}. Please check the file path and ensure the file exists. Use absolute paths for better reliability.`
      }
    ]
  };
}
```

## Tool Annotations

### 1. Annotation Types and Usage

#### readOnlyHint
Indicates tools that don't modify their environment:

```json
{
  "annotations": {
    "title": "Weather Information",
    "readOnlyHint": true,
    "openWorldHint": true
  }
}
```

#### destructiveHint
Marks tools that may perform destructive operations:

```json
{
  "annotations": {
    "title": "Delete File",
    "readOnlyHint": false,
    "destructiveHint": true,
    "idempotentHint": true,
    "openWorldHint": false
  }
}
```

#### idempotentHint
Indicates tools that can be safely called multiple times:

```json
{
  "annotations": {
    "title": "Create Directory",
    "readOnlyHint": false,
    "destructiveHint": false,
    "idempotentHint": true,
    "openWorldHint": false
  }
}
```

#### openWorldHint
Indicates interaction with external systems:

```json
{
  "annotations": {
    "title": "Web Search",
    "readOnlyHint": true,
    "openWorldHint": true
  }
}
```

### 2. Annotation Combinations

| Tool Type | readOnly | destructive | idempotent | openWorld | Example |
|-----------|----------|-------------|------------|-----------|---------|
| Data Query | true | false | true | false | `get_database_record` |
| Web API | true | false | true | true | `search_web` |
| File Creation | false | false | true | false | `create_directory` |
| File Deletion | false | true | true | false | `delete_file` |
| Data Analysis | true | false | true | false | `analyze_csv` |

## Security Considerations

### 1. Input Validation
- **Sanitize all inputs**: Never trust user-provided data
- **Validate file paths**: Prevent directory traversal attacks
- **Check permissions**: Ensure proper access controls
- **Rate limiting**: Implement appropriate throttling

```typescript
function validateFilePath(path: string): boolean {
  // Prevent directory traversal
  if (path.includes('..') || path.includes('~')) {
    return false;
  }
  
  // Ensure path is within allowed directories
  const allowedPaths = ['/tmp', '/workspace'];
  return allowedPaths.some(allowed => path.startsWith(allowed));
}
```

### 2. Authentication and Authorization
- **Validate credentials**: Check authentication tokens
- **Implement role-based access**: Control tool access by user role
- **Audit tool usage**: Log tool invocations for security monitoring

### 3. Data Protection
- **Encrypt sensitive data**: Protect data in transit and at rest
- **Avoid logging secrets**: Don't include sensitive data in logs
- **Sanitize outputs**: Remove sensitive information from responses

## Performance Optimization

### 1. Response Time Optimization
- **Cache frequently accessed data**: Implement intelligent caching
- **Use connection pooling**: Reuse database/API connections
- **Implement timeouts**: Set reasonable operation timeouts
- **Optimize data processing**: Use efficient algorithms and data structures

### 2. Resource Management
- **Stream large data**: Use streaming for large files/datasets
- **Limit response sizes**: Prevent memory exhaustion
- **Clean up resources**: Properly dispose of file handles, connections

```typescript
async function processLargeFile(filePath: string): Promise<CallToolResult> {
  const maxSize = 10 * 1024 * 1024; // 10MB limit
  const stats = await fs.promises.stat(filePath);
  
  if (stats.size > maxSize) {
    return {
      isError: true,
      content: [
        {
          type: "text",
          text: `File too large: ${stats.size} bytes. Maximum size is ${maxSize} bytes.`
        }
      ]
    };
  }
  
  // Process file...
}
```

### 3. Pagination Support
Implement pagination for tools that return large datasets:

```json
{
  "inputSchema": {
    "type": "object",
    "properties": {
      "query": {"type": "string"},
      "page": {"type": "integer", "minimum": 1, "default": 1},
      "pageSize": {"type": "integer", "minimum": 1, "maximum": 100, "default": 20}
    }
  }
}
```

## Testing and Validation

### 1. Unit Testing
Test each tool's core functionality:

```typescript
describe('WeatherTool', () => {
  it('should return weather data for valid location', async () => {
    const result = await weatherTool.call({
      location: 'New York',
      units: 'metric'
    });
    
    expect(result.isError).toBe(false);
    expect(result.content).toHaveLength(1);
    expect(result.content[0].type).toBe('text');
  });
  
  it('should handle invalid location gracefully', async () => {
    const result = await weatherTool.call({
      location: ''
    });
    
    expect(result.isError).toBe(true);
    expect(result.content[0].text).toContain('Invalid input');
  });
});
```

### 2. Integration Testing
Test tool interactions with external services:

```typescript
describe('WeatherTool Integration', () => {
  it('should handle API rate limiting', async () => {
    // Mock rate limit response
    mockApiResponse(429, { error: 'Rate limit exceeded' });
    
    const result = await weatherTool.call({
      location: 'New York'
    });
    
    expect(result.isError).toBe(true);
    expect(result.content[0].text).toContain('rate limit');
  });
});
```

### 3. Schema Validation
Validate input and output schemas:

```typescript
import Ajv from 'ajv';

const ajv = new Ajv();

function validateToolInput(tool: Tool, input: any): boolean {
  const validate = ajv.compile(tool.inputSchema);
  return validate(input);
}

function validateToolOutput(tool: Tool, output: any): boolean {
  if (tool.outputSchema) {
    const validate = ajv.compile(tool.outputSchema);
    return validate(output.structuredContent);
  }
  return true;
}
```

## Documentation Standards

### 1. Tool Documentation Template

```markdown
## Tool Name: get_weather_forecast

### Description
Retrieves detailed weather forecast information for a specified location using the OpenWeatherMap API.

### Parameters
- `location` (string, required): City name, coordinates (lat,lng), or zip code
- `days` (integer, optional): Number of forecast days (1-14, default: 7)
- `units` (string, optional): Temperature units ('metric'|'imperial'|'kelvin', default: 'metric')

### Returns
- Weather forecast data including temperature, conditions, humidity, and wind information
- Structured JSON data with forecast for each day
- Optional weather map image if available

### Error Conditions
- Invalid location format
- API rate limit exceeded
- Network connectivity issues
- Unsupported location (outside API coverage)

### Examples
```json
{
  "location": "New York",
  "days": 5,
  "units": "metric"
}
```

### Annotations
- Read-only: Yes
- Open world: Yes (accesses external weather API)
- Idempotent: Yes
```

### 2. Code Documentation
Include comprehensive inline documentation:

```typescript
/**
 * Retrieves weather forecast for a specified location
 * 
 * @param request - Tool call request containing location and options
 * @returns Promise<CallToolResult> Weather forecast data or error
 * 
 * @throws {Error} When location parameter is missing or invalid
 * @throws {Error} When external API is unavailable
 * 
 * @example
 * ```typescript
 * const result = await getWeatherForecast({
 *   location: "London",
 *   days: 3,
 *   units: "metric"
 * });
 * ```
 */
async function getWeatherForecast(
  request: CallToolRequest
): Promise<CallToolResult> {
  // Implementation...
}
```

## Implementation Examples

### 1. Simple Calculator Tool

```typescript
import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { CallToolRequestSchema, CallToolResult } from "@modelcontextprotocol/sdk/types.js";

const server = new Server({
  name: "calculator-server",
  version: "1.0.0"
}, {
  capabilities: {
    tools: {}
  }
});

server.setRequestHandler(CallToolRequestSchema, async (request) => {
  if (request.params.name === "calculate") {
    const { operation, a, b } = request.params.arguments;
    
    try {
      let result: number;
      switch (operation) {
        case "add":
          result = a + b;
          break;
        case "subtract":
          result = a - b;
          break;
        case "multiply":
          result = a * b;
          break;
        case "divide":
          if (b === 0) {
            throw new Error("Division by zero is not allowed");
          }
          result = a / b;
          break;
        default:
          throw new Error(`Unsupported operation: ${operation}`);
      }
      
      return {
        content: [
          {
            type: "text",
            text: `${a} ${operation} ${b} = ${result}`
          }
        ],
        structuredContent: {
          operation,
          operands: [a, b],
          result
        }
      };
    } catch (error) {
      return {
        isError: true,
        content: [
          {
            type: "text",
            text: `Calculation error: ${error.message}`
          }
        ]
      };
    }
  }
  
  throw new Error(`Unknown tool: ${request.params.name}`);
});
```

## Conclusion

Following these best practices will help you create robust, secure, and user-friendly MCP tools that integrate seamlessly with LLM applications. Remember to:

1. **Design with the user in mind**: Clear names, descriptions, and error messages
2. **Implement proper security**: Validate inputs, sanitize outputs, control access
3. **Handle errors gracefully**: Provide actionable error messages
4. **Optimize for performance**: Cache data, limit response sizes, use timeouts
5. **Test thoroughly**: Unit tests, integration tests, edge cases
6. **Document comprehensively**: Code comments, API documentation, examples

By following these guidelines, your tools will be reliable, maintainable, and provide excellent user experiences for LLM interactions.

## MCP Resources for Splunk Enterprise

### Understanding Resources vs Tools in Splunk Context

**MCP Resources** are application-controlled data sources that provide context to LLMs, while **Tools** are model-controlled executable functions. For Splunk enterprise environments, resources should expose configuration data, search results, and knowledge objects that LLMs can use for analysis and decision-making.

## 🏢 **Multi-Tenant Resources with Client-Specific Configurations**

### **The Challenge: Client-Configured Splunk Connections**

When clients provide their own Splunk configurations, you face these key challenges:

1. **Dynamic Resource Discovery**: Resources vary per client's Splunk instance
2. **Security Isolation**: Each client should only access their own data  
3. **Connection Management**: Efficient handling of multiple Splunk connections
4. **URI Scoping**: Resources must be scoped to specific clients

### **Solution Architecture: Client-Scoped Resources**

#### **1. Client Identity & Security**
```python
# Client identity based on configuration hash
@dataclass
class ClientIdentity:
    client_id: str          # Hash-based secure identifier  
    session_id: str         # MCP session ID
    config_hash: str        # Deterministic config hash
    splunk_host: str        # For auditing
    created_at: float       # For cleanup

# Example client ID generation
def create_client_identity(client_config: Dict) -> str:
    config_str = f"{host}|{port}|{username}|{scheme}"
    config_hash = hashlib.sha256(config_str.encode()).hexdigest()[:16]
    return f"client_{config_hash}_{session_id[:8]}"
```

#### **2. Client-Scoped URI Patterns**
```python
# Multi-tenant resource URIs
CLIENT_SCOPED_PATTERNS = {
    "config": "splunk://client/{client_id}/config/{config_file}",
    "health": "splunk://client/{client_id}/health/{component}/status", 
    "search": "splunk://client/{client_id}/search/results/{search_id}",
    "schema": "splunk://client/{client_id}/schema/index/{index_name}"
}

# Example client-scoped URIs
"splunk://client/abc123def/config/indexes.conf"
"splunk://client/abc123def/health/indexer/status"  
"splunk://client/xyz789ghi/search/results/1234567890.12345"
```

#### **3. Dynamic Resource Discovery**

Resources are discovered **per-client** based on their Splunk instance:

```python
async def list_resources(ctx: Context) -> List[Dict[str, Any]]:
    """Dynamically discover client-specific resources"""
    
    # 1. Extract client config from MCP context
    client_config = get_client_config_from_context(ctx)
    if not client_config:
        return []  # No resources without client config
    
    # 2. Create secure client identity  
    identity = create_client_identity(ctx, client_config)
    
    # 3. Establish client-specific Splunk connection
    service = get_splunk_service(client_config)
    
    # 4. Discover available resources for this client
    resources = []
    
    # Configuration files available on this instance
    for config_file in ["indexes.conf", "props.conf", "transforms.conf"]:
        uri = f"splunk://client/{identity.client_id}/config/{config_file}"
        resources.append({
            "uri": uri,
            "name": f"{config_file} ({identity.splunk_host})",
            "description": f"Configuration for client {identity.client_id}",
            "mimeType": "text/plain"
        })
    
    # Health monitoring for client's components
    for component in ["indexer", "search", "forwarder"]:
        uri = f"splunk://client/{identity.client_id}/health/{component}/status"
        resources.append({
            "uri": uri,
            "name": f"Health: {component} ({identity.splunk_host})",
            "description": f"{component} health for client {identity.client_id}",
            "mimeType": "application/json"
        })
    
    return resources
```

#### **4. Secure Resource Access Control**

```python
async def read_resource(ctx: Context, uri: str) -> str:
    """Read resource with client isolation"""
    
    # 1. Extract client config and create identity
    client_config = get_client_config_from_context(ctx)
    identity = create_client_identity(ctx, client_config)
    
    # 2. Validate URI belongs to this client
    if identity.client_id not in uri:
        raise SecurityError(f"Access denied: URI {uri} not owned by client")
    
    # 3. Get client-specific Splunk connection  
    service = get_splunk_service(client_config)
    
    # 4. Read resource content with client's connection
    content = await get_resource_content(service, uri, identity)
    
    # 5. Audit log access
    logger.info(f"Resource accessed by {identity.client_id}: {uri}")
    
    return content
```

### **Connection Management & Performance**

#### **1. Connection Pooling per Client**
```python
class ClientConnectionManager:
    def __init__(self):
        self._connections: Dict[str, client.Service] = {}
        self._client_identities: Dict[str, ClientIdentity] = {}
    
    async def get_client_connection(self, ctx: Context, client_config: Dict) -> Tuple[ClientIdentity, client.Service]:
        """Get or create client-specific connection"""
        identity = create_client_identity(ctx, client_config)
        
        # Reuse existing connection if available
        if identity.client_id in self._connections:
            return identity, self._connections[identity.client_id]
        
        # Create new connection
        service = get_splunk_service(client_config)
        self._connections[identity.client_id] = service
        self._client_identities[identity.client_id] = identity
        
        return identity, service
```

#### **2. Security Validation**
```python
def validate_client_config(config: Dict[str, Any]):
    """Validate client config for security"""
    required_fields = ['splunk_host', 'splunk_username', 'splunk_password']
    
    for field in required_fields:
        if not config.get(field):
            raise SecurityError(f"Required field missing: {field}")
    
    # Prevent injection attacks
    host = config['splunk_host']
    if not isinstance(host, str) or not host.strip():
        raise SecurityError("Invalid host format")
    
    # Port validation
    port = config.get('splunk_port', 8089)
    if not isinstance(port, int) or port < 1 or port > 65535:
        raise SecurityError("Invalid port")
```

### **Resource Implementation Examples**

#### **1. Client-Scoped Configuration Resource**
```python
class SplunkConfigResource(ClientScopedResource):
    def __init__(self):
        super().__init__(
            base_uri_template="splunk://client/{client_id}/config/{config_file}",
            name="Splunk Configuration",
            description="Client-specific configuration files"
        )
    
    async def get_content(self, ctx: Context, uri: str) -> str:
        # Extract client config and validate access
        client_config = self._get_client_config_from_context(ctx)
        identity, service = await self.client_manager.get_client_connection(ctx, client_config)
        
        # Validate URI ownership
        if identity.client_id not in uri:
            raise SecurityError("Access denied")
        
        # Extract config file from URI
        config_file = uri.split("/")[-1]  # e.g., "indexes.conf"
        
        # Read from client's Splunk instance
        config_name = config_file.split('.')[0]  # Remove .conf
        response = service.get(f"configs/conf-{config_name}")
        raw_config = response.body.read()
        
        # Format with client context
        formatted = f"""
# Splunk Configuration: {config_file}
# Client: {identity.client_id}  
# Host: {identity.splunk_host}
# Retrieved: {datetime.utcnow().isoformat()}Z

{raw_config}
"""
        return formatted
```

#### **2. Client-Scoped Health Resource**
```python
class SplunkHealthResource(ClientScopedResource):
    def __init__(self):
        super().__init__(
            base_uri_template="splunk://client/{client_id}/health/{component}/status",
            name="Health Status", 
            supports_subscriptions=True  # Real-time updates
        )
    
    async def get_content(self, ctx: Context, uri: str) -> str:
        identity, service = await self._get_client_connection(ctx)
        
        # Extract component from URI  
        component = uri.split("/")[-2]  # "indexer", "search", etc.
        
        # Get health data from client's Splunk
        info = service.info()
        health_data = {
            "client_id": identity.client_id,
            "component": component,
            "timestamp": time.time(),
            "splunk_info": {
                "version": info.get("version"),
                "server_name": info.get("serverName"),
                "license_state": info.get("licenseState")
            },
            "status": "healthy"
        }
        
        return json.dumps(health_data, indent=2)
```

### **MCP Server Integration**

#### **Register Resources with Server Capabilities**
```python
# Declare full resource capabilities
{
  "capabilities": {
    "resources": {
      "subscribe": True,      # Individual resource subscriptions
      "listChanged": True     # Resource list change notifications  
    }
  }
}

# Register resource handlers with FastMCP
@app.list_resources()
async def list_resources_handler(ctx: Context):
    """Handle resources/list requests with client scoping"""
    handler = get_resource_handler()
    return await handler.list_resources(ctx)

@app.read_resource() 
async def read_resource_handler(ctx: Context, uri: str):
    """Handle resources/read with security validation"""
    handler = get_resource_handler()
    content = await handler.read_resource(ctx, uri)
    return {
        "contents": [{
            "uri": uri,
            "mimeType": "text/plain",
            "text": content
        }]
    }
```

## 🔒 **Security Best Practices**

### **1. Client Isolation**
- **Hash-based identities**: Deterministic but opaque client IDs
- **URI validation**: Ensure clients only access their own resources
- **Connection pooling**: Separate connections per client
- **Audit logging**: Track all resource access

### **2. Configuration Security**
- **Input validation**: Sanitize all client-provided configs
- **Credential protection**: Never log passwords or tokens
- **Connection limits**: Prevent resource exhaustion
- **Timeout management**: Clean up idle connections

### **3. Content Security** 
- **Data sanitization**: Remove sensitive info from resource content
- **Size limits**: Prevent memory exhaustion from large configs
- **Rate limiting**: Protect against abuse
- **Error handling**: Don't leak internal information

### Core Splunk Resource Categories

#### 1. Configuration Resources
```python
# Splunk configuration files as resources
SPLUNK_CONFIG_RESOURCES = [
    {
        "uri": "splunk://client/{client_id}/config/indexes.conf",
        "name": "Index Configuration",
        "description": "Current index settings, retention policies, and storage paths",
        "mimeType": "text/plain",
        "capabilities": ["subscribe", "listChanged"]
    },
    {
        "uri": "splunk://client/{client_id}/config/props.conf",
        "name": "Props Configuration", 
        "description": "Field extraction, parsing rules, and data preprocessing settings",
        "mimeType": "text/plain"
    },
    {
        "uri": "splunk://client/{client_id}/config/server.conf",
        "name": "Server Configuration",
        "description": "Server-level settings and cluster configuration",
        "mimeType": "text/plain"
    }
]
```

#### 2. Knowledge Object Resources
```python
# Splunk knowledge objects as contextual resources
KNOWLEDGE_OBJECT_RESOURCES = [
    {
        "uriTemplate": "splunk://client/{client_id}/knowledge/datamodel/{model_name}",
        "name": "Data Model Schema",
        "description": "CIM-compliant data model definitions and field mappings",
        "mimeType": "application/json"
    },
    {
        "uri": "splunk://client/{client_id}/knowledge/eventtypes",
        "name": "Event Types Library",
        "description": "Categorized event type definitions for log classification",
        "mimeType": "application/json"
    },
    {
        "uri": "splunk://client/{client_id}/knowledge/macros",
        "name": "Search Macros",
        "description": "Reusable search macro definitions and parameters",
        "mimeType": "application/json"
    }
]
```

### Resource URI Patterns for Splunk

```python
# Recommended URI patterns for Splunk resources
SPLUNK_URI_PATTERNS = {
    # Configuration resources (client-scoped)
    "config": "splunk://client/{client_id}/config/{config_file}",
    "app_config": "splunk://client/{client_id}/apps/{app_name}/config/{config_file}",
    
    # Knowledge objects (client-scoped)
    "datamodel": "splunk://client/{client_id}/knowledge/datamodel/{model_name}",
    "eventtypes": "splunk://client/{client_id}/knowledge/eventtypes/{eventtype_name}",
    "macros": "splunk://client/{client_id}/knowledge/macros/{macro_name}",
    "lookups": "splunk://client/{client_id}/knowledge/lookups/{lookup_name}",
    
    # Search context (client-scoped)
    "search_results": "splunk://client/{client_id}/search/results/{search_id}",
    "saved_search": "splunk://client/{client_id}/search/saved/{search_name}/results",
    "recent_logs": "splunk://client/{client_id}/logs/recent/{index}?timeframe={timeframe}",
    
    # Monitoring data (client-scoped)
    "health": "splunk://client/{client_id}/health/{component}/status",
    "performance": "splunk://client/{client_id}/monitoring/performance/{metric_type}",
    "license": "splunk://client/{client_id}/monitoring/license/usage",
    
    # Dashboards (client-scoped)
    "dashboard_def": "splunk://client/{client_id}/dashboards/{dashboard_id}/definition",
    "dashboard_data": "splunk://client/{client_id}/dashboards/{dashboard_id}/data",
    
    # Apps and deployments (client-scoped)
    "app_manifest": "splunk://client/{client_id}/apps/{app_name}/manifest",
    "deployment_status": "splunk://client/{client_id}/deployment/status/{deployment_id}"
}
```

### Benefits of Multi-Tenant Splunk Resources

1. **Complete Data Isolation**: Each client only accesses their own Splunk environment
2. **Scalable Resource Management**: Connection pooling and efficient client handling  
3. **Secure Access Control**: Hash-based client identity with URI validation
4. **Dynamic Resource Discovery**: Resources adapt to each client's Splunk capabilities
5. **Real-time Awareness**: Subscription capabilities for live updates per client
6. **Context-Aware Intelligence**: LLMs get client-specific context for accurate assistance

### Resource vs Tool Decision Matrix

| Splunk Function | Resource | Tool | Reason |
|----------------|----------|------|--------|
| Configuration files | ✅ | ❌ | Static data for context |
| Search execution | ❌ | ✅ | Action that modifies state |
| Search results | ✅ | ❌ | Data for analysis context |
| Dashboard definitions | ✅ | ❌ | Static structure for reference |
| Health metrics | ✅ | ❌ | Monitoring data for context |
| App deployment | ❌ | ✅ | Action that changes system |
| Knowledge objects | ✅ | ❌ | Reference data for decisions |
| Alert creation | ❌ | ✅ | Action that creates objects |

## Conclusion

Following these best practices will help you create robust, secure, and user-friendly MCP tools that integrate seamlessly with LLM applications. Remember to:

1. **Design with the user in mind**: Clear names, descriptions, and error messages
2. **Implement proper security**: Validate inputs, sanitize outputs, control access
3. **Handle errors gracefully**: Provide actionable error messages
4. **Optimize for performance**: Cache data, limit response sizes, use timeouts
5. **Test thoroughly**: Unit tests, integration tests, edge cases
6. **Document comprehensively**: Code comments, API documentation, examples

By following these guidelines, your tools will be reliable, maintainable, and provide excellent user experiences for LLM interactions.
