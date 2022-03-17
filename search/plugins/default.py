from django.http import HttpRequest
from search.models import Search, Field, Code
from SolrClient import SolrResponse


def plugin_api_version():
    return 1.1


def pre_search_solr_query(context: dict, solr_query: dict, request: HttpRequest, search: Search, fields: dict, codes: dict, facets: list, record_ids: str):
    return context, solr_query


def post_search_solr_query(context: dict, solr_response: SolrResponse, solr_query: dict, request: HttpRequest, search: Search, fields: dict, codes: dict, facets: list, record_ids: str):
    return context, solr_response


def pre_record_solr_query(context: dict, solr_query: dict, request: HttpRequest, search: Search, fields: dict, codes: dict, facets: list, record_ids: str):
    return context, solr_query


def post_record_solr_query(context: dict, solr_response: SolrResponse, solr_query: dict, request: HttpRequest, search: Search, fields: dict, codes: dict, facets: list, record_ids: str):
    return context, solr_response


def pre_export_solr_query(solr_query: dict, request: HttpRequest, search: Search, fields: dict, codes: dict, facets: list):
    return solr_query


def post_export_solr_query(solr_response: SolrResponse, solr_query: dict, request: HttpRequest, search: Search, fields: dict, codes: dict, facets: list):
    return solr_response


def pre_mlt_solr_query(context: dict, solr_query: dict, request: HttpRequest, search: Search, fields: dict, codes: dict, record_is: str):
    return context, solr_query


def post_mlt_solr_query(context: dict, solr_response: SolrResponse, solr_query: dict, request: HttpRequest, search: Search, fields: dict, codes: dict, record_ids: str):
    return context, solr_response


def filter_csv_record(csv_record,search: Search, fields: dict, codes: dict, format: str):
    return True,  csv_record


def load_csv_record(csv_record: dict, solr_record: dict, search: Search, fields: dict, codes: dict, format: str):
    return solr_record

# Version 1.1 Methods

def pre_render_search(context: dict, template: str, request: HttpRequest, lang: str, search: Search, fields: dict, codes: dict):
    """
    If required, make changes to the context before rendering the search page or modify the template name
    :param context: the Django view context to be used
    :param template: the default name of the  template to be rendered
    :param request: the HTTP request object
    :param lang: the language of the page being rendered
    :param search: the application search object
    :param fields: the application field objects
    :param codes: the application code objects to be used
    :return: context object, and the template name
    """
    return context, template

def pre_render_record(context: dict, template: str, request: HttpRequest, lang: str, search: Search, fields: dict, codes: dict):
    """
    If required, make changes to the context before rendering the record page or modify the template name
    :param context: the Django view context to be used
    :param template: the default name of the  template to be rendered
    :param request: the HTTP request object
    :param lang: the language of the page being rendered
    :param search: the application search object
    :param fields: the application field objects
    :param codes: the application code objects to be used
    :return: context object, and the template name
    """
    return context, template
