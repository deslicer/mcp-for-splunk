# GetSplunkHealthParameters


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**splunk_host** | **str** | Splunk server hostname or IP address. If not provided, uses the server&#39;s configured connection. | [optional] [default to 'None']
**splunk_port** | **str** | Splunk management port (typically 8089). Defaults to server configuration. | [optional] [default to 'None']
**splunk_username** | **str** | Splunk username for authentication. Uses server configuration if not provided. | [optional] [default to 'None']
**splunk_password** | **str** | Splunk password for authentication. Uses server configuration if not provided. | [optional] [default to 'None']
**splunk_scheme** | **str** | Connection scheme (&#39;http&#39; or &#39;https&#39;). Defaults to server configuration. | [optional] [default to 'None']
**splunk_verify_ssl** | **str** | Whether to verify SSL certificates. Defaults to server configuration. | [optional] [default to 'None']

## Example

```python
from splunk_mcp_client.models.get_splunk_health_parameters import GetSplunkHealthParameters

# TODO update the JSON string below
json = "{}"
# create an instance of GetSplunkHealthParameters from a JSON string
get_splunk_health_parameters_instance = GetSplunkHealthParameters.from_json(json)
# print the JSON string representation of the object
print(GetSplunkHealthParameters.to_json())

# convert the object into a dict
get_splunk_health_parameters_dict = get_splunk_health_parameters_instance.to_dict()
# create an instance of GetSplunkHealthParameters from a dict
get_splunk_health_parameters_from_dict = GetSplunkHealthParameters.from_dict(get_splunk_health_parameters_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


