from django.core.management.base import BaseCommand, CommandError
from pathlib import Path
import json
from search.models import Code, Field, Search
import logging


class Command(BaseCommand):
    help = 'Load Organization information from the JSON output of the organization_list command'

    logger = logging.getLogger(__name__)

    def add_arguments(self, parser):
        parser.add_argument('--org_file', type=str, help='Organization List file', required=True)
        parser.add_argument('--field', type=str, help='field name', required=True)
        parser.add_argument('--search', type=str, help='search name', required=True)

    def handle(self, *args, **options):
        org_file = Path(options['org_file'])
        if org_file.is_file():
            try:
                with open(options['org_file'], 'r', encoding='utf-8-sig', errors="ignore") as org_file:
                    orgs = json.load(org_file)
                    for org in orgs:
                        search = Search.objects.get(search_id=options['search'])
                        field = Field.objects.get(field_id=options['field'], search_id=search)
                        code, created = Code.objects.get_or_create(field_fid_id=field.fid, code_id=org['name'])
                        owner_org_titles = org['title'].split('|')
                        code.label_en = owner_org_titles[0].strip()
                        if len(owner_org_titles) == 1:
                            code.label_fr = owner_org_titles[0].strip()
                        else:
                            code.label_fr = owner_org_titles[1].strip()
                        code.extra_01 = org['id'].lower()
                        if '-' in org['name']:
                            code.extra_01 = org['name']
                            acronym = org['name'].split('-')
                            code.extra_01_en = acronym[0].strip()
                            code.extra_01_fr = acronym[1].strip()
                        else:
                            code.extra_01_en = org['name']
                            code.extra_01_fr = org['name']
                        code.save()
            except Exception as x:
                self.logger.error(x)
            self.logger.info("Imported file {0}".format(options['org_file']))

        else:
            self.logger.error("Cannot find file {0}".format(options['org_file']))
            exit(-1)



