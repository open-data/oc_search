from django.core.management.base import BaseCommand, CommandError
from pathlib import Path
import json
from search.models import Code, Field, Search
import logging


class Command(BaseCommand):
    help = 'Compare existing Organization information from the JSON output of the CKAN organization_list command'

    logger = logging.getLogger(__name__)

    ckan_orgs = {}

    org_codes = {}

    def add_arguments(self, parser):
        parser.add_argument('--org_file', type=str, help='Organization List file', required=True)
        parser.add_argument('--field', type=str, help='field name', required=True)
        parser.add_argument('--search', type=str, help='search name', required=True)
        parser.add_argument('--action', type=str, choices=['compare', 'purge_unmatched', 'add_new'], default='compare',
                            help="Options are 'compare': show differences between JSON and Codes, 'purge_unmatched': "
                            "delete codes not found in JSON, 'add_new': create missing codes from JSON" )
        parser.add_argument('--dry_run', action="store_true", help="Do a dry run withouth deleting from or adding to the database")

    def handle(self, *args, **options):
        org_file = Path(options['org_file'])

        # Load the organizations in the CKAN JSON Orginization file

        if not org_file.is_file():
            self.logger.error("Cannot find file {0}".format(options['org_file']))
        else:
            with open(options['org_file'], 'r', encoding='utf-8-sig', errors="ignore") as org_file:
                for org in org_file:
                    org_obj = json.loads(org)
                    org_id = org_obj["name"]
                    owner_org_titles = org_obj['title'].split('|')
                    label_en = owner_org_titles[0].strip()
                    label_fr = ""
                    if len(owner_org_titles) == 1:
                        label_fr = owner_org_titles[0].strip()
                    else:
                        label_fr = owner_org_titles[1].strip()                    
                    org_entry = {
                        'id': org_id, 
                        'label_en': label_en, 
                        'label_fr': label_fr,
                        'extra_01': org_obj['name'],
                        'extra_01_en': org_obj["shortform"]["en"],
                        'extra_01_fr': org_obj["shortform"]["fr"]
                        }
                    self.ckan_orgs[org_id.lower()] = org_entry

        # Load the org codes from the Search datatbase

        search = Search.objects.get(search_id=options['search'])
        field = Field.objects.get(field_id=options['field'], search_id=search)
        code_qs = Code.objects.filter(field_fid=field)
        for org_code in code_qs:
            self.org_codes[org_code.code_id.lower()] = {
                'id': org_code.code_id, 
                'label_en': org_code.label_en, 
                'label_fr': org_code.label_fr,
                'extra_01': org_code.extra_01,
                'extra_01_en': org_code.extra_01_en,
                'extra_01_fr': org_code.extra_01_fr                
            }

        # Compare CKAN and Codes and display a list of mismatches

        count = 0
        if options['action'] == "compare":
            # 2 cycles required, loop through file lookin for codes, and loop through code looking at file
            for k in self.ckan_orgs.keys():
                if k not in self.org_codes:
                    print(f"Organization \"{k}\" from CKAN not found in Search")
                    count += 1
            
            for k in self.org_codes.keys():
                if k not in self.ckan_orgs:
                    print(f"Organization \"{k}\" in Search not found in CKAN")
                    count += 1
            
            print(f"{count} difference(s) found")

        # Remove any org codes that do not appear the CKAN org dump file

        elif options['action'] == "purge_unmatched":
            for k in self.org_codes.keys():
                if k not in self.ckan_orgs:
                    dedcode = Code.objects.get(code_id=k, field_fid=field)
                    if not options['dry_run']:
                        dedcode.delete()
                        print(f"Deleting org code {dedcode.code_id}")
                    else:
                        print(f"Will delete org code {k}")

        # Add any organizations that appear in the CKAN dump file but not in the search org codes

        elif options['action'] == "add_new":
            for k in self.ckan_orgs.keys():
                if k not in self.org_codes:
                    if not options['dry_run']:       
                        new_code, created = Code.objects.get_or_create(
                            code_id=self.ckan_orgs[k]['id'], 
                            field_fid_id=field.fid,
                            label_en=self.ckan_orgs[k]['label_en'],
                            label_fr=self.ckan_orgs[k]['label_fr'],
                            extra_01=self.ckan_orgs[k]['extra_01'],
                            extra_01_en=self.ckan_orgs[k]['extra_01_en'],
                            extra_01_fr=self.ckan_orgs[k]['extra_01_fr']
                        )
                        new_code.save()
                        if created:
                            print(f"Created new org code {self.ckan_orgs[k]['id']}")
                        else:
                            print(f"Updating org code {self.ckan_orgs[k]['id']}")
                    else:
                        print(f"Will add new org code {self.ckan_orgs[k]['id']}")


        exit()