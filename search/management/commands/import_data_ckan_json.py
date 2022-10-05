from babel.dates import format_date
from datetime import datetime
from django.core.management.base import BaseCommand
from django.conf import settings
import json
import logging
from search.models import Search, Field, Code
from SolrClient import SolrClient
from SolrClient.exceptions import ConnectionError
from time import time
import traceback

IGNORED_FIELDS = ['creator_user_id', 'groups', 'isopen', 'license_title', 'license_url', 'notes', 'num_resources',
                  'num_tags', 'private', 'relationships_as_object', 'relationships_as_subject', 'revision_id',
                  'schema', 'state', 'tags', 'title', 'validation_options', 'validation_status',
                  'validation_timestamp', 'version']
BILINGUAL_FIELDS = ['additional_note', 'contributor', 'data_series_issue_identification', 'data_series_name', 'maintainer_contact_form',
                    'metadata_contact', 'notes_translated', 'org_section', 'org_title_at_publication',
                    'position_name', 'program_page_url', 'series_publication_dates', 'title_translated']
DATE_FIELDS = {'metadata_created', 'metadata_modified', 'federated_date_modified', 'date_modified'}
# Note: in Solr all resource fieldnames are prefixed with "resource_". resource_type in already prefixed
RESOURCE_FIELDS = ['character_set', 'data_quality', 'datastore_active', 'date_published', 'format', 'language',
                   'name_translated', 'related_relationship', 'related_type', 'resource_type', 'size', 'url']


