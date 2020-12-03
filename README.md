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

*NOTE* In addition to Python, the search application also requires Solr *.x and the custom python solr library [Solr Ciient](https://github.com/thriuin/SolrClient)
## Django Plugins ##

Three Django plugins are used:

1. [Rosetta](https://django-rosetta.readthedocs.io/index.html) Provides a UI for language translation
2. [Django import/export](https://django-import-export.readthedocs.io/en/latest/)  Django application and library for importing and exporting data with included admin integration.
3. [Django Jazzmin Admin Theme](https://django-jazzmin.readthedocs.io/) *(Optional)* Provides a more modern Ui for the Django admin interface

## Commands ##

Several custom Django management comments are available  

### create_solr_core

To run: `python manage.py create_solr_core <search name>`

`<search name` Is th name of a search that has been previously defined either by running a load script or
through the Djanoo admin UI.

### import_schema_ckan_yaml

To run: `python manage.py import_schema_ckan_yaml --yaml_file <yaml file> --search_id <unique search ID> --title_en <English Title> --title_fr <French Title> [--reset]`

This command will parse the CKAN YAML file and load it into the search model database

### import_data_csv

To run: `python manage.py --csv <CSV file> --search <Unique search ID> --core <Solr Core Name> [--nothing_to_report]`

---

## Creating a New Search

Creating a new proactive disclosure search requires several steps

1. Create a new blank Solr and copy in the synonyms files
2. Create a search model by importing the CKAN recombinant Yaml file using the `import_schema_ckan_yaml` command
3. Customize the Solr core schema for the seach model using the `create_solr_core` command
4. Import the data from the proactive disclosure CSV file using the `import_data_csv` command

