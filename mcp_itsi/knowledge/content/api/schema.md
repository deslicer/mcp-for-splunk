# ITSI REST API schema (4.21)

> Source: <https://help.splunk.com/en/splunk-it-service-intelligence/splunk-it-service-intelligence/leverage-rest-apis/4.21/itsi-rest-api-schema/itsi-rest-api-schema>
>
> Auto-generated from the ITSI 4.21 REST API schema docs by
> `scripts/itsi_schema`. Do not edit by hand — run the refresh script instead.
> For machine-usable schemas and validation, use the `itsi_get_object_schema`,
> `itsi_list_object_schemas` and `itsi_validate_object_payload` tools.

ITSI stores its configuration in the splunkd KV store. **Do not** write to the
KV store directly — always go through the REST endpoints. Common system fields
(`object_type`, `create_time`, `mod_time`, `_owner`, `_user`, `version`, ...)
are server-generated and read-only.


## Object types

`base_service_template`, `correlation_search`, `deep_dive`, `entity`, `entity_type`, `event_management_state`, `glass_table`, `home_view`, `kpi_base_search`, `kpi_threshold_template`, `maintenance_calendar`, `notable_event_aggregation_policy`, `notable_event_comment`, `notable_event_email_template`, `notable_event_group`, `service`, `team`

## Subordinate structures

`anomaly_detection_algorithm_settings`, `deep_dive_lane_setting`, `entity_rules`, `entity_type_dashboard_drilldown`, `entity_type_data_drilldown`, `entity_type_vital_metrics`, `event_management_export`, `glass_table_icon`, `glass_table_widget_configuration`, `kpi_threshold_levels`, `kpi_threshold_settings`, `service_kpi`, `service_template_kpi`, `time_variate_thresholds_specification`

---

# Object type schemas

## Service Template (`base_service_template`)

**Endpoint:** `/itoa_interface/base_service_template`  

ITSI service templates help you manage shared content for similar services. Services linked to a service template receive content from the service template, such as KPIs and entity rules. You must create a service template from an existing service. The `base_service_template` object contains KPI definitions, entity rules, and any linked services.

**Subordinate objects:** `entity_rules`, `service_template_kpi`

| Field | Type | Req | Description |
| --- | --- | --- | --- |
| `_key` | string | - | Auto-generated unique identifier for this service template. |
| `description` | string | - | User defined description for the service template. |
| `title` | string | yes | Title of this service template. |
| `kpis` | array | - | Array of KPI descriptions for this service template. *(nested: `service_template_kpi`)* |
| `entity_rules` | array | - | Array of rules describing entities referenced by this service template. *(nested: `entity_rules`)* |
| `service_id` | string | - | _key value of the service this service template is generated from. |
| `sec_grp` | string | - | The team the service template belongs to. Service templates can only belong to default_itsi_security_group (Global team). |
| `linked_services` | array | - | Array of services linked to this service template. if the user does not have access to all linked services, the linked_services field only contains the services they have read access to. |
| `total_linked_services` | integer | - | The number of services linked to this service template. |
| `last_sync_error` | string | - | Error message if the last sync operation failed. |
| `sync_status` | string | - | Sync status of service template: "synced", "sync_scheduled", "syncing", "sync failed". |
| `scheduled_time` | string | - | The time to push service template changes to linked services if "sync later" is selected rather than "sync now". |
| `scheduled_job` | object | - | Sync job detail if "sync later" is selected rather than "sync now". |
| `template_tags` | array | - | The service tags contained within the template. |
| `object_type` | string | read-only | Name of the object type. |
| `create_by` | string | read-only | The user who created this object. |
| `create_source` | string | read-only | The sourcetype initiating create. Has value `manual` for user-initiated creates. For internal use only. |
| `create_time` | string | read-only | Timestamp at the time of creation based on UTC time zone. |
| `mod_source` | string | read-only | Sourcetype initiating modification. Has value `manual` for user-initiated modifications. For internal use only. |
| `mod_time` | string | read-only | Timestamp of the last modification based on UTC time zone. |
| `_owner` | string | read-only | Splunk user `nobody`. |
| `_user` | string | read-only | User who performed the most recent operation on this object. |
| `version` | string | read-only | The version of the object. Currently the same as the ITSI app version. |

## Correlation Search (`correlation_search`)

**Endpoint:** `/event_management_interface/correlation_search`  

`correlation_search` contains the data for a correlation search. A correlation search is a recurring search that generates a notable event when search results meet specific conditions. A multi-KPI alert is a type of correlation search.

| Field | Type | Req | Description |
| --- | --- | --- | --- |
| `is_scheduled` | integer | - | Values: 1 means scheduled; 0 means not scheduled. |
| `disabled` | integer | - | Values: 1 means disabled; 0 means enabled. |
| `cron_schedule` | string | - | Schedule searches to run periodically at fixed times, dates, or intervals using a cron expression. Default value is `*/5* * * *` (every 5 minutes). |
| `dispatch.earliest_time` | string | - | Indicates the beginning of the time range for the search. The default value is `-15m`. |
| `dispatch.latest_time` | string | - | Indicates the end of the time range for the search. The default value is `-now`. |
| `description` | string | - | A description of the type of issue the search is intended to detect. |
| `search` | string | - | The Splunk search to run. |
| `name` | string | - | A name that describes the correlation search. For example, "cpu_load_percent". |
| `action.itsi_event_generator.param.title` | string | - | The title to use for the notable event in Episode Review. For example, `mysql-01 server cpu Load %`. |
| `action.itsi_event_generator.param.description` | string | - | A brief phrase to describe the notable event. For example, "This alert triggers when DB CPU load on the mysql-01 server reaches 80%." |
| `action.itsi_event_generator.param.status` | string | - | The triage status of the event in Episode Review. You can provide a token in the format `%fieldname%` to substitute the value of a third-party alert field. Values must match an integer specified in `$SPLUNK_HOME/etc/apps/SA-ITOA/local/itsi_notable_event_status.conf` or `/default/itsi_notable_event_status.conf` if a local version does not exist. By default, these values are 0-5. |
| `action.itsi_event_generator.param.owner` | array | - | The ITSI role to which the notable event is assigned in Episode Review. |
| `action.itsi_event_generator.param.severity` | string | - | The level of importance of the event. You can provide a token in the format `%fieldname%` to substitute the value of a third-party alert field. Values must match an integer specified in `$SPLUNK_HOME/etc/apps/SA-ITOA/local/itsi_notable_event_severity.conf` or `/default/itsi_notable_event_severity.conf` if a local version does not exist. By default, these values are 1-6. |
| `action.itsi_event_generator.param.drilldown_search_title` | string | - | The name of the drilldown search link. You can drill down to a specific Splunk search from an episode in Episode Review. |
| `action.itsi_event_generator.param.drilldown_search_search` | string | - | The Splunk search you drill down to. |
| `action.itsi_event_generator.param.drilldown_search_latest_offset` | string | - | Defines how far ahead from the time of the event to look for related events. |
| `action.itsi_event_generator.param.drilldown_search_earliest_offset` | string | - | Defines how far back from the time of the event to start looking for related events. |
| `action.itsi_event_generator.param.drilldown_title` | string | - | The name of the drilldown website link if you want to drill down to a specific website from the episode in Episode Review. |
| `action.itsi_event_generator.param.drilldown_uri` | string | - | The website you drill down to. |
| `action.itsi_event_generator.param.event_identifier_fields` | string | - | These identifier fields form the event hash field, which is added to every notable event to help identify unique alarm types. |
| `action.itsi_event_generator.param.service_ids` | string | - | One or more ITSI services to which this correlation search applies. You can only specify services that belong to teams for which you have read access. |
| `action.itsi_event_generator.param.entity_lookup_field` | string | - | The field in the data retrieved by the correlation search that is used to look up corresponding entities. For example, `host`. |
| `action.itsi_event_generator.param.search_type` | string | - | search_type = "basic", "composite_kpi_score_type", or composite_kpi_percentage_type |
| `action.itsi_event_generator.param.meta_data` | object | - | One of two JSON object schemas, depending on whether it is a correlation search or a multi-KPI alert. Correlation search object schema: - threshold_health_score - threshold score set by user - threshold_status - threshold status (default is undefined) - suppression criteria fields - alert_type - score or status - is_suppression - if suppression is enabled or not - is_consecutive - if count is consecutive or not - count - minimum number of times if this alert happens - suppression_period - suppression period in minute if it is non-consecutive - min_alert_period - minimum alert period of selected KPIs - run_every - frequency of search in minutes - score_based_kpis - list of KPIs which is added as part of a composite KPI. Each object in the list must have kpiid - <kpi id>, serviceid - <service id>, urgency - <urgency value> Multi-KPI alert object schema: - time_label - time label for time range - percentage_based_kpis - list of KPIs and service IDs included. Each item should contain kpiid - <kpi id>, serviceid - <service id>, label_thresholds - <threshold and operation type for trigger>. label_thresholds data format is as follows: `{ operation : 'OR', // default for now thresholds : [ { severity: <severity name>, percentage: <percentage value>, percentage_operation: '>=', // default for now } ...... ] }` |
| `action.itsi_event_generator.param.editor` | string | - | One of two values: advance_correlation_builder_editor or multi_kpi_alert_editor. It directs to the specific UI page to make edits based on the type of search, correlation search or multi-KPI alert. |
| `action.itsi_event_generator` | integer | - | Value: 1 |
| `actions` | string | - | Value: itsi_event_generator |
| `alert.suppress` | integer | - | Enable suppression to minimize the number of duplicate notable events sent to Episode Review. Values: 1 (means enabled) or 0 (means disabled). |
| `alert.suppress.fields` | string | - | The fields to consider when determining if another event matches the current one. |
| `alert.suppress.period` | string | - | The number of seconds to ignore other events that have the same field values. |
| `action.rss` | integer | - | Included in RSS feed. Values: 1 (means enabled) or 0 (means disabled). |
| `action.email` | integer | - | Send an email when the alert is triggered. Values: 1 (means enabled) or 0 (means disabled). |
| `action.email.to` | string | - | The email addresses to send the email to. |
| `action.email.subject` | string | - | The subject of the email. |
| `action.email.sendcsv` | integer | - | Send an email in CSV format. Values: 1 (means enabled) or 0 (means disabled). |
| `action.email.sendpdf` | integer | - | Send an email with a PDF attachment. Values: 1 (means enabled) or 0 (means disabled). |
| `action.email.inline` | integer | - | Send an email with the text inline. Values: 1 (means enabled) or 0 (means disabled). |
| `action.email.format` | string | - | Default value is pdf. Other values: html, csv. |
| `action.email.sendresults` | string | - | Include alert information as an email attachment. Values: 1 (means enabled) or 0 (means disabled). |
| `action.script` | integer | - | Triggers a shell script if enabled. Values: 1 (means enabled) or 0 (means disabled). |
| `action.script.filename` | string | - | Provide the file name of the shell script to run when this alert is triggered. |
| `object_type` | string | read-only | Name of the object type. |
| `create_by` | string | read-only | The user who created this object. |
| `create_source` | string | read-only | The sourcetype initiating create. Has value `manual` for user-initiated creates. For internal use only. |
| `create_time` | string | read-only | Timestamp at the time of creation based on UTC time zone. |
| `mod_source` | string | read-only | Sourcetype initiating modification. Has value `manual` for user-initiated modifications. For internal use only. |
| `mod_time` | string | read-only | Timestamp of the last modification based on UTC time zone. |
| `_owner` | string | read-only | Splunk user `nobody`. |
| `_user` | string | read-only | User who performed the most recent operation on this object. |
| `version` | string | read-only | The version of the object. Currently the same as the ITSI app version. |

