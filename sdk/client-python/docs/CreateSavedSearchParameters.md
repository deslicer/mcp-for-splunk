# CreateSavedSearchParameters


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**name** | **str** |  | 
**search** | **str** |  | 
**description** | **str** |  | [optional] [default to '""']
**earliest_time** | **str** |  | [optional] [default to '""']
**latest_time** | **str** |  | [optional] [default to '""']
**app** | **str** |  | [optional] [default to 'None']
**sharing** | **str** |  | [optional] [default to '"user"']
**is_scheduled** | **bool** |  | [optional] [default to False]
**cron_schedule** | **str** |  | [optional] [default to '""']
**is_visible** | **bool** |  | [optional] [default to True]

## Example

```python
from splunk_mcp_client.models.create_saved_search_parameters import CreateSavedSearchParameters

# TODO update the JSON string below
json = "{}"
# create an instance of CreateSavedSearchParameters from a JSON string
create_saved_search_parameters_instance = CreateSavedSearchParameters.from_json(json)
# print the JSON string representation of the object
print(CreateSavedSearchParameters.to_json())

# convert the object into a dict
create_saved_search_parameters_dict = create_saved_search_parameters_instance.to_dict()
# create an instance of CreateSavedSearchParameters from a dict
create_saved_search_parameters_from_dict = CreateSavedSearchParameters.from_dict(create_saved_search_parameters_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


