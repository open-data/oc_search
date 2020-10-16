from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from search.models import Search, Field, Code
import logging


class Command(BaseCommand):
    help = 'Delete a search from the database'

    logger = logging.getLogger(__name__)

    def add_arguments(self, parser):
        parser.add_argument('--search_id', type=str, help='Unique code identifier for the search', required=True)

    def handle(self, *args, **options):

        try:
            search = Search.objects.get(search_id=options['search_id'])
            search.delete()
        except Exception as x:
            self.logger.error(x)