## Deep Dive (`deep_dive`)

**Endpoint:** `/itoa_interface/deep_dive`  

ITSI deep dives are investigative tools that help you identify and troubleshoot issues in your IT environment. You can use deep dives to view KPI search results over time, zoom-in on KPI metrics and log events, and visually correlate root cause. You can add different types of lanes to a deep dive view, including KPI lanes, which let you view KPI metrics in detail. You can also add lanes to view ad hoc and data model searches. `deep_dive` objects contain all of the elements required to render deep dive lanes.

**Subordinate objects:** `deep_dive_lane_setting`

| Field | Type | Req | Description |
| --- | --- | --- | --- |
| `_key` | string | - | Auto-generated unique identifier for this deep dive. |
| `description` | string | - | User-defined description for this deep dive. |
| `title` | string | yes | Name of the deep dive. |
| `object_type` | string | read-only | deep_dive |
| `earliest_time` | string | - | Earliest time for all of the searches in this deep dive. |
| `latest_time` | string | - | Latest time for all of the searches in this deep dive. |
| `focus_id` | string | - | The service id of the service in focus. |
| `topology_id` | string | - | Define the service to be put in focus in the deep dive topology view. If none exists then the focus_id is set as the topology_id. view sidebar |
| `lane_settings_collection` | array | - | <Array of lane settings specifying each lane's configuration. See Deep Dive Lane Settings. *(nested: `deep_dive_lane_setting`)* |
| `is_named` | boolean | - | True when the deep dive is saved, false otherwise. |
| `create_by` | string | read-only | The user who created this object. |
| `create_source` | string | read-only | The sourcetype initiating create. Has value `manual` for user-initiated creates. For internal use only. |
| `create_time` | string | read-only | Timestamp at the time of creation based on UTC time zone. |
| `mod_source` | string | read-only | Sourcetype initiating modification. Has value `manual` for user-initiated modifications. For internal use only. |
| `mod_time` | string | read-only | Timestamp of the last modification based on UTC time zone. |
| `_owner` | string | read-only | Splunk user `nobody`. |
| `_user` | string | read-only | User who performed the most recent operation on this object. |
| `version` | string | read-only | The version of the object. Currently the same as the ITSI app version. |

## Entity (`entity`)

**Endpoint:** `/itoa_interface/entity`  

An entity is a basic unit of configuration in an IT environment that meets a specific need for an IT service. Entities are usually servers, but can be other IT infrastructure components, such as network devices, storage subsystems, applications, and so on. Entities are optional. The `entity` object contains field aliases and values that identify the entity in KPI searches.

| Field | Type | Req | Description |
| --- | --- | --- | --- |
| `_key` | string | - | Auto-generated unique identifier for this entity. Can be any unique value. |
| `title` | string | yes | Name of the entity. Can be any unique value. |
| `description` | string | - | User defined description of the entity. |
| `object_type` | string | read-only | entity |
| `identifier` | object | - | _values_: Array of alias values that identify the entity _fields_: Array of search fields that identify events for the entity. |
| `informational` | object | - | _values_: Array of alias values that provide information/description for the entity. _fields_: Array of search fields to extract information/description of the entity. |
| `services` | array | - | Array of sub-objects with _key and title fields of services monitoring this entity via rules configured in services. |
| `sec_grp` | string | - | The team the object belongs to. The entity object can only belong to default_itsi_security_group (Global team). |
| `sai_entity_key` | string | - | This field exists in ITSI entities that have been merged with SAI entities. It symbolizes the original SAI entities's _key and is used for drilldowns to SAI. |
| `entity_type_ids` | array | - | Array of _key values for each entity type associated with the entity. |
| `create_by` | string | read-only | The user who created this object. |
| `create_source` | string | read-only | The sourcetype initiating create. Has value `manual` for user-initiated creates. For internal use only. |
| `create_time` | string | read-only | Timestamp at the time of creation based on UTC time zone. |
| `mod_source` | string | read-only | Sourcetype initiating modification. Has value `manual` for user-initiated modifications. For internal use only. |
| `mod_time` | string | read-only | Timestamp of the last modification based on UTC time zone. |
| `_owner` | string | read-only | Splunk user `nobody`. |
| `_user` | string | read-only | User who performed the most recent operation on this object. |
| `version` | string | read-only | The version of the object. Currently the same as the ITSI app version. |

## Entity Type (`entity_type`)

**Endpoint:** `/itoa_interface/entity_type`  

An `entity_type` defines how to classify a type of data source. For example, you can create a Linux, Windows, Unix/Linux add-on, VMware, or Kubernetes entity type. An entity type can include zero or more data drilldowns and zero or more dashboard drilldowns. You can use a single data drilldown or dashboard drilldown for multiple entity types.

**Subordinate objects:** `entity_type_dashboard_drilldown`, `entity_type_data_drilldown`, `entity_type_vital_metrics`

