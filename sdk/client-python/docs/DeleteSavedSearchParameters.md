# DeleteSavedSearchParameters


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**name** | **str** |  | 
**confirm** | **bool** |  | [optional] [default to False]
**app** | **str** |  | [optional] [default to 'None']
**owner** | **str** |  | [optional] [default to 'None']

## Example

```python
from splunk_mcp_client.models.delete_saved_search_parameters import DeleteSavedSearchParameters

# TODO update the JSON string below
json = "{}"
# create an instance of DeleteSavedSearchParameters from a JSON string
delete_saved_search_parameters_instance = DeleteSavedSearchParameters.from_json(json)
# print the JSON string representation of the object
print(DeleteSavedSearchParameters.to_json())

# convert the object into a dict
delete_saved_search_parameters_dict = delete_saved_search_parameters_instance.to_dict()
# create an instance of DeleteSavedSearchParameters from a dict
delete_saved_search_parameters_from_dict = DeleteSavedSearchParameters.from_dict(delete_saved_search_parameters_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


