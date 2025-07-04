# Splunk MCP Client - Python SDK

The official Python client SDK for the MCP Server for Splunk, providing seamless integration with Splunk operations through the Model Context Protocol.

## Installation

### Via PyPI (Recommended)

```bash
pip install splunk-mcp-client
```

### From Source

```bash
git clone https://github.com/your-org/mcp-server-for-splunk.git
cd mcp-server-for-splunk/sdk/client-python
pip install -e .
```

### Requirements

- Python 3.8+
- requests >= 2.25.0
- urllib3 >= 1.26.0
- python-dateutil >= 2.8.0

## Quick Start

### Basic Configuration

```python
from splunk_mcp_client import McpClient
from splunk_mcp_client.configuration import Configuration
from splunk_mcp_client.exceptions import ApiException

# Configure the client
config = Configuration(
    host="http://localhost:8001/mcp"
)

# Create client instance
client = McpClient(configuration=config)
```

### First API Call

```python
try:
    # Check Splunk health
    result = client.tools_api.tools_call_post({
        "jsonrpc": "2.0",
        "method": "tools/call",
        "params": {
            "name": "get_splunk_health",
            "arguments": {}
        },
        "id": "health_check"
    })
    
    if not result.result.is_error:
        print(f"Splunk is healthy: {result.result.content}")
    else:
        print(f"Health check failed: {result.result.content}")
        
except ApiException as e:
    print(f"API call failed: {e}")
```

## Configuration Options

### Basic Configuration

```python
from splunk_mcp_client.configuration import Configuration

config = Configuration(
    host="http://localhost:8001/mcp",
    debug=False,
    verify_ssl=True
)
```

### With Authentication Headers

```python
import os

config = Configuration(
    host="http://localhost:8001/mcp",
    api_key={
        'X-Splunk-Host': os.getenv('SPLUNK_HOST'),
        'X-Splunk-Username': os.getenv('SPLUNK_USERNAME'),
        'X-Splunk-Password': os.getenv('SPLUNK_PASSWORD'),
        'X-Splunk-Verify-SSL': 'true'
    }
)
```

### Advanced Configuration

```python
from splunk_mcp_client.configuration import Configuration
import urllib3

# Disable SSL warnings (not recommended for production)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

config = Configuration(
    host="http://localhost:8001/mcp",
    debug=True,
    verify_ssl=False,
    ssl_ca_cert="/path/to/ca.pem",
    cert_file="/path/to/client.pem",
    key_file="/path/to/client.key",
    connection_pool_maxsize=100,
    proxy="http://proxy.company.com:8080"
)
```

## Tool Categories & Examples

### Admin Tools

#### Get Configurations

```python
def get_splunk_config(client, conf_file, stanza=None):
    """Retrieve Splunk configuration settings."""
    try:
        result = client.tools_api.tools_call_post({
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": "get_configurations",
                "arguments": {
                    "conf_file": conf_file,
                    "stanza": stanza
                }
            },
            "id": "get_config"
        })
        
        if not result.result.is_error:
            return result.result.content[0].text
        else:
            raise Exception(f"Failed to get config: {result.result.content}")
            
    except ApiException as e:
        raise Exception(f"API error: {e}")

# Example usage
config_data = get_splunk_config(client, "props", "default")
print(f"Props configuration: {config_data}")
```

#### List Applications

```python
def list_applications(client):
    """List all installed Splunk applications."""
    try:
        result = client.tools_api.tools_call_post({
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": "list_apps",
                "arguments": {}
            },
            "id": "list_apps"
        })
        
        if not result.result.is_error:
            return json.loads(result.result.content[0].text)
        else:
            raise Exception(f"Failed to list apps: {result.result.content}")
            
    except ApiException as e:
        raise Exception(f"API error: {e}")

# Example usage
apps = list_applications(client)
print(f"Found {len(apps['apps'])} applications")
for app in apps['apps']:
    print(f"  - {app['name']}: {app['label']}")
```

#### Manage Applications

