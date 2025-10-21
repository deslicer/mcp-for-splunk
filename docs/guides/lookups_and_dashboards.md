# Lookups and Dashboards Tools

## Overview

The MCP Server for Splunk provides tools to list and manage Splunk lookup files, lookup definitions, and dashboards. These tools enable discovery and inspection of knowledge objects without modifying them.

## Lookup Tools

### list_lookup_files

List CSV lookup table files available in Splunk.

**Usage:**

```python
{
    "owner": "nobody",      # Optional: Filter by owner (default: nobody)
    "app": "-",             # Optional: Filter by app (default: - for all)
    "count": 0,             # Optional: Max results, 0=all (default: 0)
    "offset": 0,            # Optional: Pagination offset (default: 0)
    "search_filter": ""     # Optional: Filter like 'name=*geo*'
}
```

**Returns:**

```json
{
    "status": "success",
    "lookup_files": [
        {
            "name": "geo_attr_countries.csv",
            "filename": "geo_attr_countries.csv",
            "app": "search",
            "owner": "nobody",
            "sharing": "global",
            "updated": "2024-01-15T10:30:00",
            "size": 1024,
            "permissions": {
                "read": ["*"],
                "write": ["admin"]
            },
            "id": "https://splunk:8089/servicesNS/nobody/search/data/lookup-table-files/geo_attr_countries.csv"
        }
    ],
    "count": 1,
    "total_available": 1,
    "offset": 0
}
```

**Example:**

```
list_lookup_files with:
- app: "search"
- search_filter: "name=*geo*"
```

**To view CSV content:**

Use the `run_splunk_search` tool with `inputlookup`:

```
run_splunk_search with query: "| inputlookup geo_attr_countries.csv"
```

**REST Endpoint:**

