# Splunk Dashboard Studio Cheatsheet (9.4)

A concise reference for authoring Dashboard Studio definitions (JSON) suitable for REST creation via the `create_dashboard` tool.

## Core Concepts

- **Dashboard Definition**: JSON that describes layout, data sources, visualizations, inputs, tokens, and event handlers
- **Studio vs Classic**: Studio uses JSON definition (or hybrid XML with `<definition>`). Focus on pure JSON for REST
- **Key Objects**:
  - `version` (string): e.g., "1.0.0"
  - `title` (string)
  - `dataSources` (object): search or saved search providers
  - `visualizations` (object): visualization instances with type and options
  - `layout` (object): positioning/size grid for viz
  - Optional: `inputs`, `tokens`, `eventHandlers`

## Minimal Skeleton

```json
{
  "version": "1.0.0",
  "title": "My Dashboard",
  "dataSources": {},
  "visualizations": {},
  "layout": { "type": "absolute", "options": {} }
}
```

## Data Sources

Dashboard Studio supports three primary data source types. Prefer saved searches for reliability and performance.

### ds.search (Ad Hoc Searches)

For inline SPL queries created directly in the dashboard:

```json
{
  "dataSources": {
    "ds_cpu": {
      "type": "ds.search",
      "options": {
        "query": "index=_internal | stats avg(exec_time_ms) as avg by component",
        "queryParameters": { "earliest": "-24h", "latest": "now" },
        "refresh": "5s",
        "refreshType": "delay"
      }
    }
  }
}
```

**Key options**:

- `query` (required): SPL search string
- `queryParameters`: Override global time range with `earliest`/`latest`
- `refresh`: Auto-refresh interval (e.g., "5s", "1m")
- `refreshType`: "delay" (after search completes) or "interval" (from dispatch)

### ds.savedSearch (Reports/Saved Searches)

For referencing existing saved searches - **recommended for scheduled dashboards**:

```json
{
  "dataSources": {
    "ds_report": {
      "type": "ds.savedSearch",
      "options": {
        "ref": "Top 100 sourcetypes in the last 24 hours",
        "app": "search",
        "refresh": "5s",
        "refreshType": "interval"
      }
    }
  }
}
```

**Key options**:

- `ref` (required): Exact name of saved search/report
- `app`: App where saved search lives (default: current app)
- `refresh`/`refreshType`: Only for non-scheduled searches

**Performance benefit**: Scheduled saved searches run once and cache results, reducing server load for multi-user dashboards.

### ds.chain (Chain Searches)

For optimizing dashboards with multiple visualizations sharing a common base search:

```json
{
  "dataSources": {
    "ds_base": {
      "type": "ds.search",
      "options": {
        "query": "index=_internal | stats count by status"
      }
    },
    "ds_success": {
      "type": "ds.chain",
      "options": {
        "query": "| where status < 300 | stats sum(count) as Success",
        "extend": "ds_base"
      }
    },
    "ds_errors": {
      "type": "ds.chain",
      "options": {
        "query": "| where status >= 400 | stats sum(count) as Errors",
        "extend": "ds_base"
      }
    }
  }
}
```

**Chain search rules**:

- Base search should be **transforming** (use `stats`, `chart`, `timechart`, etc.)
- Chain searches inherit time range and refresh from base
- Can chain one level deep: base → chain1 → chain2 (max 2 levels)
- Fields used in chains must exist in base search results

## Visualizations

Example single value and time chart with key options:

```json
{
  "visualizations": {
    "sv1": {
      "type": "splunk.singlevalue",
      "title": "Average Exec (ms)",
      "dataSources": { "primary": "ds_cpu" },
      "options": {
        "majorValue": { "field": "avg" },
        "trendDisplay": "line"
      }
    },
    "tc1": {
      "type": "splunk.timechart",
      "title": "Exec by Time",
      "dataSources": { "primary": "ds_cpu" },
      "options": {
        "series": [{ "field": "avg", "name": "Avg Exec" }],
        "legend": { "visible": true }
      }
    }
  }
}
```

### Common Visualization Types

- `splunk.singlevalue` - Single metric display
- `splunk.timechart` - Time-series line/area chart
- `splunk.table` - Data table
- `splunk.bar` - Bar chart
- `splunk.pie` - Pie chart
- `splunk.column` - Column chart
- `splunk.area` - Area chart
- `splunk.scatter` - Scatter plot

## Layout

Absolute layout example with two panels:

```json
{
  "layout": {
    "type": "absolute",
    "options": {},
    "structure": [
      { "item": "sv1", "position": { "x": 0, "y": 0, "w": 6, "h": 3 } },
      { "item": "tc1", "position": { "x": 0, "y": 3, "w": 12, "h": 6 } }
    ]
  }
}
```

**Grid system**: 12 columns, units in grid cells. Position: `{x, y, w, h}`.

## Inputs and Tokens (optional)

```json
{
  "inputs": {
    "timeRange": { 
      "type": "input.timerange", 
      "options": { 
        "defaultValue": { "earliest": "-24h", "latest": "now" } 
      } 
    }
  },
  "tokens": {
    "t_earliest": { "type": "token.constant", "value": "$timeRange.earliest$" },
    "t_latest": { "type": "token.constant", "value": "$timeRange.latest$" }
  }
}
```

Use tokens in searches via `$token$`.

## Authoring Tips

- Prefer `ds.savedSearch` for reliability; keep ad-hoc SPL short and efficient
- Keep JSON valid, minimal; avoid UI-only/undocumented properties
- Ensure each viz wires a `primary` data source; set fields in `options`
- Use absolute layout for simple placement; validate widths/heights
- Pin version `"1.0.0"` unless docs require newer features

## Complete Example

```json
{
  "version": "1.0.0",
  "title": "System Exec Overview",
  "dataSources": {
    "ds_cpu": {
      "type": "ds.search",
      "options": {
        "query": "index=_internal | bin _time span=5m | stats avg(exec_time_ms) as avg by _time",
        "queryParameters": { "earliest": "-24h", "latest": "now" }
      }
    }
  },
  "visualizations": {
    "sv1": {
      "type": "splunk.singlevalue",
      "title": "Avg Exec (ms)",
      "dataSources": { "primary": "ds_cpu" },
      "options": { "majorValue": { "field": "avg" } }
    },
    "tc1": {
      "type": "splunk.timechart",
      "title": "Avg Exec over Time",
      "dataSources": { "primary": "ds_cpu" },
      "options": { "series": [{ "field": "avg", "name": "Avg" }] }
    }
  },
  "layout": {
    "type": "absolute",
    "structure": [
      { "item": "sv1", "position": { "x": 0, "y": 0, "w": 6, "h": 3 } },
      { "item": "tc1", "position": { "x": 0, "y": 3, "w": 12, "h": 6 } }
    ]
  }
}
```

## Canonical References

- [Dashboard Framework Introduction](https://splunkui.splunk.com/Packages/dashboard-docs/Introduction)
- [Dashboard Docs Package](https://splunkui.splunk.com/Packages/dashboard-docs/)
- [What is a Dashboard Definition?](https://help.splunk.com/en/splunk-enterprise/create-dashboards-and-reports/dashboard-studio/9.4/source-code-editor/what-is-a-dashboard-definition)
- [Add and Format Visualizations](https://help.splunk.com/en/splunk-enterprise/create-dashboards-and-reports/dashboard-studio/9.4/visualizations/add-and-format-visualizations)
- [Visualization Configuration Options](https://help.splunk.com/en/splunk-enterprise/create-dashboards-and-reports/dashboard-studio/9.4/configuration-options-reference/visualization-configuration-options)
