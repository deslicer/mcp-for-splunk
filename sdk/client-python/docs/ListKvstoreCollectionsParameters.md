# ListKvstoreCollectionsParameters


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**app** | **str** |  | [optional] [default to 'None']

## Example

```python
from splunk_mcp_client.models.list_kvstore_collections_parameters import ListKvstoreCollectionsParameters

# TODO update the JSON string below
json = "{}"
# create an instance of ListKvstoreCollectionsParameters from a JSON string
list_kvstore_collections_parameters_instance = ListKvstoreCollectionsParameters.from_json(json)
# print the JSON string representation of the object
print(ListKvstoreCollectionsParameters.to_json())

# convert the object into a dict
list_kvstore_collections_parameters_dict = list_kvstore_collections_parameters_instance.to_dict()
# create an instance of ListKvstoreCollectionsParameters from a dict
list_kvstore_collections_parameters_from_dict = ListKvstoreCollectionsParameters.from_dict(list_kvstore_collections_parameters_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


