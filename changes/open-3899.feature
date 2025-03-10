Add new command `compare_orgs_ckan_json` for manaaging the CKAN organization field that is present in most custom searches

```
usage: manage.py compare_orgs_ckan_json [-h] --org_file ORG_FILE --field FIELD --search SEARCH
                                        [--action {compare,purge_unmatched,add_new}] [--dry_run] [--version]
                                        [-v {0,1,2,3}] [--settings SETTINGS] [--pythonpath PYTHONPATH] [--traceback]
                                        [--no-color] [--force-color] [--skip-checks]

Compare existing Organization information from the JSON output of the CKAN organization_list command

options:
  -h, --help            show this help message and exit
  --org_file ORG_FILE   Organization List file
  --field FIELD         field name
  --search SEARCH       search name
  --action {compare,purge_unmatched,add_new}
                        Options are 'compare': show differences between JSON and Codes, 'purge_unmatched': delete
                        codes not found in JSON, 'add_new': create missing codes from JSON
  --dry_run             Do a dry run withouth deleting from or adding to the database
```