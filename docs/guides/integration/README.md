# AI Client Integration Guide

This guide shows you how to connect popular AI clients to your MCP Server for Splunk.

## 🎯 Overview

The MCP Server for Splunk supports two transport modes:
- **stdio**: Direct process communication (best for local AI clients)
- **HTTP**: Network communication (best for web-based AI agents)

## 🏗️ Basic Configuration Pattern

All AI clients follow a similar pattern:

1. **Command**: Points to the MCP server executable
2. **Transport**: stdio (local) or HTTP (remote)
3. **Environment**: Splunk connection details
4. **Arguments**: Server-specific parameters

## 📱 Client Integration Examples

### Claude Desktop

The most popular MCP client for interactive AI conversations.

**Configuration file location:**
- **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`
- **macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Linux**: `~/.config/Claude/claude_desktop_config.json`

**Basic Configuration:**
```json
{
  "mcpServers": {
    "splunk": {
      "command": "fastmcp",
      "args": ["run", "/path/to/mcp-server-for-splunk/src/server.py"],
      "env": {
        "SPLUNK_HOST": "your-splunk.company.com",
        "SPLUNK_USERNAME": "your-username",
        "SPLUNK_PASSWORD": "your-password",
        "SPLUNK_PORT": "8089",
        "SPLUNK_VERIFY_SSL": "false"
      }
    }
  }
}
```

**Production Configuration:**
```json
{
  "mcpServers": {
    "splunk-prod": {
      "command": "fastmcp",
      "args": ["run", "/opt/mcp-server-for-splunk/src/server.py"],
      "env": {
        "SPLUNK_HOST": "prod-splunk.company.com",
        "SPLUNK_USERNAME": "mcp-user",
        "SPLUNK_VERIFY_SSL": "true"
      }
    },
    "splunk-dev": {
      "command": "fastmcp",
      "args": ["run", "/opt/mcp-server-for-splunk/src/server.py"],
      "env": {
        "SPLUNK_HOST": "dev-splunk.company.com",
        "SPLUNK_USERNAME": "dev-user",
        "SPLUNK_VERIFY_SSL": "false"
      }
    }
  }
}
```

### Cursor IDE

Perfect for AI-assisted development with Splunk integration.

**Configuration file location:**
- **Global**: `~/.cursor/mcp_servers.json`
- **Project**: `.cursor/mcp_servers.json` (project-specific)

**Basic Configuration:**
```json
{
  "mcpServers": {
    "splunk": {
      "command": "uv",
      "args": ["run", "fastmcp", "run", "src/server.py"],
      "cwd": "/path/to/mcp-server-for-splunk",
      "env": {
        "MCP_SPLUNK_HOST": "localhost",
        "MCP_SPLUNK_USERNAME": "admin",
        "MCP_SPLUNK_PASSWORD": "Chang3d!"
      }
    }
  }
}
```

**Development Configuration:**
```json
{
  "mcpServers": {
    "splunk-local": {
      "command": "python",
      "args": ["-m", "fastmcp", "run", "src/server.py"],
      "cwd": "${workspaceFolder}",
      "env": {
        "PYTHONPATH": "${workspaceFolder}",
        "SPLUNK_HOST": "localhost",
        "SPLUNK_USERNAME": "admin",
        "SPLUNK_PASSWORD": "Chang3d!",
        "DEBUG": "true"
      }
    }
  }
}
```

### Google Agent Development Kit (ADK)

For building AI agents with Google's framework.

**Python Configuration:**
```python
from google.adk.tools.mcp_tool.mcp_toolset import MCPToolset, StdioServerParameters

# Basic setup
splunk_mcp = MCPToolset(
    connection_params=StdioServerParameters(
        command='fastmcp',
        args=['run', '/path/to/mcp-server-for-splunk/src/server.py'],
        env={
            'SPLUNK_HOST': 'your-splunk.company.com',
            'SPLUNK_USERNAME': 'your-username',
            'SPLUNK_PASSWORD': 'your-password'
        }
    )
)

# Create agent with Splunk tools
splunk_agent = LlmAgent(
    model='gemini-2.0-flash',
    tools=[splunk_mcp],
    system_instruction="You are a Splunk expert assistant."
)
```

**Advanced Configuration:**
```python
import os
from google.adk.tools.mcp_tool.mcp_toolset import MCPToolset, StdioServerParameters

