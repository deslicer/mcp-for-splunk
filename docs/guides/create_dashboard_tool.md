# Create Dashboard Tool

Create new Splunk dashboards (Simple XML or Dashboard Studio) programmatically via the MCP Server.

## Overview

The `create_dashboard` tool enables AI agents and automation to create dashboards in Splunk without manual UI interaction. It supports both Classic Simple XML dashboards and modern Dashboard Studio JSON dashboards with automatic type detection.

**What it does:**

- Creates new Classic XML or Studio JSON dashboards
- Automatically detects dashboard type from definition format
- Optionally overwrites existing dashboards
- Sets sharing permissions and access control lists (ACLs)
- Updates labels and descriptions after creation

**REST Endpoint:**

- `POST /servicesNS/{owner}/{app}/data/ui/views`
- [Splunk Docs: Dashboard Studio REST API](https://docs.splunk.com/Documentation/Splunk/9.4.2/DashStudio/RESTusage)

## Prerequisites

- Splunk connection configured and active
- User must have `write` permission in the target app
- For ACL updates, appropriate role permissions required

## Usage

### Basic Parameters

```python
{
    "name": "my_dashboard",              # Required: Dashboard ID
    "definition": "<dashboard>...</dashboard>",  # Required: XML or JSON
    "owner": "nobody",                   # Optional: Default 'nobody'
    "app": "search",                     # Optional: Default 'search'
    "label": "My Dashboard",             # Optional: Human-readable label
    "description": "Dashboard desc",     # Optional: Description text
    "dashboard_type": "auto",            # Optional: 'classic', 'studio', 'auto'
    "overwrite": false                   # Optional: Update if exists
}
```

### Advanced Parameters (ACL)

```python
{
    "sharing": "app",                    # Optional: 'user', 'app', 'global'
    "read_perms": ["admin", "power"],    # Optional: Roles with read access
    "write_perms": ["admin"]             # Optional: Roles with write access
}
```

## Examples

### Create Classic XML Dashboard

```python
xml_definition = """<dashboard>
  <label>System Health Dashboard</label>
  <description>Monitor system health metrics</description>
  <row>
    <panel>
      <title>Events Over Time</title>
      <chart>
        <search>
          <query>index=_internal | timechart count</query>
          <earliest>-24h</earliest>
          <latest>now</latest>
        </search>
        <option name="charting.chart">line</option>
      </chart>
    </panel>
  </row>
</dashboard>"""

result = await create_dashboard.execute(
    ctx=context,
    name="system_health",
    definition=xml_definition,
    label="System Health Dashboard",
    app="search"
)
```

### Create Dashboard Studio Dashboard

```python
studio_definition = {
    "version": "1.0.0",
    "title": "Performance Dashboard",
    "description": "Real-time performance monitoring",
    "dataSources": {
        "ds_search1": {
            "type": "ds.search",
            "options": {
                "query": "index=_internal | stats count by sourcetype"
            }
        }
    },
    "visualizations": {
        "viz_chart1": {
            "type": "viz.bar",
            "dataSources": {
                "primary": "ds_search1"
            },
            "options": {
                "backgroundColor": "#1e1e1e"
            }
        }
    },
    "layout": {
        "type": "absolute",
        "structure": [
            {
                "item": "viz_chart1",
                "position": {"x": 0, "y": 0, "w": 400, "h": 300}
            }
        ]
    }
}

result = await create_dashboard.execute(
    ctx=context,
    name="performance_dashboard",
    definition=studio_definition,
    dashboard_type="studio",
    app="myapp"
)
```

### Overwrite Existing Dashboard

```python
result = await create_dashboard.execute(
    ctx=context,
    name="existing_dashboard",
    definition=updated_xml,
    overwrite=True,  # Update if exists
    label="Updated Dashboard Name"
)
```

### Create with ACL Permissions

```python
result = await create_dashboard.execute(
    ctx=context,
    name="security_dashboard",
    definition=dashboard_json,
    sharing="app",                    # App-level sharing
    read_perms=["admin", "power"],    # Read access
    write_perms=["admin"],            # Write access
    app="security_app"
)
```

## Response Format

### Success Response

```json
{
    "status": "success",
    "name": "system_health",
    "label": "System Health Dashboard",
    "type": "classic",
    "app": "search",
    "owner": "nobody",
    "sharing": "app",
    "description": "Monitor system health metrics",
    "version": "1.0",
    "permissions": {
        "read": ["*"],
        "write": ["admin", "power"]
    },
    "web_url": "https://splunk:8000/en-US/app/search/system_health",
    "id": "https://splunk:8089/servicesNS/nobody/search/data/ui/views/system_health"
}
```

### Error Response

```json
{
    "status": "error",
    "error": "HTTP 409 Conflict (Dashboard already exists - use overwrite=True to update)"
}
```

## Dashboard Type Detection

The tool automatically detects dashboard type using these heuristics:

**Classic (Simple XML):**

- Definition is XML string starting with `<dashboard>`
- Contains Simple XML elements like `<row>`, `<panel>`, `<chart>`

**Dashboard Studio:**

- Definition is JSON object/string
- Contains Studio keys like `dataSources`, `visualizations`, `layout`
- Or hybrid XML with `<definition>` tag containing CDATA-wrapped JSON

**Override Detection:**

- Set `dashboard_type="classic"` to force Classic XML
- Set `dashboard_type="studio"` to force Dashboard Studio
- Set `dashboard_type="auto"` to auto-detect (default)

## Common Workflows

### Dashboard Discovery and Creation

1. **List existing dashboards:**

   ```python
   list_dashboards(app="search", type_filter="any")
   ```

2. **Get dashboard template:**

   ```python
   get_dashboard_definition(name="template_dashboard", app="search")
   ```

3. **Modify and create new:**

   ```python
   create_dashboard(
       name="new_dashboard",
       definition=modified_definition,
       label="New Dashboard"
   )
   ```

4. **Verify creation:**

   ```python
   get_dashboard_definition(name="new_dashboard", app="search")
   ```

### Dashboard Migration

```python
# 1. Get source dashboard
source = await get_dashboard_definition(
    name="old_dashboard",
    app="source_app"
)

# 2. Create in new app
result = await create_dashboard(
    name="new_dashboard",
    definition=source["definition"],
    label=source["label"],
    app="target_app",
    sharing="app"
)
```

## Error Handling

### Common Errors

**409 Conflict - Dashboard Exists:**

```json
{
    "error": "HTTP 409 Conflict (Dashboard 'my_dashboard' already exists)"
}
```

**Solution:** Use `overwrite=True` to update the existing dashboard.

**403 Forbidden - Permission Denied:**

```json
{
    "error": "HTTP 403 Forbidden (Permission denied - check role/capabilities)"
}
```

**Solution:** Verify user has `write` permission in the target app.

**400 Bad Request - Invalid Definition:**

```json
{
    "error": "Invalid 'definition' type. Expect dict or str"
}
```

**Solution:** Ensure definition is valid XML string or JSON object.

**404 Not Found - Invalid Namespace:**

```json
{
    "error": "HTTP 404 Not Found (Endpoint not found - check owner/app)"
}
```

**Solution:** Verify the owner and app exist and are accessible.

## Best Practices

### Definition Format

**Classic XML:**

- Use well-formed XML with proper closing tags
- Include `<label>` element for dashboard title
- Test XML syntax before creation
- Use `<description>` for dashboard documentation

**Dashboard Studio:**

- Follow Studio JSON schema
- Include required fields: `dataSources`, `visualizations`, `layout`
- Test JSON validity before creation
- Use Studio editor to generate initial JSON

### Naming Conventions

- Use lowercase with underscores: `system_health_dashboard`
- Avoid special characters except underscore and hyphen
- Keep names descriptive but concise
- Use consistent naming across dashboards

### Permissions

- Default sharing is `user` (private)
- Use `app` sharing for team dashboards
- Use `global` sharing sparingly (visible to all apps)
- Limit write permissions to admin roles
- Grant read permissions based on role requirements

### Overwrite Safety

- Always verify dashboard before overwriting
- Use `get_dashboard_definition` to check current state
- Consider backing up dashboard XML/JSON before overwrite
- Test overwrites in development environment first

## Security Considerations

**Access Control:**

- Dashboards respect Splunk RBAC
- Users need appropriate app permissions
- ACL settings control visibility and editability
- Private dashboards only visible to owner

**Data Security:**

- Dashboard queries run with user's permissions
- Sensitive data access controlled by index permissions
- Review queries for information disclosure
- Avoid hardcoding credentials in dashboard definitions

## Limitations

**Splunk API Constraints:**

- Label and description require separate API call after creation
- Some dashboard metadata not settable at creation time
- ACL updates require additional permissions
- Studio dashboards require Splunk 9.0+

**Tool Limitations:**

- Cannot delete dashboards (use Splunk UI or REST API directly)
- Cannot manage dashboard panels individually
- Cannot set all dashboard properties (e.g., theme, refresh interval)
- No validation of SPL queries within dashboard definitions

## Related Tools

- **list_dashboards**: Discover existing dashboards
- **get_dashboard_definition**: Retrieve dashboard source
- **run_splunk_search**: Test dashboard queries
- **me**: Check current user permissions

## References

- [Splunk Dashboard Studio REST API](https://docs.splunk.com/Documentation/Splunk/9.4.2/DashStudio/RESTusage)
- [Simple XML Reference](https://docs.splunk.com/Documentation/Splunk/latest/Viz/PanelreferenceforSimplifiedXML)
- [Dashboard Studio Documentation](https://docs.splunk.com/Documentation/Splunk/latest/DashStudio/About)
- [REST API: Knowledge Endpoints](https://docs.splunk.com/Documentation/Splunk/9.4.1/RESTREF/RESTknowledge)

## Troubleshooting

### Dashboard Not Appearing

**Check creation success:**

```python
result = await create_dashboard(...)
if result["status"] == "success":
    print(f"Dashboard URL: {result['web_url']}")
```

**Verify with list:**

```python
dashboards = await list_dashboards(
    app="search",
    search_filter=f"name={dashboard_name}"
)
```

### Permission Issues

**Check user role:**

```python
user_info = await me()
print(f"Roles: {user_info['roles']}")
```

**Verify app permissions:**

- Ensure user has write access to target app
- Check if app exists and is accessible
- Verify namespace (owner/app combination)

### Type Detection Issues

**Force dashboard type:**

```python
# Force Classic XML
create_dashboard(
    name="my_dashboard",
    definition=xml_string,
    dashboard_type="classic"  # Override auto-detection
)

# Force Dashboard Studio
create_dashboard(
    name="my_dashboard",
    definition=json_object,
    dashboard_type="studio"  # Override auto-detection
)
```

---

**Need help?** Check [Splunk REST API documentation](https://docs.splunk.com/Documentation/Splunk/latest/RESTREF/RESTlist) or review the [lookups_and_dashboards.md](lookups_and_dashboards.md) guide for related tools.
