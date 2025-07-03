# GetConfigurationsParameters


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**conf_file** | **str** | Configuration file name without .conf extension (e.g., &#39;props&#39;, &#39;transforms&#39;, &#39;inputs&#39;, &#39;outputs&#39;, &#39;server&#39;, &#39;web&#39;) | 
**stanza** | **str** | Specific stanza name within the conf file to retrieve. If not provided, returns all stanzas in the file. | [optional] [default to 'None']

## Example

```python
from splunk_mcp_client.models.get_configurations_parameters import GetConfigurationsParameters

# TODO update the JSON string below
json = "{}"
# create an instance of GetConfigurationsParameters from a JSON string
get_configurations_parameters_instance = GetConfigurationsParameters.from_json(json)
# print the JSON string representation of the object
print(GetConfigurationsParameters.to_json())

# convert the object into a dict
get_configurations_parameters_dict = get_configurations_parameters_instance.to_dict()
# create an instance of GetConfigurationsParameters from a dict
get_configurations_parameters_from_dict = GetConfigurationsParameters.from_dict(get_configurations_parameters_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


