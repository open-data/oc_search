
from search.models import  Field, Code
from django.core.management.base import BaseCommand, CommandError
import logging


class Command(BaseCommand):
    help = 'Export the code values for a single field to a JSON file'

    logger = logging.getLogger(__name__)

    def add_arguments(self, parser):
        parser.add_argument('--code_file', type=str, help='Directory to write export files to', required=True)
        parser.add_argument('--search', type=str, help='Search ID Name', required=True)
        parser.add_argument('--field', type=str, help='Field ID Name (field_id)', required=True)

    def handle(self, *args, **options):

        # Export Codes for the Field
        code_field = Field.objects.filter(search_id__search_id=options['search']).get(field_id=options['field'])
        codes = Code.objects.filter(field_fid__fid=code_field.fid)
        if codes.count() > 0:
            code_path = options['code_file']
            codes_as_json = [c.to_json() for c in codes]

            if len(codes_as_json) > 0:
                with open(code_path, 'w', encoding='utf-8', errors="ignore") as search_file:
                    cs = f'[{",".join(codes_as_json)}]'
                    search_file.write(cs)
                logging.info(f'{len(codes_as_json)} Codes exported to {code_path}')
            else:
                logging.info("No Codes exported")
        else:
            logging.info(f"No codes found for {options['field']}")

