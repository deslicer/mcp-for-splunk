# Splunk MCP Client Examples

This guide provides practical examples for using the Python client SDK with the MCP Server for Splunk.

## Table of Contents

- [Quick Start](#quick-start)
- [Health & Monitoring](#health--monitoring)
- [Search Operations](#search-operations)
- [Administrative Tasks](#administrative-tasks)
- [KV Store Operations](#kv-store-operations)
- [Configuration Management](#configuration-management)
- [Error Handling](#error-handling)
- [Advanced Usage](#advanced-usage)

## Quick Start

### Basic Setup

```python
import splunk_mcp_client
from splunk_mcp_client.rest import ApiException
from pprint import pprint
import json

# Configure the client
configuration = splunk_mcp_client.Configuration(
    host = "http://localhost:8001/mcp"  # Your MCP server endpoint
)

# Create API client
api_client = splunk_mcp_client.ApiClient(configuration)
api_instance = splunk_mcp_client.DefaultApi(api_client)
```

### Helper Function for Tool Calls

```python
def call_mcp_tool(tool_name: str, arguments: dict = None):
    """Helper function to call MCP tools"""
    if arguments is None:
        arguments = {}
    
    tool_request = splunk_mcp_client.ToolCallRequest(
        jsonrpc="2.0",
        method="tools/call",
        params={
            "name": tool_name,
            "arguments": arguments
        },
        id="1"
    )
    
    try:
        response = api_instance.tools_call_post(tool_request)
        # Parse the JSON response
        result = json.loads(response.result.content[0])
        return result
    except ApiException as e:
        print(f"Exception when calling {tool_name}: {e}")
        return None
```

## Health & Monitoring

### Check Splunk Health

```python
def check_splunk_health():
    """Check the health of your Splunk instance"""
    result = call_mcp_tool("get_splunk_health")
    
    if result and result.get("status") == "connected":
        print("✅ Splunk is healthy")
        print(f"Version: {result['version']}")
        print(f"Server: {result['server_name']}")
        return True
    else:
        print("❌ Splunk health check failed")
        if result and "error" in result:
            print(f"Error: {result['error']}")
        return False

# Usage
check_splunk_health()
```

### Get Feature Health Status

```python
def get_degraded_features():
    """Get features that are in warning or critical state"""
    result = call_mcp_tool("get_latest_feature_health", {"max_results": 50})
    
    if result and result.get("status") == "success":
        features = result.get("degraded_features", [])
        if features:
            print(f"⚠️  Found {len(features)} degraded features:")
            for feature in features:
                print(f"  - {feature['feature']}: {feature['health']} ({feature['reason']})")
        else:
            print("✅ All features are healthy")
    else:
        print("❌ Failed to get feature health")

# Usage
get_degraded_features()
```

## Search Operations

### One-shot Search

```python
def quick_search(query: str, time_range: str = "-1h"):
    """Perform a quick one-shot search"""
    result = call_mcp_tool("run_oneshot_search", {
        "query": query,
        "earliest_time": time_range,
        "latest_time": "now",
        "max_results": 100
    })
    
    if result and result.get("status") == "success":
        events = result.get("results", [])
        print(f"Found {len(events)} events")
        return events
    else:
        print(f"Search failed: {result.get('error', 'Unknown error')}")
        return []

# Usage examples
events = quick_search("index=_internal error")
events = quick_search("index=main source=/var/log/*", "-24h")
```

### Job-based Search

```python
def run_search_job(query: str):
    """Run a search job and wait for results"""
    result = call_mcp_tool("run_splunk_search", {
        "query": query,
        "earliest_time": "-24h",
        "latest_time": "now"
    })
    
    if result and result.get("status") == "completed":
        print(f"✅ Search completed (Job ID: {result['job_id']})")
        print(f"Found {len(result['results'])} results")
        return result["results"]
    else:
        print(f"❌ Search failed: {result.get('error', 'Unknown error')}")
        return []

# Usage
results = run_search_job("index=_internal | stats count by component")
```

### Saved Search Management

```python
def list_my_saved_searches():
    """List saved searches for the current user"""
    result = call_mcp_tool("list_saved_searches")
    
    if result and result.get("status") == "success":
        searches = result.get("saved_searches", [])
        print(f"Found {len(searches)} saved searches:")
        for search in searches:
            print(f"  - {search['name']}: {search['search']}")
        return searches
    return []

def create_saved_search(name: str, search_query: str):
    """Create a new saved search"""
    result = call_mcp_tool("create_saved_search", {
        "name": name,
        "search": search_query,
        "description": f"Created via MCP client",
        "earliest_time": "-24h",
        "latest_time": "now"
    })
    
    if result and result.get("status") == "success":
        print(f"✅ Created saved search: {name}")
        return True
    else:
        print(f"❌ Failed to create saved search: {result.get('error')}")
        return False

def execute_saved_search(name: str):
    """Execute an existing saved search"""
    result = call_mcp_tool("execute_saved_search", {
        "name": name,
        "mode": "oneshot"
    })
    
    if result and result.get("status") == "success":
        print(f"✅ Executed saved search: {name}")
        return result.get("results", [])
    else:
        print(f"❌ Failed to execute saved search: {result.get('error')}")
        return []

# Usage
searches = list_my_saved_searches()
create_saved_search("error_summary", "index=_internal error | stats count by component")
results = execute_saved_search("error_summary")
```

## Administrative Tasks

### App Management

```python
def list_installed_apps():
    """List all installed Splunk apps"""
    result = call_mcp_tool("list_apps")
    
    if result and result.get("status") == "success":
        apps = result.get("apps", [])
        print(f"Found {len(apps)} installed apps:")
        for app in apps:
            status = "✅ Enabled" if not app.get("disabled", False) else "❌ Disabled"
            print(f"  - {app['name']}: {app.get('label', 'N/A')} ({status})")
        return apps
    return []

def manage_app(app_name: str, action: str):
    """Enable, disable, or restart an app"""
    result = call_mcp_tool("manage_apps", {
        "app_name": app_name,
        "action": action
    })
    
    if result and result.get("status") == "success":
        print(f"✅ Successfully {action}d app: {app_name}")
        return True
    else:
        print(f"❌ Failed to {action} app: {result.get('error')}")
        return False

# Usage
apps = list_installed_apps()
manage_app("search", "restart")
```

### User Management

```python
def list_users():
    """List all Splunk users"""
    result = call_mcp_tool("list_users")
    
    if result and result.get("status") == "success":
        users = result.get("users", [])
        print(f"Found {len(users)} users:")
        for user in users:
            roles = ", ".join(user.get("roles", []))
            print(f"  - {user['name']}: {roles}")
        return users
    return []

# Usage
users = list_users()
```

## KV Store Operations

### Collection Management

```python
def list_kv_collections():
    """List all KV Store collections"""
    result = call_mcp_tool("list_kvstore_collections")
    
    if result and result.get("status") == "success":
        collections = result.get("collections", [])
        print(f"Found {len(collections)} KV Store collections:")
        for collection in collections:
            print(f"  - {collection['name']}: {collection.get('app', 'N/A')}")
        return collections
    return []

def create_kv_collection(app: str, collection_name: str, fields: dict = None):
    """Create a new KV Store collection"""
    args = {
        "app": app,
        "collection": collection_name
    }
    if fields:
        args["fields"] = fields
    
    result = call_mcp_tool("create_kvstore_collection", args)
    
    if result and result.get("status") == "success":
        print(f"✅ Created KV collection: {collection_name}")
        return True
    else:
        print(f"❌ Failed to create collection: {result.get('error')}")
        return False

def query_kv_data(collection: str, query: dict = None):
    """Query data from a KV Store collection"""
    args = {"collection": collection}
    if query:
        args["query"] = query
    
    result = call_mcp_tool("get_kvstore_data", args)
    
    if result and result.get("status") == "success":
        data = result.get("data", [])
        print(f"Found {len(data)} records in {collection}")
        return data
    else:
        print(f"❌ Failed to query collection: {result.get('error')}")
        return []

# Usage
collections = list_kv_collections()
create_kv_collection("search", "my_lookup", {"user": "string", "score": "number"})
data = query_kv_data("my_lookup")
```

## Configuration Management

### View Configuration Files

```python
def get_configuration(conf_file: str, stanza: str = None):
    """Get Splunk configuration from a .conf file"""
    args = {"conf_file": conf_file}
    if stanza:
        args["stanza"] = stanza
    
    result = call_mcp_tool("get_configurations", args)
    
    if result and result.get("status") == "success":
        config = result.get("configuration", {})
        if stanza:
            print(f"Configuration for [{stanza}] in {conf_file}.conf:")
        else:
            print(f"Configuration for {conf_file}.conf:")
        
        for section, settings in config.items():
            if isinstance(settings, dict):
                print(f"\n[{section}]")
                for key, value in settings.items():
                    print(f"  {key} = {value}")
        return config
    else:
        print(f"❌ Failed to get configuration: {result.get('error')}")
        return {}

# Usage examples
get_configuration("indexes")  # Get all index configurations
get_configuration("indexes", "main")  # Get main index configuration only
get_configuration("props")  # Get props.conf
get_configuration("server")  # Get server.conf
```

### Data Discovery

```python
def discover_data_sources():
    """Discover available data sources and sourcetypes"""
    
    # Get indexes
    indexes_result = call_mcp_tool("list_indexes")
    indexes = []
    if indexes_result and indexes_result.get("status") == "success":
        indexes = [idx["name"] for idx in indexes_result.get("indexes", [])]
    
    # Get sources
    sources_result = call_mcp_tool("list_sources")
    sources = []
    if sources_result and sources_result.get("status") == "success":
        sources = [src["source"] for src in sources_result.get("sources", [])]
    
    # Get sourcetypes
    sourcetypes_result = call_mcp_tool("list_sourcetypes")
    sourcetypes = []
    if sourcetypes_result and sourcetypes_result.get("status") == "success":
        sourcetypes = [st["sourcetype"] for st in sourcetypes_result.get("sourcetypes", [])]
    
    print(f"Data Discovery Summary:")
    print(f"  📊 Indexes: {len(indexes)}")
    print(f"  📁 Sources: {len(sources)}")
    print(f"  🏷️  Sourcetypes: {len(sourcetypes)}")
    
    return {
        "indexes": indexes,
        "sources": sources,
        "sourcetypes": sourcetypes
    }

# Usage
data_info = discover_data_sources()
```

## Error Handling

### Robust Error Handling Pattern

```python
def safe_mcp_call(tool_name: str, arguments: dict = None, retries: int = 3):
    """Make MCP tool calls with retry logic and comprehensive error handling"""
    
    for attempt in range(retries):
        try:
            result = call_mcp_tool(tool_name, arguments)
            
            if result is None:
                raise Exception("No response from MCP server")
            
            if result.get("status") == "error":
                error_msg = result.get("error", "Unknown error")
                raise Exception(f"Tool error: {error_msg}")
            
            return result
            
        except Exception as e:
            print(f"Attempt {attempt + 1} failed: {e}")
            if attempt == retries - 1:
                print(f"❌ Failed after {retries} attempts")
                raise
            else:
                import time
                time.sleep(2 ** attempt)  # Exponential backoff

# Usage
try:
    result = safe_mcp_call("get_splunk_health")
    print("✅ Health check successful")
except Exception as e:
    print(f"❌ Health check failed: {e}")
```

## Advanced Usage

### Batch Operations

```python
def batch_health_check():
    """Perform comprehensive health check"""
    checks = {
        "splunk_health": lambda: call_mcp_tool("get_splunk_health"),
        "feature_health": lambda: call_mcp_tool("get_latest_feature_health"),
        "app_status": lambda: call_mcp_tool("list_apps"),
    }
    
    results = {}
    for check_name, check_func in checks.items():
        try:
            result = check_func()
            results[check_name] = result.get("status") == "success" if result else False
            print(f"{'✅' if results[check_name] else '❌'} {check_name}")
        except Exception as e:
            results[check_name] = False
            print(f"❌ {check_name}: {e}")
    
    overall_health = all(results.values())
    print(f"\n🏥 Overall Health: {'✅ Healthy' if overall_health else '❌ Issues Detected'}")
    return results

# Usage
health_summary = batch_health_check()
```

### Custom Search Workflows

```python
def analyze_errors_workflow():
    """Complete workflow for error analysis"""
    print("🔍 Starting error analysis workflow...")
    
    # Step 1: Quick error count
    error_count_query = 'index=_internal error | stats count'
    quick_results = call_mcp_tool("run_oneshot_search", {
        "query": error_count_query,
        "earliest_time": "-1h"
    })
    
    if quick_results and quick_results.get("status") == "success":
        count = quick_results["results"][0]["count"] if quick_results["results"] else "0"
        print(f"📊 Found {count} errors in the last hour")
    
    # Step 2: Detailed error breakdown
    error_breakdown_query = '''
    index=_internal error 
    | stats count by component, log_level 
    | sort -count
    '''
    
    detailed_results = call_mcp_tool("run_splunk_search", {
        "query": error_breakdown_query,
        "earliest_time": "-24h"
    })
    
    if detailed_results and detailed_results.get("status") == "completed":
        print(f"📋 Error breakdown (last 24h):")
        for result in detailed_results["results"][:10]:  # Top 10
            print(f"  - {result.get('component', 'Unknown')}: {result.get('count', 0)} errors")
    
    print("✅ Error analysis workflow completed")

# Usage
analyze_errors_workflow()
```

### Integration with MCP Resources

```python
# Note: Resource access would typically be done through MCP resource endpoints
# This example shows how you might structure resource-based workflows

def get_troubleshooting_context():
    """Get context for troubleshooting using MCP resources"""
    print("🔧 Gathering troubleshooting context...")
    
    # Get current health
    health = call_mcp_tool("get_splunk_health")
    
    # Get configuration info
    indexes_config = call_mcp_tool("get_configurations", {"conf_file": "indexes"})
    
    # Get recent errors
    recent_errors = call_mcp_tool("run_oneshot_search", {
        "query": "index=_internal error | head 10",
        "earliest_time": "-1h"
    })
    
    context = {
        "health_status": health.get("status") if health else "unknown",
        "config_available": indexes_config.get("status") == "success" if indexes_config else False,
        "recent_error_count": len(recent_errors.get("results", [])) if recent_errors else 0
    }
    
    print(f"📋 Troubleshooting Context:")
    print(f"  - Health: {context['health_status']}")
    print(f"  - Config accessible: {context['config_available']}")
    print(f"  - Recent errors: {context['recent_error_count']}")
    
    return context

# Usage
context = get_troubleshooting_context()
```

## Complete Example: Monitoring Dashboard

```python
def monitoring_dashboard():
    """Create a simple monitoring dashboard"""
    print("🖥️  Splunk Monitoring Dashboard")
    print("=" * 40)
    
    # Health checks
    print("\n🏥 HEALTH STATUS")
    health = call_mcp_tool("get_splunk_health")
    if health and health.get("status") == "connected":
        print(f"✅ Splunk: Connected (v{health.get('version', 'Unknown')})")
    else:
        print("❌ Splunk: Disconnected")
    
    # Feature health
    features = call_mcp_tool("get_latest_feature_health", {"max_results": 5})
    if features and features.get("status") == "success":
        degraded = features.get("degraded_features", [])
        if degraded:
            print(f"⚠️  {len(degraded)} degraded features detected")
        else:
            print("✅ All features healthy")
    
    # Data summary
    print("\n📊 DATA SUMMARY")
    indexes = call_mcp_tool("list_indexes")
    if indexes and indexes.get("status") == "success":
        print(f"📁 Indexes: {len(indexes.get('indexes', []))}")
    
    sourcetypes = call_mcp_tool("list_sourcetypes")
    if sourcetypes and sourcetypes.get("status") == "success":
        print(f"🏷️  Sourcetypes: {len(sourcetypes.get('sourcetypes', []))}")
    
    # Recent activity
    print("\n⚡ RECENT ACTIVITY")
    recent_events = call_mcp_tool("run_oneshot_search", {
        "query": "index=_internal | stats count",
        "earliest_time": "-1h"
    })
    
    if recent_events and recent_events.get("status") == "success":
        count = recent_events["results"][0]["count"] if recent_events["results"] else "0"
        print(f"📈 Events (last hour): {count}")
    
    print("\n" + "=" * 40)
    print("Dashboard refresh completed ✅")

# Usage
if __name__ == "__main__":
    with splunk_mcp_client.ApiClient(configuration) as api_client:
        api_instance = splunk_mcp_client.DefaultApi(api_client)
        monitoring_dashboard()
```

This examples guide provides comprehensive patterns for using the Splunk MCP Client SDK effectively in real-world scenarios. 