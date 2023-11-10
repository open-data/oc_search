import sys
from django.core.management.base import BaseCommand
from django.conf import settings
from search.models import Search, Field, Code
from SolrClient import SolrClient
from SolrClient.exceptions import ConnectionError
import csv
import logging
import time


class Command(BaseCommand):
    help = 'Django manage command that will directly index CSV data to a Solr search core.'

    logger = logging.getLogger(__name__)
    # class variables that hold the search models
    search_target = None
    solr_core = None
    indexed_count = 0

    def add_arguments(self, parser):
        parser.add_argument('--search', type=str, help='The Search ID that is being loaded', required=True)
        parser.add_argument('--csv', type=str, help='CSV filename to import', required=True)
        parser.add_argument('--purge', required=False, action='store_true', default=False,
                            help='Purge all records before loading data to the Solr core')

    def handle(self, *args, **options):

        try:
            # Retrieve the Search  and Field models from the database
            solr = SolrClient(settings.SOLR_SERVER_URL)
            self.search_target = Search.objects.get(search_id=options['search'])
            self.solr_core = self.search_target.solr_core_name

            if options['purge']:
                solr.delete_doc_by_query(self.solr_core, "*:*")
                self.logger.info("Purging all records")

            with open(options['csv'], 'r', encoding='utf-8-sig', errors="xmlcharrefreplace") as csv_file:
                csv_reader = csv.DictReader(csv_file, dialect='excel')
                for row_num, solr_record in enumerate(csv_reader):
                    solr_items = [solr_record]
                    try:
                        solr.index(self.solr_core, solr_items)
                        self.indexed_count += 1
                    except ConnectionError as cex:
                        self.logger.warning(
                            f"Unexpected error encountered while indexing starting on row {row_num + 1}. Row data has {len(solr_items)} items")
                        for sitm in solr_items:
                            self.logger.warning(f"{sitm}")
                        # Force a delay to give the network/system time to recover - hopefully
                        time.sleep(1)
                    except Exception as ex:
                        for sitm in solr_items:
                            self.logger.warning(f"{sitm}")
            # If there were changes, then commit them
            if self.indexed_count > 0:
                solr.commit(self.solr_core, softCommit=True)
            self.logger.info(f"\nTotal rows processed: {self.indexed_count}")

        except Exception as x:
            self.logger.error('Unexpected Error "{0}"'.format(x.args))
        finally:
            sys.stdout.write("Indexing completed")
