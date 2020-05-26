from django.core.management.base import BaseCommand, CommandError
from pathlib import Path
from search.models import Search, Field,  Code
from yaml import load, FullLoader
try:
    from yaml import CLoader as Loader
except ImportError:
    from yaml import Loader
import logging


class Command(BaseCommand):
    help = 'Load Schema information from a CKAN recombinant YAML file'

    logger = logging.getLogger(__name__)

    def add_arguments(self, parser):
        parser.add_argument('--yaml_file', type=str, help='Location of YAML file', required=True)
        parser.add_argument('--search_id', type=str, help='Unique code identifier for the search', required=True)
        parser.add_argument('--title_en', type=str, help='English Title', required=True)
        parser.add_argument('--title_fr', type=str, help='French Title', required=True)

    def handle(self, *args, **options):
        yaml_path = Path(options['yaml_file'])
        if yaml_path.is_file():
            try:
                with open(options['yaml_file'], 'r', encoding='utf-8-sig', errors="ignore") as yaml_file:
                    schema = load(yaml_file, Loader=FullLoader)
                    search, created = Search.objects.get_or_create(search_id=options['search_id'])
                    search.label_en = options['title_en']
                    search.label_fr = options['title_fr']
                    search.save()

                    for travel_field in schema['resources'][0]['fields']:
                        if not travel_field['datastore_id'] in ('record_created', 'record_modified', 'user_modified'):
                            field, created = Field.objects.get_or_create(field_id=travel_field['datastore_id'])
                            field.search_id = search
                            field.label_en = travel_field['label']['en']
                            field.label_fr = travel_field['label']['fr']
                            field.save()
            except Exception as x:
                self.logger.error(x)
            self.logger.info("Imported file {0}".format(options['yaml_file']))
        else:
            self.logger.error("Cannot find file {0}".format(options['yaml_file']))
            exit(-1)
