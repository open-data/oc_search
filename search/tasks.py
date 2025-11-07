import datetime

from celery import shared_task
import csv
from datetime import datetime, timedelta
from django.conf import settings
import hashlib
import logging
import os
from .models import Event
from SolrClient2 import SolrClient, SolrResponse
from SolrClient2.exceptions import ConnectionError, SolrError
import time


def cache_search_results_file(cached_filename: str, sr: SolrResponse, rows=0, field_list={}, lang='en'):
    if len(sr.docs) == 0:
        return False
    if not os.path.exists(cached_filename):
        # Write out the header with the UTF8 byte-order marker for Excel first
      
        with open(f"{cached_filename}.tmp", 'w', newline='', encoding='utf8') as csv_file:
            cache_writer = csv.writer(csv_file, dialect='excel', quoting=csv.QUOTE_NONNUMERIC)
            #### the values from the dict docs[0] can be used to find the column headers
            ## in the field_list dict.
            label_header = []
            headers = list(sr.docs[0])
            for colname in headers:
                colname = colname.strip(" _,").lower()
                if colname.lower() == 'id':
                    label_header.append('ID')
                elif colname == "name" and lang == "fr":
                    label_header.append('Nom')                    
                elif colname == "year" and lang == "fr":
                    label_header.append('Année')
                elif colname in field_list:
                    if field_list[colname]:
                        label_header.append(field_list[colname])
                    else:
                        label_header.append(colname.capitalize())
                elif colname[-3:] in ('_fr', '_en'):
                    if colname[:-3] in field_list:
                        label_header.append(field_list[colname[:-3]])
                    else:
                        label_header.append(colname[:-3])
                elif colname[-4:] in ('_fra', '_eng'):
                    if colname[:-4] in field_list:
                        label_header.append(field_list[colname[:-3]])
                    elif colname[:-1] in field_list:
                        label_header.append(field_list[colname[:-1]])
                    else:
                        label_header.append(colname[:-4])                        
                else:
                    label_header.append(colname.replace('_', ' ').capitalize())
            #label_header[0] = u'\N{BOM}' + label_header[0]
            cache_writer.writerow(label_header)

        with open(f"{cached_filename}.tmp", 'r') as header_file:
            data = header_file.read()
        with open(cached_filename, 'w', newline='', encoding='utf8') as csv_file:
            csv_file.write(u'\N{BOM}' + data)  

        ######  @TODO  - Need to remove header_file immediately

        
        # Use a CSV writer with forced quoting for the body of the file
        with open(cached_filename, 'a', newline='', encoding='utf8') as csv_file:
            cache_writer = csv.writer(csv_file, dialect='excel', quoting=csv.QUOTE_ALL)
            c = 0
            for i in sr.docs:
                if rows != 0 and c > rows:
                    break
                try:
                    for j in i.keys():
                        if isinstance(i[j], list):
                            i[j] = ",".join(i[j])
                    cache_writer.writerow(i.values())
                    c += 1
                except UnicodeEncodeError:
                    pass
    return True

## OPEN-4055: Accept a list of Fields for the exported search results
@shared_task()
def export_search_results_csv(request_url, query, lang, core, fieldlist: dict):
    cache_dir = settings.EXPORT_FILE_CACHE_DIR
    hashed_query = hashlib.sha1(request_url.encode('utf8')).hexdigest()
    fileroot = core.replace("search_", "rechercher_") if  lang == "fr" else core
    cached_filename = os.path.join(cache_dir, f"{fileroot}_{hashed_query}_{lang}.csv")
    static_filename = f'{settings.EXPORT_FILE_CACHE_URL}/{fileroot}_{hashed_query}_{lang}.csv'

    # Check the cache. If the results already exist,then just return the filename, no need to query Solr
    if os.path.exists(cached_filename):
        # If the cached file is over 5 minutes old, just delete and continue.
        if time.time() - os.path.getmtime(cached_filename) > 600:
            os.remove(cached_filename)
        else:
            return f"{static_filename}"
    solr = SolrClient(settings.SOLR_SERVER_URL)
    solr_response = solr.query(core, query, request_handler='export')

    # Either create and cache the the search results or return the cached file
    if cache_search_results_file(cached_filename=cached_filename, sr=solr_response, field_list=fieldlist, lang=lang):
        return f"{static_filename}"
    else:
        return ""


@shared_task()
def save_search_logs_to_file():

    logger = logging.getLogger(__name__)

    one_week_ago = datetime.today() - timedelta(days=settings.SEARCH_LOGGING_ARCHIVE_AFTER_X_DAYS)
    logger.info(f'Archiving Search Event Log entries older than {one_week_ago.strftime("%A, %B %d, %Y")} to {settings.SEARCH_LOGGING_ARCHIVE_FILE}')

    # For new log files, write out the header
    if not os.path.exists('settings.SEARCH_LOGGING_ARCHIVE_FILE'):
        # Write out the header with the UTF8 byte-order marker for Excel first
        with open(settings.SEARCH_LOGGING_ARCHIVE_FILE, 'w', newline='', encoding='utf8') as csv_file:
            log_writer = csv.writer(csv_file, dialect='excel', quoting=csv.QUOTE_NONE)
            headers = ['id', 'search_id', 'component_id', 'title', 'event_timestamp', 'category', 'message']
            headers[0] = u'\N{BOM}' + headers[0]
            log_writer.writerow(headers)

    # Use a CSV writer with forced quoting for the body of the file
    with open(settings.SEARCH_LOGGING_ARCHIVE_FILE, 'a', newline='', encoding='utf8') as csv_file:
        log_writer = csv.writer(csv_file, dialect='excel', quoting=csv.QUOTE_ALL)
        older_logs = Event.objects.order_by('event_timestamp').filter(log_timestamp__lte=one_week_ago)
        for log in older_logs:
            log_entry = [log.id, log.search_id, log.component_id, log.title, log.event_timestamp, log.category, log.message]
            log_writer.writerow(log_entry)
            log.delete()
        logger.info(f'{older_logs.count()} log entries purged.')


@shared_task()
def purge_search_info_events():

    logger = logging.getLogger(__name__)

    one_hour_ago = datetime.today() - timedelta(hours=1)
    old_ckan_events = Event.objects.filter(event_timestamp__lte=one_hour_ago, component_id='data_import_ckan_json.remote', category='success')
    for event in old_ckan_events:
        event.delete()
