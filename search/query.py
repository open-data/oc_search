import bleach
from django.http import HttpRequest
from math import ceil
from nltk.tokenize.regexp import RegexpTokenizer
import os
import re
from search.models import Search, Field
from urllib import parse


def url_part_escape(orig):
    """
    simple encoding for url-parts where all non-alphanumerics are
    wrapped in e.g. _xxyyzz_ blocks w/hex UTF-8 xx, yy, zz values
    used for safely including arbitrary unicode as part of a url path
    all returned characters will be in [a-zA-Z0-9_-]
    """
    return '_'.join(
        s.hex() if i % 2 else s.decode('ascii')
        for i, s in enumerate(
            re.split(b'([^-a-zA-Z0-9]+)', orig.encode('utf-8'))
        )
    )


def url_part_unescape(urlpart):
    """
    reverse url_part_escape
    """
    return ''.join(
        bytes.fromhex(s).decode('utf-8') if i % 2 else s
        for i, s in enumerate(urlpart.split('_'))
    )


# Credit to https://gist.github.com/kgriffs/c20084db6686fee2b363fdc1a8998792 for this function
def uuid_pattern(version):
    return re.compile(
        (
            '[a-f0-9]{8}-' +
            '[a-f0-9]{4}-' +
            version + '[a-f0-9]{3}-' +
            '[89ab][a-f0-9]{3}-' +
            '[a-f0-9]{12}$'
        ),
        re.IGNORECASE
    )


def calc_pagination_range(num_found: int, pagesize, current_page, delta=2):
    # @TODO This is not very efficient - could be refactored
    pages = int(ceil(num_found / pagesize))
    if current_page > pages:
        current_page = pages
    elif current_page < 1:
        current_page = 1
    left = current_page - delta
    right = current_page + delta + 1
    pagination = []
    spaced_pagination = []

    for p in range(1, pages + 1):
        if (p == 1) or (p == pages) or (left <= p < right):
            pagination.append(p)

    last = None
    for p in pagination:
        if last:
            if p - last == 2:
                spaced_pagination.append(last + 1)
            elif p - last != 1:
                spaced_pagination.append(0)
        spaced_pagination.append(p)
        last = p

    return spaced_pagination


def calc_starting_row(page_num, rows_per_page=10):
    """
    Calculate a starting row for the Solr search results. We only retrieve one page at a time
    :param page_num: Current page number
    :param rows_per_page: number of rows per page
    :return: starting row
    """
    page = 1
    try:
        page = int(page_num)
    except ValueError:
        pass
    if page < 1:
        page = 1
    elif page > 100000:  # @magic_number: arbitrary upper range
        page = 100000
    return rows_per_page * (page - 1), page


def get_search_terms(search_text: str):
    # Get any search terms

    tr = RegexpTokenizer('[^"\s]\S*|".+?"', gaps=False)

    # Respect quoted strings
    search_terms = tr.tokenize(search_text)
    if len(search_terms) == 0:
        solr_search_terms = "*"
    else:
        solr_search_terms = ' '.join(search_terms)
    return solr_search_terms


def get_query_fields(query_lang: str, fields: dict):
    qf = ['id']
    for f in fields:
        if fields[f].solr_field_lang in [query_lang, 'bi']:
            qf.append(f)
            if fields[f].solr_extra_fields:
                if fields[f].solr_field_lang == query_lang:
                    qf.extend(fields[f].solr_extra_fields.split(","))
                else:
                    copy_fields = fields[f].solr_extra_fields.split(",")
                    for copy_field in copy_fields:
                        if copy_field.endswith("_" + query_lang):
                            qf.append(copy_field)
            if fields[f].solr_field_is_coded:
                code_value_field = "{0}_{1}".format(f, query_lang)
                if code_value_field not in qf:
                    qf.append(code_value_field)
    return qf


