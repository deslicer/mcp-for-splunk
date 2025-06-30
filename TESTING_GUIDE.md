# MCP Server Testing Guide

This guide explains how to test the resources in your MCP Server for Splunk.

## Quick Start - Using MCP Inspector

The MCP Inspector is a web-based tool for testing MCP servers. It's already running in your Docker setup.

### 1. Access MCP Inspector

Open your browser and go to: **http://localhost:3001**

### 2. Connect to Your MCP Server

In the MCP Inspector interface:

1. **Server URL**: Enter `http://localhost:8001/mcp/`
2. **Transport**: Select "HTTP" 
3. **Protocol Version**: Use "2024-11-05"
4. Click **Connect**

### 3. Available Resources to Test

Your MCP server currently provides these resources:

#### Basic Test Resources
- `health://status` - Simple health check
- `info://server` - Server information and capabilities  
- `test://data` - Sample JSON data for testing
- `test://greeting/{name}` - Personalized greeting (template resource)

#### Splunk Resources  
- `splunk://simple-status` - Splunk connection status
- `splunk://config/indexes.conf` - Splunk configuration files (requires client config)
- `splunk://health/status` - Splunk health information (requires client config)
- `splunk://apps` - Installed Splunk applications (requires client config)

### 4. Testing Steps in MCP Inspector

1. **List Resources**: Click on "Resources" tab to see all available resources
2. **Read Resources**: Click on any resource to read its content
3. **Test Templates**: For template resources like `test://greeting/{name}`, replace `{name}` with actual values

## Testing with Splunk Configuration

For Splunk-specific resources, you need to provide client configuration via HTTP headers:

### Required Headers for Splunk Resources

Add these headers in the MCP Inspector or your HTTP client:

```
X-Splunk-Host: so1
X-Splunk-Port: 8089
X-Splunk-Username: admin
X-Splunk-Password: Chang3d!
X-Splunk-Scheme: https
X-Splunk-Verify-SSL: false
```

### Setting Headers in MCP Inspector

1. In the connection settings, look for "Headers" or "Custom Headers" section
2. Add each header with its value
3. Reconnect to apply the headers

## Direct HTTP Testing (Advanced)

If you want to test with curl or other HTTP clients, you need to handle the Streamable HTTP protocol:

### 1. Initialize Session

```bash
curl -X POST "http://localhost:8001/mcp/" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d '{
    "jsonrpc": "2.0",
    "id": 1,
    "method": "initialize",
    "params": {
      "protocolVersion": "2024-11-05",
      "capabilities": {"resources": {}},
      "clientInfo": {"name": "Test Client", "version": "1.0"}
    }
  }'
```

### 2. Extract Session ID

The response will contain a session ID that you need for subsequent requests.

### 3. List Resources

```bash
curl -X POST "http://localhost:8001/mcp/" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -H "X-MCP-Session-ID: YOUR_SESSION_ID" \
  -d '{
    "jsonrpc": "2.0",
    "id": 2,
    "method": "resources/list"
  }'
```

## Resource Types Explained

### Static Resources
- Return the same content every time
- Examples: `health://status`, `info://server`

### Template Resources  
- Accept parameters in the URI
- Examples: `test://greeting/{name}`
- Replace `{name}` with actual values like `test://greeting/Alice`

### Client-Scoped Resources
- Require client configuration (Splunk credentials)
- Use different Splunk instances per client
- Examples: `splunk://config/*`, `splunk://health/*`

## Troubleshooting

### Common Issues

1. **"No client configuration found"**
   - Add Splunk headers: X-Splunk-Host, X-Splunk-Username, X-Splunk-Password
   - Make sure the headers are properly formatted

2. **"Connection refused"**
   - Check if Docker containers are running: `docker ps`
   - Restart containers: `docker-compose -f docker-compose-modular.yml restart`

3. **"Session ID missing"**
   - For direct HTTP testing, you must initialize a session first
   - Use MCP Inspector for easier testing

### Checking Logs

View server logs:
```bash
docker logs mcp-server-modular --tail 20
```

View inspector logs:
```bash  
docker logs mcp-inspector-modular --tail 20
```

## Expected Behavior

### Working Resources (No Auth Required)
- `health://status` → "OK"
- `info://server` → JSON with server information
- `test://data` → Sample JSON data
- `test://greeting/Alice` → "Hello, Alice! Welcome to the MCP Server for Splunk."

### Splunk Resources (Auth Required)
- Without headers: "No client configuration found" error
- With valid headers: Actual Splunk data
- With invalid headers: Connection errors

## Next Steps

1. **Test Basic Resources**: Start with `health://status` and `info://server`
2. **Test Template Resources**: Try `test://greeting/YourName`
3. **Add Splunk Headers**: Test Splunk-specific resources
4. **Check Logs**: Monitor server logs for troubleshooting
5. **Iterate**: Add your own resources and test them

## Client ID Information

**You don't need to know the client ID beforehand.** The MCP server generates and manages client IDs automatically:

- For HTTP transport: Session ID serves as client identifier
- Client configuration is extracted from HTTP headers
- Each session gets isolated access to Splunk resources
- The client ID is used internally for logging and resource isolation

The MCP Inspector handles all session management automatically! 