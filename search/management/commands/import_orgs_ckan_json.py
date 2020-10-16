from django.core.management.base import BaseCommand
from pathlib import Path
import json
from search.models import Organizations
import logging


class Command(BaseCommand):
    help = 'Load Organizations information from the JSON output of the organization_list command'

    logger = logging.getLogger(__name__)

    def add_arguments(self, parser):
        parser.add_argument('--org_file', type=str, help='Organizations List file', required=True)

    def handle(self, *args, **options):
        org_file = Path(options['org_file'])
        if org_file.is_file():
            try:
                with open(options['org_file'], 'r', encoding='utf-8-sig', errors="ignore") as org_file:
                    orgs = json.load(org_file)
                    print(orgs)
                    for org in orgs:
                        organization, created = Organizations.objects.get_or_create(name=org['name'])
                        owner_org_titles = org['title'].split('|')
                        organization.title_en = owner_org_titles[0].strip()
                        organization.title_fr = owner_org_titles[1].strip()
                        organization.id = org['id']
                        organization.save()
                        print(org["title"])
            except Exception as x:
                self.logger.error(x)
            self.logger.info("Imported file {0}".format(options['org_file']))
        else:
            self.logger.error("Cannot find file {0}".format(options['org_file']))
            exit(-1)



