# GetSavedSearchDetailsParameters


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**name** | **str** |  | 
**app** | **str** |  | [optional] [default to 'None']
**owner** | **str** |  | [optional] [default to 'None']

## Example

```python
from splunk_mcp_client.models.get_saved_search_details_parameters import GetSavedSearchDetailsParameters

# TODO update the JSON string below
json = "{}"
# create an instance of GetSavedSearchDetailsParameters from a JSON string
get_saved_search_details_parameters_instance = GetSavedSearchDetailsParameters.from_json(json)
# print the JSON string representation of the object
print(GetSavedSearchDetailsParameters.to_json())

# convert the object into a dict
get_saved_search_details_parameters_dict = get_saved_search_details_parameters_instance.to_dict()
# create an instance of GetSavedSearchDetailsParameters from a dict
get_saved_search_details_parameters_from_dict = GetSavedSearchDetailsParameters.from_dict(get_saved_search_details_parameters_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


