import csv
from django.core.management.base import BaseCommand
from django.conf import settings
import json
import logging
from os import path
from search.models import Search, Field, Code, Setting, SearchLog
from search.query import get_query_fields
import traceback
import SolrClient


class Command(BaseCommand):
    help = 'Do a search quality evaluatoin test run'

    def __init__(self, *args, **kwargs):
        super().__init__()
        self.logger = logging.getLogger(__name__)
        # class variables that hold the search models
        self.search_target = None
        self.solr_core = None
        self.search_fields = None
        self.field_codes = {}
        self.solr = SolrClient(settings.SOLR_SERVER_URL)

    def add_arguments(self, parser):
        parser.add_argument('--search', type=str, help='The Search ID that is being evaluated', required=True)
        parser.add_argument('--csv', type=str, help='CSV file with search tests', required=True)
        parser.add_argument('--run_label', type=str, help='Test Run label. Example: "ATI with P4"', required=True)

    def handle(self, *args, **options):
        try:
            self.search_target = Search.objects.get(search_id=options['search'])
            self.solr_core = self.search_target.solr_core_name

            self.search_fields = Field.objects.filter(search_id=self.search_target,
                alt_format='ALL') | Field.objects.filter(
                search_id=self.search_target, alt_format='')

# @NOTE Not sure this is needed
            for search_field in self.search_fields:

                codes = Code.objects.filter(field_fid=search_field)
                # Most csv_fields will not  have codes, so the queryset will be zero length
                if len(codes) > 0:
                    code_dict = {}
                    for code in codes:
                        code_dict[code.code_id.lower()] = code
                self.field_codes[search_field.field_id] = code_dict

        except Search.DoesNotExist as x:
            self.logger.error('Search not found: "{0}"'.format(x))
            exit(-1)
        except Field.DoesNotExist as x1:
            self.logger.error('Fields not found for search: "{0}"'.format(x1))

        # Verify the CSV test file exists

        if not path.exists(options['csv']):
            self.logger.error(f'File not found: {options["csv"]}')
            exit(-1)

        # Process the records in the CSV file one at a time
        with open(options['csv'], 'r', encoding='utf-8-sig', errors="xmlcharrefreplace") as csv_file:
            csv_reader = csv.DictReader(csv_file, dialect='excel')
            for row_num, csv_record in enumerate(csv_reader):
                try:
                    # Query Solr with the indicated text and evaluate its results
                    solr_query = {'q': csv_record['text_en'], 'defType': 'edismax', 'sow': True, 'sort': 'score desc'}
                    solr_query['q.op'] = self.search_target.solr_default_op
                    solr_query['qf'] = get_query_fields('en', self.search_fields)

                except Exception as x:
                    self.logger.error('Unexpected Error "{0}" while processing row {1}'.format(x, row_num + 1))
                    if settings.DEBUG:
                        traceback.print_exception(type(x), x, x.__traceback__)
