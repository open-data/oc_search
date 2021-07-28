from babel.dates import format_date
from babel.numbers import format_currency, format_decimal, parse_decimal
from datetime import datetime
from django.core.management.base import BaseCommand
from django.conf import settings
import importlib
import pkgutil
from search.models import Search, Field, Code
import search.plugins
from SolrClient import SolrClient
from SolrClient.exceptions import ConnectionError
import csv
import logging
import time


class Command(BaseCommand):

    help = 'Django manage command that will import CSV data into a Solr search that created with the ' \
           'import_schema_ckan_yaml command'

    logger = logging.getLogger(__name__)

    # class variables that hold the search models
    search_target = None
    solr_core = None
    search_fields = None
    csv_fields = {}
    all_fields = {}
    field_codes = {}

    # Number of rows to commit to Solr at a time
    cycle_on = 1000

    discovered_plugins = {
            name: importlib.import_module(name)
            for finder, name, ispkg
            in pkgutil.iter_modules(search.plugins.__path__, search.plugins.__name__ + ".")
        }

    def add_arguments(self, parser):
        parser.add_argument('--search', type=str, help='The Search ID that is being loaded', required=True)
        parser.add_argument('--csv', type=str, help='CSV filename to import', required=True)
        parser.add_argument('--quiet', required=False, action='store_true', default=False,
                            help='Only display error messages')
        parser.add_argument('--nothing_to_report', required=False,  action='store_true', default=False,
                            help='Use this switch to indicate if the CSV files that is being loaded contains '
                                 '"Nothing To Report" data')

    def set_empty_fields(self, solr_record: dict):

        for sf in self.all_fields:
            if (sf.field_id not in solr_record and sf != 'default_fmt') or solr_record[sf.field_id] == '':
                if sf.default_export_value:
                    default_fmt = sf.default_export_value.split('|')
                    if default_fmt[0] in ['str', 'date']:
                        solr_record[sf.field_id] = str(default_fmt[1])
                    elif default_fmt[0] == 'int':
                        solr_record[sf.field_id] = int(default_fmt[1])
                    elif default_fmt[0] == 'float':
                        solr_record[sf.field_id] = float(default_fmt[1])
                    else:
                        solr_record[sf.field_id] = ''
        return solr_record

    def handle(self, *args, **options):

        total = 0
        cycle = 0

        try:
            # Retrieve the Search  and Field models from the database
            solr = SolrClient(settings.SOLR_SERVER_URL)
            try:
                self.search_target = Search.objects.get(search_id=options['search'])
                self.solr_core = self.search_target.solr_core_name
                self.all_fields = Field.objects.filter(search_id=self.search_target)
                if options['quiet']:
                    self.logger.level = logging.ERROR
                if options['nothing_to_report']:
                    self.search_fields = Field.objects.filter(search_id=self.search_target, alt_format='ALL') | Field.objects.filter(search_id=self.search_target, alt_format='NTR')
                else:
                    self.search_fields = Field.objects.filter(search_id=self.search_target, alt_format='ALL') | Field.objects.filter(search_id=self.search_target, alt_format='')
                for search_field in self.search_fields:
                    self.csv_fields[search_field.field_id] = search_field

                    codes = Code.objects.filter(field_id=search_field)
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

            # Process the records in the CSV file one at a time
            with open(options['csv'], 'r', encoding='utf-8-sig', errors="ignore") as csv_file:
                csv_reader = csv.DictReader(csv_file, dialect='excel')
                solr_items = []
                for row_num, csv_record in enumerate(csv_reader):

                    # Determine record ID for regular PD
                    record_id = ""
                    if not options['nothing_to_report']:
                        if self.search_target.id_fields:
                            id_values = []
                            for id_field in self.search_target.id_fields.split(","):
                                id_values.append(csv_record[id_field])
                            record_id = ",".join(id_values)
                    else:

                        if 'month' in solr_record:
                            solr_record['id'] = "{0}-{1}-{2}".format(solr_record['owner_org'], solr_record['year'], solr_record['month'])
                        elif 'quarter' in solr_record:
                            solr_record['id'] = "{0}-{1}-{2}".format(solr_record['owner_org'], solr_record['year'],
                                                                     solr_record['quarter'])

                    # Clear out the Solr core. on the first line
                    if total == 0 and not options['nothing_to_report']:
                        solr.delete_doc_by_query(self.solr_core, "*:*")
                        self.logger.info("Purging all records")
                    elif total == 0 and options['nothing_to_report']:
                        solr.delete_doc_by_query(self.solr_core, "format:NTR")
                        solr.commit(self.solr_core, softCommit=True)
                        self.logger.info("Purging NTR records")
                    total += 1
                    cycle += 1

                    # Call plugins if they exist for this search type. This is where a developer can introduce
                    # code to customize the data that is loaded into Solr for a particular search.
                    search_type_plugin = 'search.plugins.{0}'.format(options['search'])
                    if search_type_plugin in self.discovered_plugins:
                        include, filtered_record = self.discovered_plugins[search_type_plugin].filter_csv_record(csv_record, self.search_target, self.csv_fields, self.field_codes, 'NTR' if options['nothing_to_report'] else '')
                        if not include:
                            continue
                        else:
                            csv_record = filtered_record
                    # Create a dictionary for each record loaded into  Solr
                    solr_record = {'format': 'NTR' if options['nothing_to_report'] else 'DEFAULT'}
                    for csv_field in csv_reader.fieldnames:
                        # Verify that it is a known field
                        if csv_field not in self.csv_fields and csv_field not in ('owner_org_title', 'owner_org'):
                            self.logger.error("CSV files contains unknown field: {0}".format(csv_field))
                            exit(-1)
                        if csv_field == 'owner_org_title':
                            continue

                        # Handle multi-valued fields here
                        if self.csv_fields[csv_field].solr_field_multivalued:
                            solr_record[csv_field] = csv_record[csv_field].split(',')
                            # Copy fields fo report cannot use multi-values - so directly populate with original string
                            if self.csv_fields[csv_field].solr_field_export:
                                for extra_field in self.csv_fields[csv_field].solr_field_export.split(','):
                                    solr_record[extra_field] = csv_record[csv_field]
                        else:
                            solr_record[csv_field] = csv_record[csv_field]

                        # Automatically expand out dates and numbers for use with Solr export handler
                        if self.csv_fields[csv_field].solr_field_type == 'pdate':
                            try:
                                if csv_record[csv_field]:
                                    csv_date = datetime.strptime(csv_record[csv_field], '%Y-%m-%d')
                                    solr_record[csv_field + '_en'] = format_date(csv_date, locale='en')
                                    solr_record[csv_field + '_fr'] = format_date(csv_date, locale='fr')
                                    if self.csv_fields[csv_field].is_default_year:
                                        solr_record['year'] = csv_date.year
                                    if self.csv_fields[csv_field].is_default_month:
                                        solr_record['month'] = csv_date.month
                                else:
                                    solr_record[csv_field + '_en'] = ''
                                    solr_record[csv_field + '_fr'] = ''
                            except ValueError as x2:
                                self.logger.error('Row {0}, Record {1}, Invalid date: "{1}"'.format(row_num + 2, record_id, x2))
                                solr_record[csv_field] = ''
                                continue
                        elif self.csv_fields[csv_field].solr_field_type in ['pint', 'pfloat']:
                            if solr_record[csv_field]:
                                if solr_record[csv_field] == '.':
                                    solr_record[csv_field] = "0"
                                csv_decimal = parse_decimal(solr_record[csv_field], locale='en_US')
                                if self.csv_fields[csv_field].solr_field_is_currency:
                                    solr_record[csv_field + '_en'] = format_currency(csv_decimal, 'CAD', locale='en_CA')
                                    solr_record[csv_field + '_fr'] = format_currency(csv_decimal, 'CAD', locale='fr_CA')
                                else:
                                    solr_record[csv_field + '_en'] = format_decimal(csv_decimal, locale='en_CA')
                                    solr_record[csv_field + '_fr'] = format_decimal(csv_decimal, locale='fr_CA')
                            else:
                                solr_record[csv_field + '_en'] = ''
                                solr_record[csv_field + '_fr'] = ''

                        # Lookup the expanded code value from the codes dict of dict
                        if csv_field in self.field_codes:
                            if csv_record[csv_field]:

                                if self.csv_fields[csv_field].solr_field_multivalued:
                                    codes_en = []
                                    codes_fr = []
                                    for code_value in csv_record[csv_field].split(","):
                                        if code_value.lower() in self.field_codes[csv_field]:
                                            codes_en.append(self.field_codes[csv_field][code_value.lower()].label_en)
                                            codes_fr.append(self.field_codes[csv_field][code_value.lower()].label_fr)
                                        else:
                                            self.logger.error("Row {0}, Record {1}. Unknown code value: {2} for field: {3}".format(
                                                row_num + 2, record_id, code_value, csv_field))
                                    solr_record[csv_field + '_en'] = codes_en
                                    solr_record[csv_field + '_fr'] = codes_fr
                                else:
                                    if csv_record[csv_field].lower() in self.field_codes[csv_field]:
                                        solr_record[csv_field + '_en'] = self.field_codes[csv_field][csv_record[csv_field].lower()].label_en
                                        solr_record[csv_field + '_fr'] = self.field_codes[csv_field][csv_record[csv_field].lower()].label_fr
                                    else:
                                        self.logger.error("Row {0}, Record {1}. Unknown code value: {2} for field: {3}".format(
                                            row_num + 2, record_id, csv_record[csv_field], csv_field))
                    solr_record = self.set_empty_fields(solr_record)

                    # Set the Solr ID field (Nothing To Report records are excluded)
                    if not options['nothing_to_report']:
                        solr_record['id'] = record_id
                    else:
                        if 'month' in solr_record:
                            solr_record['id'] = "{0}-{1}-{2}".format(solr_record['owner_org'], solr_record['year'], solr_record['month'])
                        elif 'quarter' in solr_record:
                            solr_record['id'] = "{0}-{1}-{2}".format(solr_record['owner_org'], solr_record['year'],
                                                                     solr_record['quarter'])

                    # Call plugins if they exist for this search type. This is where a developer can introduce
                    # code to customize the data that is loaded into Solr for a particular search.
                    if search_type_plugin in self.discovered_plugins:
                        solr_record = self.discovered_plugins[search_type_plugin].load_csv_record(csv_record, solr_record, self.search_target, self.csv_fields, self.field_codes, 'NTR' if options['nothing_to_report'] else '')

                    solr_items.append(solr_record)

                    # Write to Solr whenever the cycle threshold is reached
                    if cycle >= self.cycle_on:
                        # try to connect to Solr up to 10 times
                        for countdown in reversed(range(10)):
                            try:
                                solr.index(self.solr_core, solr_items)
                                self.logger.info("{0} rows processed".format(total))
                                cycle = 0
                                solr_items.clear()
                                break
                            except ConnectionError as cex:
                                if not countdown:
                                    raise
                                self.logger.info("Solr error: {0}. Waiting to try again ... {1}".format(cex, countdown))
                                time.sleep((10 - countdown) * 5)

                # Write and remaining records to Solr and commit
                if cycle > 0:
                    # try to connect to Solr up to 10 times
                    for countdown in reversed(range(10)):
                        try:
                            solr.index(self.solr_core, solr_items)
                            total += len(solr_items)
                            self.logger.info("{0} rows processed".format(cycle))
                            cycle = 0
                            solr_items.clear()
                            break
                        except ConnectionError as cex:
                            if not countdown:
                                raise
                            self.logger.info("Solr error: {0}. Waiting to try again ... {1}".format(cex, countdown))
                            time.sleep((10 - countdown) * 5)

                solr.commit(self.solr_core, softCommit=True, waitSearcher=True)
                self.logger.info("Total rows processed: {0}".format(total))

        except Exception as x:
            self.logger.error('Unexpected Error "{0}"'.format(x))
