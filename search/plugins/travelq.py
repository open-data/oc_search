from babel.numbers import format_currency, format_decimal, parse_decimal, NumberFormatError
from django.http import HttpRequest
from search.models import Search, Field, Code
from SolrClient import SolrResponse


def pre_solr_query(context: dict, solr_query: dict, request: HttpRequest, search: Search, fields: dict, codes: dict, facets: list, record_ids: str):
    return context, solr_query


def post_solr_query(context: dict, solr_response: SolrResponse, request: HttpRequest, search: Search, fields: dict, codes: dict, facets: list, record_ids: str):
    return context, solr_response


def load_csv_record(csv_record: dict, solr_record: dict, search: Search, fields: dict, codes: dict, format: str):
    # The Travel search uses a highly customized search range for total dollar values. Populate the English and
    # French total range with the appropriate values.
    # NOTE: the fields total_range_fr and total_range_en have to be manually added to the schema

    try:
        if 'total' in solr_record and solr_record['total'] and format != 'NTR':
            total_decimal = parse_decimal(solr_record['total'], locale='en_US')
            if - 0 < total_decimal < 250:
                solr_record['total_range'] = 'r6'
            elif 250 <= total_decimal < 500:
                solr_record['total_range_'] = 'r5'
            elif 500 <= total_decimal < 1000:
                solr_record['total_range'] = 'r4'
            elif 1000 <= total_decimal < 5000:
                solr_record['total_range'] = 'r3'
            elif 5000 <= total_decimal < 25000:
                solr_record['total_range'] = 'r2'
            elif 25000 < total_decimal:
                solr_record['total_range'] = 'r1'
            else:
                solr_record['total_range'] = 'r7'
        else:
            solr_record['total_range'] = 'r7'


    except NumberFormatError as nfe:
        print(nfe)

    return solr_record
