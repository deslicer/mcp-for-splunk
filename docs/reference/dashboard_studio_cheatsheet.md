# Splunk Dashboard Studio Cheatsheet (9.4)

A concise reference for authoring Dashboard Studio definitions (JSON) suitable for REST creation via the `create_dashboard` tool.

This file is expected by `get_studio_topic("cheatsheet")` and must be included in the Python package under `docs/reference/`.

## Minimal skeleton

```json
{
  "version": "1.0.0",
  "title": "My Dashboard",
  "dataSources": {},
  "visualizations": {},
  "layout": { "type": "absolute", "options": {} }
}
```

## Key concepts

- Prefer `ds.savedSearch` when possible for performance.
- Bind time picker inputs to tokens and pass them into `queryParameters.earliest/latest`.
- Use `ds.chain` to share a base transforming search.

## References

- https://help.splunk.com/en/splunk-enterprise/create-dashboards-and-reports/dashboard-studio/9.4/source-code-editor/what-is-a-dashboard-definition
- https://help.splunk.com/en/splunk-enterprise/create-dashboards-and-reports/dashboard-studio/9.4/visualizations/add-and-format-visualizations
- https://help.splunk.com/en/splunk-enterprise/create-dashboards-and-reports/dashboard-studio/9.4/configuration-options-reference/visualization-configuration-options