```python
def manage_application(client, app_name, action):
    """Enable, disable, or restart a Splunk application."""
    valid_actions = ["enable", "disable", "restart", "reload"]
    if action not in valid_actions:
        raise ValueError(f"Invalid action. Must be one of: {valid_actions}")
    
    try:
        result = client.tools_api.tools_call_post({
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": "manage_apps",
                "arguments": {
                    "action": action,
                    "app_name": app_name
                }
            },
            "id": f"manage_app_{action}"
        })
        
        if not result.result.is_error:
            return json.loads(result.result.content[0].text)
        else:
            raise Exception(f"Failed to {action} app: {result.result.content}")
            
    except ApiException as e:
        raise Exception(f"API error: {e}")

# Example usage
result = manage_application(client, "search", "restart")
print(f"App restart result: {result}")
```

### Search Tools

#### One-shot Search

```python
def run_quick_search(client, query, earliest_time="-15m", latest_time="now", max_results=100):
    """Execute a quick search and return results immediately."""
    try:
        result = client.tools_api.tools_call_post({
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": "run_oneshot_search",
                "arguments": {
                    "query": query,
                    "earliest_time": earliest_time,
                    "latest_time": latest_time,
                    "max_results": max_results
                }
            },
            "id": "quick_search"
        })
        
        if not result.result.is_error:
            search_results = json.loads(result.result.content[0].text)
            return search_results
        else:
            raise Exception(f"Search failed: {result.result.content}")
            
    except ApiException as e:
        raise Exception(f"API error: {e}")

# Example usage
results = run_quick_search(
    client, 
    "index=main sourcetype=access_combined | head 10",
    earliest_time="-1h"
)
print(f"Found {results['count']} events")
for event in results.get('events', []):
    print(f"  Time: {event.get('_time')} - {event.get('_raw', '')[:100]}...")
```

#### Complex Search with Job Tracking

```python
def run_complex_search(client, query, earliest_time="-24h", latest_time="now"):
    """Execute a complex search with job tracking."""
    try:
        result = client.tools_api.tools_call_post({
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": "run_splunk_search",
                "arguments": {
                    "query": query,
                    "earliest_time": earliest_time,
                    "latest_time": latest_time
                }
            },
            "id": "complex_search"
        })
        
        if not result.result.is_error:
            job_results = json.loads(result.result.content[0].text)
            return job_results
        else:
            raise Exception(f"Search failed: {result.result.content}")
            
    except ApiException as e:
        raise Exception(f"API error: {e}")

# Example usage
job_results = run_complex_search(
    client,
    "index=main | stats count by sourcetype | sort -count",
    earliest_time="-7d"
)
print(f"Search job completed with {job_results['event_count']} events")
print(f"Job statistics: {job_results['job_stats']}")
```

#### Saved Search Management