class Command(BaseCommand):

    help = 'Import CKAN JSON lines of Open Canada packages'

    logger = logging.getLogger(__name__)
    # class variables that hold the search models
    search_target = None
    solr_core = None
    # search_fields: dict[str, Field] = {}
    search_fields = {}
    all_fields = {}
    # field_codes: dict[str, Code] = {}
    field_codes = {}
    # Number of rows to commit to Solr at a time
    cycle_on = 1000

    resource_map = {}
    # creating a mapping between resource fields and Solr fields
    for r in RESOURCE_FIELDS:
        if r.startswith("resource_"):
            resource_map[r] = r
        elif r == "name_translated":
            resource_map["name_translated_en"] = "resource_name_translated_en"
            resource_map["name_translated_fr"] = "resource_name_translated_fr"
        else:
            resource_map[r] = "resource_" + r

    def set_value(self, field_name, raw_value, solr_record, id):
        if field_name in IGNORED_FIELDS:
            pass
        elif field_name in BILINGUAL_FIELDS:

            # Note that supported langauge codes include "en" and "fr", and also their automated translation
            # equivalents "en-t-fr" and "fr-t-en". We want to track which fields use automated translation since
            # this is used by the web UI.

            ens = ['en', 'en-t-fr']
            frs = ['fr', 'fr-t-en']
            lang_found = False
            automation = False
            for lang_code in ens:
                if lang_code in raw_value:
                    if isinstance(raw_value[lang_code], str):
                        solr_record[field_name + "_en"] = raw_value[lang_code]
                    else:
                        solr_record[field_name + "_en"] = str(raw_value[lang_code])
                        self.logger.warning(f"Unusual data encountered in record {id} for field {field_name}: {solr_record[field_name + '_en']}")
                    if lang_code == 'en-t-fr':
                        automation = True
                lang_found = True
            if not lang_found:
                solr_record[field_name + "_en"] = "-"
            if automation:
                solr_record['machine_translated_fields'].append(field_name + "_en")

            lang_found = False
            automation = False
            for lang_code in frs:
                if lang_code in raw_value:
                    if isinstance(raw_value[lang_code], str):
                        solr_record[field_name + "_fr"] = raw_value[lang_code]
                    else:
                        solr_record[field_name + "_fr"] = str(raw_value[lang_code])
                        self.logger.warning(f"Unusual data encountered in record {id} for field {field_name}: {solr_record[field_name + '_fr']}")
                    if lang_code == 'fr-t-en':
                        automation = True
                lang_found = True
            if not lang_found:
                solr_record[field_name + "_fr"] = "-"
            if automation:
                solr_record['machine_translated_fields'].append(field_name + "_fr")

        elif field_name in DATE_FIELDS:
            # Requires Python 3.9+ This line cna replace the clunky IF statement
            # raw_date = datetime.fromisoformat(raw_value)
            if 'T' in raw_value:
                raw_date = datetime.strptime(raw_value, "%Y-%m-%dT%H:%M:%S.%f")
            elif len(raw_value) == 10:
                raw_date = datetime.strptime(raw_value, "%Y-%m-%d")
            else:
                raw_date = datetime.strptime(raw_value, "%Y-%m-%d %H:%M:%S")
            solr_record[field_name] = raw_value
            solr_record[field_name + '_en'] = format_date(raw_date, locale='en')
            solr_record[field_name + '_fr'] = format_date(raw_date, locale='fr')
        elif field_name in self.search_fields:
            # Emoty values are problematic since Solr won't index a blank space. Use the dash as the understood
            # indicator for an empty value
            if raw_value is None or not raw_value:
                raw_value = "-"
            elif self.search_fields[field_name].solr_field_is_coded:
                #self.logger.info(f'Field: {field_name}, Value: {raw_value}')
                if type(raw_value) == list:
                    values = []
                    values_en = []
                    values_fr = []
                    for val in raw_value:
                        values.append(val)
                        values_en.append(self.field_codes[field_name][val].label_en)
                        values_fr.append(self.field_codes[field_name][val].label_fr)
                    if len(values) > 0:
                        solr_record[field_name] = ",".join(values)
                        solr_record[field_name + "_en"] = ",".join(values_en)
                        solr_record[field_name + "_fr"] = ",".join(values_fr)
                    else:
                        solr_record[field_name] = ["-"]
                        solr_record[field_name + "_en"] = ["-"]
                        solr_record[field_name + "_fr"] = ["-"]
                else:
                    ri = str(raw_value).lower()
                    solr_record[field_name] = raw_value
                    solr_record[field_name + "_en"] = self.field_codes[field_name][ri].label_en
                    solr_record[field_name + "_fr"] = self.field_codes[field_name][ri].label_fr
            else:
                solr_record[field_name] = raw_value

        return solr_record

    def handle_resources(self, resources, solr_record):

        # create dict of lists to hold the collected multi-value resource fields
        solr_resources = {}
        datastore_enabled = False
        for r in self.resource_map:
            solr_resources[self.resource_map[r]] = []

        # set a list of unique file formats for the dataset as a whole
        formats = []

        for res in resources:
            for res_value in RESOURCE_FIELDS:
                if res_value in res:
                    if res_value == "name_translated":
                        if 'en' in res[res_value]:
                            solr_resources[self.resource_map[res_value + "_en"]].append(res[res_value]['en'])
                        elif 'en-t-fr'in res[res_value]:
                            solr_resources[self.resource_map[res_value + "_en"]].append(res[res_value]['en-t-fr'])
                        if 'fr' in res[res_value]:
                            solr_resources[self.resource_map[res_value + "_fr"]].append(res[res_value]['fr'])
                        elif 'fr-t-en' in res[res_value]:
                            solr_resources[self.resource_map[res_value + "_fr"]].append(res[res_value]['fr-t-en'])
                    elif res_value == "datastore_active":
                        if res[res_value]:
                            datastore_enabled = True
                    elif isinstance(res[res_value], list):
                        if len(res[res_value]) > 0:
                            solr_resources[self.resource_map[res_value]].append(",".join(res[res_value]))
                        else:
                            solr_resources[self.resource_map[res_value]].append('-')
                    else:
                        solr_resources[self.resource_map[res_value]].append(res[res_value])
                    if res_value == "format":
                        if not res["format"] in formats:
                            formats.append(res["format"] )
                else:
                    solr_resources[self.resource_map[res_value]].append('-')

        solr_record['formats'] = formats

        if datastore_enabled:
            solr_record['datastore_enabled'] = 'True'
        else:
            solr_record['datastore_enabled'] = 'False'
        solr_record.update(solr_resources)
        return solr_record
        # format, language[], name_translated, resource_type, url

    def add_arguments(self, parser):
        parser.add_argument('--search', type=str, help='The Search ID that is being loaded', required=True)
        parser.add_argument('--jsonl', type=str, help='JSON lines filename to import', required=True)
        parser.add_argument('--quiet', required=False, action='store_true', default=False,
                            help='Only display error messages')

    def set_empty_fields(self, solr_record: dict):

        for sf in self.all_fields:
            self.set_empty_field(solr_record, sf)
        return solr_record

    def set_empty_field(self, solr_record: dict, sf: Field):
        if (sf.field_id not in solr_record and sf not in ['default_fmt', 'unique_identifier']) \
            or solr_record[sf.field_id] == '' \
            or (isinstance(solr_record[sf.field_id], list) and len(solr_record[sf.field_id]) < 1) \
            or (isinstance(solr_record[sf.field_id], list) and solr_record[sf.field_id][0] == ''):
            if sf.default_export_value:
                default_fmt = sf.default_export_value.split('|')
                if default_fmt[0] in ['str', 'date']:
                    solr_record[sf.field_id] = str(default_fmt[1])
                    if sf.solr_field_is_coded:
                        solr_record[sf.field_id + "_en"] = str(default_fmt[1])
                        solr_record[sf.field_id + "_fr"] = str(default_fmt[1])
                elif default_fmt[0] == 'int':
                    solr_record[sf.field_id] = int(default_fmt[1])
                    if sf.solr_field_is_coded:
                        solr_record[sf.field_id + "_en"] = int(default_fmt[1])
                        solr_record[sf.field_id + "_fr"] = int(default_fmt[1])
                elif default_fmt[0] == 'float':
                    solr_record[sf.field_id] = float(default_fmt[1])
                    if sf.solr_field_is_coded:
                        solr_record[sf.field_id + "_en"] = float(default_fmt[1])
                        solr_record[sf.field_id + "_fr"] = float(default_fmt[1])
                else:
                    solr_record[sf.field_id] = ''

    def handle(self, *args, **options):

        solr_records = []
        try:
            # Retrieve the Search  and Field models from the database
            solr = SolrClient(settings.SOLR_SERVER_URL)

            try:
                self.search_target = Search.objects.get(search_id=options['search'])
                self.solr_core = self.search_target.solr_core_name
                self.all_fields = Field.objects.filter(search_id=self.search_target)
                self.all_fields_dict = {}
                for f in self.all_fields:
                    self.all_fields_dict[f.field_id] = f;
                if options['quiet']:
                    self.logger.level = logging.WARNING
                sf = Field.objects.filter(search_id=self.search_target,
                                                          alt_format='ALL') | Field.objects.filter(
                    search_id=self.search_target, alt_format='')
                solr.delete_doc_by_query(self.solr_core, "*:*")
                self.logger.info("Purging all records")

                for search_field in sf:
                    self.search_fields[search_field.field_id] = search_field
                    codes = Code.objects.filter(field_id=search_field)
                    # Most csv_fields will not  have codes, so the queryset will be zero length
                    if len(codes) > 0:
                        code_dict = {}
                        for code in codes:
                            code_dict[code.code_id.lower()] = code
                        self.field_codes[search_field.field_id] = code_dict

                with open(options['jsonl'], 'r', encoding='utf-8-sig', errors="ignore") as json_file:
                    for dataset in json_file:
                        solr_record = {'machine_translated_fields': ['-'],
                                       'subject': [],
                                       'subject_en': [],
                                       'subject_fr': []}
                        ds = json.loads(dataset)
                        #self.logger.info(f'Importing {ds["id"]}')
                        for f in ds:
                            # Organization, resources, and type requires special handling
                            if f == 'organization':
                                org = ds[f]['name']
                                solr_record = self.set_value('owner_org', org, solr_record, ds['id'])
                            elif f == 'owner_org':
                                # Ignore the root owner_org - it is a CKAN UUID
                                pass
                            elif f == 'resources':
                                solr_record = self.handle_resources(ds[f], solr_record)
                                formats_en = []
                                formats_fr = []
                                for f in solr_record['formats']:
                                    if f.lower() in self.field_codes['resource_format']:
                                        formats_en.append(self.field_codes['resource_format'][f.lower()].label_en)
                                        formats_fr.append(self.field_codes['resource_format'][f.lower()].label_fr)
                                solr_record['formats_en'] = formats_en
                                solr_record['formats_fr'] = formats_fr
                            elif f == 'type':
                                solr_record = self.set_value('dataset_type', ds[f], solr_record, ds['id'])
                            elif f == "subject":
                                for s in ds[f]:
                                    solr_record['subject_en'].append(self.field_codes['subject'][s].label_en)
                                    solr_record['subject_fr'].append(self.field_codes['subject'][s].label_fr)
                                    solr_record['subject'].append(s)
                            elif f == 'keywords':
                                if 'en' in ds[f]:
                                    solr_record['keywords_en'] = ds[f]['en']
                                    solr_record['keywords_en_text'] = ds[f]['en']
                                if 'en-t-fr' in ds[f]:
                                    solr_record['keywords_en'] = ds[f]['en-t-fr']
                                    solr_record['keywords_en_text'] = ds[f]['en-t-fr']
                                    solr_record['machine_translated_fields'].append('keywords_en')
                                if 'fr' in ds[f]:
                                    solr_record['keywords_fr'] = ds[f]['fr']
                                    solr_record['keywords_fr_text'] = ds[f]['fr']
                                if 'fr-t-en' in ds[f]:
                                    solr_record['keywords_fr'] = ds[f]['fr-t-en']
                                    solr_record['keywords_fr_text'] = ds[f]['fr-t-en']
                                    solr_record['machine_translated_fields'].append('keywords_fr')
                            elif f == "credit":
                                if isinstance(ds[f], list):
                                    c_en = []
                                    c_fr = []
                                    for c in ds[f]:
                                        if 'credit_name' in c:
                                            if 'en' in c['credit_name']:
                                                c_en.append(c['credit_name']['en'])
                                            if 'fr' in c['credit_name']:
                                                c_fr.append(c['credit_name']['fr'])
                                    if len(c_en) > 0:
                                        solr_record['credit_en'] = c_en
                                    else:
                                        solr_record['credit_en'] = ['-']
                                    if len(c_fr) > 0:
                                        solr_record['credit_fr'] = c_fr
                                    else:
                                        solr_record['credit_fr'] = ['-']
                                else:
                                    pass
                            else:
                                solr_record = self.set_value(f, ds[f], solr_record, ds['id'])

                        # Ensure all empty CSV fields are set to appropriate or default values

                        solr_record = self.set_empty_fields(solr_record)

                        solr_record['machine_translated_fields'] = ",".join(solr_record['machine_translated_fields'])

                        solr_records.append(solr_record)
                        #self.logger.info(json.dumps(solr_record, indent=4))

                        # Write to Solr whenever the cycle threshold is reached
                        if len(solr_records) >= self.cycle_on:
                            # try to connect to Solr up to 10 times
                            for countdown in reversed(range(10)):
                                try:
                                    solr.index(self.solr_core, solr_records)
                                    cycle = 0
                                    self.logger.info(f'Sent {len(solr_records)} to Solr')
                                    solr_records.clear()
                                    break
                                except ConnectionError as cex:
                                    if not countdown:
                                        raise
                                    self.logger.error(
                                        "Solr error: {0}. Waiting to try again ... {1}".format(cex, countdown))
                                    time.sleep((10 - countdown) * 5)

                    for countdown in reversed(range(10)):
                        try:
                            if len(solr_records) > 0:
                                solr.index(self.solr_core, solr_records)
                            cycle = 0
                            self.logger.info(f'Sent {len(solr_records)} to Solr')
                            solr_records.clear()
                            solr.commit(self.solr_core, softCommit=True, waitSearcher=True)
                            break
                        except ConnectionError as cex:
                            if not countdown:
                                raise
                            self.logger.error(
                                "Solr error: {0}. Waiting to try again ... {1}".format(cex, countdown))
                            time.sleep((10 - countdown) * 5)
            except Search.DoesNotExist as x:
                self.logger.error('Search not found: "{0}"'.format(x))
                exit(-1)
            except Field.DoesNotExist as x1:
                self.logger.error('Fields not found for search: "{0}"'.format(x1))
            finally:
                solr.commit(self.solr_core)

        except Exception as x:
            traceback.print_exception(type(x), x, x.__traceback__)
            self.logger.error('Unexpected Error "{0}"'.format(x))
