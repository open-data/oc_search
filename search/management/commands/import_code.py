from search.models import Field, Code
from django.core.management.base import BaseCommand, CommandError
import json
import logging
from os import path


class Command(BaseCommand):
    help = 'Import code values for a single existing field from a JSON file.'

    logger = logging.getLogger(__name__)

    def add_arguments(self, parser):
        parser.add_argument('--code_file', type=str, help='JSON file that contains the code values', required=True)
        parser.add_argument('--search', type=str, help='Search Name', required=True)
        parser.add_argument('--field', type=str, help='Full Field DB Name (fid)', required=True)

    def handle(self, *args, **options):

        if not path.exists(options['code_file']):
            raise CommandError('JSON data file not found: ' + options['code_file'])

        # Import Codes -
        if path.exists(options['code_file']) and path.getsize(options['code_file']) > 0:
            with open(options['code_file'], 'r', encoding='utf-8-sig', errors="ignore") as json_file:
                imported_data = json.load(json_file)
                for code_defn in imported_data:
                    try:
                        new_field = Field.objects.get(fid=code_defn["field_fid"])
                        new_code, created = Code.objects.get_or_create(cid=code_defn['cid'], field_fid=new_field)
                        new_code.from_dict(code_defn, new_field)
                        new_code.save()
                        if created:
                            logging.info(f"Imported new Code {new_code.code_id} for Field {new_field.fid}")
                        else:
                            logging.info(f"Updated Code model {new_code.code_id} for Field {new_field.fid}")
                    except KeyError as ke:
                        raise CommandError(f"Unable to create Code record. Missing field {ke}")
                code_count = len(imported_data)
        else:
            logging.info("Skipping missing or empty Codes import data file")

