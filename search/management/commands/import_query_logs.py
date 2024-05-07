import csv
from datetime import datetime
from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from django.utils import timezone as utimezone
import os.path
from search.models import SearchLog


class Command(BaseCommand):
    help = 'Import search query logs to the database'

    def add_arguments(self, parser):
        parser.add_argument('--csv', type=str, required=True, help='CSV file with search query logs')

    def handle(self, *args, **options):
        if not os.path.exists(options['csv']):
            raise CommandError(f"CSV file: Cannot find {options['csv']}")
        with open(options['csv'], 'r', encoding='utf-8-sig', errors="xmlcharrefreplace") as csv_file:
            fieldnames = ('timestamp', 'hostname', 'search_type', 'page_type',
                          'search_format', 'session_id', 'page_no', 'sort_order',
                          'search_text', 'facets', 'results_no')
            csv_reader = csv.DictReader(csv_file, fieldnames=fieldnames, dialect='excel')
            for row in csv_reader:
                try:
                    sll = SearchLog.objects.create(**row)
                    sll.save()

                except ValueError as ve:
                    print(f"Invalid value {ve}")
