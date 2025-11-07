from search.models import Field, Code
from django.core.management.base import BaseCommand, CommandError
from os import path
from termcolor import colored, cprint
import textwrap
import yaml


class Command(BaseCommand):
    help = 'Import code values for a custom search from a CKAN Recombinant YAML file.'


    def add_arguments(self, parser):
        parser.add_argument('--codes', type=str, help='YAML file that contains the code values', required=True)
        parser.add_argument('--reset', type=bool, default=False, help="Remove all existing codes")
        parser.add_argument('--dryrun', action='store_true', help="Do a dry run, do not make any changes")
        

    def handle(self, *args, **options):

        if not path.exists(options['codes']):
            raise CommandError('YAML data file not found: ' + options['codes'])

        if path.exists(options['codes']) and path.getsize(options['codes']) > 0:
            code_doc = yaml.safe_load(open(options['codes'], encoding='utf-8-sig', errors="ignore"))
            # print(code_doc)
            search_id = code_doc['dataset_type']
            print(f"Loading codes for search {search_id}\n")
            yaml_fields = {}
            for field in code_doc['resources'][0]['fields']:
                field_id = field['datastore_id']
                yaml_fields[field_id] = True
                cprint(colored(f"Field: {field_id}", "cyan"))  
                if 'choices' in field:
                    yaml_codes = {}
                    for code in field['choices']:
                        field_fid = f"{search_id}_{field_id}"
                        code_cid = f"{field_fid}_{code}"
                        yaml_codes[code] = True
                        try:
                            field_obj = Field.objects.get(fid=field_fid)
                            if options['dryrun']:
                                if Code.objects.filter(cid=code_cid, field_fid=field_obj).exists():
                                    cprint (colored(f"    Update an existing code {code_cid}", "green"))
                                else:
                                    cprint (colored(f"    Create a new code {code_cid}"), "yellow")
                            else:
                                cprint(colored(f"  Code: {code} EN: {textwrap.shorten(field['choices'][code]['en'], 24, placeholder='...')} FR: {textwrap.shorten(field['choices'][code]['fr'], 24, placeholder='...')}", "light_cyan"))
                                new_code, created = Code.objects.get_or_create(cid=code_cid, field_fid=field_obj)
                                new_code.code_id = code
                                new_code.label_en = field['choices'][code]['en']
                                new_code.label_fr = field['choices'][code]['fr']
                                new_code.save()
                                if created:
                                    cprint(colored(f"    Imported new Code {new_code.code_id} for Field {field_obj.fid}", "yellow"))
                                else:
                                    cprint(colored(f"    Updated Code model {new_code.code_id} for Field {field_obj.fid}", "green"))
                        except KeyError as ke:
                            raise CommandError(f"Field {field_fid} not found in database {ke}")
                    db_codes = Code.objects.filter(field_fid_id=field_fid)
                    for db_code in db_codes:
                        if db_code.code_id not in yaml_codes:
                            cprint (colored(f"    Existing code '{db_code.code_id}' not found in yaml", "light_red"))
            # Identify database fields that do not exist in the YAML file. Such fields are legitimate, particulary
            # for handling text search of string fields.
            db_fields = Field.objects.filter(search_id_id=search_id)
            found_flag = False
            for db_field in db_fields:
                if db_field.field_id not in yaml_fields:
                    found_flag = True
                    cprint (colored(f"Search field '{db_field.field_id}' does not exist in yaml"), "light_magenta")
            if found_flag:
                print("Search may have additional fields for specific purposes. Manual verification required")
