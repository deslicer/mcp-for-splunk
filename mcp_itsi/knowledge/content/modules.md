# ITSI modules and Content Packs — distilled

> Source: <https://help.splunk.com/en/splunk-it-service-intelligence/splunk-it-service-intelligence/reduce-time-to-insights/4.18/introduction>

> **Heads up:** ITSI modules are being **deprecated** in favour of the
> **Splunk App for Content Packs**. Module Builder was removed in 4.4.0.
> New deployments should prefer Content Packs.

## What modules ship in the box

| Module                                     | Role                                                                |
|--------------------------------------------|---------------------------------------------------------------------|
| ITSI Application Server Module             | App server workload, performance, behaviour.                         |
| ITSI Database Module                       | Database tier monitoring (Oracle, MSSQL, MySQL, PostgreSQL).         |
| ITSI End User Experience Monitoring Module | Page load time, render time, error rates.                            |
| ITSI Load Balancer Module                  | Network LB / ADC health and triage.                                  |
| ITSI Operating System Module               | Auto-discovers and merges OS entities.                               |
| ITSI Storage Module                        | Predefined storage arrays.                                           |
| ITSI Virtualization Module                 | Virtualised compute environments.                                    |
| ITSI Web Server Module                     | Web server performance metrics.                                      |

## Mechanics

Modules are bundles of:

- **Add-ons** that bring data in (sourcetype mapping, CIM compliance).
- **KPI templates** that map metrics onto KPIs.
- **Entity-level drilldowns**.
- **Service templates** for the canonical roles in the module.

ITSI consumes module configuration via files; they're integrated through
the ITSI configuration files described in
"List of ITSI configuration files" in the Administer ITSI manual.

## Splunk App for Content Packs

Content packs are the modern replacement: bundled knowledge objects you
install via the Splunk App for Content Packs. The schema mirrors what
modules used (entities, services, KPI templates) but uses the standard
ITSI REST surface.

## Migration tips

- **Audit existing modules** with `itsi_list_service_templates` and
  `itsi_list_kpi_base_searches` to know what you depend on.
- **Pin add-on versions**. Modules historically shipped with specific
  add-on versions; content packs do not — manage add-on lifecycle
  separately.
- **Re-create custom KPIs** from your modules as service-template KPIs
  before retiring the module.