class SplunkAgent:
    def __init__(self, environment='prod'):
        # Environment-specific configuration
        config = self._get_config(environment)

        self.mcp_toolset = MCPToolset(
            connection_params=StdioServerParameters(
                command='fastmcp',
                args=['run', config['server_path']],
                env=config['env']
            )
        )

        self.agent = LlmAgent(
            model='gemini-2.0-flash',
            tools=[self.mcp_toolset],
            system_instruction=config['system_instruction']
        )

    def _get_config(self, environment):
        configs = {
            'prod': {
                'server_path': '/opt/mcp-server-for-splunk/src/server.py',
                'env': {
                    'SPLUNK_HOST': 'prod-splunk.company.com',
                    'SPLUNK_USERNAME': os.getenv('PROD_SPLUNK_USER'),
                    'SPLUNK_PASSWORD': os.getenv('PROD_SPLUNK_PASS'),
                    'SPLUNK_VERIFY_SSL': 'true'
                },
                'system_instruction': 'You are a production Splunk assistant. Be careful with destructive operations.'
            },
            'dev': {
                'server_path': './src/server.py',
                'env': {
                    'SPLUNK_HOST': 'dev-splunk.company.com',
                    'SPLUNK_USERNAME': os.getenv('DEV_SPLUNK_USER'),
                    'SPLUNK_PASSWORD': os.getenv('DEV_SPLUNK_PASS'),
                    'SPLUNK_VERIFY_SSL': 'false'
                },
                'system_instruction': 'You are a development Splunk assistant. Feel free to experiment.'
            }
        }
        return configs[environment]

# Usage
prod_agent = SplunkAgent('prod')
response = prod_agent.agent.send_message("What's the health of our Splunk cluster?")
```

### Continue.dev

AI-powered code assistant with MCP support.

**Configuration file**: `.continue/config.json`

```json
{
  "models": [
    {
      "title": "Claude 3.5 Sonnet",
      "provider": "anthropic",
      "model": "claude-3-5-sonnet-20241022"
    }
  ],
  "mcpServers": [
    {
      "name": "splunk",
      "command": "fastmcp",
      "args": ["run", "src/server.py"],
      "cwd": "/path/to/mcp-server-for-splunk",
      "env": {
        "SPLUNK_HOST": "localhost",
        "SPLUNK_USERNAME": "admin",
        "SPLUNK_PASSWORD": "Chang3d!"
      }
    }
  ]
}
```

### OpenAI API Integration

For custom applications using OpenAI's API with MCP tools.

**Python Example:**
```python
import openai
from mcp import ClientSession, StdioServerParameters
import asyncio

class SplunkAIAssistant:
    def __init__(self):
        self.openai_client = openai.OpenAI()
        self.mcp_session = None

    async def connect_mcp(self):
        """Connect to MCP server"""
        server_params = StdioServerParameters(
            command="fastmcp",
            args=["run", "src/server.py"],
            env={
                "SPLUNK_HOST": "your-splunk.company.com",
                "SPLUNK_USERNAME": "your-username",
                "SPLUNK_PASSWORD": "your-password"
            }
        )

        self.mcp_session = ClientSession(server_params)
        await self.mcp_session.initialize()

    async def query_splunk(self, user_question: str):
        """Process user question with Splunk context"""
        if not self.mcp_session:
            await self.connect_mcp()

        # Get available tools
        tools = await self.mcp_session.list_tools()

        # Use OpenAI to understand intent and call appropriate tools
        response = self.openai_client.chat.completions.create(
            model="gpt-4",
            messages=[
                {
                    "role": "system",
                    "content": f"You have access to these Splunk tools: {[t.name for t in tools]}"
                },
                {"role": "user", "content": user_question}
            ],
            tools=[self._convert_mcp_tool(tool) for tool in tools]
        )

        return response

# Usage
assistant = SplunkAIAssistant()
result = asyncio.run(assistant.query_splunk("Show me system health"))
```

## 🌐 HTTP Transport Integration

For web-based applications or remote access.

### Basic HTTP Client

```python
import requests
import json

class HTTPMCPClient:
    def __init__(self, base_url="http://localhost:8001"):
        self.base_url = base_url
        self.session = requests.Session()

        # Set Splunk credentials via headers
        self.session.headers.update({
            'X-Splunk-Host': 'your-splunk.company.com',
            'X-Splunk-Username': 'your-username',
            'X-Splunk-Password': 'your-password'
        })

    def call_tool(self, tool_name, arguments=None):
        """Call MCP tool via HTTP"""
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": arguments or {}
            }
        }

        response = self.session.post(
            f"{self.base_url}/mcp/",
            json=payload,
            headers={'Content-Type': 'application/json'}
        )

        return response.json()

    def list_tools(self):
        """Get available tools"""
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/list"
        }

        response = self.session.post(
            f"{self.base_url}/mcp/",
            json=payload
        )

        return response.json()

# Usage
client = HTTPMCPClient()
health = client.call_tool("get_splunk_health")
tools = client.list_tools()
```

### Web Application Integration

**JavaScript/Node.js Example:**
```javascript
class SplunkMCPClient {
    constructor(baseUrl = 'http://localhost:8001') {
        this.baseUrl = baseUrl;
        this.headers = {
            'Content-Type': 'application/json',
            'X-Splunk-Host': 'your-splunk.company.com',
            'X-Splunk-Username': 'your-username',
            'X-Splunk-Password': 'your-password'
        };
    }

    async callTool(toolName, arguments = {}) {
        const payload = {
            jsonrpc: "2.0",
            id: 1,
            method: "tools/call",
            params: {
                name: toolName,
                arguments: arguments
            }
        };

        const response = await fetch(`${this.baseUrl}/mcp/`, {
            method: 'POST',
            headers: this.headers,
            body: JSON.stringify(payload)
        });

        return await response.json();
    }

