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
        parser.add_argument('--c1', type=str, help='Extra choice field to add to code extra field 01. Specify c1 or b1, but not both.', required=False)
        parser.add_argument('--c2', type=str, help='Extra choice field to add to code extra field 02. Specify c2 or b2, but not both.', required=False)
        parser.add_argument('--c3', type=str, help='Extra choice field to add to code extra field 03. Specify c3 or b3, but not both.', required=False)
        parser.add_argument('--c4', type=str, help='Extra choice field to add to code extra field 04. Specify c4 or b4, but not both.', required=False)
        parser.add_argument('--c5', type=str, help='Extra choice field to add to code extra field 05. Specify c5 or b5, but not both.', required=False)
        parser.add_argument('--b1', type=str, help='Extra bilingual choice field to add to code extra field 01', required=False)
        parser.add_argument('--b2', type=str, help='Extra bilingual choice field to add to code extra field 02', required=False)
        parser.add_argument('--b3', type=str, help='Extra bilingual choice field to add to code extra field 03', required=False)
        parser.add_argument('--b4', type=str, help='Extra bilingual choice field to add to code extra field 04', required=False)
        parser.add_argument('--b5', type=str, help='Extra bilingual choice field to add to code extra field 05', required=False)
        

    def handle(self, *args, **options):

        if not path.exists(options['codes']):
            raise CommandError('YAML data file not found: ' + options['codes'])

        if path.exists(options['codes']) and path.getsize(options['codes']) > 0:
            code_doc = yaml.safe_load(open(options['codes'], encoding='utf-8-sig', errors="ignore"))
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
                                if isinstance(field['choices'][code], dict):
                                    en = field['choices'][code]['en']
                                    fr = field['choices'][code]['fr']
                                else:
                                    en = fr = code
                                cprint(colored(f"  Code: {code} EN: {textwrap.shorten(en, 24, placeholder='...')} FR: {textwrap.shorten(fr, 24, placeholder='...')}", "light_cyan"))
                                new_code, created = Code.objects.get_or_create(cid=code_cid, field_fid=field_obj)

                                new_code.code_id = code
                                new_code.label_en = en
                                new_code.label_fr = fr

                                for i in range(1, 6):
                                    if f'c{i}' in options and options[f'c{i}']:

                                        extra_option = options[f'c{i}']

                                        if extra_option in field['choices'][code]:
                                            extra = field['choices'][code][extra_option]
                                            setattr(new_code, f'extra_{i:02}', extra)
                                            setattr(new_code, f'extra_{i:02}_en', '')
                                            setattr(new_code, f'extra_{i:02}_fr', '')
                                            if extra is None:
                                                extra = ""
                                            elif isinstance(extra, list):
                                                extra = ",".join(map(str, extra))
                                            else:
                                                extra = str(extra)
                                            cprint(
                                                f"        Extra Code for {extra_option}: "
                                                f"{textwrap.shorten(extra, 24, placeholder='...')}",
                                                "magenta"
                                            )

                                for i in range(1, 6):
                                    if f'b{i}' in options and options[f'b{i}']:

                                        extra_option = options[f'b{i}']

                                        if extra_option in field['choices'][code]:
                                            extra_en = field['choices'][code][extra_option]['en'] if 'en' in field['choices'][code][extra_option] else ''
                                            extra_fr = field['choices'][code][extra_option]['fr'] if 'fr' in field['choices'][code][extra_option] else ''
                                            setattr(new_code, f'extra_{i:02}', '')
                                            setattr(new_code, f'extra_{i:02}_en', extra_en)
                                            setattr(new_code, f'extra_{i:02}_fr', extra_fr)
                                            cprint(
                                                f"        Extra Code for {extra_option}:"
                                                f" EN: {textwrap.shorten(extra_en, 24, placeholder='...')}"
                                                f" FR: {textwrap.shorten(extra_fr, 24, placeholder='...')}",
                                                "magenta"
                                            )
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