```python
class SavedSearchManager:
    def __init__(self, client):
        self.client = client
    
    def list_searches(self, owner=None, app=None):
        """List all saved searches."""
        try:
            result = self.client.tools_api.tools_call_post({
                "jsonrpc": "2.0",
                "method": "tools/call",
                "params": {
                    "name": "list_saved_searches",
                    "arguments": {
                        "owner": owner,
                        "app": app
                    }
                },
                "id": "list_saved_searches"
            })
            
            if not result.result.is_error:
                return json.loads(result.result.content[0].text)
            else:
                raise Exception(f"Failed to list searches: {result.result.content}")
                
        except ApiException as e:
            raise Exception(f"API error: {e}")
    
    def create_search(self, name, search_query, description="", schedule=None):
        """Create a new saved search."""
        try:
            arguments = {
                "name": name,
                "search": search_query,
                "description": description
            }
            
            if schedule:
                arguments.update({
                    "is_scheduled": True,
                    "cron_schedule": schedule
                })
            
            result = self.client.tools_api.tools_call_post({
                "jsonrpc": "2.0",
                "method": "tools/call",
                "params": {
                    "name": "create_saved_search",
                    "arguments": arguments
                },
                "id": "create_saved_search"
            })
            
            if not result.result.is_error:
                return json.loads(result.result.content[0].text)
            else:
                raise Exception(f"Failed to create search: {result.result.content}")
                
        except ApiException as e:
            raise Exception(f"API error: {e}")
    
    def execute_search(self, name, earliest_time=None, latest_time=None):
        """Execute an existing saved search."""
        try:
            arguments = {"name": name}
            if earliest_time:
                arguments["earliest_time"] = earliest_time
            if latest_time:
                arguments["latest_time"] = latest_time
            
            result = self.client.tools_api.tools_call_post({
                "jsonrpc": "2.0",
                "method": "tools/call",
                "params": {
                    "name": "execute_saved_search",
                    "arguments": arguments
                },
                "id": "execute_saved_search"
            })
            
            if not result.result.is_error:
                return json.loads(result.result.content[0].text)
            else:
                raise Exception(f"Failed to execute search: {result.result.content}")
                
        except ApiException as e:
            raise Exception(f"API error: {e}")

# Example usage
search_manager = SavedSearchManager(client)

# List searches
searches = search_manager.list_searches()
print(f"Found {len(searches['searches'])} saved searches")

# Create a new search
new_search = search_manager.create_search(
    name="Daily Error Summary",
    search_query="index=main level=ERROR | stats count by host",
    description="Daily summary of errors by host",
    schedule="0 6 * * *"  # Daily at 6 AM
)
print(f"Created search: {new_search}")

# Execute a search
results = search_manager.execute_search(
    "Daily Error Summary",
    earliest_time="-24h"
)
print(f"Search results: {results}")
```

### Data Discovery Tools

#### Index and Source Discovery

```python
def discover_data_sources(client):
    """Discover available data sources in Splunk."""
    try:
        # Get indexes
        indexes_result = client.tools_api.tools_call_post({
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": "list_indexes",
                "arguments": {}
            },
            "id": "list_indexes"
        })
        
        # Get sources
        sources_result = client.tools_api.tools_call_post({
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": "list_sources",
                "arguments": {}
            },
            "id": "list_sources"
        })
        
        # Get sourcetypes
        sourcetypes_result = client.tools_api.tools_call_post({
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": "list_sourcetypes",
                "arguments": {}
            },
            "id": "list_sourcetypes"
        })
        
        discovery = {}
        
        if not indexes_result.result.is_error:
            discovery['indexes'] = json.loads(indexes_result.result.content[0].text)
        
        if not sources_result.result.is_error:
            discovery['sources'] = json.loads(sources_result.result.content[0].text)
        
        if not sourcetypes_result.result.is_error:
            discovery['sourcetypes'] = json.loads(sourcetypes_result.result.content[0].text)
        
        return discovery
        
    except ApiException as e:
        raise Exception(f"API error: {e}")

# Example usage
data_sources = discover_data_sources(client)
print(f"Data Discovery Results:")
print(f"  Indexes: {len(data_sources.get('indexes', {}).get('indexes', []))}")
print(f"  Sources: {len(data_sources.get('sources', {}).get('sources', []))}")
print(f"  Sourcetypes: {len(data_sources.get('sourcetypes', {}).get('sourcetypes', []))}")
```

### Health & Monitoring

#### System Health Check

```python
def comprehensive_health_check(client):
    """Perform a comprehensive health check."""
    try:
        # Server health
        server_health = client.tools_api.tools_call_post({
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": "get_splunk_health",
                "arguments": {}
            },
            "id": "server_health"
        })
        
        # Feature health
        feature_health = client.tools_api.tools_call_post({
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": "get_latest_feature_health",
                "arguments": {
                    "max_results": 50
                }
            },
            "id": "feature_health"
        })
        
        health_report = {
            "timestamp": datetime.now().isoformat(),
            "server_healthy": False,
            "features_healthy": True,
            "issues": []
        }
        
        # Process server health
        if not server_health.result.is_error:
            server_data = json.loads(server_health.result.content[0].text)
            health_report["server_healthy"] = server_data.get("status") == "connected"
            health_report["server_info"] = server_data
        else:
            health_report["issues"].append(f"Server health check failed: {server_health.result.content}")
        
        # Process feature health
        if not feature_health.result.is_error:
            feature_data = json.loads(feature_health.result.content[0].text)
            health_report["feature_issues"] = feature_data.get("degraded_features", [])
            if health_report["feature_issues"]:
                health_report["features_healthy"] = False
        else:
            health_report["issues"].append(f"Feature health check failed: {feature_health.result.content}")
        
        return health_report
        
    except ApiException as e:
        raise Exception(f"API error: {e}")

# Example usage
health = comprehensive_health_check(client)
print(f"Health Report ({health['timestamp']}):")
print(f"  Server Healthy: {health['server_healthy']}")
print(f"  Features Healthy: {health['features_healthy']}")
if health['issues']:
    print(f"  Issues: {health['issues']}")
```