- `GET /servicesNS/{owner}/{app}/data/lookup-table-files`
- [Splunk Docs: Knowledge Endpoints](https://help.splunk.com/en/splunk-enterprise/leverage-rest-apis/rest-api-reference/9.4/knowledge-endpoints/knowledge-endpoint-descriptions)

---

### list_lookup_definitions

List lookup definitions (transforms) configured in Splunk.

**Usage:**

```python
{
    "owner": "nobody",
    "app": "-",
    "count": 0,
    "offset": 0,
    "search_filter": ""
}
```

**Returns:**

```json
{
    "status": "success",
    "lookup_definitions": [
        {
            "name": "geo_countries",
            "filename": "geo_attr_countries.csv",
            "type": "file",
            "match_type": "WILDCARD(country)",
            "fields_list": "country,latitude,longitude,code",
            "external_cmd": "",
            "external_type": "",
            "min_matches": 0,
            "max_matches": 1,
            "default_match": "",
            "case_sensitive_match": true,
            "app": "search",
            "owner": "nobody",
            "sharing": "global",
            "updated": "2024-01-15T10:30:00",
            "permissions": {
                "read": ["*"],
                "write": ["admin"]
            },
            "id": "https://splunk:8089/servicesNS/nobody/search/data/transforms/lookups/geo_countries"
        }
    ],
    "count": 1,
    "total_available": 1,
    "offset": 0
}
```

**Example:**

```
list_lookup_definitions with:
- app: "search"
- search_filter: "type=file"
```

**REST Endpoint:**

- `GET /servicesNS/{owner}/{app}/data/transforms/lookups`
- [Splunk Docs: Knowledge Endpoints](https://docs.splunk.com/Documentation/Splunk/9.4.1/RESTREF/RESTknowledge)

---

## Dashboard Tools

### list_dashboards

List dashboards in Splunk (both Simple XML and Dashboard Studio).

**Usage:**

```python
{
    "owner": "nobody",
    "app": "-",
    "count": 0,
    "offset": 0,
    "search_filter": "",           # Optional: Filter like 'name=*security*'
    "type_filter": "any"           # Optional: 'classic', 'studio', or 'any'
}
```

**Returns:**

```json
{
    "status": "success",
    "dashboards": [
        {
            "name": "security_overview",
            "label": "Security Overview",
            "type": "classic",
            "app": "search",
            "owner": "nobody",
            "sharing": "global",
            "description": "Security monitoring dashboard",
            "updated": "2024-01-15T10:30:00",
            "version": "1.0",
            "permissions": {
                "read": ["*"],
                "write": ["admin"]
            },
            "web_url": "https://splunk:8000/en-US/app/search/security_overview",
            "id": "https://splunk:8089/servicesNS/nobody/search/data/ui/views/security_overview"
        },
        {
            "name": "performance_dashboard",
            "label": "Performance Dashboard",
            "type": "studio",
            "app": "myapp",
            "owner": "admin",
            "sharing": "app",
            "description": "System performance monitoring",
            "updated": "2024-01-14T09:15:00",
            "version": "2.0",
            "permissions": {
                "read": ["admin", "power"],
                "write": ["admin"]
            },
            "web_url": "https://splunk:8000/en-US/app/myapp/performance_dashboard",
            "id": "https://splunk:8089/servicesNS/admin/myapp/data/ui/views/performance_dashboard"
        }
    ],
    "count": 2,
    "total_available": 2,
    "offset": 0,
    "type_filter": "any"
}
```

**Type Detection:**

- **classic**: Simple XML dashboards (XML format in `eai:data`)
- **studio**: Dashboard Studio dashboards (JSON format in `eai:data`)

**Example:**

```
list_dashboards with:
- app: "search"
- type_filter: "studio"
```

**REST Endpoint:**

- `GET /servicesNS/{owner}/{app}/data/ui/views?search=isDashboard=1`
- [Splunk Docs: Dashboard Studio REST](https://docs.splunk.com/Documentation/Splunk/latest/DashStudio/RESTusage)

---

### get_dashboard_definition

Get the raw definition of a specific dashboard (Simple XML or Dashboard Studio JSON).

**Usage:**

```python
{
    "name": "security_overview",    # Required: Dashboard name
    "owner": "nobody",               # Optional: Default 'nobody'
    "app": "search"                  # Optional: Default 'search'
}
```

**Returns (Classic Dashboard):**

```json
{
    "status": "success",
    "name": "security_overview",
    "label": "Security Overview",
    "type": "classic",
    "app": "search",
    "owner": "nobody",
    "sharing": "global",
    "description": "Security monitoring dashboard",
    "updated": "2024-01-15T10:30:00",
    "version": "1.0",
    "definition": "<dashboard>\n  <label>Security Overview</label>\n  <row>\n    <panel>\n      <title>Events Over Time</title>\n      <chart>\n        <search>\n          <query>index=security | timechart count</query>\n        </search>\n      </chart>\n    </panel>\n  </row>\n</dashboard>",
    "permissions": {
        "read": ["*"],
        "write": ["admin"]
    },
    "web_url": "https://splunk:8000/en-US/app/search/security_overview",
    "id": "https://splunk:8089/servicesNS/nobody/search/data/ui/views/security_overview"
}
```

**Returns (Dashboard Studio):**

```json
{
    "status": "success",
    "name": "performance_dashboard",
    "label": "Performance Dashboard",
    "type": "studio",
    "app": "myapp",
    "owner": "admin",
    "sharing": "app",
    "description": "System performance monitoring",
    "updated": "2024-01-14T09:15:00",
    "version": "2.0",
    "definition": {
        "version": "1.0.0",
        "title": "Performance Dashboard",
        "dataSources": {
            "ds_search1": {
                "type": "ds.search",
                "options": {
                    "query": "index=_internal | stats count"
                }
            }
        },
        "visualizations": {
            "viz_chart1": {
                "type": "viz.line",
                "dataSources": {
                    "primary": "ds_search1"
                }
            }
        }
    },
    "permissions": {
        "read": ["admin", "power"],
        "write": ["admin"]
    },
    "web_url": "https://splunk:8000/en-US/app/myapp/performance_dashboard",
    "id": "https://splunk:8089/servicesNS/admin/myapp/data/ui/views/performance_dashboard"
}
```

**Example:**

```
get_dashboard_definition with:
- name: "security_overview"
- app: "search"
```

**REST Endpoint:**

- `GET /servicesNS/{owner}/{app}/data/ui/views/{name}`
- [Splunk Docs: Dashboard Studio REST](https://docs.splunk.com/Documentation/Splunk/latest/DashStudio/RESTusage)

---

## Common Patterns

### Discovering Lookups Workflow

1. **List all lookup files:**

   ```
   list_lookup_files with app: "-"
   ```

2. **Find lookup definitions:**

   ```
   list_lookup_definitions with app: "-"
   ```

3. **View lookup content:**

   ```
   run_splunk_search with query: "| inputlookup <filename>"
   ```

### Dashboard Discovery Workflow

1. **List all dashboards:**

   ```
   list_dashboards with type_filter: "any"
   ```

2. **Filter Studio dashboards:**

   ```
   list_dashboards with type_filter: "studio"
   ```

3. **Get dashboard definition:**

   ```
   get_dashboard_definition with name: "<dashboard_name>", app: "<app>"
   ```

4. **Open in Splunk Web:**
   Use the `web_url` from the response

---

## Permissions & Security

All tools respect Splunk's role-based access control (RBAC):

- **401 Unauthorized**: Authentication failed
- **403 Forbidden**: User lacks required capabilities
- **404 Not Found**: Object doesn't exist or user can't see it

**Required Capabilities:**

- Lookup files/definitions: `list_storage_passwords` or `admin_all_objects`
- Dashboards: `read` permission on the dashboard's app

---

## Pagination

For large environments, use pagination:

```python
# Get first 100 lookups
list_lookup_files with count: 100, offset: 0

# Get next 100
list_lookup_files with count: 100, offset: 100
```

Set `count: 0` to retrieve all results (default).

---

## Error Handling

All tools return consistent error responses:

```json
{
    "status": "error",
    "error": "Detailed error message with context"
}
```

Common errors:

- Connection issues: Check Splunk connectivity
- Permission denied: Verify user role and capabilities
- Not found: Check namespace (owner/app) and object name

---

## References

- [Splunk REST API: Knowledge Endpoints](https://help.splunk.com/en/splunk-enterprise/leverage-rest-apis/rest-api-reference/9.4/knowledge-endpoints/knowledge-endpoint-descriptions)
- [Splunk REST API: Transforms/Lookups](https://docs.splunk.com/Documentation/Splunk/9.4.1/RESTREF/RESTknowledge)
- [Splunk Dashboard Studio REST API](https://docs.splunk.com/Documentation/Splunk/latest/DashStudio/RESTusage)
- [Splunk Python SDK Documentation](https://docs.splunk.com/DocumentationStatic/PythonSDK/)