def get_mlt_fields(request: HttpRequest, fields: dict):
    qf = ['id']
    for f in fields:
        if fields[f].solr_field_lang in [request.LANGUAGE_CODE, 'bi']:
            if fields[f].solr_field_type in ['search_text_en', 'search_text_en', 'string']:
                qf.append(f)
    return qf


def create_solr_query(request: HttpRequest, search: Search, fields: dict, Codes: dict, facets: list, start_row: int,
                      rows: int, record_id: str, export=False, highlighting=False, default_sort='score desc',
                      override_sort=False):
    """
    Create a complete query to send to the SolrClient query.
    :param request: The HttpRequest for the page
    :param search: The Search Model
    :param fields: A dictionary or Field model objects
    :param Codes: A dictionary of Code model objects
    :param facets: A list of the facets used in the query
    :param start_row: An integer of the starting row for results to return
    :param rows: An integer of the number of reows to return
    :param record_id: If used, is a list of record ID. Used to retrieve specific records from Solr
    :param export: Set to true if constructing the query for a /export Solr handler query
    :param highlighting: set to true if the query should include search term highlighting
    :return: A dictionary representing a Solr query for use with the SolrClient library
    """
    using_facets = len(facets) > 0

    # Look for known fields in the GET request
    known_fields = {}
    solr_query = {'q': '*', 'defType': 'edismax', 'sow': True}

    # Most search pages in the app use HTTP GET method, but the data export uses POST method with CSTF protection.
    # This impacts how user data is retrieved.

    # The request is for a specific record - other fields should not be present
    if record_id:
        solr_query['q'] = 'id:"{0}"'.format(record_id)

    # Pre-process the search request URL
    else:
        if len(request.GET) > 0:
            for request_field in request.GET.keys():
                if request_field == 'search_text' and not record_id:
                    solr_query['q'] = get_search_terms(request.GET.get('search_text'))
                    if request.LANGUAGE_CODE == 'fr':
                        solr_query['q'] = solr_query['q'].replace(' OU ', ' OR ').replace(" ET ", " AND ").replace(' PAS ', ' NOT ').replace("(PAS ", "(NOT ")
                        if solr_query['q'].startswith('PAS '):
                            solr_query['q'] = "NOT " + solr_query['q'][4:]
                elif request_field == 'sort' and not record_id:
                    if request.LANGUAGE_CODE == 'fr':
                        solr_query['sort'] = request.GET.get('sort') if request.GET.get('sort') in search.results_sort_order_fr.split(',') else default_sort
                    else:
                        solr_query['sort'] = request.GET.get('sort') if request.GET.get('sort') in search.results_sort_order_en.split(',') else default_sort
                elif request_field in fields:
                    known_fields[request_field] = request.GET.get(request_field).split('|')
                elif request_field in ["page", "wbdisable", "_ga"]:
                    pass
                else:
                    if request.GET.get(request_field):
                        solr_query = {"error": bleach.clean(f"{request_field}={request.GET.get(request_field)}")}
                    else:
                        solr_query = {"error": bleach.clean(f"{request_field}")}
                    solr_query['error_search_path'] = request.path
                    return solr_query

        elif request.POST.get("export_query"):

            # Currently only the data export uses a POST form, so export fields are hard-coded here, and default sort order is used

            qurl = parse.urlsplit(request.POST.get('export_search_path'))
            keys = parse.parse_qs(qurl.query)
            for request_field in keys:
                if request_field == 'search_text' and not record_id:
                    solr_query['q'] = get_search_terms(keys[request_field][0])
                elif request_field == 'sort' and not record_id:
                    solr_query['sort'] = default_sort
                elif request_field in fields:
                    known_fields[request_field] = keys[request_field][0].split('|')

        # If sort not specified in the request, then use the default
        if 'sort' not in solr_query:
            solr_query['sort'] = default_sort

        # Sometimes, the sort order will be forced to the default value
        if override_sort:
            solr_query['sort'] = default_sort

        solr_query['q.op'] = search.solr_default_op

    # Create a Solr query field list based on the Fields Model. Expand the field list where needed
    solr_query['qf'] = get_query_fields(request.LANGUAGE_CODE, fields)

    if export:
        ef = ['id']
        for f in fields:
            if fields[f].solr_field_lang in [request.LANGUAGE_CODE, 'bi']:
                if fields[f].solr_field_type in ['string', 'pint', 'pfloat', 'pdate']:
                    if not fields[f].solr_field_is_coded and f != "unique_identifier":
                        ef.append(f)
                    if fields[f].solr_field_is_coded and f[-2:] not in ['_en', '_fr'] and f not in ['month', 'year']:
                        ef.append("{0}_{1}".format(f, request.LANGUAGE_CODE))
                elif fields[f].solr_field_type in ["search_text_en", "search_text_fr", 'text_general', 'text_keyword']:
                    if fields[f].solr_field_export:
                        for extra_field in fields[f].solr_field_export.split(","):
                            ef.append(extra_field.strip())
        solr_query['fl'] = ",".join(ef)
    else:
        solr_query['fl'] = ",".join(solr_query['qf'])
    if not export:
        solr_query['start'] = start_row
        solr_query['rows'] = rows
    if not export and highlighting:
        hl_fields = []
        hl_field_types = ["search_text_en", "string", 'text_general']
        if request.LANGUAGE_CODE == 'fr':
            hl_field_types = ["search_text_fr", "string", 'text_general']
        for field in fields:
            if fields[field].solr_field_type in hl_field_types:
                hl_fields.append(field)
                if fields[field].solr_extra_fields:
                    for extra_field in fields[field].solr_extra_fields.split(","):
                        if extra_field.endswith("_en") or extra_field.endswith("_fr"):
                            hl_fields.append(extra_field.strip())
        solr_query.update({
            'hl': 'on',
            'hl.method': 'unified',
            'hl.simple.pre': '<mark>',
            'hl.simple.post': '</mark>',
            'hl.snippets': 10,
            'hl.fl': hl_fields,
            'hl.highlightMultiTerm': True,
        })

    # Set a default sort order
    if 'sort' not in solr_query:
        solr_query['sort'] = 'score desc'

    if using_facets:
        solr_query['facet'] = True
        solr_query['facet.sort'] = 'index'
        solr_query['facet.method'] = 'enum'
        solr_query['facet.mincount'] = 1
        fq = []
        ff = []
        for facet in facets:
            solr_query['f.{0}.facet.sort'.format(facet)] = fields[facet].solr_facet_sort
            solr_query['f.{0}.facet.limit'.format(facet)] = fields[facet].solr_facet_limit
            if facet in known_fields:
                # Use this query syntax when facet search values are specified
                quoted_terms = ['"{0}"'.format(item) for item in known_fields[facet]]
                facet_text = '{{!tag=tag_{0}}}{0}:({1})'.format(facet, ' OR '.join(quoted_terms))
                fq.append(facet_text)
                ff.append('{{!ex=tag_{0}}}{0}'.format(facet))
            else:
                # Otherwise just retrieve the entire facet
                ff.append(facet)
        solr_query['fq'] = fq
        solr_query['facet.field'] = ff
    if export and solr_query['sort'] == "score desc":
        solr_query['sort'] = "id asc"
    if search.solr_debugging:
        solr_query['debugQuery'] = True
    return solr_query


def create_solr_mlt_query(request: HttpRequest, search: Search, fields: dict, start_row: int, record_id: str):
    solr_query = {
        'q': 'id:"{0}"'.format(record_id),
        'mlt': True,
        'mlt.count': search.mlt_items,
        'mlt.boost': True,
        'start': start_row,
        'rows': search.mlt_items,
        'fl':  get_query_fields(request.LANGUAGE_CODE, fields),
        'mlt.fl': get_mlt_fields(request, fields),
        'mlt.mintf': 1,
        'mlt.minwl': 3,
        'mlt.mindf': 2,
        'mlt.maxdfpct': 50,
    }
    return solr_query

