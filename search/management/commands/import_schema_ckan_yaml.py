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
        parser.add_argument('--search_id', type=str, help='A unique code identifier for the Search', required=True)
        parser.add_argument('--title_en', type=str, help='An English title to use for the search', required=True)
        parser.add_argument('--title_fr', type=str, help='A French title to use for the search', required=True)
        parser.add_argument('--reset', action='store_true', required=False, default=False,
                            help='Flag to overwrite previous Search settings that were loaded. '
                                 'By default the search is  updated, not overwritten')

    def process_yaml_field(self, search, yaml_field, reset=False, is_ntr=False):
        '''
        Process a field record from the YAML file
        :param search: Unique search identifier
        :param yaml_field: The YAML object for the field
        :param reset:  Update or overwrite
        :param is_ntr: Inidcator if this is a field for Nothing To Report record
        :return: None
        '''

        # Do not bother processing CKAN internal fields, othewise retrieve or create the Field model
        if not yaml_field['datastore_id'] in ('record_created', 'record_modified', 'user_modified'):
            field, created = Field.objects.get_or_create(field_id=yaml_field['datastore_id'],
                                                         search_id=search)
            field.search_id = search
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
                    choice.label_en = yaml_field['choices'][ccode]["en"]
                    choice.label_fr = yaml_field['choices'][ccode]["fr"]
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
        field.save()

        field, created = Field.objects.get_or_create(field_id='owner_org_en', search_id=search)
        field.solr_field_type = 'string'
        field.solr_field_lang = 'en'
        field.label_en = 'Organization'
        field.label_fr = "Organisation"
        field.solr_field_stored = True
        field.solr_field_indexed = True
        field.default_export_value = "str|-"
        field.save()

        field, created = Field.objects.get_or_create(field_id='owner_org_fr', search_id=search)
        field.solr_field_type = 'string'
        field.solr_field_lang = 'fr'
        field.label_en = 'Organization'
        field.label_fr = "Organisation"
        field.solr_field_stored = True
        field.solr_field_indexed = True
        field.default_export_value = "str|-"
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
                    search, created = Search.objects.get_or_create(search_id=options['search_id'])
                    search.label_en = options['title_en']
                    search.label_fr = options['title_fr']
                    # Set the ID according to the datastore_primary_key fields
                    search.id_fields = ",".join(schema['resources'][0]['datastore_primary_key']).strip(",")
                    search.save()

                    # Process regular PD data file fields
                    for yaml_field in schema['resources'][0]['fields']:
                        self.process_yaml_field(search, yaml_field, options['reset'], is_ntr=False)

                    # Process Nothing To report fields if present
                    if len(schema['resources']) > 1:
                        for yaml_field in schema['resources'][1]['fields']:
                            self.process_yaml_field(search, yaml_field, options['reset'], is_ntr=True)

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
