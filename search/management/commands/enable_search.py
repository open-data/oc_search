from search.models import Search
from django.core.management.base import BaseCommand
import logging


class Command(BaseCommand):
    help = 'Set a custom search to the Enabled state'

    logger = logging.getLogger(__name__)

    def add_arguments(self, parser):
        parser.add_argument('--search', type=str, help='A unique code identifier for the Search', required=True)

    def handle(self, *args, **options):

        try:
            the_search = Search.objects.get(search_id=options['search'])
            the_search.is_disabled = False
            the_search.save()
            self.logger.info(f'Search "{the_search.label_en}" enabled')
        except Search.DoesNotExist:
            self.logger.warning(f'No Search {options["search"]} found')
            exit(1)
