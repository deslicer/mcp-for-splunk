# ListSavedSearchesParameters


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**owner** | **str** |  | [optional] [default to 'None']
**app** | **str** |  | [optional] [default to 'None']
**sharing** | **str** |  | [optional] [default to 'None']
**include_disabled** | **bool** |  | [optional] [default to False]

## Example

```python
from splunk_mcp_client.models.list_saved_searches_parameters import ListSavedSearchesParameters

# TODO update the JSON string below
json = "{}"
# create an instance of ListSavedSearchesParameters from a JSON string
list_saved_searches_parameters_instance = ListSavedSearchesParameters.from_json(json)
# print the JSON string representation of the object
print(ListSavedSearchesParameters.to_json())

# convert the object into a dict
list_saved_searches_parameters_dict = list_saved_searches_parameters_instance.to_dict()
# create an instance of ListSavedSearchesParameters from a dict
list_saved_searches_parameters_from_dict = ListSavedSearchesParameters.from_dict(list_saved_searches_parameters_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


