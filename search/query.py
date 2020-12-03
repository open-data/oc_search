from django.http import HttpRequest
from math import ceil
from nltk.tokenize.regexp import RegexpTokenizer
import os
import re
from search.models import Search, Field


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


def calc_pagination_range(num_found: int, pagesize, current_page):
    pages = int(ceil(num_found / pagesize))
    delta = 2
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


def calc_starting_row(page_num, rows_per_age=10):
    """
    Calculate a starting row for the Solr search results. We only retrieve one page at a time
    :param page_num: Current page number
    :param rows_per_age: number of rows per page
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
    return rows_per_age * (page - 1), page


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


def create_solr_query(request: HttpRequest, search: Search, fields: dict, Codes: dict, facets: list, start_row: int,
                      rows: int, record_id: str, export=False):
    using_facets = len(facets) > 0

    # Look for known fields in the GET request
    known_fields = {}
    solr_query = {'q': '*', 'defType': 'edismax'}

    for request_field in request.GET.keys():
        if request_field == 'search_text' and not record_id:
            solr_query['q'] = get_search_terms(request.GET.get('search_text'))
        elif request_field == 'sort' and not record_id:
            solr_query['sort'] = request.GET.get('sort') if request.GET.get('sort') in search.results_sort_order.split(',') else 'score desc'
        elif request_field in fields:
            known_fields[request_field] = request.GET.get(request_field).split('|')

    # This happens for record reviews
    if record_id:
        record_id_esc = url_part_escape(record_id)
        solr_query['q'] = 'id:"{0}"'.format(record_id_esc)

    solr_query['q.op'] = "AND"

    # Create a Solr query field list based on the Fields Model. Expand the field list where needed
    # solr_query['fl'] = ",".join(fields.keys())
    qf = ['id']
    for f in fields:
        if Field(f).solr_field_lang in [request.LANGUAGE_CODE, 'bi']:
            qf.append(f)
            if fields[f].solr_extra_fields:
                qf.extend(fields[f].solr_extra_fields.split(","))
            if fields[f].solr_field_is_coded:
                code_value_field = "{0}_{1}".format(f, request.LANGUAGE_CODE)
                if code_value_field not in  qf:
                    qf.append(code_value_field)
    solr_query['qf'] = qf
    if export:
        ef = ['id']
        for f in fields:
            if fields[f].solr_field_lang in [request.LANGUAGE_CODE, 'bi']:
                if fields[f].solr_field_type in ['string', 'pint', 'pfloat', 'pdate']:
                    ef.append(f)
        solr_query['fl'] = ",".join(ef)
    else:
        solr_query['fl'] = ",".join(qf)
    if not export:
        solr_query['start'] = start_row
        solr_query['rows'] = rows

    # Set a default sort order
    if 'sort' not in solr_query:
        solr_query['sort'] = 'score desc'

    if using_facets:
        solr_query['facet'] = True
        solr_query['facet.sort'] = 'index'
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
    return solr_query
