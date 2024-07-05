Added support for Service Canada's Survey Invitation Manager (https://github.com/ServiceCanada/invitation-manager).

By default this feature is disabled. In order to enable it:

1. Add "IM_ENABLED = True" to the Django project's settings.py file
2. Extract the contents of the Invitation-manager release to the "search/templates/snippets/im" directory in the project
3. Configure IM appropriately using the "im.json" and "config.JSON" files.
