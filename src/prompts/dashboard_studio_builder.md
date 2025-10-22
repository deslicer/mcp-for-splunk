# Dashboard Studio Builder Prompt

Instructions for creating valid Splunk Dashboard Studio definitions (JSON) for REST-based creation via `create_dashboard` tool.

## Your Task

Design and output a complete Dashboard Studio definition as a JSON object suitable for the `definition` parameter of the `create_dashboard` tool with `dashboard_type="studio"`.

## Authoring Steps

### 1. Clarify Requirements

- **Purpose**: What is the dashboard's goal? (monitoring, reporting, analysis, etc.)
- **Audience**: Who will use it? (admins, analysts, executives, etc.)
- **KPIs**: Which metrics or data points are critical?
- **Time Range**: What time window is relevant? (real-time, hourly, daily, historical)
- **Data Sources**: Saved searches available, or ad-hoc SPL needed?

### 2. Select Visualizations

Choose appropriate visualization types for each KPI:

- **Single Value**: For key metrics, KPIs, counts
- **Time Chart**: For trends over time
- **Table**: For detailed data, lists
- **Bar/Column**: For comparisons across categories
- **Pie**: For proportions, percentages
- **Area**: For cumulative trends
- **Scatter**: For correlations

### 3. Map SPL Queries

- **Prefer saved searches**: More reliable, tested, performant
- **Ad-hoc SPL**: Keep simple, efficient, indexed fields only
- **Time binning**: Use `bin _time span=...` for time series
- **Stats/Aggregation**: Ensure correct field names for viz options

### 4. Define Data Sources

For each unique query, create a data source:

```json
"dataSources": {
  "ds_<name>": {
    "type": "ds.search" | "ds.savedSearch",
    "options": {
      "query": "<SPL>" | "name": "<saved_search_name>",
      "queryParameters": { "earliest": "<time>", "latest": "<time>" }
    }
  }
}
```

### 5. Wire Visualizations

For each visualization:

```json
"visualizations": {
  "viz_<name>": {
    "type": "splunk.<viztype>",
    "title": "<Title>",
    "dataSources": { "primary": "ds_<name>" },
    "options": {
      // Type-specific configuration
      // Refer to cheatsheet for common options
    }
  }
}
```

### 6. Add Layout

Use absolute layout with 12-column grid:

```json
"layout": {
  "type": "absolute",
  "structure": [
    { "item": "viz_<name>", "position": { "x": 0, "y": 0, "w": 6, "h": 3 } }
  ]
}
```

**Grid Guidelines**:

- Width (`w`): 1-12 columns
- Height (`h`): Typical values 2-6 for most viz
- Positioning: Top-left is `{x: 0, y: 0}`

### 7. Validate JSON

- **Structure**: Ensure `version`, `title`, `dataSources`, `visualizations`, `layout` are present
- **Data Source Wiring**: Each viz `primary` references valid data source ID
- **Field Names**: Options reference fields returned by SPL
- **Valid JSON**: No trailing commas, proper quotes, balanced braces

### 8. Output Final Definition

Return the complete JSON object only. No explanatory text before or after.

## Constraints for REST Creation

- **No UI-Only Fields**: Omit internal/transient properties not in documentation
- **Documented Options Only**: Use only options from canonical configuration reference
- **No Deprecated Features**: Avoid legacy/deprecated visualization types or options
- **Minimal Definition**: Include only necessary fields; omit defaults
- **Version Pin**: Use `"version": "1.0.0"` unless newer features required

## Output Contract

### Required Top-Level Keys

- `version` (string): "1.0.0"
- `title` (string): Dashboard title
- `dataSources` (object): At least one data source
- `visualizations` (object): At least one visualization
- `layout` (object): Absolute layout with structure array

### Optional Top-Level Keys

- `inputs` (object): Time pickers, dropdowns, etc.
- `tokens` (object): Variables for dynamic queries
- `eventHandlers` (object): Interaction handlers

### Output Format

```json
{
  "version": "1.0.0",
  "title": "...",
  "dataSources": { ... },
  "visualizations": { ... },
  "layout": { ... }
}
```

## Quick Checks

Before outputting, verify:

- [ ] JSON is valid (use a validator if available)
- [ ] All required keys present (`version`, `title`, `dataSources`, `visualizations`, `layout`)
- [ ] Each visualization references existing data source
- [ ] Field names in viz `options` match SPL output fields
- [ ] Grid positions don't overlap excessively
- [ ] Layout `structure` includes all visualization IDs

## Example Workflow

**Input**: "Create a dashboard showing CPU usage and error count from _internal index"

**Output**:

```json
{
  "version": "1.0.0",
  "title": "System Health Dashboard",
  "dataSources": {
    "ds_cpu": {
      "type": "ds.search",
      "options": {
        "query": "index=_internal | bin _time span=5m | stats avg(cpu_seconds) as avg_cpu by _time",
        "queryParameters": { "earliest": "-4h", "latest": "now" }
      }
    },
    "ds_errors": {
      "type": "ds.search",
      "options": {
        "query": "index=_internal log_level=ERROR | stats count as error_count",
        "queryParameters": { "earliest": "-4h", "latest": "now" }
      }
    }
  },
  "visualizations": {
    "viz_cpu": {
      "type": "splunk.timechart",
      "title": "CPU Usage Over Time",
      "dataSources": { "primary": "ds_cpu" },
      "options": {
        "series": [{ "field": "avg_cpu", "name": "Avg CPU" }]
      }
    },
    "viz_errors": {
      "type": "splunk.singlevalue",
      "title": "Total Errors",
      "dataSources": { "primary": "ds_errors" },
      "options": {
        "majorValue": { "field": "error_count" }
      }
    }
  },
  "layout": {
    "type": "absolute",
    "structure": [
      { "item": "viz_errors", "position": { "x": 0, "y": 0, "w": 4, "h": 3 } },
      { "item": "viz_cpu", "position": { "x": 0, "y": 3, "w": 12, "h": 6 } }
    ]
  }
}
```

## Resources

- **Cheatsheet**: `dashboard-studio://cheatsheet` (quick reference)
- **Links**: `dashboard-studio://links` (canonical documentation URLs)
- **Tool**: Use `create_dashboard` with `dashboard_type="studio"` and this JSON as `definition`

---

**Remember**: Output ONLY the JSON definition. Keep it minimal, valid, and suitable for direct use with `create_dashboard`.
