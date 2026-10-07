# Environment files

Each YAML file here is one environment. It lists machine groups and the
Splunk apps that should land on them.

Add an app with:

```yaml
  - inventory_group: search_heads
    apps:
      - source_path: apps/my_ta
```

`inventory_group` is the machine group name from the Deslicer dashboard
(`^[A-Za-z0-9_-]+$` only — CI reject names with spaces or CLI flags; the old
UUID matrix path could not inject argv). `source_path` is a folder in this
repository.

See the repository README for how the repo works and what to do next.