## Error Handling & Best Practices

### Robust Error Handling

```python
import logging
from tenacity import retry, stop_after_attempt, wait_exponential

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SplunkMCPClient:
    def __init__(self, host, **config_kwargs):
        self.config = Configuration(host=host, **config_kwargs)
        self.client = McpClient(configuration=self.config)
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10)
    )
    def robust_tool_call(self, tool_name, arguments, request_id=None):
        """Make a robust tool call with retry logic."""
        if request_id is None:
            request_id = str(uuid.uuid4())
        
        try:
            logger.info(f"Calling tool {tool_name} with ID {request_id}")
            
            result = self.client.tools_api.tools_call_post({
                "jsonrpc": "2.0",
                "method": "tools/call",
                "params": {
                    "name": tool_name,
                    "arguments": arguments
                },
                "id": request_id
            })
            
            if result.result.is_error:
                error_msg = f"Tool {tool_name} failed: {result.result.content}"
                logger.error(error_msg)
                raise Exception(error_msg)
            
            logger.info(f"Tool {tool_name} completed successfully")
            return json.loads(result.result.content[0].text)
            
        except ApiException as e:
            logger.error(f"API error for tool {tool_name}: {e}")
            raise
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error for tool {tool_name}: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error for tool {tool_name}: {e}")
            raise

# Example usage
client = SplunkMCPClient(
    host="http://localhost:8001/mcp",
    debug=True
)

try:
    health = client.robust_tool_call("get_splunk_health", {})
    print(f"Health check successful: {health}")
except Exception as e:
    print(f"Health check failed after retries: {e}")
```

### Connection Pool Management

```python
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

class SplunkMCPPool:
    def __init__(self, host, pool_size=10, **config_kwargs):
        self.host = host
        self.config_kwargs = config_kwargs
        self.pool_size = pool_size
        self._local = threading.local()
    
    def get_client(self):
        """Get a thread-local client instance."""
        if not hasattr(self._local, 'client'):
            config = Configuration(host=self.host, **self.config_kwargs)
            self._local.client = McpClient(configuration=config)
        return self._local.client
    
    def execute_parallel_calls(self, calls):
        """Execute multiple tool calls in parallel."""
        def make_call(call_spec):
            client = self.get_client()
            tool_name, arguments, call_id = call_spec
            
            try:
                result = client.tools_api.tools_call_post({
                    "jsonrpc": "2.0",
                    "method": "tools/call",
                    "params": {
                        "name": tool_name,
                        "arguments": arguments
                    },
                    "id": call_id
                })
                
                if not result.result.is_error:
                    return {
                        "id": call_id,
                        "success": True,
                        "result": json.loads(result.result.content[0].text)
                    }
                else:
                    return {
                        "id": call_id,
                        "success": False,
                        "error": result.result.content
                    }
            except Exception as e:
                return {
                    "id": call_id,
                    "success": False,
                    "error": str(e)
                }
        
        results = {}
        with ThreadPoolExecutor(max_workers=self.pool_size) as executor:
            future_to_id = {
                executor.submit(make_call, call): call[2] 
                for call in calls
            }
            
            for future in as_completed(future_to_id):
                result = future.result()
                results[result["id"]] = result
        
        return results

# Example usage
pool = SplunkMCPPool(host="http://localhost:8001/mcp", pool_size=5)

# Define parallel calls
calls = [
    ("get_splunk_health", {}, "health_check"),
    ("list_indexes", {}, "get_indexes"),
    ("list_sources", {}, "get_sources"),
    ("list_sourcetypes", {}, "get_sourcetypes"),
    ("list_apps", {}, "get_apps")
]

# Execute in parallel
results = pool.execute_parallel_calls(calls)

for call_id, result in results.items():
    if result["success"]:
        print(f"✓ {call_id}: Success")
    else:
        print(f"✗ {call_id}: {result['error']}")
```

