import csv
from datetime import datetime

from Tools.scripts.dutree import store
from dateutil import tz
from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from django.utils import timezone as utimezone
import os.path
from search.models import Search, Field, Code, SearchLog, SearchLogFilters
from urllib import parse


class Command(BaseCommand):
    help = 'Process the query logs and extract valid filters'

    searches = {}
    fields = {}
    has_codes = {}
    codes = {}

    def __init__(self):
        super().__init__()

        search_queryset = Search.objects.all()
        for s in search_queryset:
            self.searches[s.search_id] = s

        for sid in self.searches.keys():
            sfields = []
            code_flags = {}
            field_queryset = Field.objects.filter(search_id_id=sid)
            for f in field_queryset:
                sfields.append(f.field_id)
                code_flags[f.field_id] = f.solr_field_is_coded
            self.fields[sid] = sfields
            self.has_codes[sid] = code_flags

        for sid in self.searches.keys():
            scodes = {}
            codes_queryset = Code.objects.filter(field_fid__search_id__search_id=sid)
            for code in codes_queryset:
                code_entry = [code.label_en[0:220], code.label_fr[0:220]]
                scodes[code.code_id.lower()] = code_entry
            self.codes[sid] = scodes


    def add_arguments(self, parser):
        parser.add_argument('--from', type=str, required=True, help='Date From "YYYY-MM-DD"')
        parser.add_argument('--to', type=str, required=True, help='Date To "YYYY-MM-DD"')
        parser.add_argument('--verbose', action='store_true', help='Display warnings')


    def handle(self, *args, **options):

        # Validate the options
        from_date = datetime.now()
        to_date = datetime.now()
        try:
            from_date = datetime.strptime(options['from'], "%Y-%m-%d")
            to_date = datetime.strptime(options['to'], "%Y-%m-%d")
            from_date = from_date.replace(tzinfo=tz.tzutc())
            to_date = to_date.replace(tzinfo=tz.tzutc())
        except ValueError as e:
            raise CommandError(e)

        log_entries = SearchLog.objects.filter(timestamp__gte=from_date, timestamp__lte=to_date)
        print(f"Found {log_entries.count()} log entries")

        bad_entry_count = 0
        unknown_entry_count = 0
        good_entry_count = 0

        for log_entry in log_entries:
            if log_entry.facets:
                # Validate that the facet log entry is actually a comma-seperated list of facets
                facet_fields = log_entry.facets.strip(",").split(',')
                for f in facet_fields:
                    # Validate the facet entry is a "Key:Value" pair
                    if isinstance(f, str) and ":" in f:
                        field_value = f.split(':')
                        if len(field_value) != 2:
                            bad_entry_count += 1
                        else:
                            # Validate if it is referencing a valid field or the WET wbdiable par
                            if log_entry.search_type not in self.fields or field_value[0] not in self.fields[log_entry.search_type] or field_value[0] == "wbdisable":
                                if options["verbose"]:
                                    print(f"Unknown field {field_value[0]} in {log_entry.search_type} log (ID: {log_entry.timestamp})")
                                unknown_entry_count += 1
                            else:
                                # Validate if the value is valid if the field has codes
                                if field_value[1]:
                                    if field_value[0] in self.has_codes[log_entry.search_type]:
                                        if not self.has_codes[log_entry.search_type][field_value[0]]:
                                            break

                                    fdequote = parse.unquote_plus(field_value[1]).lower().replace("+", " ")
                                    fdes = fdequote.split('|')
                                    for fde in fdes:
                                        if fde in self.codes[log_entry.search_type]:
                                            good_entry_count += 1
                                            try:
                                                # If it exists, no need to overwrite it
                                                slf = SearchLogFilters.objects.get(searchlog_id=log_entry.id,
                                                                                   search_type=log_entry.search_type,
                                                                                   facet=field_value[0])
                                            except SearchLogFilters.DoesNotExist:
                                                slf = SearchLogFilters.objects.create(searchlog_id=log_entry,
                                                                                      search_type=log_entry.search_type,
                                                                                      facet=field_value[0],
                                                                                      facet_en=self.codes[log_entry.search_type][fde][0],
                                                                                      facet_fr=self.codes[log_entry.search_type][fde][1],
                                                                                      value=fde)
                                                slf.save()
                                        else:
                                            if options["verbose"]:
                                                print(f"Unknown facet value {fde} for facet {field_value[0]} in {log_entry.search_type} log (ID: {log_entry.timestamp})")
                                            unknown_entry_count += 1
                                else:
                                    bad_entry_count += 1
                    else:
                        bad_entry_count += 1


        print(f"Found {good_entry_count} good, {bad_entry_count} bad, and {unknown_entry_count} unknown facets")


