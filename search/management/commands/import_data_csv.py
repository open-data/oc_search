import os
import sys

from babel.dates import format_date
from babel.numbers import format_currency, format_decimal, parse_decimal, NumberFormatError
from datetime import datetime
from django.core.management.base import BaseCommand
from django.conf import settings
from .goc_prev_org_names import add_prev_dept_names
import importlib
import pkgutil
import re
from search.models import Search, Field, Code, Event
import search.plugins
from SolrClient2 import SolrClient
from SolrClient2.exceptions import ConnectionError
import traceback
import csv
import logging
import time

# Magic Solr String field max length
MAX_FIELD_LENGTH = 31000


class Command(BaseCommand):
    help = 'Django manage command that will import CSV data into a custom Open Canada search'

    logger = logging.getLogger(__name__)

    # class variables that hold the search models
    search_target = None
    solr_core = None
    search_fields = None
    csv_fields = {}
    all_fields = {}
    field_codes = {}

    # Number of rows to commit to Solr at a time
    cycle_on = settings.IMPORT_DATA_CSV_SOLR_INDEX_GROUP_SIZE

    discovered_plugins = {
        name: importlib.import_module(name)
        for finder, name, ispkg
        in pkgutil.iter_modules(search.plugins.__path__, search.plugins.__name__ + ".")
    }

    def add_arguments(self, parser):
        parser.add_argument('--search', type=str, help='The Search ID that is being loaded', required=True)
        parser.add_argument('--csv', type=str, help='CSV filename to import', required=True)
        parser.add_argument('--quiet', required=False, action='store_true', help='Deprecated option')
        parser.add_argument('--nothing_to_report', required=False, action='store_true', default=False,
                            help='Use this switch to indicate if the CSV files that is being loaded contains '
                                 '"Nothing To Report" data')
        parser.add_argument('--report_duplicates', required=False, action='store_true', default=False,
                            help='Use this switch to indicate if the CSV files that is being loaded contains duplicate IDs')
        parser.add_argument('--append', required=False, action='store_true', default=False,
                            help='Add these records, do not truncate the Solr core')
        parser.add_argument('--not_pd', required=False, action='store_true', default=False,
                            help='Not Loading GoC Proactive Disclosure data, so do not do default department data handling')
        parser.add_argument('--verbose', required=False, action='store_true', default=False,
                            help="Display rolling count when importing large datasets")

    def set_empty_fields(self, solr_record: dict):

        for sf in self.all_fields:
            self.set_empty_field(solr_record, sf)
        return solr_record

    def set_empty_field(self, solr_record: dict, sf: Field):
        # look for empty fields, empty multi-value fields, and empty multi-value codes and set them
        if (sf.field_id not in solr_record and sf != 'default_fmt') or (solr_record[sf.field_id] == '') or \
            (isinstance(solr_record[sf.field_id], list) and len(solr_record[sf.field_id]) < 1) or \
            (isinstance(solr_record[sf.field_id], list) and solr_record[sf.field_id][0] == ''):
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
            if sf.solr_field_is_coded:
                solr_record[f"{sf.field_id}_en"] = "-"
                solr_record[f"{sf.field_id}_fr"] = "-"

    def handle(self, *args, **options):

        total = 0
        commit_count = 0
        cycle = 0
        index_cycle = 0
        error_count = 0

        try:
            # Retrieve the Search  and Field models from the database
            solr = SolrClient(settings.SOLR_SERVER_URL)
            try:
                self.search_target = Search.objects.get(search_id=options['search'])
                self.solr_core = self.search_target.solr_core_name
                self.all_fields = Field.objects.filter(search_id=self.search_target)
                if options['verbose']:
                    self.logger.level = logging.INFO
                else:
                    self.logger.level = logging.WARNING
                if options['nothing_to_report']:
                    self.search_fields = Field.objects.filter(search_id=self.search_target,
                                                              alt_format='ALL') | Field.objects.filter(
                        search_id=self.search_target, alt_format='NTR')
                else:
                    self.search_fields = Field.objects.filter(search_id=self.search_target,
                                                              alt_format='ALL') | Field.objects.filter(
                        search_id=self.search_target, alt_format='')
                for search_field in self.search_fields:
                    self.csv_fields[search_field.field_id] = search_field

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

            if options['report_duplicates']:
                ids = {}

            # Test for the existence of the bad data directory.

            if not os.path.exists(settings.IMPORT_DATA_CSV_BAD_DATA_DIR):
                self.logger.error(f'Error report directory: "{settings.IMPORT_DATA_CSV_BAD_DATA_DIR}" cannot be found.'
                                  ' Location is set by IMPORT_DATA_CSV_BAD_DATA_DIR in the settings file')
                exit(-1)

            solr_items = []

            # Clear out the Solr core when loading default data

            if options['nothing_to_report']:
                solr.delete_doc_by_query(self.solr_core, "format:NTR")
                solr.commit(self.solr_core, softCommit=True)
                self.logger.info("Purging NTR records")
            elif not options['append']:
                solr.delete_doc_by_query(self.solr_core, "*:*")
                self.logger.info("Purging all records")
                # Not committing here, as we are going to be adding a lot of records

            # Process the records in the CSV file one at a time
            with open(options['csv'], 'r', encoding='utf-8-sig', errors="xmlcharrefreplace") as csv_file:
                with open(os.path.join(settings.IMPORT_DATA_CSV_BAD_DATA_DIR, os.path.basename(options['csv'])), 'w', encoding="utf-8-sig") as bd_file:

                    csv_reader = csv.DictReader(csv_file, dialect='excel')
                    bd_writer = None

                    for row_num, csv_record in enumerate(csv_reader):
                        try:
                            # Create a dictionary for each record loaded into  Solr
                            solr_record = {'format': 'NTR' if options['nothing_to_report'] else 'DEFAULT'}

                            # Determine record ID for regular PD
                            record_id = ""
                            if not options['nothing_to_report']:
                                if self.search_target.id_fields:
                                    id_values = []
                                    for id_field in self.search_target.id_fields.split(","):
                                        id_values.append(str(csv_record[id_field]).replace("/", "_"))
                                    record_id = ",".join(id_values)
                            else:

                                if 'month' in csv_record and 'month' in self.csv_fields:
                                    record_id = "{0}-{1}-{2}".format(csv_record['owner_org'], csv_record['year'],
                                                                     csv_record['month'])
                                elif 'quarter' in csv_record:
                                    if 'fiscal_year' in csv_record:
                                        record_id = "{0}-{1}-{2}".format(csv_record['owner_org'],
                                                                         csv_record['fiscal_year'],
                                                                         csv_record['quarter'])
                                    elif 'year' in csv_record:
                                        record_id = "{0}-{1}-{2}".format(csv_record['owner_org'], csv_record['year'],
                                                                         csv_record['quarter'])
                                    else:
                                        record_id = "{0}-{1}-{2}".format(
                                            csv_record['owner_org'], csv_record['quarter'])

                            if options['report_duplicates']:
                                if record_id in ids:
                                    self.logger.error('Duplicate record ID found: "{0}"'.format(record_id))
                                ids[record_id] = True

                            cycle += 1
                            index_cycle += 1

                            # Call plugins if they exist for this search type. This is where a developer can introduce
                            # code to customize the data that is loaded into Solr for a particular search.

                            search_type_plugin = 'search.plugins.{0}'.format(options['search'])
                            if search_type_plugin in self.discovered_plugins:
                                include, filtered_record = self.discovered_plugins[
                                    search_type_plugin].filter_csv_record(
                                    csv_record, self.search_target, self.csv_fields, self.field_codes,
                                    'NTR' if options['nothing_to_report'] else '')
                                if not include:
                                    continue
                                else:
                                    csv_record = filtered_record

                            # Process every field in the record

                            for csv_field in csv_record:

                                # Verify that it is a known field

                                fields_to_ignore = (
                                    'owner_org_title', 'owner_org', 'record_created', 'record_modified',
                                    'user_modified')
                                fields_not_loaded = (
                                    'owner_org_title', 'record_created', 'user_modified', 'record_modified',)
                                if csv_field not in self.csv_fields and csv_field not in fields_to_ignore:
                                    self.logger.error("CSV files contains unknown field: {0}".format(csv_field))
                                    exit(-1)
                                if csv_field in fields_not_loaded:
                                    continue

                                # Handle multi-valued fields here. Use custom delimiter and strip whitespace from values

                                if self.csv_fields[csv_field].solr_field_multivalued:
                                    delimiter = self.csv_fields[csv_field].solr_field_multivalue_delimeter
                                    solr_record[csv_field] = list(
                                        map(lambda c: c.strip(), csv_record[csv_field].split(delimiter)))
                                else:
                                    solr_record[csv_field] = csv_record[csv_field]

                                #  However, Solr fields used for export must be single value strings

                                if self.csv_fields[csv_field].solr_field_export:
                                    for extra_field in self.csv_fields[csv_field].solr_field_export.split(','):
                                        # print(f"{csv_record[csv_field]}, {type(csv_record[csv_field])}")

                                        if self.csv_fields[csv_field].solr_field_multivalued:
                                            solr_record[extra_field] = csv_record[csv_field]
                                            # Ensure these undefined fields have default values
                                            if not solr_record[extra_field]:
                                                solr_record[extra_field] = "-"

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
                                        self.logger.error(
                                            'Row {0}, Record {1}, Invalid date: "{1}"'.format(row_num + 2, record_id, x2))
                                        solr_record[csv_field] = ''
                                        continue
                                elif self.csv_fields[csv_field].solr_field_type in ['pint', 'pfloat']:
                                    if solr_record[csv_field]:
                                        if solr_record[csv_field] == '.':
                                            solr_record[csv_field] = "0"
                                        if self.csv_fields[csv_field].solr_field_is_currency:
                                            csv_normalized = re.sub("[^-0-9.,]", '', solr_record[csv_field])
                                            try:
                                                csv_decimal = parse_decimal(csv_normalized, locale='en_US').normalize()
                                                if self.csv_fields[csv_field].solr_field_type == 'pfloat':
                                                    solr_record[csv_field] = float(csv_decimal)
                                                elif self.csv_fields[csv_field].solr_field_type == 'pint':
                                                    solr_record[csv_field] = int(csv_decimal)
                                                solr_record[csv_field + '_en'] = format_currency(csv_decimal, 'CAD',
                                                                                             locale='en_CA')

                                                try:
                                                    solr_record[csv_field + '_fr'] = format_currency(csv_decimal, 'CAD',
                                                                                                     locale='fr_CA')
                                                except KeyError as kex:
                                                    # Sometimes the Babel locale cannot properly format the currency for French
                                                    solr_record[csv_field + '_fr'] = format_decimal(csv_decimal,
                                                                                                    locale='fr_CA')
                                            except NumberFormatError as nfx:
                                                self.logger.error(f'Unexpected Error "{nfx}" while processing field {csv_field} in row {row_num + 1}')
                                        else:
                                            try:
                                                csv_decimal = parse_decimal(solr_record[csv_field], locale='en_US')
                                                solr_record[
                                                    csv_field + '_en'] = format_decimal(csv_decimal, locale='en_CA')
                                                solr_record[
                                                    csv_field + '_fr'] = format_decimal(csv_decimal, locale='fr_CA')
                                            except NumberFormatError as nfx:
                                                self.logger.error(f'Unexpected Error "{nfx}" while processing field {csv_field} in row {row_num + 1}')
                                    else:
                                        solr_record[csv_field + '_en'] = ''
                                        solr_record[csv_field + '_fr'] = ''
                                elif self.csv_fields[csv_field].solr_field_type == 'search_text_en':
                                    if len(solr_record[csv_field]) == 0:
                                        self.set_empty_field(solr_record, self.csv_fields[csv_field])
                                        solr_record[csv_field + 'g'] = str(solr_record[csv_field]).strip()
                                    elif len(solr_record[csv_field]) > MAX_FIELD_LENGTH:
                                        solr_record[csv_field + 'g'] = str(
                                            solr_record[csv_field][:MAX_FIELD_LENGTH]).strip() + " ..."
                                        self.logger.warning(
                                            "Row {0}, Length of {1} is {2}, truncated to {3}".format(
                                                total, csv_field + 'g', len(solr_record[csv_field]),len(solr_record[csv_field + 'g'])))
                                    elif csv_field + 'g' not in solr_record:
                                        solr_record[csv_field + 'g'] = solr_record[csv_field]
                                elif self.csv_fields[csv_field].solr_field_type == 'search_text_fr':
                                    if len(solr_record[csv_field]) == 0:
                                        self.set_empty_field(solr_record, self.csv_fields[csv_field])
                                        solr_record[csv_field + 'a'] = str(solr_record[csv_field]).strip()
                                    elif len(solr_record[csv_field]) > MAX_FIELD_LENGTH:
                                        solr_record[csv_field + 'a'] = str(
                                            solr_record[csv_field][:MAX_FIELD_LENGTH]).strip() + " ..."
                                        self.logger.warning(
                                            "Row {0}, Length of {1} is {2}, truncated to {3}".format(
                                                total, csv_field + 'a', len(solr_record[csv_field]), len(solr_record[csv_field + 'a'])))
                                    elif csv_field + 'a' not in solr_record:
                                        solr_record[csv_field + 'a'] = solr_record[csv_field]

                                # Lookup the expanded code value from the preloaded codes dict of values dict

                                if csv_field in self.field_codes:
                                    if csv_record[csv_field]:

                                        #  Handle multi-valued codes

                                        if self.csv_fields[csv_field].solr_field_multivalued:
                                            codes_en = []
                                            codes_fr = []
                                            for code_value in csv_record[csv_field].split(","):
                                                cv = code_value.lower().strip()
                                                if cv in self.field_codes[csv_field]:
                                                    codes_en.append(
                                                        self.field_codes[csv_field][cv].label_en)
                                                    codes_fr.append(
                                                        self.field_codes[csv_field][cv].label_fr)
                                                else:
                                                    self.logger.warning(
                                                        "Row {0}, Record {1}. Unknown code value: {2} for field: {3}".format(
                                                            row_num + 2, record_id, code_value, csv_field))
                                                    codes_en.append("-")
                                                    codes_fr.append("-")
                                            solr_record[csv_field + '_en'] = codes_en
                                            solr_record[csv_field + '_fr'] = codes_fr

                                        # Handle single codes

                                        else:
                                            if csv_record[csv_field].lower() in self.field_codes[csv_field]:
                                                solr_record[csv_field + '_en'] = self.field_codes[csv_field][
                                                    csv_record[csv_field].lower()].label_en
                                                solr_record[csv_field + '_fr'] = self.field_codes[csv_field][
                                                    csv_record[csv_field].lower()].label_fr

                                                if csv_field == "owner_org" and not options['not_pd']:
                                                    solr_record = add_prev_dept_names(
                                                        csv_record['owner_org'],
                                                        solr_record,
                                                        [self.field_codes[csv_field][csv_record[csv_field].lower()].label_en],
                                                        [self.field_codes[csv_field][csv_record[csv_field].lower()].label_fr],
                                                        [csv_record['owner_org'].split('-')[0] if "-" in csv_record['owner_org'] else csv_record['owner_org']],
                                                        [csv_record['owner_org'].split('-')[1] if "-" in csv_record['owner_org'] else csv_record['owner_org']]
                                                    )

                                            else:
                                                self.logger.warning(
                                                    "Row {0}, Record {1}. Unknown code value: {2} for field: {3}".format(
                                                        row_num + 2, record_id, csv_record[csv_field], csv_field))
                                                solr_record[csv_field + '_en'] = "-"
                                                solr_record[csv_field + '_fr'] = "-"

                                                # Ensure all empty CSV fields are set to appropriate or default values

                            solr_record = self.set_empty_fields(solr_record)

                            # Set the Solr ID field (Nothing To Report records are excluded)

                            solr_record['id'] = record_id

                            # Call plugins if they exist for this search type. This is where a developer can introduce
                            # code to customize the data that is loaded into Solr for a particular search.

                            if search_type_plugin in self.discovered_plugins:
                                solr_record = self.discovered_plugins[search_type_plugin].load_csv_record(csv_record,
                                                                                                          solr_record,
                                                                                                          self.search_target,
                                                                                                          self.csv_fields,
                                                                                                          self.field_codes,
                                                                                                          'NTR' if
                                                                                                          options[
                                                                                                              'nothing_to_report'] else '')

                            if bd_writer is None:
                                bd_writer = csv.DictWriter(bd_file, fieldnames=solr_record.keys())
                                bd_writer.writeheader()
                                bd_file.flush()

                            solr_items.append(solr_record)
                            total += 1

                            # In debug mode, index the data to Solr much more frequently. This can be helpful for isolating
                            # problem rows. Otherwise use large batches
                            if index_cycle >= settings.IMPORT_DATA_CSV_SOLR_INDEX_GROUP_SIZE:
                                try:
                                    solr.index(self.solr_core, solr_items)
                                    commit_count += len(solr_items)

                                except ConnectionError as cex:

                                    self.logger.warning(f"Solr error starting on row {total}. Row data has {len(solr_items)} items")
                                    for sitm in solr_items:
                                        self.logger.warning(f"{sitm}")
                                        bd_writer.writerow(sitm)
                                    self.logger.warning(f"Connection Error. Args: {cex.args}")
                                    error_count += 1
                                    # Force a delay to give the network/system time to recover - hopefully
                                    time.sleep(2)

                                except Exception as x:
                                    self.logger.warning(f'Unexpected error "{x}" encountered while indexing starting on row {total}. Row data has {len(solr_items)} items')
                                    for sitm in solr_items:
                                        self.logger.warning(f"{sitm}")
                                        bd_writer.writerow(sitm)
                                        bd_file.flush()
                                    error_count += 1
                                    # Force a delay to give the network/system time to recover - hopefully
                                    time.sleep(2)
                                finally:
                                    solr_items.clear()
                                    index_cycle = 0

                            # Commit to Solr whenever the cycle threshold is reached
                            if cycle >= self.cycle_on:
                                if options['verbose']:
                                    sys.stdout.write(f"{total} rows processed\r")
                                cycle = 0
                            if error_count > 100:
                                if options['verbose']:
                                    self.logger.info(f"{error_count} errors so far")

                        except Exception as x:
                            self.logger.error(f'Unexpected Error "{x}" while processing row {row_num + 1}')
                            if options['verbose']:
                                traceback.print_exception(type(x), x, x.__traceback__)

                    # Write and remaining records to Solr and commit

                    try:
                        if len(solr_items) > 0:
                            solr.index(self.solr_core, solr_items)
                            commit_count += len(solr_items)
                            Event.objects.create(search_id=options['search'], component_id="import_data_csv",
                                                 title=f"Total rows processed: {total}, committed to Solr: {commit_count}",
                                                 category='success', message=f"For Search {options['search']}, {total} records loaded from {options['csv']}")
                    except ConnectionError as cex:
                        self.logger.warning(
                            f"Unexpected error encountered while indexing starting on row {total}. Row data has {len(solr_items)} items")
                        for sitm in solr_items:
                            self.logger.warning(f"{sitm}")
                            bd_writer.writerow(sitm)
                            bd_file.flush()
                        error_count += 1
                        # Force a delay to give the network/system time to recover - hopefully
                        time.sleep(2)
                    except Exception as ex:
                        for sitm in solr_items:
                            self.logger.warning(f"{sitm}")
                            bd_writer.writerow(sitm)
                            bd_file.flush()
                    finally:
                        solr.commit(self.solr_core, softCommit=True, waitSearcher=True)
                        sys.stdout.write(f"\nTotal rows processed: {total}, committed to Solr: {commit_count}")

        except Exception as x:
            self.logger.error('Unexpected Error "{0}"'.format(x.args))
        finally:
            sys.stdout.write("Import completed")
