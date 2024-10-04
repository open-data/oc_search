# Importing Custom Searches #

Custom search definitions can be imported into OCS2. OCS2 must be set up and running
before importing.

## Example: Importing Open Data ##

### 1. Create a Solr Core ###

On the Solr server, create a new core. Search uses the convention `search_<search id>`
for the name of the Solr core. Search ID is the unique search indentifier. Open Data is
an exception and uses the Solr core name search_opencanada. Copy in the language extensions
from the OC Search project into the new core's configuration.

```bash
solr create -c search_opencanada
cp -Rf `oc_search\oc_search\solr\conf \var\solr\data\search_opencanada\conf\`
```
Reload the new core using the Solr Web Admin interface.

### 2. Clone the Git Repository ###

Clone the GitHub repository to a suitable location.

```bash
git clone https://github.com/open-data/oc_searches.git
```
### 3. Activate the Search virtual environment ###

Activate the Search virtual environment. This will give you access to Search's custom management commands.

```bash
source venv/scripts/active
```

### 4. Run the import command

Use the `import_search` command to import the new defintion.

```bash
python .\manage.py import_search --search data --import_dir ..\oc_searches\ --include_db
```

After importing the search, there are several commands needed to completely rebuilt the Django resources
```bash
python manage.py combine_messages
python manage.py compilemessages -l fr
python manage.py collectstatic --noinput
```

At this point, the data search will be empty. To load the data, download a copy of the CKAN JSON catalog for the portal
and import it into Solr using a custom command.

```bash
python .\manage.py data_import_ckan_json --search data --type jsonl --json .\data\od-do-canada.jsonl --reset
```

### 5. Run Django ###

In a development environment, you can start the Django web application from the command line.

```bash
python manage.py runserver
```
