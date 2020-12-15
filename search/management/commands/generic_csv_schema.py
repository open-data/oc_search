import csv
from django.core.management.base import BaseCommand
from pathlib import Path
from search.models import Search, Field, Code

import logging

class Command(BaseCommand):

    help = 'Load generic column information from a CSV file with headers into the Search model'

    logger = logging.getLogger(__name__)

    def add_arguments(self, parser):
        parser.add_argument('--csv_file', type=str, help='Filepath for the CSV file', required=True)
        parser.add_argument('--search_id', type=str, help='A unique code identifier for the Search', required=True)
        parser.add_argument('--title_en', type=str, help='An English title to use for the search', required=True)
        parser.add_argument('--title_fr', type=str, help='A French title to use for the search', required=True)
        parser.add_argument('--reset', action='store_true', required=False, default=False,
                            help='Flag to overwrite previous Search settings that were loaded. '
                                 'By default the search is  updated, not overwritten')

    def handle(self, *args, **options):

        # Verify file exists, then load YAML
        csv_path = Path(options['csv_file'])
        if csv_path.is_file():
            try:
                with open(csv_path, 'r', encoding='utf-8-sig', errors="ignore") as csv_file:
                    csv_reader = csv.DictReader(csv_file, dialect='excel')
                    next(csv_reader)

                    # Create or get the search record
                    search, created = Search.objects.get_or_create(search_id=options['search_id'])
                    search.label_en = options['title_en']
                    search.label_fr = options['title_fr']
                    search.save()

                    for fn in csv_reader.fieldnames:
                        field, created = Field.objects.get_or_create(field_id=fn, search_id=search)
                        field.label_en = fn
                        field.label_fr = fn
                        field.solr_field_type = 'string'
                        field.save()
                        self.logger.info (fn)
            except Exception as x:
                self.logger.error("Unexpected Error: {0}".format(x))
            self.logger.info("Imported file {0}".format(options['csv_file']))
        else:
            self.logger.error("Cannot find file {0}".format(options['yaml_file']))
            exit(-1)
