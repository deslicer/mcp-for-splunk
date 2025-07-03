# RunSplunkSearchParameters


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**query** | **str** |  | 
**earliest_time** | **str** |  | [optional] [default to '"-24h"']
**latest_time** | **str** |  | [optional] [default to '"now"']

## Example

```python
from splunk_mcp_client.models.run_splunk_search_parameters import RunSplunkSearchParameters

# TODO update the JSON string below
json = "{}"
# create an instance of RunSplunkSearchParameters from a JSON string
run_splunk_search_parameters_instance = RunSplunkSearchParameters.from_json(json)
# print the JSON string representation of the object
print(RunSplunkSearchParameters.to_json())

# convert the object into a dict
run_splunk_search_parameters_dict = run_splunk_search_parameters_instance.to_dict()
# create an instance of RunSplunkSearchParameters from a dict
run_splunk_search_parameters_from_dict = RunSplunkSearchParameters.from_dict(run_splunk_search_parameters_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


