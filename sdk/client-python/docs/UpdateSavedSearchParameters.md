# UpdateSavedSearchParameters


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**name** | **str** |  | 
**search** | **str** |  | [optional] [default to 'None']
**description** | **str** |  | [optional] [default to 'None']
**earliest_time** | **str** |  | [optional] [default to 'None']
**latest_time** | **str** |  | [optional] [default to 'None']
**is_scheduled** | **str** |  | [optional] [default to 'None']
**cron_schedule** | **str** |  | [optional] [default to 'None']
**is_visible** | **str** |  | [optional] [default to 'None']
**app** | **str** |  | [optional] [default to 'None']
**owner** | **str** |  | [optional] [default to 'None']

## Example

```python
from splunk_mcp_client.models.update_saved_search_parameters import UpdateSavedSearchParameters

# TODO update the JSON string below
json = "{}"
# create an instance of UpdateSavedSearchParameters from a JSON string
update_saved_search_parameters_instance = UpdateSavedSearchParameters.from_json(json)
# print the JSON string representation of the object
print(UpdateSavedSearchParameters.to_json())

# convert the object into a dict
update_saved_search_parameters_dict = update_saved_search_parameters_instance.to_dict()
# create an instance of UpdateSavedSearchParameters from a dict
update_saved_search_parameters_from_dict = UpdateSavedSearchParameters.from_dict(update_saved_search_parameters_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


