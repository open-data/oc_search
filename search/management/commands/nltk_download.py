from django.core.management.base import BaseCommand
from django.conf import settings
import logging
import nltk


class Command(BaseCommand):
    help = 'Download the NLTK Stopwords and punkt tokenizer to a project folder'

    logger = logging.getLogger(__name__)

    def handle(self, *args, **options):

        try:
            nltk.download('stopwords',download_dir=settings.NLTK_DATADIR)
            nltk.download('punkt', download_dir=settings.NLTK_DATADIR)
        except Exception as x:
            self.logger.error(x)
