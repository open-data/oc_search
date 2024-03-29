from datetime import datetime, timezone
from django.core.management.base import BaseCommand
from pathlib import Path
from search.models import Search, Field, Code
from yaml import load, FullLoader
try:
    from yaml import CLoader as Loader
except ImportError:
    from yaml import Loader
import logging


class Command(BaseCommand):

    help = 'Load Schema information from a CKAN recombinant YAML file into the Search model'

    logger = logging.getLogger(__name__)

    field_types = {
        'money': 'pfloat',
        'text': 'string',
        'date': 'pdate'
    }

    def add_arguments(self, parser):
        parser.add_argument('--yaml_file', type=str, help='Filepath for the CKAN recombinant YAML file', required=True)
        parser.add_argument('--search', type=str, help='A unique code identifier for the Search', required=True)
        parser.add_argument('--title_en', type=str, help='An English title to use for the search', required=True)
        parser.add_argument('--title_fr', type=str, help='A French title to use for the search', required=True)
        parser.add_argument('--reset', action='store_true', required=False, default=False,
                            help='Flag to overwrite previous Search settings that were loaded. '
                                 'By default the search is  updated, not overwritten')
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

    def process_yaml_field(self, search, yaml_field, resource_name, options, is_ntr=False):
        '''
        Process a field record from the YAML file
        :param search: Unique search identifier
        :param yaml_field: The YAML object for the field
        :param reset:  Update or overwrite
        :param is_ntr: Inidcator if this is a field for Nothing To Report record
        :return: None
        '''

        reset = options['reset'] if 'reset' in options else False

        # Do not bother processing CKAN internal fields, otherwise retrieve or create the Field model
        if not yaml_field['datastore_id'] in ('record_created', 'record_modified', 'user_modified'):
            field, created = Field.objects.get_or_create(field_id=yaml_field['datastore_id'],
                                                         search_id=search)
            field.search_id = search
            field.format_name = resource_name
            if isinstance(yaml_field['label'], str):
                field.label_en = yaml_field['label']
                field.label_fr = yaml_field['label']
            elif isinstance(yaml_field['label'], dict):
                field.label_en = yaml_field['label']['en']
                field.label_fr = yaml_field['label']['fr']

            # Is nothing to report flag
            if is_ntr:
                if created:
                    if field.alt_format == 'NTR':
                        field.alt_format = 'ALL'
                else:
                    field.alt_format = 'NTR'

            # Don't override the optional fields in case it was manually edited
            if created or reset is True:
                if 'datastore_type' in yaml_field:
                    if yaml_field['datastore_type'] in self.field_types:
                        # defaults to string in the model
                        field.solr_field_type = self.field_types[yaml_field['datastore_type']]
                        if yaml_field['datastore_type'] == 'money':
                            field.solr_field_is_currency = True
                            field.default_export_value = "float|0.0"

                # Automatically expand dates and strings for English and French
                if field.field_id.endswith('_en'):
                    field.solr_field_type = 'search_text_en'
                    field.solr_field_lang = 'en'
                    field.solr_field_export = field.field_id + 'g'
                elif field.field_id.endswith('_fr'):
                    field.solr_field_type = 'search_text_fr'
                    field.solr_field_lang = 'fr'
                    field.solr_field_export = field.field_id + 'a'
                elif field.field_id.endswith('_date'):
                    field.solr_field_type = 'pdate'
                    field.default_export_value = "date|0001-01-01T00:00:00"

                    # The default year is sometimes used  for data facets
                    if 'extract_date_year' in yaml_field:
                        if yaml_field['extract_date_year']:
                            field.is_default_year = True
                    if 'extract_date_month' in yaml_field:
                        if yaml_field['extract_date_month']:
                            field.is_default_month = True

                # Determine i field is multivalued
                if 'validators' in yaml_field:
                    validators = str(yaml_field['validators']).split(" ")
                    for validtor in validators:
                        if validtor == 'scheming_multiple_choice':
                            field.solr_field_multivalued = True

            # If the field has code values, save those to the Code models for the field
            if 'choices' in yaml_field:
                field.solr_field_is_coded = True
                for ccode in yaml_field['choices']:
                    choice, created = Code.objects.get_or_create(code_id=ccode, field_id=field)
                    if 'en' in yaml_field['choices'][ccode]:
                        choice.label_en = yaml_field['choices'][ccode]["en"]
                    else:
                        choice.label_en = yaml_field['choices'][ccode]
                    if 'fr' in yaml_field['choices'][ccode]:
                        choice.label_fr = yaml_field['choices'][ccode]["fr"]
                    else:
                        choice.label_fr = yaml_field['choices'][ccode]
                    if 'lookup' in yaml_field['choices'][ccode]:
                        choice.lookup_codes_default = ",".join(yaml_field['choices'][ccode]['lookup'])
                    if 'conditional_lookup' in yaml_field['choices'][ccode]:

                        for cl in yaml_field['choices'][ccode]['conditional_lookup']:
                            if 'column' in cl:
                                choice.lookup_date_field = cl['column']
                                choice.lookup_codes_conditional = ",".join(cl['lookup'])
                                if 'less_than' in cl:
                                    choice.lookup_date = datetime.strptime(cl['less_than'], '%Y-%m-%d')
                                    choice.lookup_date = choice.lookup_date.replace(tzinfo=timezone.utc)
                                    choice.lookup_test = Code.LookupTests.LESSTHAN
                            elif 'lookup' in cl:
                                choice.lookup_codes_default = ",".join(cl['lookup'])  # list of codes
                    if 'c1' in options and options['c1']:
                        if options['c1'] in yaml_field['choices'][ccode]:
                            choice.extra_01 = yaml_field['choices'][ccode][options['c1']]
                    if 'c2' in options and options['c2']:
                        if options['c2'] in yaml_field['choices'][ccode]:
                            choice.extra_02 = yaml_field['choices'][ccode][options['c2']]
                    if 'c3' in options and options['c3']:
                        if options['c3'] in yaml_field['choices'][ccode]:
                            choice.extra_03 = yaml_field['choices'][ccode][options['c3']]
                    if 'c4' in options and options['c4']:
                        if options['c4'] in yaml_field['choices'][ccode]:
                            choice.extra_04 = yaml_field['choices'][ccode][options['c4']]
                    if 'c5' in options and options['c5']:
                        if options['c5'] in yaml_field['choices'][ccode]:
                            choice.extra_05 = yaml_field['choices'][ccode][options['c5']]
                    if 'b1' in options and options['b1']:
                        if options['b1'] in yaml_field['choices'][ccode]:
                            choice.extra_01_en = yaml_field['choices'][ccode][options['b1']]['en'] if 'en' in yaml_field['choices'][ccode][options['b1']] else ''
                            choice.extra_01_fr = yaml_field['choices'][ccode][options['b1']]['fr'] if 'fr' in yaml_field['choices'][ccode][options['b1']] else choice.extra_01_en
                    if 'b2' in options and options['b2']:
                        if options['b2'] in yaml_field['choices'][ccode]:
                            choice.extra_02_en = yaml_field['choices'][ccode][options['b2']]['en'] if 'en' in yaml_field['choices'][ccode][options['b2']] else ''
                            choice.extra_02_fr = yaml_field['choices'][ccode][options['b2']]['fr'] if 'fr' in yaml_field['choices'][ccode][options['b2']] else choice.extra_02_en
                    if 'b3' in options and options['b3']:
                        if options['b3'] in yaml_field['choices'][ccode]:
                            choice.extra_03_en = yaml_field['choices'][ccode][options['b3']]['en'] if 'en' in yaml_field['choices'][ccode][options['b3']] else ''
                            choice.extra_03_fr = yaml_field['choices'][ccode][options['b3']]['fr'] if 'fr' in yaml_field['choices'][ccode][options['b3']] else choice.extra_03_en
                    if 'b4' in options and options['b4']:
                        if options['b4'] in yaml_field['choices'][ccode]:
                            choice.extra_04_en = yaml_field['choices'][ccode][options['b4']]['en'] if 'en' in yaml_field['choices'][ccode][options['b4']] else ''
                            choice.extra_04_fr = yaml_field['choices'][ccode][options['b4']]['fr'] if 'fr' in yaml_field['choices'][ccode][options['b4']] else choice.extra_04_en
                    if 'b1' in options and options['b5']:
                        if options['b5'] in yaml_field['choices'][ccode]:
                            choice.extra_05_en = yaml_field['choices'][ccode][options['b5']]['en'] if 'en' in yaml_field['choices'][ccode][options['b5']] else ''
                            choice.extra_05_fr = yaml_field['choices'][ccode][options['b5']]['fr'] if 'fr' in yaml_field['choices'][ccode][options['b5']] else choice.extra_05_en

                    choice.save()

            if "choices_lookup" in yaml_field:
                for lucode in yaml_field['choices_lookup']:
                    choice, created = Code.objects.get_or_create(code_id=lucode, field_id=field, is_lookup=True)
                    choice.label_en = yaml_field['choices_lookup'][lucode]["en"]
                    choice.label_fr = yaml_field['choices_lookup'][lucode]["fr"]
                    choice.save()
            field.save()

    def add_org_fields(self, search):
        '''
        Create the default organization fields for a search
        :param search: Unique search identifier
        :return: None
        '''

        # Add the Organization fields
        field, created = Field.objects.get_or_create(field_id='owner_org', search_id=search)
        field.solr_field_type = 'string'
        field.solr_field_lang = 'bi'
        field.label_en = 'Organization Code'
        field.label_fr = "Code de l'organisation"
        field.solr_field_stored = True
        field.solr_field_indexed = True
        field.default_export_value = "str|-"
        field.solr_field_is_coded = True
        field.alt_format = 'ALL;'
        field.save()

    def add_format_field(selfself, search):
        field, created = Field.objects.get_or_create(field_id='format', search_id=search)
        field.solr_field_type = 'string'
        field.solr_field_lang = 'bi'
        field.label_en = 'Record Format'
        field.label_fr = "Format d'enregistrement"
        field.solr_field_stored = True
        field.solr_field_indexed = True
        field.default_export_value = "str|-"
        field.save()

    def handle(self, *args, **options):

        # Verify file exists, then load YAML
        yaml_path = Path(options['yaml_file'])
        if yaml_path.is_file():
            try:
                with open(options['yaml_file'], 'r', encoding='utf-8-sig', errors="ignore") as yaml_file:
                    schema = load(yaml_file, Loader=FullLoader)
                    search, created = Search.objects.get_or_create(search_id=options['search'])
                    search.label_en = options['title_en']
                    search.label_fr = options['title_fr']
                    # Set the ID according to the datastore_primary_key fields
                    search.id_fields = ",".join(schema['resources'][0]['datastore_primary_key']).strip(",")
                    search.save()

                    # Process regular PD data file fields
                    for yaml_field in schema['resources'][0]['fields']:
                        self.process_yaml_field(search, yaml_field, schema['resources'][0]['resource_name'], options, is_ntr=False)

                    # Process Nothing To report fields if present
                    if len(schema['resources']) > 1:
                        for yaml_field in schema['resources'][1]['fields']:
                            self.process_yaml_field(search, yaml_field, schema['resources'][1]['resource_name'], options, is_ntr=True)

                    # always add default organization fields
                    self.add_org_fields(search)

                    # Always add a format field.
                    self.add_format_field(search)

            except Exception as x:
                self.logger.error("Unexpected Error: {0}".format(x))
            self.logger.info("Imported file {0}".format(options['yaml_file']))
        else:
            self.logger.error("Cannot find file {0}".format(options['yaml_file']))
            exit(-1)
