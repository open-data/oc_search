# Plugin API Changes

OCS provides a custom plug-in system that allows developers to highly customize Search actions. It does this by
allowing developers to write custom code that is used in various OCS functions like displaying search results or
loading CSV files. The functionality available to plug-ins has expended over time. Every plug-in must indicate what
version of the plug-in API it supports.

## Version 1.1

Added two new API functions that are called just before the search page is rendered and just before the record page is rendered:

```python
def pre_render_search(context: dict, template: str, request: HttpRequest, lang: str, search: Search, fields: dict, codes: dict):

def pre_render_record(context: dict, template: str, request: HttpRequest, lang: str, search: Search, fields: dict, codes: dict):
```

## Version 1.2

`pre_render_search()` function updated to include a view-type parameter, that allows rendering to differentiate between views like
Search and More-Like-This
```python
def pre_render_search(context: dict, template: str, request: HttpRequest, lang: str, search: Search, fields: dict, codes: dict, view_type='search'):
```

[Back](../README.md#building-new-commands)