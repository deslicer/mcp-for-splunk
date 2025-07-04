# RunOneshotSearchParameters


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**query** | **str** |  | 
**earliest_time** | **str** |  | [optional] [default to '"-15m"']
**latest_time** | **str** |  | [optional] [default to '"now"']
**max_results** | **int** |  | [optional] 

## Example

```python
from splunk_mcp_client.models.run_oneshot_search_parameters import RunOneshotSearchParameters

# TODO update the JSON string below
json = "{}"
# create an instance of RunOneshotSearchParameters from a JSON string
run_oneshot_search_parameters_instance = RunOneshotSearchParameters.from_json(json)
# print the JSON string representation of the object
print(RunOneshotSearchParameters.to_json())

# convert the object into a dict
run_oneshot_search_parameters_dict = run_oneshot_search_parameters_instance.to_dict()
# create an instance of RunOneshotSearchParameters from a dict
run_oneshot_search_parameters_from_dict = RunOneshotSearchParameters.from_dict(run_oneshot_search_parameters_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