| Field | Type | Req | Description |
| --- | --- | --- | --- |
| `title` | string | yes | The name of the entity type. |
| `description` | string | - | A description of the entity type. |
| `dashboard_drilldowns` | array | - | An array of dashboard drilldown objects. Each dashboard drilldown defines an internal or external resource you specify with a URL and parameters that map to one of an entity fields. The parameters are passed to the resource when you open the URL. See [Entity Type Dashboard Drilldown](https://help.splunk.com/en/splunk-it-service-intelligence/splunk-it-service-intelligence/leverage-rest-apis/4.21/itsi-rest-api-schema/itsi-rest-api-schema#db5a9c8d_7a60_4c88_9385_44cf3fb415b5--en__ITSI_REST_API_schema). *(nested: `entity_type_dashboard_drilldown`)* |
| `data_drilldown` | array | - | An array of data drilldown objects. Each data drilldown defines filters for raw data associated with entities that belong to the entity type. See [Entity Type Data Drilldown](https://help.splunk.com/en/splunk-it-service-intelligence/splunk-it-service-intelligence/leverage-rest-apis/4.21/itsi-rest-api-schema/itsi-rest-api-schema#ade3ea81_9cb7_4514_a0c4_dedaa2e5e9f1--en__Entity_Type_Data_Drilldown). *(nested: `entity_type_data_drilldown`)* |
| `vital_metrics` | array | - | An array of vital metric objects. Vital metrics are statistical calculations based on SPL searches that represent the overall health of entities of that type. See [Entity Type Vital Metrics](https://help.splunk.com/en/splunk-it-service-intelligence/splunk-it-service-intelligence/leverage-rest-apis/4.21/itsi-rest-api-schema/itsi-rest-api-schema#id_76df76d8_0f87_4b90_b28d_1cda9f70b7cc--en__Entity_Type_Vital_Metrics). *(nested: `entity_type_vital_metrics`)* |
| `object_type` | string | read-only | Name of the object type. |
| `create_by` | string | read-only | The user who created this object. |
| `create_source` | string | read-only | The sourcetype initiating create. Has value `manual` for user-initiated creates. For internal use only. |
| `create_time` | string | read-only | Timestamp at the time of creation based on UTC time zone. |
| `mod_source` | string | read-only | Sourcetype initiating modification. Has value `manual` for user-initiated modifications. For internal use only. |
| `mod_time` | string | read-only | Timestamp of the last modification based on UTC time zone. |
| `_owner` | string | read-only | Splunk user `nobody`. |
| `_user` | string | read-only | User who performed the most recent operation on this object. |
| `version` | string | read-only | The version of the object. Currently the same as the ITSI app version. |

## Event Management State (`event_management_state`)

**Endpoint:** `/event_management_interface/event_management_state`  

The `event_management_state` object stores user settings for custom saved views of Episode Review. For instructions to save custom views through the UI, see [Save a custom view of Episode Review](https://help.splunk.com/?resourceId=ITSI_EA_CustomizeEpisode) in the _User Manual_.

| Field | Type | Req | Description |
| --- | --- | --- | --- |
| `_key` | string | - | The unique ID for Episode Review view in the KV store. |
| `title` | string | - | A user-defined name for the custom episode review. |
| `earliest` | string | - | The earliest time for the main search in the Episode Review custom view. |
| `latest` | string | - | The latest time for the main search in the Episode Review custom view. |
| `fetchLimit` | integer | - | The maximum number of notable events to fetch in a single request. |
| `sortField` | string | - | The field in the data (column in Episode Review) to sort notable events by. |
| `sortDirection` | string | - | Whether to sort notable events in ascending or descending order. |
| `arbitrarySearch` | string | - | The Splunk search string used to filter raw notable events. |
| `filterCollection` | array | - | A set of filters that represent the Episode Review page filters. |
| `viewingOption` | string | - | Whether to display notable events as standard or prominent mode in Episode Review. |
| `eventDeduplication` | boolean | - | If true, episode view is turned on. Otherwise individual notable events are displayed. |
| `columnsShown` | array | - | A list of fields in the data (columns in Episode Review) to display. |
| `object_type` | string | read-only | Name of the object type. |
| `create_by` | string | read-only | The user who created this object. |
| `create_source` | string | read-only | The sourcetype initiating create. Has value `manual` for user-initiated creates. For internal use only. |
| `create_time` | string | read-only | Timestamp at the time of creation based on UTC time zone. |
| `mod_source` | string | read-only | Sourcetype initiating modification. Has value `manual` for user-initiated modifications. For internal use only. |
| `mod_time` | string | read-only | Timestamp of the last modification based on UTC time zone. |
| `_owner` | string | read-only | Splunk user `nobody`. |
| `_user` | string | read-only | User who performed the most recent operation on this object. |
| `version` | string | read-only | The version of the object. Currently the same as the ITSI app version. |

## Glass Table (`glass_table`)

**Endpoint:** `/itoa_interface/glass_table`  

ITSI glass tables are custom visualizations that let you monitor KPI search results. `glass_table` objects define all widgets and drawing elements that appear in the glass table.

**Subordinate objects:** `glass_table_widget_configuration`, `glass_table_icon`

| Field | Type | Req | Description |
| --- | --- | --- | --- |
| `_key` | string | - | Unique identifier for this glass table. |
| `title` | string | yes | Name of this glass table. |
| `description` | string | - | User-defined description for this glass table. |
| `object_type` | string | read-only | glass_table. |
| `latest` | string | - | Latest time for all of the widget searches on the glass table. |
| `latest_label` | string | - | Latest label displayed in the glass table instant picker. Matches latest attribute. |
| `svg_coordinates` | string | - | x and y viewbox offsets for the glass table. |
| `content` | array | - | Array of JSON structures containing all attributes needed to draw the glass table. See Glass Table Widget Configuration. |
| `is_epoch` | boolean | - | True when the glass table uses a custom (non-preset) time, false otherwise. |
| `templateSelectedServiceId` | string | - | The id of the service currently in focus if templatization is enabled. |
| `templateSwappableServiceIds` | array | - | The array of services available to be swapped to for templatization. |
| `create_by` | string | read-only | The user who created this object. |
| `create_source` | string | read-only | The sourcetype initiating create. Has value `manual` for user-initiated creates. For internal use only. |
| `create_time` | string | read-only | Timestamp at the time of creation based on UTC time zone. |
| `mod_source` | string | read-only | Sourcetype initiating modification. Has value `manual` for user-initiated modifications. For internal use only. |
| `mod_time` | string | read-only | Timestamp of the last modification based on UTC time zone. |
| `_owner` | string | read-only | Splunk user `nobody`. |
| `_user` | string | read-only | User who performed the most recent operation on this object. |
| `version` | string | read-only | The version of the object. Currently the same as the ITSI app version. |

## Service Analyzer (`home_view`)

**Endpoint:** `/itoa_interface/home_view`  

Service Analyzer is the ITSI UI home page. It displays service and KPI health scores that are trending at top severity levels. You can configure Service Analyzer to filter the display of services and KPIs relevant to the user. The Service Analyzer object is called `home_view`.

| Field | Type | Req | Description |
| --- | --- | --- | --- |
| `_key` | string | - | Unique ID for the entry in KV store. |
| `object_type` | string | read-only | home_view |
| `-owner` | string | - | User that creates the saved service analyzer. |
| `title` | string | - | User given title for the service analyzer. |
| `earliest_time` | string | - | Earliest time for the searches. |
| `latest_time` | string | - | Latest time for the searches. |
| `serviceWhitelist` | string | - | List of filtered services. |
| `kpiWhitelist` | string | - | List of filtered kpis. |
| `isServiceFilterEnabled` | boolean | - | True if services are filtered, false by default. |
| `isKpiFilterEnabled` | string | - | True if kpis are filtered, false by default. |
| `serviceTilesSettings` | object | - | SeverityTilesSettingModel with number of kpi tiles and filter. |
| `view` | string | - | Determines if service analyzer view is standard or full screen. Standard is default. |
| `isDefault` | string | - | True if it is the default (standard) service analyzer, false otherwise. |
| `titleSize` | string | - | medium\\|large\], large by default. |
| `searchType` | string | - | maxseverity\] \[aggregate\\|maxseverity\] aggregate shows the most recent service value and the max severity is service value unless there is an entity value with worst severity. |
| `create_by` | string | read-only | The user who created this object. |
| `create_source` | string | read-only | The sourcetype initiating create. Has value `manual` for user-initiated creates. For internal use only. |
| `create_time` | string | read-only | Timestamp at the time of creation based on UTC time zone. |
| `mod_source` | string | read-only | Sourcetype initiating modification. Has value `manual` for user-initiated modifications. For internal use only. |
| `mod_time` | string | read-only | Timestamp of the last modification based on UTC time zone. |
| `_owner` | string | read-only | Splunk user `nobody`. |
| `_user` | string | read-only | User who performed the most recent operation on this object. |
| `version` | string | read-only | The version of the object. Currently the same as the ITSI app version. |

## KPI Base Search (`kpi_base_search`)

**Endpoint:** `/itoa_interface/kpi_base_search`  

Searches that can be aggregated together to reduce overall search load. KPI Base Searches include the core attributes of a KPI for search generation. `kpi_base_search` objects are contained within the KPI (`kpis`) object data structure.

| Field | Type | Req | Description |
| --- | --- | --- | --- |
| `entity_alias_filtering_fields` | string | - | The fields to filter on. See KPI definition. |
| `_version` | string | read-only | ITSI version number of this KPI base search. |
| `description` | string | - | General description for this KPI base search. |
| `mod_source` | string | read-only | Source of the last modification. |
| `mod_time` | string | read-only | The time of the last modification based on UTC time zone. |
| `is_service_entity_filter` | boolean | - | If true a filter is used on the search based on the entities included in the service. |
| `actions` | string | - |  |
| `object_type` | string | read-only | kpi_base_search |
| `is_entity_breakdown` | boolean | - | Determines if search breaks down by entities. |
| `_owner` | string | read-only | KV store owner. |
| `source_itsi_da` | string | - | Source of DA used for this search. See KPI Threshold Templates. |
| `metrics` | array | - | Set of statistical operations performed on threshold field. |
| `aggregate_statop` | string | - | Statistical operation (avg, max, median, stdev, and so on) used to combine data for the aggregate alert_value (used for all KPI). |
| `unit` | string | - | User-defined units for the values in threshold field. |
| `title` | string | yes | Name of this metric |
| `_key` | string | - | Internal identifier. |
| `threshold_field` | string | - | The field on which the statistical operation runs. |
| `entity_statop` | string | - | Statistical operation (avg, max, mean, and so on) used to combine data for alert_values on a per entity basis (used if is_entity_breakdown is true). |
| `search_alert_earliest` | string | - | Earliest time to look for events every time KPI search runs. This determines how far back each time window is during KPI search runs. |
| `alert_period` | string | - | User specified interval to run the KPI search in minutes. |
| `alert_lag` | string | - | Contains the number of seconds of lag to apply to the alert search, max is 30 minutes (1800 seconds). |
| `base_search` | string | - | KPI search defined by user for this KPI. All generated searches for the KPI are based on this search. |
| `entity_id_fields` | string | - | Fields from this KPI's search events that will be mapped to the alias fields defined in entities for the service containing this KPI. This field enables the KPI search to tie the aliases of entities to the fields from the KPI events in identifying entities at search time. |
| `identifying_name` | string | read-only | Internal only |
| `mod_timestamp` | string | read-only | Timestamp of last modification based on UTC time zone. |
| `acl` | object | read-only | Access control blob. |
| `_user` | string | read-only | Like owner, but different. |
| `sec_grp` | string | - | The team the object belongs to. This object can only belong to default_itsi_security_group (Global team). |
| `create_by` | string | read-only | The user who created this object. |
| `create_source` | string | read-only | The sourcetype initiating create. Has value `manual` for user-initiated creates. For internal use only. |
| `create_time` | string | read-only | Timestamp at the time of creation based on UTC time zone. |
| `version` | string | read-only | The version of the object. Currently the same as the ITSI app version. |

## KPI Threshold Templates (`kpi_threshold_template`)

**Endpoint:** `/itoa_interface/kpi_threshold_template`  

A `kpi_threshold_template` is a set of predefined threshold values that you can apply to multiple KPIs.

| Field | Type | Req | Description |
| --- | --- | --- | --- |
| `title` | string | yes | Name of this template. |
| `description` | string | - | Description of this particular template. |
| `adaptive_thresholding_training_window` | string | - | Earliest time for the adaptive threshold training algorithm to run over. The latest time is always `now`. |
| `time_variate_thresholds` | boolean | - | If true, thresholds for alerts are pulled from time_variate_thresholds_specification. |
| `time_variate_thresholds_specification` | object | - | Data structure for time variate threshold specification. |
| `adaptive_thresholds_is_enabled` | boolean | - | If true, adaptive thresholding is enabled for this KPI. |
| `sec_grp` | string | - | The team the object belongs to. This object can only belong to default_itsi_security_group (Global team). |
| `object_type` | string | read-only | Name of the object type. |
| `create_by` | string | read-only | The user who created this object. |
| `create_source` | string | read-only | The sourcetype initiating create. Has value `manual` for user-initiated creates. For internal use only. |
| `create_time` | string | read-only | Timestamp at the time of creation based on UTC time zone. |
| `mod_source` | string | read-only | Sourcetype initiating modification. Has value `manual` for user-initiated modifications. For internal use only. |
| `mod_time` | string | read-only | Timestamp of the last modification based on UTC time zone. |
| `_owner` | string | read-only | Splunk user `nobody`. |
| `_user` | string | read-only | User who performed the most recent operation on this object. |
| `version` | string | read-only | The version of the object. Currently the same as the ITSI app version. |

## Maintenance Calendar (`maintenance_calendar`)

**Endpoint:** `/maintenance_services_interface/maintenance_calendar`  

Use `maintenance_calendar` to put services and entities in maintenance mode at required intervals.

| Field | Type | Req | Description |
| --- | --- | --- | --- |
| `_key` | string | - | Unique ID for the entry in the KV store. |
| `title` | string | - | Title of the maintenance window. |
| `comment` | string | - | Optional description of the maintenance window. |
| `objects` | array | - | Array of dictionaries describing the objects put in maintenance by this maintenance window. The schema for each object definition in the array: `_key`: Unique if assigned to the object currently. `object_type`: Type of object being identified. Currently only `entity` and `service` are supported. |
| `start_time` | string | - | Timestamp that marks the beginning of maintenance window. Based on UTC time. |
| `end_time` | string | - | Timestamp that marks the end of maintenance window. Based on UTC time. |
| `object_type` | string | read-only | Name of the object type. |
| `create_by` | string | read-only | The user who created this object. |
| `create_source` | string | read-only | The sourcetype initiating create. Has value `manual` for user-initiated creates. For internal use only. |
| `create_time` | string | read-only | Timestamp at the time of creation based on UTC time zone. |
| `mod_source` | string | read-only | Sourcetype initiating modification. Has value `manual` for user-initiated modifications. For internal use only. |
| `mod_time` | string | read-only | Timestamp of the last modification based on UTC time zone. |
| `_owner` | string | read-only | Splunk user `nobody`. |
| `_user` | string | read-only | User who performed the most recent operation on this object. |
| `version` | string | read-only | The version of the object. Currently the same as the ITSI app version. |

## Notable Event Aggregation Policy (`notable_event_aggregation_policy`)

**Endpoint:** `/event_management_interface/notable_event_aggregation_policy`  

`notable_event_aggregation_policy` contains the data for a notable event aggregation policy which aggregates notable events into episodes.

| Field | Type | Req | Description |
| --- | --- | --- | --- |
| `disabled` | boolean | - | `1` if the aggregation policy is disabled and `0` if enabled. |
| `breaking_criteria` | object | - | A JSON blob of all the criteria used to break an episode. |
| `filter_criteria` | object | - | A JSON blob of all the criteria used to filter events into an episode. |
| `is_default` | boolean | - | Indicates if this is the default aggregation policy. `1` if it's the default policy and `0` if not. |
| `description` | string | - | The description of the notable event aggregation policy. |
| `group_severity` | string | - | The default severity of each episode created by the notable event aggregation policy. |
| `group_status` | string | - | The default status of each episode created by the notable event aggregation policy. |
| `group_asignee` | string | - | The default owner of each episode created by the notable event aggregation policy. |
| `group_description` | string | - | The default description of each episode created by the notable event aggregation policy. |
| `title` | string | - | The title of the notable event aggregation policy. |
| `rules` | array | - | An array of all the rules and actions to be executed for the notable event aggregation policy. |
| `split_by_field` | string | - | A string containing all the fields to split episodes by. |
| `object_type` | string | read-only | Name of the object type. |
| `create_by` | string | read-only | The user who created this object. |
| `create_source` | string | read-only | The sourcetype initiating create. Has value `manual` for user-initiated creates. For internal use only. |
| `create_time` | string | read-only | Timestamp at the time of creation based on UTC time zone. |
| `mod_source` | string | read-only | Sourcetype initiating modification. Has value `manual` for user-initiated modifications. For internal use only. |
| `mod_time` | string | read-only | Timestamp of the last modification based on UTC time zone. |
| `_owner` | string | read-only | Splunk user `nobody`. |
| `_user` | string | read-only | User who performed the most recent operation on this object. |
| `version` | string | read-only | The version of the object. Currently the same as the ITSI app version. |

## Notable Event Comment (`notable_event_comment`)

**Endpoint:** `/event_management_interface/notable_event_comment`  

`notable_event_comment` contains comments associated with an episode.

| Field | Type | Req | Description |
| --- | --- | --- | --- |
| `comment` | string | - | The text of the comment. |
| `event_id` | string | - | The episode ID that the comment is associated with. |
| `is_group` | boolean | - | The episode ID that the comment is associated with. |
| `filter_search` | string | - | The search to retrieve all the comments for an episode. |
| `earliest_time` | string | - | The time, in UTC, of the first event in the episode. |
| `latest_time` | string | - | The time, in UTC, of the last event in the episode. |
| `object_type` | string | read-only | Name of the object type. |
| `create_by` | string | read-only | The user who created this object. |
| `create_source` | string | read-only | The sourcetype initiating create. Has value `manual` for user-initiated creates. For internal use only. |
| `create_time` | string | read-only | Timestamp at the time of creation based on UTC time zone. |
| `mod_source` | string | read-only | Sourcetype initiating modification. Has value `manual` for user-initiated modifications. For internal use only. |
| `mod_time` | string | read-only | Timestamp of the last modification based on UTC time zone. |
| `_owner` | string | read-only | Splunk user `nobody`. |
| `_user` | string | read-only | User who performed the most recent operation on this object. |
| `version` | string | read-only | The version of the object. Currently the same as the ITSI app version. |

## Notable Event Email Template (`notable_event_email_template`)

**Endpoint:** `/event_management_interface/notable_event_email_template`  

`notable_event_email_template` contains the data for email templates for episode actions. Once you create a template it's available for selection in all aggregation policies and is not policy-specific.

| Field | Type | Req | Description |
| --- | --- | --- | --- |
| `title` | string | - | The name of the message template. This element is required. |
| `message` | string | - | The body of the email. Supports tokens such as `$result.title$` and `$result.description$`. This element is required. |
| `object_type` | string | read-only | Name of the object type. |
| `create_by` | string | read-only | The user who created this object. |
| `create_source` | string | read-only | The sourcetype initiating create. Has value `manual` for user-initiated creates. For internal use only. |
| `create_time` | string | read-only | Timestamp at the time of creation based on UTC time zone. |
| `mod_source` | string | read-only | Sourcetype initiating modification. Has value `manual` for user-initiated modifications. For internal use only. |
| `mod_time` | string | read-only | Timestamp of the last modification based on UTC time zone. |
| `_owner` | string | read-only | Splunk user `nobody`. |
| `_user` | string | read-only | User who performed the most recent operation on this object. |
| `version` | string | read-only | The version of the object. Currently the same as the ITSI app version. |

## Notable Event Group (`notable_event_group`)

**Endpoint:** `/event_management_interface/notable_event_group`  

The `notable_event_group` contains information about an episode.

| Field | Type | Req | Description |
| --- | --- | --- | --- |
| `severity` | string | - | The level of importance of the episode. Values must match an integer specified in the default version of `itsi_notable_event_severity.conf` (or the local version if you created one). Default values: `1` \- Info `2` \- Normal `3` \- Low `4` \- Medium `5` \- High `6` \- Critical |
| `status` | string | - | The triage status of the episode in Episode Review. Values must match an integer specified in the default version of `itsi_notable_event_status.conf` (or the local version if you created one). Default values: `0` \- Unassigned `1` \- New `2` \- In Progress `3` \- Pending `4` \- Resolved `5` \- Closed |
| `owner` | string | - | The Splunk user who is the owner of the episode. |
| `_key` | string | - | The episode ID that a change is associated with. |
| `object_type` | string | read-only | Name of the object type. |
| `create_by` | string | read-only | The user who created this object. |
| `create_source` | string | read-only | The sourcetype initiating create. Has value `manual` for user-initiated creates. For internal use only. |
| `create_time` | string | read-only | Timestamp at the time of creation based on UTC time zone. |
| `mod_source` | string | read-only | Sourcetype initiating modification. Has value `manual` for user-initiated modifications. For internal use only. |
| `mod_time` | string | read-only | Timestamp of the last modification based on UTC time zone. |
| `_owner` | string | read-only | Splunk user `nobody`. |
| `_user` | string | read-only | User who performed the most recent operation on this object. |
| `version` | string | read-only | The version of the object. Currently the same as the ITSI app version. |

## Service (`service`)

**Endpoint:** `/itoa_interface/service`  

An ITSI service is a representation of a real world IT service. You can configure an ITSI service to monitor various IT metrics using KPI searches, which reflect the health of a service. ITSI services can describe any real world IT service, such as a network service or email service. The `service` object contains the service definition, including entities, KPIs, and dependent services.

**Subordinate objects:** `entity_rules`, `service_kpi`

| Field | Type | Req | Description |
| --- | --- | --- | --- |
| `_key` | string | - | Auto-generated unique identifier for this service. |
| `description` | string | - | User defined description for the service. |
| `title` | string | yes | Title of this service. |
| `kpis` | array | - | Array of KPI descriptions for this service. *(nested: `service_kpi`)* |
| `entity_rules` | array | - | Array of rules describing entities referenced by this service. *(nested: `entity_rules`)* |
| `services_depends_on` | array | - | Array of service descriptions with KPIs in those services that this service depends on. |
| `service_id` | string | - | _key value of service that this service depends on. |
| `kpis_depending_on` | array | - | Array of _key ids for each KPI in service identified by serviceid, which this service will depend on. |
| `services_depending_on_me` | array | - | An array of service descriptions with KPIs in this service that those services depend on. |
| `serviceid` | string | - | _key value of service that depends on this service. |
| `enabled` | boolean | - | If set to 1, service is enabled. If value is absent or not set to 1, service is disabled. On upgrade service is flagged as enabled. |
| `sec_grp` | string | - | The team the object belongs to. |
| `base_service_template_id` | string | - | The ID of the service template the service is linked to. Not required. If empty, the service is not linked to a service template. To create a service based on a service template, include this field. |
| `service_tags` | object | - | The tags for the service. The `service_tags` object can have an array for `tags` and `template_tags`. `tags` are regular tags that are added manually and `template_tags` are tags that are populated from a service template. Tags have to be strings and can't contain the following characters: `/ \ " ' ! @ ? . , ; $ ^` Example `service_tags` object: JSONCopy ```json "service_tags": { "tags": [ "unix", "seattle" ], "template_tags": [ "cloud_systems", "us-west" ] }, ``` |
| `object_type` | string | read-only | Name of the object type. |
| `create_by` | string | read-only | The user who created this object. |
| `create_source` | string | read-only | The sourcetype initiating create. Has value `manual` for user-initiated creates. For internal use only. |
| `create_time` | string | read-only | Timestamp at the time of creation based on UTC time zone. |
| `mod_source` | string | read-only | Sourcetype initiating modification. Has value `manual` for user-initiated modifications. For internal use only. |
| `mod_time` | string | read-only | Timestamp of the last modification based on UTC time zone. |
| `_owner` | string | read-only | Splunk user `nobody`. |
| `_user` | string | read-only | User who performed the most recent operation on this object. |
| `version` | string | read-only | The version of the object. Currently the same as the ITSI app version. |

## Team (`team`)

**Endpoint:** `/itoa_interface/team`  

Teams are used to restrict service-level information in the following objects: - Glass tables - Service analyzers - Deep dives - Episode Review - Correlation searches - Multi-KPI alerts The team object is called `team`.

| Field | Type | Req | Description |
| --- | --- | --- | --- |
| `identifying_name` | string | read-only | The name of the team. Does not have to match `title`. |
| `acl` | object | read-only | Access control list for the team. Must include itoa_admin. |
| `title` | string | yes | User provided name of the team. Does not have to match `identifying_name`. |
| `description` | string | - | User provided description of the team. |
| `children` | array | - | List of private teams created in ITSI. For private teams, this field will be an empty list. |
| `parents` | array | - | The parent of this team. Cannot be configured in current release. |
| `_key` | string | - | Unique ID for the entry in KV store. |
| `object_type` | string | read-only | Name of the object type. |
| `create_by` | string | read-only | The user who created this object. |
| `create_source` | string | read-only | The sourcetype initiating create. Has value `manual` for user-initiated creates. For internal use only. |
| `create_time` | string | read-only | Timestamp at the time of creation based on UTC time zone. |
| `mod_source` | string | read-only | Sourcetype initiating modification. Has value `manual` for user-initiated modifications. For internal use only. |
| `mod_time` | string | read-only | Timestamp of the last modification based on UTC time zone. |
| `_owner` | string | read-only | Splunk user `nobody`. |
| `_user` | string | read-only | User who performed the most recent operation on this object. |
| `version` | string | read-only | The version of the object. Currently the same as the ITSI app version. |

---

# Subordinate structure schemas

## Anomaly Detection Algorithm Settings (`anomaly_detection_algorithm_settings`)

**Kind:** subordinate (nested) structure  

| Field | Type | Req | Description |
| --- | --- | --- | --- |
| `Sensitivity` | integer | - | Determines sensitivity of algorithm to variance in data. Note that acceptable values for both trending and cohesive algorithm sensitivity are between 0 and the `sensitivity_max` parameter value, as specified in the respective `[trending:limits]`and `[cohesive:limits`\] stanzas, in `mad.conf` in the `SA-ITSI-MetricAD` namespace. |
| `object_type` | string | read-only | Name of the object type. |
| `create_by` | string | read-only | The user who created this object. |
| `create_source` | string | read-only | The sourcetype initiating create. Has value `manual` for user-initiated creates. For internal use only. |
| `create_time` | string | read-only | Timestamp at the time of creation based on UTC time zone. |
| `mod_source` | string | read-only | Sourcetype initiating modification. Has value `manual` for user-initiated modifications. For internal use only. |
| `mod_time` | string | read-only | Timestamp of the last modification based on UTC time zone. |
| `_owner` | string | read-only | Splunk user `nobody`. |
| `_user` | string | read-only | User who performed the most recent operation on this object. |
| `version` | string | read-only | The version of the object. Currently the same as the ITSI app version. |

## Deep Dive Lane Setting (`deep_dive_lane_setting`)

**Kind:** subordinate (nested) structure  

Configuration settings that define what information a deep dive lane shows. Deep dive views use these settings for per lane configuration.

| Field | Type | Req | Description |
| --- | --- | --- | --- |
| `title` | string | - | Name of the lane to display. |
| `subtitle` | string | - | The subtitle of the lane to display. |
| `laneType` | string | - | The type of lane to render. Possible values: event, kpi, metric (the default). |
| `graphType` | string | - | The type of graph to render |
| `search` | string | - | The search to use to get data for the lane. |
| `searchSource` | string | - | Represents how a search is generated. Possible values: datamodel, ad hoc search, or kpi search. |
| `dataModelSpecification` | object | - | An object showing the selections that went into the generation of the search, null unless searchSource is data model. If defined, it is structured as {datamodel: <Data Model name> object: <Object Name>, field: <Field Info Data Structure>. |
| `dataModelStatOp` | string | - | Stats operation used in the data model search. |
| `dataModelWhereClause` | string | - | Where clause defined during data model search creation. |
| `overwriteKpiTitle` | string | - | Overwrite KPI title with user specified title. |
| `overwriteEntityTitle` | string | - | Overwrite Entity title with user specified title. |
| `kpiTitle` | string | - | The original title of the KPI as defined in the KPI model. |
| `kpiServiceId` | string | - | The id of the service associated with the selected KPI. |
| `kpiUnit` | string | - | The unit of the KPI driving this lane. |
| `kpiAddToSummary` | string | - | Add or remove from kpi summary based on user selection. \[yes, no\] Yes runs the search against kpi summary index and no runs raw search. |
| `kpiStatsOp` | string | - | Stats operation to calculate the KPI value, avg by default \[avg, max, min, median\]. |
| `entityAddToSummary` | string | - | Shows the accelerated output for entity lanes. Always set to "yes." |
| `thresholdIndicationEnabled` | string | - | Enable/disable threshold indication. Disabled by default. |
| `thresholdIndicationType` | string | - | Type of threshold indication. \[foreground/background\] Foreground selected by default. |
| `hideGraph` | string | - | Only available with background threshold indications. If selected, hides the graph and only shows the top view with background thresholds \[yes, no\]. |
| `verticalAxisScale` | string | - | Determines the scale of the y axis. It is linear or log. |
| `verticalAxisBoundaryType` | string | - | Determine the extent of the y axis. It is staticValue, value, or zeroValue. |
| `verticalAxisStaticBounds` | object | - | If static, these are the bounds to use. Otherwise this is ignored. This is an object of the form\[<min number>, <max number>\]. |
| `dataGaps` | string | - | null values in the data can be represented as gaps or connected through the graph. |
| `graphColor` | string | - | The color of the graph to render. |
| `graphSeries` | string | - | The field in the data which to plot as the range, if unspecified plots all. |
| `excludeSeries` | string | - | The series of data to omit from being displayed in graph. Series with a leading _ (indicating internal use) is always excluded. |
| `laneOverlaySettingsModel` | object | - | Model to define the overlay lane settings. |
| `object_type` | string | read-only | Name of the object type. |
| `create_by` | string | read-only | The user who created this object. |
| `create_source` | string | read-only | The sourcetype initiating create. Has value `manual` for user-initiated creates. For internal use only. |
| `create_time` | string | read-only | Timestamp at the time of creation based on UTC time zone. |
| `mod_source` | string | read-only | Sourcetype initiating modification. Has value `manual` for user-initiated modifications. For internal use only. |
| `mod_time` | string | read-only | Timestamp of the last modification based on UTC time zone. |
| `_owner` | string | read-only | Splunk user `nobody`. |
| `_user` | string | read-only | User who performed the most recent operation on this object. |
| `version` | string | read-only | The version of the object. Currently the same as the ITSI app version. |

## Entity Rules (`entity_rules`)

**Kind:** subordinate (nested) structure  

`entity_rules` determine the specific entities that a KPI monitors in a service. This includes entities directly identified by title, and entities identified by regular expression-based rules.

| Field | Type | Req | Description |
| --- | --- | --- | --- |
| `rule_condition` | string | - | Uses the value AND indicating this rule appends all nested rules contained in the `rule_items` attribute. |
| `rule_items` | array | - | Array of rules that are appended within a rule group. |
| `field` | string | - | The field in the entity definition to compare values to evaluate this rule. |
| `rule_type` | string | - | Takes values `not` or `matches` to indicate whether it's an inclusion or exclusion rule. Value can be `matchesblank` or `doesnotmatchblank` when used with service templates. |
| `value` | string | - | Values to evaluate in the rule. To specify multiple values, separate them with a comma. Values are not case sensitive. |
| `field_type` | string | - | Takes values `alias` or `info` specifying in which category of fields the `field` attribute is located. |
| `object_type` | string | read-only | Name of the object type. |
| `create_by` | string | read-only | The user who created this object. |
| `create_source` | string | read-only | The sourcetype initiating create. Has value `manual` for user-initiated creates. For internal use only. |
| `create_time` | string | read-only | Timestamp at the time of creation based on UTC time zone. |
| `mod_source` | string | read-only | Sourcetype initiating modification. Has value `manual` for user-initiated modifications. For internal use only. |
| `mod_time` | string | read-only | Timestamp of the last modification based on UTC time zone. |
| `_owner` | string | read-only | Splunk user `nobody`. |
| `_user` | string | read-only | User who performed the most recent operation on this object. |
| `version` | string | read-only | The version of the object. Currently the same as the ITSI app version. |

## Entity Type Dashboard Drilldown (`entity_type_dashboard_drilldown`)

**Kind:** subordinate (nested) structure  

A `dashboard_drilldown` lists the dashboards associated with an entity and its entity type.

| Field | Type | Req | Description |
| --- | --- | --- | --- |
| `title` | string | - | The name of the dashboard. |
| `id` | string | - | A unique identifier for the dashboard. |
| `base_url` | string | - | An internal or external URL that points to the dashboard. This setting exists because for internal purposes, navigation suggestions are treated as dashboards. This setting is only required if `is_splunk_dashboard` is `false`. |
| `is_splunk_dashboard` | boolean | - | `true` if the dashboard is a Splunk XML dashboard. If it's another dashboard type such as a JSON dashboard from the Splunk Dashboards app, or if it's a navigation link, this value is `false`. |
| `dashboard_type` | string | - | The type of dashboard being added. This element is required. The following options are available: - `xml_dashboard` \- a Splunk XML dashboard. Any dashboards you add must be of this type. - `navigation_link` \- a navigation URL. Should be used when `base_url` is specified. |
| `params` | object | - | A set of parameters for the entity dashboard drilldown that provide a mapping of a URL parameter and its alias and static parameters. |
| `object_type` | string | read-only | Name of the object type. |
| `create_by` | string | read-only | The user who created this object. |
| `create_source` | string | read-only | The sourcetype initiating create. Has value `manual` for user-initiated creates. For internal use only. |
| `create_time` | string | read-only | Timestamp at the time of creation based on UTC time zone. |
| `mod_source` | string | read-only | Sourcetype initiating modification. Has value `manual` for user-initiated modifications. For internal use only. |
| `mod_time` | string | read-only | Timestamp of the last modification based on UTC time zone. |
| `_owner` | string | read-only | Splunk user `nobody`. |
| `_user` | string | read-only | User who performed the most recent operation on this object. |
| `version` | string | read-only | The version of the object. Currently the same as the ITSI app version. |

## Entity Type Data Drilldown (`entity_type_data_drilldown`)

**Kind:** subordinate (nested) structure  

A `data_drilldown` is a basic unit of configuration for an entity type. Entity data drilldown specifies filters that correlate raw data in Splunk indexes with an entity.

| Field | Type | Req | Description |
| --- | --- | --- | --- |
| `title` | string | - | Name of the drilldown. |
| `type` | string | - | Type of raw data to associate with. Must be either `metrics` or `events`. |
| `static_filter` | object | - | Filter down to a subset of raw data associated with the entity using static information like sourcetype. |
| `entity_field_filter` | array | - | Further filter down to the raw data associated with the entity based on a set of selected entity alias or informational fields. |
| `object_type` | string | read-only | Name of the object type. |
| `create_by` | string | read-only | The user who created this object. |
| `create_source` | string | read-only | The sourcetype initiating create. Has value `manual` for user-initiated creates. For internal use only. |
| `create_time` | string | read-only | Timestamp at the time of creation based on UTC time zone. |
| `mod_source` | string | read-only | Sourcetype initiating modification. Has value `manual` for user-initiated modifications. For internal use only. |
| `mod_time` | string | read-only | Timestamp of the last modification based on UTC time zone. |
| `_owner` | string | read-only | Splunk user `nobody`. |
| `_user` | string | read-only | User who performed the most recent operation on this object. |
| `version` | string | read-only | The version of the object. Currently the same as the ITSI app version. |

## Entity Type Vital Metrics (`entity_type_vital_metrics`)

**Kind:** subordinate (nested) structure  

`vital_metrics` are a basic unit of configuration for an entity type. Vital metrics are statistical calculations based on SPL searches that represent the overall health of entities of that type.

| Field | Type | Req | Description |
| --- | --- | --- | --- |
| `metric_name` | string | - | The title of the vital metric. When creating vital metrics, it's a best practice to include the aggregation method and the name of the metric being calculated. For example, `Average CPU usage`. |
| `search` | string | - | The search that computes the vital metric. The search must specify the following fields: - `val` for the value of the metric. - `_time` because the UI attempts to render changes over time. You can achieve this by adding `span={time}` to your search. - Fields as described in the `split_by_fields` configuration of this vital metric. For example, your search should be split by `host,region` if the `split_by_fields` configuration is \[ "host", "region" \]. |
| `split_by_fields` | array | - | The fields that the `search` configuration is split on. Make sure the value matches the split by fields in the actual search. For example: search = "..... by host, region" split_by_fields = \["host", "region"\] |
| `matching_entity_fields` | array | - | Specifies the aliases of an entity to use to match with the fields specified by `split_by_fields` in the search result. The order of values should match the order of split_by_fields and the mapping is 1 to 1, so they must be of the same length. For example: split_by_fields = \["InstanceId", "region"\] matching_entity_fields = \["instance_id, zone"\] Note: You can only use entity aliases for this field, not informational fields |
| `is_key` | boolean | - | Indicates if the vital metric specified is a key metric. A key metric calculates the distribution of entities associated with the entity type to indicate the overall health of the entity type. The key metric is rendered as a histogram in the Infrastructure Overview. Only one vital metric can have `is_key` set to `true`. |
| `unit` | string | - | The unit of the vital metric. For example, `KB/s`. |
| `alert_rule` | object | - | Displays vital metric alert threshold information. The following parameters are displayed: - `suppress_time`: suppress the alert until this time - `cron_schedule`: frequency of alert search - `is_enabled`: if alert is enabled - `critical_threshold`: range of values that indicate critical severity level - `warning_threshold`: range of values that indicate warning severity level - `info_threshold`: range of values that indicate info severity level - `entity_filter`: filter entities based on the field dimensions For example: entity_filter: \[{"field":"os", "value":"Ubuntu", "field_type":"info"}\] |
| `object_type` | string | read-only | Name of the object type. |
| `create_by` | string | read-only | The user who created this object. |
| `create_source` | string | read-only | The sourcetype initiating create. Has value `manual` for user-initiated creates. For internal use only. |
| `create_time` | string | read-only | Timestamp at the time of creation based on UTC time zone. |
| `mod_source` | string | read-only | Sourcetype initiating modification. Has value `manual` for user-initiated modifications. For internal use only. |
| `mod_time` | string | read-only | Timestamp of the last modification based on UTC time zone. |
| `_owner` | string | read-only | Splunk user `nobody`. |
| `_user` | string | read-only | User who performed the most recent operation on this object. |
| `version` | string | read-only | The version of the object. Currently the same as the ITSI app version. |

## Event Management Export (`event_management_export`)

**Kind:** subordinate (nested) structure  

itsi\_event\_management\_export contains information about an episode.

| Field | Type | Req | Description |
| --- | --- | --- | --- |
| `export_filename` | string | - | The file name for the new file export. |
| `object_type` | string | read-only | event_management_export |
| `status` | string | - | The status of the CSV file export: started, in progress, failed, completed. |
| `_owner` | string | read-only | The Splunk user who owns the CSV file. |
| `_key` | string | - | A unique identifier to determine the CSV file object. |
| `create_by` | string | read-only | The user who created this object. |
| `create_source` | string | read-only | The sourcetype initiating create. Has value `manual` for user-initiated creates. For internal use only. |
| `create_time` | string | read-only | Timestamp at the time of creation based on UTC time zone. |
| `mod_source` | string | read-only | Sourcetype initiating modification. Has value `manual` for user-initiated modifications. For internal use only. |
| `mod_time` | string | read-only | Timestamp of the last modification based on UTC time zone. |
| `_user` | string | read-only | User who performed the most recent operation on this object. |
| `version` | string | read-only | The version of the object. Currently the same as the ITSI app version. |

## Glass Table Icon (`glass_table_icon`)

**Kind:** subordinate (nested) structure  

Contains SVG icon definitions and metadata for glass table icons.

| Field | Type | Req | Description |
| --- | --- | --- | --- |
| `_key` | string | - | Auto-generated unique identifier for this icon. |
| `title` | string | - | Name of the icon. |
| `category` | string | - | Category of the icon. |
| `default_width` | integer | - | Width of the icon. |
| `default_height` | integer | - | Height of the icon. |
| `svg_path` | string | - | SVG path defining shape of the icon. |
| `immutable` | boolean | - | Should the REST API allow editing of this icon. False for all icons imported from .conf files. |
| `_time` | string | - | Timestamp when the icon was added. |
| `_owner` | string | read-only | Name of the user that added this icon. |
| `object_type` | string | read-only | Name of the object type. |
| `create_by` | string | read-only | The user who created this object. |
| `create_source` | string | read-only | The sourcetype initiating create. Has value `manual` for user-initiated creates. For internal use only. |
| `create_time` | string | read-only | Timestamp at the time of creation based on UTC time zone. |
| `mod_source` | string | read-only | Sourcetype initiating modification. Has value `manual` for user-initiated modifications. For internal use only. |
| `mod_time` | string | read-only | Timestamp of the last modification based on UTC time zone. |
| `_user` | string | read-only | User who performed the most recent operation on this object. |
| `version` | string | read-only | The version of the object. Currently the same as the ITSI app version. |

## Glass Table Widget Configuration (`glass_table_widget_configuration`)

**Kind:** subordinate (nested) structure  

Glass Table Widget Configuration (`content`) is an array of JSON structures that contains all of the attributes needed to render the glass table. Each element of the array represents one glass table widget, and the attributes of the element are parsed into a glass table BaseWidgetViewManager object.

| Field | Type | Req | Description |
| --- | --- | --- | --- |
| `search` | string | - | The search to power the widget. |
| `labelVal` | string | - | The text to show in the label located beneath the widget. |
| `labelFlag` | boolean | - | True if labelVal is to be shown with the widget, false otherwise. |
| `vizType` | integer | - | Numeric indication of which visualization type the widget is - SingleValue, Gauge, Sparkline, SVD from 0-3, respectively |
| `threshold_field` | string | - | Field in data to which thresholds apply. |
| `threshold_comparator` | string | - | Comparator used for threshold severity computation |
| `threshold_values` | array | - | Array of values to indicate the bounds of the thresholds set for the widget. |
| `threshold_labels` | array | - | Array of labels to match the threshold values set for the widget. |
| `context_id` | string | - | Id of service to which the widget's KPI belongs. |
| `kpi_id` | string | - | Id of KPI the widget represents |
| `searchSource` | string | - | Source of search for glass table widget - can be datamodel or ad hoc. |
| `dataModelSpecification` | string | - | Data model specification for the datamodel search. |
| `dataModelStatOp` | string | - | Datamodel stats operation for the datamodel search. |
| `dataModelWhereClause` | string | - | Datamodel where clause for the datamodel search. |
| `threshold_eval` | string | - | Threshold eval search clause for threshold severity evaluation. |
| `aggregate_eval` | string | - | Aggregate eval search clause for threshold severity evaluation. |
| `base_search` | string | - | Base search of the KPI the widget represents. |
| `search_alert_earliest` | string | - | Earliest time for the search that powers the widget. |
| `entities` | string | - | List of entities that the widget's KPI contains. |
| `search_aggregate` | string | - | Aggregate search of the KPI the widget represents. |
| `search_time_series_aggregate` | string | - | Time series search of the KPI the widget represents |
| `search_time_compare` | string | - | Compare time series search of the KPI the widget represents (for the SVD viz type). |
| `search_type` | string | - | Type of search the widget is powered by. Must match one of the search_\* attributes of the widget. |
| `relativeEarliest` | string | - | Earliest time (in relative units) for the search that powers the widget. |
| `defaultWidth` | integer | - | Initial width to use for the widget. |
| `defaultHeight` | integer | - | Initial height to use for the widget. |
| `existingKPI` | boolean | - | True if KPI exists in user's system, false otherwise. |
| `alert_on` | string | - | Threshold alert type (aggregate or entities) of the KPI the widget represents. |
| `isThresholdEnabled` | boolean | - | True if thresholds should be applied to the widget's search results, false otherwise. |
| `useKPISummary` | boolean | - | true if widget uses the kpi_summary_index to power its search, false otherwise. |
| `unit` | string | - | Unit string for widget to display. |
| `gap_severity` | string | - | Gap severity value of the KPI the widget represents. |
| `gap_severity_color` | string | - | Gap severity color of the KPI the widget represents. |
| `drilldownSettingsModel` | string | - | Model to hold properties required for generating URLs for custom drilldown. |
| `useCustomDrilldown` | boolean | - | True if widget has custom drilldown turned on, false otherwise. |
| `object_type` | string | read-only | Name of the object type. |
| `create_by` | string | read-only | The user who created this object. |
| `create_source` | string | read-only | The sourcetype initiating create. Has value `manual` for user-initiated creates. For internal use only. |
| `create_time` | string | read-only | Timestamp at the time of creation based on UTC time zone. |
| `mod_source` | string | read-only | Sourcetype initiating modification. Has value `manual` for user-initiated modifications. For internal use only. |
| `mod_time` | string | read-only | Timestamp of the last modification based on UTC time zone. |
| `_owner` | string | read-only | Splunk user `nobody`. |
| `_user` | string | read-only | User who performed the most recent operation on this object. |
| `version` | string | read-only | The version of the object. Currently the same as the ITSI app version. |

## KPI Threshold Levels (`kpi_threshold_levels`)

**Kind:** subordinate (nested) structure  

KPI Threshold Levels determine how ITSI extracts health status information from KPI searches. Threshold levels are user-configured values that can be augmented further using adaptive thresholding.

| Field | Type | Req | Description |
| --- | --- | --- | --- |
| `thresholdValue` | integer | - | Value for the threshold field stats identifying this threshold level. This is the key value that defines the levels for values derived from the KPI search metrics. |
| `severityColor` | string | - | Severity color assigned for this threshold level. |
| `severityColorLight` | string | - | Severity light color assigned for this threshold level. |
| `severityValue` | integer | - | Severity value assigned for this threshold level. |
| `severityLabel` | string | - | Severity label assigned for this threshold level like info, warning, critical, etc. |
| `dynamicParam` | integer | - | Value of the dynamic parameter for adaptive thresholds. |
| `object_type` | string | read-only | Name of the object type. |
| `create_by` | string | read-only | The user who created this object. |
| `create_source` | string | read-only | The sourcetype initiating create. Has value `manual` for user-initiated creates. For internal use only. |
| `create_time` | string | read-only | Timestamp at the time of creation based on UTC time zone. |
| `mod_source` | string | read-only | Sourcetype initiating modification. Has value `manual` for user-initiated modifications. For internal use only. |
| `mod_time` | string | read-only | Timestamp of the last modification based on UTC time zone. |
| `_owner` | string | read-only | Splunk user `nobody`. |
| `_user` | string | read-only | User who performed the most recent operation on this object. |
| `version` | string | read-only | The version of the object. Currently the same as the ITSI app version. |

## KPI Threshold Settings (`kpi_threshold_settings`)

**Kind:** subordinate (nested) structure  

KPI Threshold Settings define the thresholds that a KPI uses to compute health status information. KPI Threshold Settings also contain information for rendering KPI threshold graphs.

**Subordinate objects:** `kpi_threshold_levels`

| Field | Type | Req | Description |
| --- | --- | --- | --- |
| `gaugeMin` | integer | - | Minimum value for the threshold gauge specified by user. |
| `gaugeMax` | integer | - | Maximum value for the threshold gauge specified by user. |
| `search` | string | - | Generated search used to compute the thresholds for this KPI. |
| `baseSeverityValue` | integer | - | Value for base threshold level. |
| `baseSeverityColor` | string | - | Severity color assigned for the base threshold level. |
| `baseSeverityColorLight` | string | - | Severity light color assigned for the base threshold level. |
| `baseSeverityLabel` | string | - | Severity label assigned for the base threshold level, including info, warning, critical, etc. |
| `metricField` | string | - | Thresholding field from the search. |
| `renderBoundaryMin` | integer | - | Lower bound value to use to render the graph for the thresholds. |
| `renderBoundaryMax` | integer | - | Upper bound value to use to render the graph for the thresholds. |
| `isMaxStatic` | boolean | - | True when maximum threshold value is a static value, false otherwise. |
| `isMinStatic` | boolean | - | True when min threshold value is a static value, false otherwise. |
| `object_type` | string | read-only | Name of the object type. |
| `create_by` | string | read-only | The user who created this object. |
| `create_source` | string | read-only | The sourcetype initiating create. Has value `manual` for user-initiated creates. For internal use only. |
| `create_time` | string | read-only | Timestamp at the time of creation based on UTC time zone. |
| `mod_source` | string | read-only | Sourcetype initiating modification. Has value `manual` for user-initiated modifications. For internal use only. |
| `mod_time` | string | read-only | Timestamp of the last modification based on UTC time zone. |
| `_owner` | string | read-only | Splunk user `nobody`. |
| `_user` | string | read-only | User who performed the most recent operation on this object. |
| `version` | string | read-only | The version of the object. Currently the same as the ITSI app version. |

## Service KPI (`service_kpi`)

**Kind:** subordinate (nested) structure  

KPI is the data structure that drives the monitoring of service metrics. Each KPI object contains specific information, including a user-configured base search, from which ITSI generates the search that monitors a metric. KPI objects also contain information on how to apply thresholds that determine the metric severity level. KPI objects (`kpis`) are defined and contained within the `service` object type data structure.

| Field | Type | Req | Description |
| --- | --- | --- | --- |
| `_key` | string | - | Auto-generated unique ID for this KPI. |
| `title` | string | - | User-defined name for the KPI |
| `description` | string | - | User-defined description for the KPI. |
| `type` | string | - | kpi_primary |
| `kpi_threshold_template_id` | string | - | User-defined ID for the KPI. Used to refer to KPIs within a KPI template in modules. This uniquely identifies a KPI template in ITSI. |
| `isadhoc` | boolean | - | If true the search is split on entities and thresholds are computed for both entity and aggregate. |
| `is_service_entity_filter` | boolean | - | If true a filter is used on the search based on the entities included in the service. |
| `datamode` | string | - | The data model to use for search generation if this is a data model type search. |
| `datamodel_filter` | array | - | ITSI generated clauses for user-defined filters on top of the data model fields. Used in the KPI search to filter events required by this KPI. |
| `threshold_field` | string | - | User-specified field on which statistical operations are performed and whose value determines KPI health. |
| `entity_statop` | string | - | Statistical operation (avg, max, mean, and so on) used to combine data for alert_values on a per entity basis (used if entity_breakdown is true). |
| `aggregate_statop` | string | - | Statistical operation (avg, max, median, stdev, and so on) used to combine data for the aggregate alert_value (used for all KPI). |
| `urgency` | integer | - | User-assigned importance value for this KPI. |
| `unit` | string | - | User-defined units for the values in threshold field. |
| `entity_id_fields` | string | - | Fields from this KPI's search events that will be mapped to the alias fields defined in entities for the service containing this KPI. This field enables the KPI search to tie the aliases of entities to the fields from the KPI events in identifying entities at search time. |
| `entity_alias_filtering_fields` | string | - | Subset of aliases from all entities included in the service containing this KPI, to restrict this KPI to only the subset of entities matching via the subset of aliases. Helps filter entities for this KPI among the ones selected in the service containing this KPI. |
| `cron_schedule` | string | - | The cron schedule that determines the frequency of this KPI search. |
| `base_search` | string | - | KPI search defined by user for this KPI. All generated searches for the KPI are based on this search. |
| `kpi_base_search` | string | - | A basic search generated for the KPI search. |
| `search` | string | - | Generated search for this KPI for base statistics on the threshold field. |
| `search_entities` | string | - | Generated search for this KPI for base statistics on the threshold field to use for "Per Entity" threshold type. |
| `search_aggregate` | string | - | Generated search for this KPI for base statistics on the threshold field to use for "Aggregate" or "Both" threshold type. |
| `search_time_series` | string | - | Generated search used primarily to show preview information in the KPI configuration page. |
| `search_time_series_entities` | string | - | Generated search used primarily to show preview information for "Per Entity" threshold type in the KPI configuration page |
| `search_time_series_aggregate` | string | - | Generated search used primarily to show preview information for "Aggregate" or "Both" threshold type in the KPI configuration page. |
| `search_time_compare` | string | - | Generated search used specifically by glass table. |
| `search_alert` | string | - | Generated search used for alerting based on KPI threshold. This is the search that runs on schedule via the saved search for this KPI. |
| `search_alert_entities` | string | - | Generated search to use for alerting based on KPI threshold for "Per Entity" threshold type. |
| `alert_on` | string | - | Specified if the threshold type for this KPI is "Per Entity" or "Aggregate" or "Both". Possible values: aggregate, entities, both. |
| `alert_period` | string | - | User specified interval to run the KPI search in minutes. |
| `alert_lag` | integer | - | Contains the number of seconds of lag to apply to the alert search. The maximum value is 30 minutes (1800 seconds). |
| `search_alert_earliest` | string | - | Earliest time to look for events every time KPI search runs. This determines how far back each time window is during KPI search runs. |
| `tz_offset` | string | - | ISO time zone offset. Note: Do not change this value. |
| `time_variate_thresholds` | boolean | - | If true, thresholds for alerts are pulled from time_variate_thresholds_specification. |
| `time_variate_thresholds_specification` | object | - | Data structure for time variate threshold specs. *(nested: `time_variate_thresholds_specification`)* |
| `backfill_enabled` | boolean | - | Indicates if backfill has been enabled for this KPI |
| `backfill_earliest_time` | string | - | Requested earliest time for backfill (relative time offset). Should be in the format `-Xd`, where 'd' means the time is in days, 'X' is number of days to backfill, and '-' means the date is in the past. |
| `adaptive_thresholds_is_enabled` | boolean | - | Determines if adaptive threshold is enabled for this KPI. |
| `adaptive_thresholding_training_window` | string | - | Earliest time for the Adaptive Threshold training algorithm to run over (latest time is always 'now') (e.g. '-7d') |
| `anomaly_detection_is_enabled` | boolean | - | Determines if trending anomaly detection is enabled. |
| `cohesive_anomaly_detection_is_enabled` | boolean | - | Determines if cohesive anomaly detection is enabled. |
| `anomaly_detection_alerting_enabled` | boolean | - | Determines if anomaly detection will alert for anomalies. |
| `anomaly_detection_training_window` | string | - | Earliest time for the training algorithm to run over (latest time is always 'now') (e.g. '-7d'). |
| `trending_ad` | object | - | Data structure for trending anomaly detection algorithm settings. See [Anomaly Detection Algorithm Settings](https://help.splunk.com/en/splunk-it-service-intelligence/splunk-it-service-intelligence/leverage-rest-apis/4.21/itsi-rest-api-schema/itsi-rest-api-schema#id_4278bd48_f68a_48ce_8396_b710dc0c3eb2--en__Anomaly_Detection_Algorithm_Settings). *(nested: `anomaly_detection_algorithm_settings`)* |
| `cohesive_ad` | object | - | Data structure for cohesive anomaly detection algorithm settings. See [Anomaly Detection Algorithm Settings](https://help.splunk.com/en/splunk-it-service-intelligence/splunk-it-service-intelligence/leverage-rest-apis/4.21/itsi-rest-api-schema/itsi-rest-api-schema#id_4278bd48_f68a_48ce_8396_b710dc0c3eb2--en__Anomaly_Detection_Algorithm_Settings). *(nested: `anomaly_detection_algorithm_settings`)* |
| `gap_severity` | string | - | Severity level assigned for data gaps (info, normal, low, medium, high, critical, or unknown) |
| `gap_severity_color` | string | - | Severity color assigned for data gaps. |
| `gap_severity_color_light` | string | - | Severity color assigned for data gaps. |
| `gap_severity_value` | string | - | Severity value assigned for data gaps. |
| `entity_thresholds` | object | - | User-defined thresholding levels for "Per Entity" threshold type. For more information, see KPI Threshold Setting. *(nested: `kpi_threshold_settings`)* |
| `aggregate_thresholds` | array | - | User-defined thresholding levels for "Aggregate" threshold type. For more information, see KPI Threshold Setting. *(nested: `kpi_threshold_settings`)* |
| `enabled` | boolean | - | If set to 1, KPI is enabled. If absent or not set to 1, KPI is disabled. On upgrade KPI is flagged as enabled. Field is read-only. |
| `base_service_template_id` | string | - | The key of service template object if the KPI is inherited from a service template. |
| `entity_breakdown_id_field` | string | - | KPI search events are split by the alias field defined in entities for the service containing this KPI. |
| `aggregate_outlier_detection_enabled` | boolean | - | Indicates if outlier exclusion is turned on for KPI. |
| `outlier_detection_algo` | string | - | Determines the outlier detection algorithm. |
| `outlier_detection_sensitivity` | string | - | The trigger threshold of the algorithm. For the standard deviation, this is the number of standard deviations. For interquartile range and mean absolute deviation, this is the sensitivity value. |
| `recommendation_start_date` | string | - | The date that a KPI threshold recommendation will be applied. |
| `recommendation_training_window` | string | - | String |
| `threshold_direction` | string | - | Determines if your KPI should stay above or below a specific value, or constrained to a specific range. |
| `object_type` | string | read-only | Name of the object type. |
| `create_by` | string | read-only | The user who created this object. |
| `create_source` | string | read-only | The sourcetype initiating create. Has value `manual` for user-initiated creates. For internal use only. |
| `create_time` | string | read-only | Timestamp at the time of creation based on UTC time zone. |
| `mod_source` | string | read-only | Sourcetype initiating modification. Has value `manual` for user-initiated modifications. For internal use only. |
| `mod_time` | string | read-only | Timestamp of the last modification based on UTC time zone. |
| `_owner` | string | read-only | Splunk user `nobody`. |
| `_user` | string | read-only | User who performed the most recent operation on this object. |
| `version` | string | read-only | The version of the object. Currently the same as the ITSI app version. |

## Service Template KPI (`service_template_kpi`)

**Kind:** subordinate (nested) structure  

KPI is the data structure that drives the monitoring of service metrics. KPI objects for service templates differ slightly from KPI objects for services. For example, service template KPIs can only use base searches, not ad hoc searches or searches based on data models. You can't enable anomaly detection for service template KPIs. KPI objects, `kpis`, for service templates are defined and contained within the `base_service_template` object type data structure.

**Subordinate objects:** `kpi_threshold_settings`, `time_variate_thresholds_specification`, `anomaly_detection_algorithm_settings`

| Field | Type | Req | Description |
| --- | --- | --- | --- |
| `_key` | string | - | Auto-generated unique ID for this KPI. |
| `title` | string | - | User-defined name for the KPI |
| `description` | string | - | User-defined description for the KPI. |
| `type` | string | - | kpi_primary. |
| `kpi_threshold_template_id` | string | - | User-defined ID for the KPI. Used to refer to KPIs within a KPI template in ITSI modules. This uniquely identifies a KPI template in ITSI. |
| `is_service_entity_filter` | boolean | - | If true a filter is used on the search based on the entities included in the service. |
| `datamode` | string | - | The data model to use for search generation if this is a data model type search. |
| `datamodel_filter` | array | - | ITSI generated clauses for user-defined filters on top of the data model fields. Used in the KPI search to filter events required by this KPI. |
| `threshold_field` | string | - | User-specified field on which statistical operations are performed and whose value determines KPI health. |
| `entity_statop` | string | - | Statistical operation (avg, max, mean, and so on) used to combine data for alert_values on a per entity basis (used if entity_breakdown is true). |
| `aggregate_statop` | string | - | Statistical operation (avg, max, median, stdev, and so on) used to combine data for the aggregate alert_value (used for all KPI). |
| `urgency` | integer | - | User-assigned importance value for this KPI. |
| `unit` | string | - | User-defined units for the values in threshold field. |
| `entity_id_fields` | string | - | Fields from this KPI's search events that will be mapped to the alias fields defined in entities for the service containing this KPI. This field enables the KPI search to tie the aliases of entities to the fields from the KPI events in identifying entities at search time. |
| `entity_alias_filtering_fields` | string | - | Subset of aliases from all entities included in the service containing this KPI, to restrict this KPI to only the subset of entities matching via the subset of aliases. Helps filter entities for this KPI among the ones selected in the service containing this KPI. |
| `cron_schedule` | string | - | The cron schedule that determines the frequency of this KPI search. |
| `base_search` | string | - | KPI search defined by user for this KPI. All generated searches for the KPI are based on this search. |
| `kpi_base_search` | string | - | A basic search generated for the KPI search. |
| `alert_on` | string | - | Specified if the threshold type for this KPI is "Per Entity" or "Aggregate" or "Both". Possible values: aggregate, entities, both. |
| `alert_period` | string | - | User specified interval to run the KPI search in minutes. |
| `alert_lag` | integer | - | Contains the number of seconds of lag to apply to the alert search. The maximum is 30 minutes (1800 seconds). |
| `search_alert_earliest` | string | - | Earliest time to look for events every time KPI search runs. This determines how far back each time window is during KPI search runs. |
| `tz_offset` | string | - | ISO time zone offset. Note: Do not change this value. |
| `time_variate_thresholds_specification_custom` | boolean | - | If true, thresholds for alerts are pulled from time_variate_thresholds_specification. |
| `adaptive_thresholds_is_enabled` | boolean | - | Determines if adaptive threshold is enabled for this KPI. |
| `adaptive_thresholding_training_window` | string | - | Earliest time for the Adaptive Threshold training algorithm to run over (latest time is always 'now') (e.g. '-7d') |
| `gap_severity` | string | - | Severity level assigned for data gaps (info, normal, low, medium, high, critical, or unknown) |
| `gap_severity_color` | string | - | Severity color assigned for data gaps. |
| `gap_severity_color_light` | string | - | Severity color assigned for data gaps. |
| `gap_severity_value` | string | - | Severity value assigned for data gaps. |
| `entity_thresholds` | object | - | User-defined thresholding levels for "Per Entity" threshold type. For more information, see KPI Threshold Setting. *(nested: `kpi_threshold_settings`)* |
| `aggregate_thresholds` | string | - | User-defined thresholding levels for "Aggregate" threshold type. For more information, see KPI Threshold Setting. *(nested: `kpi_threshold_settings`)* |
| `enabled` | boolean | - | If set to 1, KPI is enabled. If absent or not set to 1, KPI is disabled. On upgrade KPI is flagged as enabled. Field is read-only. |
| `entity_breakdown_id_field` | string | - | KPI search events are split by the alias field defined in entities for the service containing this KPI. |
| `object_type` | string | read-only | Name of the object type. |
| `create_by` | string | read-only | The user who created this object. |
| `create_source` | string | read-only | The sourcetype initiating create. Has value `manual` for user-initiated creates. For internal use only. |
| `create_time` | string | read-only | Timestamp at the time of creation based on UTC time zone. |
| `mod_source` | string | read-only | Sourcetype initiating modification. Has value `manual` for user-initiated modifications. For internal use only. |
| `mod_time` | string | read-only | Timestamp of the last modification based on UTC time zone. |
| `_owner` | string | read-only | Splunk user `nobody`. |
| `_user` | string | read-only | User who performed the most recent operation on this object. |
| `version` | string | read-only | The version of the object. Currently the same as the ITSI app version. |

## Time Variate Thresholds Specification (`time_variate_thresholds_specification`)

**Kind:** subordinate (nested) structure  

This data structure contains the threshold policy collection. A threshold policy includes information on which thresholds are to be applied (a threshold setting model), how those thresholds are generated, and the time periods to which the threshold policy applies. Each policy object includes a single time\_blocks attribute that contains a list of time periods with which the policy is associated. Note: In the case of static thresholding there are no parameter attributes. In the case of dynamic thresholding, parameters are stored in a simple object within the policy.

| Field | Type | Req | Description |
| --- | --- | --- | --- |
| `title` | string | - | The title of the threshold spec. Used when creating/modifying threshold spec templates. |
| `description` | string | - | User-defined description of the threshold specifications. |
| `policies` | object | - | JSON object keyed by policy ID. |
| `time_blocks` | array | - | Determines time periods with which the policy is associated. |
| `object_type` | string | read-only | Name of the object type. |
| `create_by` | string | read-only | The user who created this object. |
| `create_source` | string | read-only | The sourcetype initiating create. Has value `manual` for user-initiated creates. For internal use only. |
| `create_time` | string | read-only | Timestamp at the time of creation based on UTC time zone. |
| `mod_source` | string | read-only | Sourcetype initiating modification. Has value `manual` for user-initiated modifications. For internal use only. |
| `mod_time` | string | read-only | Timestamp of the last modification based on UTC time zone. |
| `_owner` | string | read-only | Splunk user `nobody`. |
| `_user` | string | read-only | User who performed the most recent operation on this object. |
| `version` | string | read-only | The version of the object. Currently the same as the ITSI app version. |