## Testing

### Unit Testing

```python
import unittest
from unittest.mock import Mock, patch
from splunk_mcp_client import McpClient
from splunk_mcp_client.configuration import Configuration

class TestSplunkMCPClient(unittest.TestCase):
    def setUp(self):
        self.config = Configuration(host="http://localhost:8001/mcp")
        self.client = McpClient(configuration=self.config)
    
    @patch('splunk_mcp_client.api.default_api.DefaultApi.tools_call_post')
    def test_health_check_success(self, mock_tools_call):
        # Mock successful response
        mock_response = Mock()
        mock_response.result.is_error = False
        mock_response.result.content = [Mock(text='{"status": "connected", "version": "8.2.0"}')]
        mock_tools_call.return_value = mock_response
        
        # Test
        result = self.client.tools_api.tools_call_post({
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": "get_splunk_health",
                "arguments": {}
            },
            "id": "test"
        })
        
        self.assertFalse(result.result.is_error)
        self.assertIn("status", result.result.content[0].text)
    
    @patch('splunk_mcp_client.api.default_api.DefaultApi.tools_call_post')
    def test_health_check_failure(self, mock_tools_call):
        # Mock error response
        mock_response = Mock()
        mock_response.result.is_error = True
        mock_response.result.content = ["Connection failed"]
        mock_tools_call.return_value = mock_response
        
        # Test
        result = self.client.tools_api.tools_call_post({
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": "get_splunk_health",
                "arguments": {}
            },
            "id": "test"
        })
        
        self.assertTrue(result.result.is_error)
        self.assertEqual(result.result.content, ["Connection failed"])

if __name__ == '__main__':
    unittest.main()
```

### Integration Testing

```python
import pytest
import os
from splunk_mcp_client import McpClient
from splunk_mcp_client.configuration import Configuration

@pytest.fixture
def client():
    """Create a test client instance."""
    config = Configuration(
        host=os.getenv('MCP_HOST', 'http://localhost:8001/mcp')
    )
    return McpClient(configuration=config)

def test_health_check_integration(client):
    """Test actual health check against running server."""
    result = client.tools_api.tools_call_post({
        "jsonrpc": "2.0",
        "method": "tools/call",
        "params": {
            "name": "get_splunk_health",
            "arguments": {}
        },
        "id": "integration_test"
    })
    
    assert not result.result.is_error
    health_data = json.loads(result.result.content[0].text)
    assert "status" in health_data

def test_list_tools_integration(client):
    """Test listing available tools."""
    result = client.tools_api.tools_list_post()
    
    assert result.result.tools is not None
    assert len(result.result.tools) > 0
    
    # Check for expected tools
    tool_names = [tool.name for tool in result.result.tools]
    expected_tools = [
        "get_splunk_health",
        "list_apps",
        "run_oneshot_search",
        "list_indexes"
    ]
    
    for expected_tool in expected_tools:
        assert expected_tool in tool_names

# Run with: pytest test_integration.py -v
```

## Performance Optimization

### Connection Reuse

