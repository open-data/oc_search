from django.http import HttpRequest
from search.models import Search, Field, Code
from SolrClient import SolrResponse


def pre_solr_query(context: dict, solr_query: dict, request: HttpRequest, search: Search, fields: dict, codes: dict, facets: list):
    return context, solr_query


def post_solr_query(context: dict, solr_response: SolrResponse, request: HttpRequest, search: Search, fields: dict, codes: dict, facets: list):
    return context, solr_response


def load_csv_record(csv_record: dict, solr_record: dict, search: Search, fields: dict, codes: dict):
    return solr_record
