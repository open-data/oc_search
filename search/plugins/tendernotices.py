from django.http import HttpRequest
from search.models import Search, Field, Code
from SolrClient import SolrResponse


def pre_solr_query(context: dict, solr_query: dict, request: HttpRequest, search: Search, fields: dict, codes: dict, facets: list, record_ids: str):
    if request.LANGUAGE_CODE == 'fr':
        if 'fq' in solr_query:
            solr_query['fq'].append('{!tag=tag_language}language:("Français")')
    else:
        if 'fq' in solr_query:
            solr_query['fq'].append('{!tag=tag_language}language:("English")')
    return context, solr_query


def post_solr_query(context: dict, solr_response: SolrResponse, request: HttpRequest, search: Search, fields: dict, codes: dict, facets: list, record_ids: str):
    return context, solr_response


def load_csv_record(csv_record: dict, solr_record: dict, search: Search, fields: dict, codes: dict, format: str):
    return solr_record