```python
import atexit
from splunk_mcp_client import McpClient
from splunk_mcp_client.configuration import Configuration

class OptimizedSplunkClient:
    _instance = None
    _client = None
    
    def __new__(cls, host=None, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            if host:
                cls._setup_client(host, **kwargs)
        return cls._instance
    
    @classmethod
    def _setup_client(cls, host, **kwargs):
        """Setup the shared client instance."""
        config = Configuration(
            host=host,
            connection_pool_maxsize=50,  # Increase pool size
            **kwargs
        )
        cls._client = McpClient(configuration=config)
        
        # Register cleanup
        atexit.register(cls._cleanup)
    
    @classmethod
    def _cleanup(cls):
        """Cleanup connections on exit."""
        if cls._client:
            # Close any open connections
            cls._client.rest_client.pool_manager.clear()
    
    def get_client(self):
        """Get the shared client instance."""
        if self._client is None:
            raise RuntimeError("Client not initialized. Call with host parameter first.")
        return self._client

# Usage
optimized_client = OptimizedSplunkClient(host="http://localhost:8001/mcp")
client = optimized_client.get_client()
```

### Async Operations (with asyncio)

```python
import asyncio
import aiohttp
import json
from typing import Dict, Any

class AsyncSplunkMCPClient:
    def __init__(self, host: str, **kwargs):
        self.host = host
        self.session = None
        
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def call_tool(self, tool_name: str, arguments: Dict[str, Any], request_id: str = None) -> Dict[str, Any]:
        """Make an async tool call."""
        if not self.session:
            raise RuntimeError("Client not initialized. Use 'async with' context manager.")
        
        if request_id is None:
            request_id = str(uuid.uuid4())
        
        payload = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": arguments
            },
            "id": request_id
        }
        
        async with self.session.post(
            f"{self.host}/tools/call",
            json=payload,
            headers={"Content-Type": "application/json"}
        ) as response:
            result = await response.json()
            
            if result.get("result", {}).get("isError"):
                raise Exception(f"Tool call failed: {result['result']['content']}")
            
            return json.loads(result["result"]["content"][0]["text"])

# Usage
async def main():
    async with AsyncSplunkMCPClient("http://localhost:8001/mcp") as client:
        # Single call
        health = await client.call_tool("get_splunk_health", {})
        print(f"Health: {health}")
        
        # Parallel calls
        tasks = [
            client.call_tool("list_indexes", {}),
            client.call_tool("list_sources", {}),
            client.call_tool("list_sourcetypes", {})
        ]
        
        results = await asyncio.gather(*tasks)
        print(f"Parallel results: {len(results)} completed")

# Run with: asyncio.run(main())
```

## Troubleshooting

### Common Issues

#### SSL Certificate Errors

```python
# For self-signed certificates
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

config = Configuration(
    host="https://localhost:8001/mcp",
    verify_ssl=False
)
```

#### Connection Timeouts

```python
config = Configuration(
    host="http://localhost:8001/mcp",
    timeout=60,  # Increase timeout
    connection_pool_maxsize=20
)
```

#### Debug Logging

```python
import logging

# Enable debug logging
logging.basicConfig(level=logging.DEBUG)

config = Configuration(
    host="http://localhost:8001/mcp",
    debug=True
)
```

### Performance Monitoring

```python
import time
import functools

def timing_decorator(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        start = time.time()
        result = func(*args, **kwargs)
        end = time.time()
        print(f"{func.__name__} took {end - start:.2f} seconds")
        return result
    return wrapper

@timing_decorator
def timed_health_check(client):
    return client.tools_api.tools_call_post({
        "jsonrpc": "2.0",
        "method": "tools/call",
        "params": {
            "name": "get_splunk_health",
            "arguments": {}
        },
        "id": "timed"
    })
```

## Advanced Examples

See [Advanced Examples](./examples/) for more comprehensive integration patterns including:

- Enterprise monitoring dashboards
- CI/CD integration patterns
- Microservices architecture
- Data pipeline integration
- Custom middleware development

## Contributing

Contributions to the Python SDK are welcome! Please see the main project [Contributing Guide](../../../CONTRIBUTING.md) for details.

## Support

- **Documentation**: This guide and inline docstrings
- **Examples**: Complete examples in the `examples/` directory
- **Issues**: [GitHub Issues](https://github.com/your-org/mcp-server-for-splunk/issues)
- **Community**: [Discussions](https://github.com/your-org/mcp-server-for-splunk/discussions)

## License

MIT License - see [LICENSE](../../../LICENSE) for details. 