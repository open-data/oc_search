from babel.dates import format_date
from babel.numbers import format_currency, format_decimal, parse_decimal
from datetime import datetime
from django.core.management.base import BaseCommand
from django.conf import settings
from search.models import Search, Field, Code, Organizations
from SolrClient import SolrClient
import csv
import logging


class Command(BaseCommand):

    help = 'Django manage command that will import CSV data into a Solr search that created with the ' \
           'import_schema_ckan_yaml command'

    logger = logging.getLogger(__name__)

    # Number of rows to commit to Solr at a time
    cycle_on = 1000

    def add_arguments(self, parser):
        parser.add_argument('--search', type=str, help='The name of the Search that is being loaded', required=True)
        parser.add_argument('--csv', type=str, help='CSV filename to import', required=True)
        parser.add_argument('--core', type=str, help='Solr Core name that will be used', required=True)
        parser.add_argument('--nothing_to_report', required=False,  action='store_true', default=False,
                            help='Use this switch to indicate if the CSV files that is being loaded contains '
                                 '"Nothing To Report" data')

    def handle(self, *args, **options):

        total = 0
        cycle = 0
        fields = {}
        field_codes = {}

        try:
            # Retrieve the Search  and Field models from the database
            solr = SolrClient(settings.SOLR_SERVER_URL)
            try:
                search_target = Search.objects.get(search_id=options['search'])
                search_fields = Field.objects.filter(search_id=search_target, is_ntr_field=options['nothing_to_report'])
                for search_field in search_fields:
                    fields[search_field.field_id] = search_field

                    codes = Code.objects.filter(field_id=search_field)
                    # Most fields will not  have codes, so the queryset will be zero length
                    if len(codes) > 0:
                        code_dict = {}
                        for code in codes:
                            code_dict[code.code_id] = code
                        field_codes[search_field.field_id] = code_dict

            except Search.DoesNotExist as x:
                self.logger.error('Search not found: "{0}"'.format(x))
                exit(-1)
            except Field.DoesNotExist as x1:
                self.logger.error('Fields not found for search: "{0}"'.format(x1))

            # Process the records in the CSV file one at a time
            with open(options['csv'], 'r', encoding='utf-8-sig', errors="ignore") as csv_file:
                csv_reader = csv.DictReader(csv_file, dialect='excel')
                solr_items = []
                for csv_record in csv_reader:

                    # Clear out the Solr core. on the first line
                    if total == 0 and not options['nothing_to_report']:
                        solr.delete_doc_by_query(options['core'], "*:*")
                    total += 1
                    cycle += 1

                    # Create a dictionary for each record loaded into  Solr
                    solr_record = {'is_ntr_field': options['nothing_to_report']}
                    for csv_field in csv_reader.fieldnames:
                        # Verify that it is a known field
                        if csv_field not in fields and csv_field not in ('owner_org_title', 'owner_org'):
                            self.logger.error("CSV files contains unknown field: {0}".format(csv_field))
                            exit(-1)

                        # Use the titles pulled from CKAN for consistency.
                        if csv_field == 'owner_org_title':
                            break
                        if csv_field == 'owner_org':
                            try:
                                org = Organizations.objects.get(name=csv_record['owner_org'])
                                solr_record['org_en'] = org.title_en
                                solr_record['org_fr'] = org.title_fr
                                break
                            except ValueError as ve:
                                self.logger.error('Unknown Organization: "{0}"'.format(ve))

                        solr_record[csv_field] = csv_record[csv_field]

                        # Automatically expand out dates and numbers for use with Solr export handler
                        if fields[csv_field].solr_field_type == 'pdate':
                            try:
                                if csv_record[csv_field]:
                                    csv_date = datetime.strptime(csv_record[csv_field], '%Y-%m-%d')
                                    solr_record[csv_field + '_en'] = format_date(csv_date, locale='en')
                                    solr_record[csv_field + '_fr'] = format_date(csv_date, locale='fr')
                                    if fields[csv_field].is_default_year:
                                        solr_record['year'] = csv_date.year
                                    if fields[csv_field].is_default_month:
                                        solr_record['month'] = csv_date.month
                                else:
                                    solr_record[csv_field + '_en'] = ''
                                    solr_record[csv_field + '_fr'] = ''
                            except ValueError as x2:
                                self.logger.error('Invalid date: "{0}"'.format(x2))
                        elif fields[csv_field].solr_field_type in ['pint', 'pfloat']:
                            if solr_record[csv_field]:
                                csv_decimal = parse_decimal(solr_record[csv_field], locale='en_US')
                                if fields[csv_field].solr_field_is_currency:
                                    solr_record[csv_field + '_en'] = format_currency(csv_decimal, 'CAD', locale='en_CA')
                                    solr_record[csv_field + '_fr'] = format_currency(csv_decimal, 'CAD', locale='fr_CA')
                                else:
                                    solr_record[csv_field + '_en'] = format_decimal(csv_decimal, locale='en_CA')
                                    solr_record[csv_field + '_fr'] = format_decimal(csv_decimal, locale='fr_CA')
                            else:
                                solr_record[csv_field + '_en'] = ''
                                solr_record[csv_field + '_fr'] = ''

                        # Lookup the expanded code value from the codes dict of dict
                        if csv_field in field_codes:
                            if csv_record[csv_field]:
                                if csv_record[csv_field].upper() in field_codes[csv_field]:
                                    solr_record[csv_field + '_en'] = field_codes[csv_field][csv_record[csv_field].upper()].label_en
                                    solr_record[csv_field + '_fr'] = field_codes[csv_field][csv_record[csv_field].upper()].label_fr
                                else:
                                    self.logger.info("Unknown code value: {0} for field: {1}".format(csv_record[csv_field],
                                                                                                     csv_field))

                    solr_items.append(solr_record)

                    # Write to Solr whenever the cycle threshold is reached
                    if cycle >= self.cycle_on:
                        solr.index(options['core'], solr_items)
                        solr.commit(options['core'], softCommit=True)
                        print("{0} rows processed".format(cycle))
                        cycle = 0
                        solr_items.clear()

                if cycle > 0:
                    solr.index(options['core'], solr_items)
                    total += len(solr_items)
                solr.commit(options['core'], softCommit=True, waitSearcher=True)
                print("Total rows processed: {0}".format(total))

        except Exception as x:
            self.logger.error('Unexpected Error "{0}"'.format(x))
