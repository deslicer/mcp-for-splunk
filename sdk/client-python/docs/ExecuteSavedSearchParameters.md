# ExecuteSavedSearchParameters


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**name** | **str** |  | 
**earliest_time** | **str** |  | [optional] [default to 'None']
**latest_time** | **str** |  | [optional] [default to 'None']
**mode** | **str** |  | [optional] [default to '"oneshot"']
**max_results** | **int** |  | [optional] 
**app** | **str** |  | [optional] [default to 'None']
**owner** | **str** |  | [optional] [default to 'None']

## Example

```python
from splunk_mcp_client.models.execute_saved_search_parameters import ExecuteSavedSearchParameters

# TODO update the JSON string below
json = "{}"
# create an instance of ExecuteSavedSearchParameters from a JSON string
execute_saved_search_parameters_instance = ExecuteSavedSearchParameters.from_json(json)
# print the JSON string representation of the object
print(ExecuteSavedSearchParameters.to_json())

# convert the object into a dict
execute_saved_search_parameters_dict = execute_saved_search_parameters_instance.to_dict()
# create an instance of ExecuteSavedSearchParameters from a dict
execute_saved_search_parameters_from_dict = ExecuteSavedSearchParameters.from_dict(execute_saved_search_parameters_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


