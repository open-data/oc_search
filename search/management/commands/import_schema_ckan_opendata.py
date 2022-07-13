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


def handle_choices(field, obj):
    if 'choices' in obj:
        for c in obj['choices']:
            choice, created = Code.objects.get_or_create(code_id=c['value'], field_id=field)
            if 'label' in c and isinstance(c['label'], dict):
                choice.label_en = c['label']['en']
                if 'fr' in c['label']:
                    choice.label_fr = c['label']['fr']
                else:
                    choice.label_fr = c['label']['en']
            elif 'label' in c and isinstance(c['label'], str):
                choice.label_en = c['label']
                choice.label_fr = c['label']
            else:
                choice.label_en = c['value']
                choice.label_fr = c['value']
            choice.save()


class Command(BaseCommand):

    help = 'Load Schema information from a CKAN schema and preset YAML files into the Search model. Special built for Canada Open Data for one time use'

    logger = logging.getLogger(__name__)

    presets = {}

    def add_arguments(self, parser):
        parser.add_argument('--schema_file', type=str, help='Filepath for the CKAN Open Data YAML file', required=True)
        parser.add_argument('--presets_file', type=str, help='Filepath for the CKAN Open Data presets YAML file', required=True)
        parser.add_argument('--info_file', type=str, help='Filepath for the CKAN Open Data YAML file', required=True)
        parser.add_argument('--search', type=str, help='A unique code identifier for the Search', required=True)

    def handle(self, *args, **options):

        # Verify file exists, then load YAML
        schema_path = Path(options['schema_file'])
        preset_path = Path(options['presets_file'])
        if schema_path.is_file() and preset_path.is_file():
            try:
                with open(options['schema_file'], 'r', encoding='utf-8-sig', errors="ignore") as schema_file:
                    with open(options['presets_file'], 'r', encoding='utf-8-sig', errors="ignore") as presets_file:
                        with open(options['info_file'], 'r', encoding='utf-8-sig', errors="ignore") as info_file:
                            schema = load(schema_file, Loader=FullLoader)
                            presets = load(presets_file, Loader=FullLoader)
                            info = load(info_file, Loader=FullLoader)

                            # Preload the presets

                            for pre in presets['presets']:
                                self.presets[pre['preset_name']] = pre

                            # Get the open data search object
                            search, created = Search.objects.get_or_create(search_id=options['search'])

                            # Create fields for each entry in the dataset.yaml file
                            schemas = [schema, info]
                            for s in schemas:
                                for field_class in ['dataset_fields', 'resource_fields']:
                                    for fld in s[field_class]:
                                        if 'field_name' in fld:
                                            print(f'Field {fld}')
                                            field = None
                                            if 'preset' in fld and fld['preset'] == 'fluent_text':
                                                field, created = Field.objects.get_or_create(field_id=fld['field_name'] + '_en',
                                                                                             search_id=search)
                                                field.label_en = fld['label']['en']
                                                if 'fr' in fld['label']:
                                                    field.label_fr = fld['label']['fr']
                                                else:
                                                    field.label_fr = fld['label']['en']
                                                field.format_name = options['search']
                                                field.solr_field_lang = 'en'
                                                field.solr_field_type = 'search_text_en'
                                                if field_class == 'resource_fields':
                                                    field.solr_field_multivalued = True
                                                field.save()

                                                field, created = Field.objects.get_or_create(field_id=fld['field_name'] + '_fr',
                                                                                             search_id=search)
                                                field.label_en = fld['label']['en']
                                                if 'fr' in fld['label']:
                                                    field.label_fr = fld['label']['fr']
                                                else:
                                                    field.label_fr = fld['label']['en']
                                                field.format_name = options['search']
                                                field.solr_field_lang = 'fr'
                                                field.solr_field_type = 'search_text_fr'
                                                if field_class == 'resource_fields':
                                                    field.solr_field_multivalued = True
                                                field.save()
                                            elif 'preset' in fld and fld['preset'] in ['resource_schema', 'validation_options', 'hidden_in_form']:
                                                continue
                                            else:
                                                field, created = Field.objects.get_or_create(field_id=fld['field_name'],
                                                                                             search_id=search)
                                                field.label_en = fld['label']['en']
                                                if 'fr' in fld['label']:
                                                    field.label_fr = fld['label']['fr']
                                                field.format_name = options['search']
                                                field.solr_field_lang = 'bi'
                                                field.solr_field_type = 'text_general'
                                                if field_class == 'resource_fields':
                                                    field.solr_field_multivalued = True
                                                field.save()
                                                handle_choices(field, fld)

                                        elif 'preset' in fld:
                                            pre = self.presets[fld['preset']]
                                            print(f'Preset {pre}')
                                            if 'validators' in pre['values'] and 'fluent_text' in pre['values']['validators']:
                                                for suffix in ['_en', '_fr']:
                                                    field, created = Field.objects.get_or_create(field_id=pre['values']['field_name'] + suffix, search_id=search)
                                                    if 'label' in pre['values']:
                                                        field.label_en = pre['values']['label']['en']
                                                        field.label_fr = pre['values']['label']['fr']
                                                    if field_class == 'resource_fields':
                                                        field.solr_field_multivalued = True
                                                    field.format_name = options['search']
                                                    field.save()
                                                    if 'choices' in pre['values']:
                                                        handle_choices(field, pre['values'])
                                            else:
                                                field, created = Field.objects.get_or_create(
                                                    field_id=pre['values']['field_name'], search_id=search)
                                                if 'label' in pre['values']:
                                                    field.label_en = pre['values']['label']['en']
                                                    field.label_fr = pre['values']['label']['fr']
                                                if field_class == 'resource_fields':
                                                    field.solr_field_multivalued = True
                                                field.format_name = options['search']
                                                field.save()
                                                if 'choices' in pre['values']:
                                                    handle_choices(field, pre['values'])

            except Exception as x:
                self.logger.error("Unexpected Error: {0}".format(x))

