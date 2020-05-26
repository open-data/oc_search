# Open Canada Solr Search #

This Django 3.0 application use Solr 8.x to provide a search interface into the 
Open Canada data catalog and proactive disclosure.

## Install from Source

1. Clone this project from GitHub

1. Create a virtual environment using Python 3.7 or higher

1. Install the prerequisites from the requirements.txt file

    `pip install -r requirements.txt`

1. Edit the settings.py file with the appropriate database settings and create the tables

    `python manage.py makemigrations search`<br>
    `python manage.py sqlmigrate search 0001`<br>
    `python manage,py migrate`

## Django Plugins ##

Two Django plugins are used:

1. [Rosetta](https://django-rosetta.readthedocs.io/index.html) Provides a UI for language translation
2. [Django import/export](https://django-import-export.readthedocs.io/en/latest/)  Django application and library for importing and exporting data with included admin integration.

## Commands ##

Several custom Django management comments are available  

### create_solr_core

To run: `python manage.py create_solr_core <search name>`

`<search name` Is th name of a search that has been previously defined either by running a load script or
through the Djanoo admin UI.

### import_schema_ckan_yaml

To run: `python manage.py import_schema_ckan_yaml --yaml_file ./travela.yaml --search_id travela --title_en "Travel Expenses" --title_fr "Dépenses de voyage gouvernementaux"`

This command will parse the CKAN YAML file and load it into the search model database