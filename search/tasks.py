import datetime

from celery import shared_task
import csv
from datetime import datetime, timedelta
from django.conf import settings
import hashlib
import logging
import os
from .models import SearchLog
from SolrClient import SolrClient, SolrResponse
from SolrClient.exceptions import ConnectionError, SolrError
import time


def cache_search_results_file(cached_filename: str, sr: SolrResponse, rows=100000):
    if len(sr.docs) == 0:
        return False
    if not os.path.exists(cached_filename):
        # Write out the header with the UTF8 byte-order marker for Excel first
        with open(cached_filename, 'w', newline='', encoding='utf8') as csv_file:
            cache_writer = csv.writer(csv_file, dialect='excel', quoting=csv.QUOTE_NONE)
            headers = list(sr.docs[0])
            headers[0] = u'\N{BOM}' + headers[0]
            cache_writer.writerow(headers)

        # Use a CSV writer with forced quoting for the body of the file
        with open(cached_filename, 'a', newline='', encoding='utf8') as csv_file:
            cache_writer = csv.writer(csv_file, dialect='excel', quoting=csv.QUOTE_ALL)
            c = 0
            for i in sr.docs:
                if c > rows:
                    break
                try:
                    cache_writer.writerow(i.values())
                    c += 1
                except UnicodeEncodeError:
                    pass
    return True

@shared_task()
def export_search_results_csv(request_url, query, lang, core):
    cache_dir = settings.EXPORT_FILE_CACHE_DIR
    hashed_query = hashlib.sha1(request_url.encode('utf8')).hexdigest()
    cached_filename = os.path.join(cache_dir, f"{core}_{hashed_query}_{lang}.csv")
    static_filename = f'{settings.EXPORT_FILE_CACHE_URL}/{core}_{hashed_query}_{lang}.csv'

    # Check the cache. If the results already exist,then just return the filename, no need to query Solr
    if os.path.exists(cached_filename):
        # If the cached file is over 5 minutes old, just delete and continue.
        if time.time() - os.path.getmtime(cached_filename) > 600:
            os.remove(cached_filename)
        else:
            return f"{static_filename}"
    solr = SolrClient(settings.SOLR_SERVER_URL)
    solr_response = solr.query(core, query, request_handler='export')

    if cache_search_results_file(cached_filename=cached_filename, sr=solr_response):
        return f"{static_filename}"
    else:
        return ""


@shared_task()
def save_search_logs_to_file():

    logger = logging.getLogger(__name__)

    one_week_ago = datetime.today() - timedelta(days=settings.SEARCH_LOGGING_ARCHIVE_AFTER_X_DAYS)
    logger.info(f'Archiving Search Log entries older than {one_week_ago.strftime("%A, %B %d, %Y")} to {settings.SEARCH_LOGGING_ARCHIVE_FILE}')

    # For new log files, write out the header
    if not os.path.exists('settings.SEARCH_LOGGING_ARCHIVE_FILE'):
        # Write out the header with the UTF8 byte-order marker for Excel first
        with open(settings.SEARCH_LOGGING_ARCHIVE_FILE, 'w', newline='', encoding='utf8') as csv_file:
            log_writer = csv.writer(csv_file, dialect='excel', quoting=csv.QUOTE_NONE)
            headers = ['id', 'search_id', 'log_id', 'log_timestamp', 'message', 'category']
            headers[0] = u'\N{BOM}' + headers[0]
            log_writer.writerow(headers)

    # Use a CSV writer with forced quoting for the body of the file
    with open(settings.SEARCH_LOGGING_ARCHIVE_FILE, 'a', newline='', encoding='utf8') as csv_file:
        log_writer = csv.writer(csv_file, dialect='excel', quoting=csv.QUOTE_ALL)
        older_logs = SearchLog.objects.order_by('log_timestamp').filter(log_timestamp__lte=one_week_ago)
        for log in older_logs:
            log_entry = [log.id, log.search_id, log.log_id, log.log_timestamp, log.message, log.category]
            log_writer.writerow(log_entry)
            log.delete()
        logger.info(f'{older_logs.count()} log entries purged.')