    async searchSplunk(query, timeRange = '-24h') {
        return await this.callTool('run_oneshot_search', {
            query: query,
            earliest_time: timeRange,
            max_results: 100
        });
    }

    async getSplunkHealth() {
        return await this.callTool('get_splunk_health');
    }
}

// Usage in web app
const splunk = new SplunkMCPClient();

// React component example
function SplunkDashboard() {
    const [health, setHealth] = useState(null);

    useEffect(() => {
        splunk.getSplunkHealth().then(setHealth);
    }, []);

    return (
        <div>
            <h1>Splunk Health</h1>
            {health && (
                <div>Status: {health.result.status}</div>
            )}
        </div>
    );
}
```

## 🔧 Configuration Management

### Environment-based Configuration

**Development (.env.dev):**
```env
SPLUNK_HOST=localhost
SPLUNK_USERNAME=admin
SPLUNK_PASSWORD=Chang3d!
SPLUNK_VERIFY_SSL=false
DEBUG=true
```

**Production (.env.prod):**
```env
SPLUNK_HOST=prod-splunk.company.com
SPLUNK_USERNAME=mcp-service-account
SPLUNK_VERIFY_SSL=true
LOG_LEVEL=INFO
```

### Multi-tenant Configuration

For serving multiple clients with different Splunk instances:

**Docker Compose:**
```yaml
version: '3.8'
services:
  mcp-server-tenant1:
    build: .
    environment:
      - SPLUNK_HOST=tenant1-splunk.company.com
      - SPLUNK_USERNAME=tenant1-user
      - SPLUNK_PASSWORD=tenant1-pass
    ports:
      - "8001:8000"

  mcp-server-tenant2:
    build: .
    environment:
      - SPLUNK_HOST=tenant2-splunk.company.com
      - SPLUNK_USERNAME=tenant2-user
      - SPLUNK_PASSWORD=tenant2-pass
    ports:
      - "8002:8000"
```

## 🔍 Testing Your Integration

### Validate Connection

```bash
# Test server health - Initialize session first
curl -X POST -H "Content-Type: application/json" -H "Accept: application/json, text/event-stream" \
  -d '{"jsonrpc":"2.0","id":"init","method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{"roots":{"listChanged":false}},"clientInfo":{"name":"test-client","version":"1.0.0"}}}' \
  http://localhost:8001/mcp/ -D /tmp/mcp_headers.txt

# Get server info using session ID
SESSION_ID=$(grep -i "mcp-session-id:" /tmp/mcp_headers.txt | cut -d' ' -f2 | tr -d '\r\n')
curl -X POST -H "Content-Type: application/json" -H "Accept: application/json, text/event-stream" \
  -H "mcp-session-id: $SESSION_ID" \
  -d '{"jsonrpc":"2.0","id":"test","method":"resources/read","params":{"uri":"info://server"}}' \
  http://localhost:8001/mcp/

# List available tools
curl -X POST http://localhost:8001/mcp/ \
  -H "Content-Type: application/json" \
  -H "X-Session-ID: test-session" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list"}'

# Test Splunk connection
curl -X POST http://localhost:8001/mcp/ \
  -H "Content-Type: application/json" \
  -H "X-Session-ID: test-session" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"get_splunk_health"}}'
```

### Interactive Testing

1. **MCP Inspector**: http://localhost:3001
   - Visual tool testing
   - Real-time parameter adjustment
   - Response inspection

2. **Claude Desktop Testing**:
   - "What's the health of my Splunk server?"
   - "List all available indexes"
   - "Search for errors in the last hour"

3. **Custom Client Testing**:
   - Implement health check calls
   - Test authentication
   - Validate tool responses

## 🚨 Troubleshooting

### Common Integration Issues

**"Server not found"**
- Check server is running: Initialize session and get server info (see Testing section above)
- Verify port configuration
- Check firewall settings

**"Authentication failed"**
- Verify Splunk credentials
- Check network access to Splunk server
- Test manual connection: `curl -u user:pass https://splunk:8089/services/server/info`

**"Tools not working"**
- Check server logs for errors
- Validate tool names with `tools/list`
- Test individual tools in MCP Inspector

**"Client can't connect"**
- Verify client configuration file location
- Check command path and arguments
- Restart client application

### Debug Mode

Enable detailed logging:

```env
DEBUG=true
LOG_LEVEL=DEBUG
```

Monitor logs:
```bash
# Docker
docker logs mcp-server --follow

# Local
tail -f logs/mcp-server.log
```

## 🎯 Next Steps

- **[API Reference](../../api/)** - Complete tool documentation
- **[Security Guide](../security.md)** - Secure your integrations
- **[Deployment Guide](../deployment/)** - Production deployment
- **[Contributing](../../community/contributing.md)** - Add your own tools

---

**Need help?** Join our [GitHub Discussions](https://github.com/your-org/mcp-server-for-splunk/discussions) for community support!
