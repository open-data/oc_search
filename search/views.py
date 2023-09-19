import collections
import csv
from datetime import datetime
from django.views.decorators.cache import never_cache
from django.conf import settings
from django.core.cache import caches
from django.core.exceptions import ObjectDoesNotExist
from django.http import HttpRequest, HttpResponseRedirect, FileResponse, JsonResponse
from django.utils import translation
from django.utils.translation import gettext as _
from django.views.generic import View
from django.shortcuts import render, redirect
from .forms import FieldForm
import importlib
import logging
import os
import pkgutil
import re
from .query import calc_pagination_range, calc_starting_row, create_solr_query, create_solr_mlt_query
from search.models import Search, Field, Code, Setting
from django_celery_results.models import TaskResult
import search.plugins
from SolrClient import SolrClient, SolrResponse
from SolrClient.exceptions import ConnectionError, SolrError
from search.tasks import export_search_results_csv
from unidecode import unidecode


def iter_namespace(ns_pkg):
    # Specifying the second argument (prefix) to iter_modules makes the
    # returned name an absolute name instead of a relative one. This allows
    # import_module to work without having to do additional modification to
    # the name.
    return pkgutil.iter_modules(ns_pkg.__path__, ns_pkg.__name__ + ".")


def get_error_context(search_type: str, lang: str, error_msg=""):
    return {
        "language": lang,
        "LANGUAGE_CODE": lang,
        "cdts_version": settings.CDTS_VERSION,
        "search_type": search_type,
        "search_description": "",
        "search_title": search_type,
        "dcterms_lang": 'fra' if lang == 'fr' else 'eng',
        "ADOBE_ANALYTICS_URL": settings.ADOBE_ANALYTICS_URL,
        "GOOGLE_ANALYTICS_GTM_ID": settings.GOOGLE_ANALYTICS_GTM_ID,
        "GOOGLE_ANALYTICS_PROPERTY_ID": settings.GOOGLE_ANALYTICS_PROPERTY_ID,
        "header_js_snippet": "",
        "header_css_snippet": "",
        "site_host_en": settings.OPEN_DATA_HOST_EN,
        "site_host_fr": settings.OPEN_DATA_HOST_FR,
        "breadcrumb_snippet": "search_snippets/default_breadcrumb.html",
        "footer_snippet": "search_snippets/default_footer.html",
        "body_js_snippet": "",
        "info_message_snippet": "search_snippets/default_info_message.html",
        "about_message_snippet": "search_snippets/default_about_message.html",
        "DEBUG": settings.DEBUG,
        "exception_message": error_msg
    }


class FieldFormView(View):
    def __init__(self):
        super().__init__()

    def get(self, request, *args, **kwargs):
        form = FieldForm()
        return render(request, 'field_form.html', {'form': form})

    def post(self, request, *args, **kwargs):
        # create a form instance and populate it with data from the request:
        form = FieldForm(request.POST)
        # check whether it's valid:
        if form.is_valid():
            print('Valid')
        return render(request, 'guide_form.html', {'form': form})


class SearchView(View):

    searches = {}
    search_alias_en = {}
    search_alias_fr = {}
    reverse_search_alias_en = {}
    reverse_search_alias_fr = {}
    fields = {}
    facets_en = {}
    facets_fr = {}
    codes_en = {}
    codes_fr = {}
    display_fields_en = {}
    display_fields_fr = {}
    display_fields_names_en = {}
    display_fields_names_fr = {}

    discovered_plugins = {}

    logger = logging.getLogger(__name__)

    def __init__(self):
        super().__init__()

        # Original function copied from https://packaging.python.org/guides/creating-and-discovering-plugins/
        self.discovered_plugins = {
            name: importlib.import_module(name)
            for finder, name, ispkg
            in iter_namespace(search.plugins)
        }

        # Use a local memory cache for the DB objects
        cache = caches['local']
        # Load Search and Field configuration

        if cache.get('searches') is None:
            search_queryset = Search.objects.all()
            for s in search_queryset:
                self.searches[s.search_id] = s
                if s.search_alias_en:
                    self.search_alias_en[s.search_alias_en] = s.search_id
                    self.reverse_search_alias_en[s.search_id] = s.search_alias_en
                else:
                    self.reverse_search_alias_en[s.search_id] = s.search_id
                if s.search_alias_fr:
                    self.search_alias_fr[s.search_alias_fr] = s.search_id
                    self.reverse_search_alias_fr[s.search_id] = s.search_alias_fr
                else:
                    self.reverse_search_alias_fr[s.search_id] = s.search_id
            cache.set('searches', self.searches, settings.CACHE_LOCAL_TIMEOUT)
            cache.set('search_alias_en', self.search_alias_en, settings.CACHE_LOCAL_TIMEOUT + 10)
            cache.set('search_alias_fr', self.search_alias_fr, settings.CACHE_LOCAL_TIMEOUT + 10)
            cache.set('reverse_search_alias_en', self.reverse_search_alias_en, settings.CACHE_LOCAL_TIMEOUT + 10)
            cache.set('reverse_search_alias_fr', self.reverse_search_alias_fr, settings.CACHE_LOCAL_TIMEOUT + 10)
        else:
            self.searches = cache.get('searches')
            self.search_alias_en = cache.get('search_alias_en')
            self.search_alias_fr = cache.get('search_alias_fr')
            self.reverse_search_alias_en = cache.get('reverse_search_alias_en')
            self.reverse_search_alias_fr = cache.get('reverse_search_alias_fr')

        if cache.get('fields') is None:
            for sid in self.searches.keys():
                sfields = {}
                facet_list_en = []
                facet_list_fr = []
                display_list_en = []
                display_list_fr = []
                field_queryset = Field.objects.filter(search_id_id=sid)
                for f in field_queryset:
                    sfields[f.field_id] = f
                field_queryset = Field.objects.filter(search_id_id=sid).filter(is_search_facet=True).order_by('solr_facet_display_order')
                for f in field_queryset:
                    if f.solr_field_lang == 'en':
                        facet_list_en.append(f.field_id)
                    elif f.solr_field_lang == 'fr':
                        facet_list_fr.append(f.field_id)
                    elif f.solr_field_lang == 'bi':
                        facet_list_en.append(f.field_id)
                        facet_list_fr.append(f.field_id)
                field_queryset = Field.objects.filter(search_id_id=sid).filter(is_default_display=True)
                for f in field_queryset:
                    if f.is_default_display and f.solr_field_lang == 'en':
                        display_list_en.append(f.field_id)
                    elif f.is_default_display and f.solr_field_lang == 'fr':
                        display_list_fr.append(f.field_id)
                    elif f.is_default_display and f.solr_field_lang == 'bi':
                        display_list_en.append(f.field_id)
                        display_list_fr.append(f.field_id)

                self.fields[sid] = sfields
                self.facets_en[sid] = facet_list_en
                self.facets_fr[sid] = facet_list_fr
                self.display_fields_en[sid] = display_list_en
                self.display_fields_fr[sid] = display_list_fr
                self.display_fields_names_en[sid] = self.get_default_display_fields('en', sid)
                self.display_fields_names_fr[sid] = self.get_default_display_fields('fr', sid)

            cache.set('fields', self.fields, settings.CACHE_LOCAL_TIMEOUT)
            cache.set('facets_en', self.facets_en, settings.CACHE_LOCAL_TIMEOUT + 10)
            cache.set('facets_fr', self.facets_fr, settings.CACHE_LOCAL_TIMEOUT + 10)
            cache.set('display_fields_en', self.display_fields_en, settings.CACHE_LOCAL_TIMEOUT + 10)
            cache.set('display_fields_fr', self.display_fields_fr, settings.CACHE_LOCAL_TIMEOUT + 10)
            cache.set('display_fields_names_en', self.display_fields_names_en, settings.CACHE_LOCAL_TIMEOUT + 10)
            cache.set('display_fields_names_fr', self.display_fields_names_fr, settings.CACHE_LOCAL_TIMEOUT + 10)

        else:
            self.fields = cache.get('fields')
            self.facets_en = cache.get('facets_en')
            self.facets_fr = cache.get('facets_fr')
            self.display_fields_en = cache.get('display_fields_en')
            self.display_fields_fr = cache.get('display_fields_fr')
            self.display_fields_names_en = cache.get('display_fields_names_en')
            self.display_fields_names_fr = cache.get('display_fields_names_fr')

        # Load Code configuration
        if cache.get('codes_en') is None:
            self.codes_en = {}
            self.codes_fr = {}
            for sid in self.searches.keys():
                self.codes_en[sid] = {}
                self.codes_fr[sid] = {}
                codes_queryset = Code.objects.filter(field_fid__search_id__search_id=sid)
                for code in codes_queryset:
                    # Codes are stored in a dictionary with the code_id as the key
                    if code.field_fid.field_id in self.codes_en[sid]:
                        self.codes_en[sid][code.field_fid.field_id][code.code_id] = code.label_en
                        self.codes_fr[sid][code.field_fid.field_id][code.code_id] = code.label_fr
                    else:
                        self.codes_en[sid][code.field_fid.field_id] = {code.code_id: code.label_en}
                        self.codes_fr[sid][code.field_fid.field_id] = {code.code_id: code.label_fr}
            cache.set('codes_en', self.codes_en, settings.CACHE_LOCAL_TIMEOUT)
            cache.set('codes_fr', self.codes_fr, settings.CACHE_LOCAL_TIMEOUT)
        else:
            self.codes_en = cache.get('codes_en')
            self.codes_fr = cache.get('codes_fr')

    def get_default_display_fields(self, lang: str, search_type: str):
        display_field_name = {}
        for f in self.fields[search_type]:
            if self.fields[search_type][f].solr_field_lang in [lang, 'bi']:
                if lang == 'en' and not f[:2] == 'fr':
                    display_field_name[f] = self.fields[search_type][f].label_en
                    continue
                elif lang == 'fr' and not f[:2] == 'en':
                    display_field_name[f] = self.fields[search_type][f].label_fr
                    continue
        return display_field_name

    def default_context(self, request: HttpRequest, search_type: str, lang: str):
        context = {
            "language": lang,
            "cdts_version": settings.CDTS_VERSION,
            "search_type": search_type,
            "search_description": self.searches[search_type].desc_fr if lang == 'fr' else self.searches[
                search_type].desc_fr,
            "search_title": self.searches[search_type].label_fr if lang == 'fr' else self.searches[
                search_type].label_en,
            "dcterms_lang": 'fra' if lang == 'fr' else 'eng',
            "ADOBE_ANALYTICS_URL": settings.ADOBE_ANALYTICS_URL,
            "GOOGLE_ANALYTICS_GTM_ID": settings.GOOGLE_ANALYTICS_GTM_ID,
            "GOOGLE_ANALYTICS_PROPERTY_ID": settings.GOOGLE_ANALYTICS_PROPERTY_ID,
            "GOOGLE_ANALYTICS_GA4_ID": settings.GOOGLE_ANALYTICS_GA4_ID,
            "url_uses_path": settings.SEARCH_LANG_USE_PATH,
            "url_host_en": settings.SEARCH_EN_HOSTNAME,
            "url_host_fr": settings.SEARCH_FR_HOSTNAME,
            "url_host_path": settings.SEARCH_HOST_PATH,
            "site_host_en": settings.OPEN_DATA_HOST_EN,
            "site_host_fr": settings.OPEN_DATA_HOST_FR,
            "header_js_snippet": self.searches[search_type].header_js_snippet,
            "header_css_snippet": self.searches[search_type].header_css_snippet,
            "breadcrumb_snippet": self.searches[search_type].breadcrumb_snippet,
            "record_breadcrumb_snippet": self.searches[search_type].record_breadcrumb_snippet,
            "footer_snippet": self.searches[search_type].footer_snippet,
            "body_js_snippet": self.searches[search_type].body_js_snippet,
            "info_message_snippet": self.searches[search_type].info_message_snippet,
            "about_message_snippet": self.searches[search_type].about_message_snippet,
            "mlt_enabled": self.searches[search_type].mlt_enabled,
            "query_path": request.META["QUERY_STRING"],
            "path_info": request.META["PATH_INFO"],
        }
        utl_fragments = request.META["PATH_INFO"].split('/')
        utl_fragments = utl_fragments if utl_fragments[-2] == search_type else utl_fragments[:-2]
        if utl_fragments[-1]:
            utl_fragments.append('')

        context['parent_path'] = "/".join(utl_fragments)

        return context

    def get(self, request: HttpRequest, lang='en', search_type=''):
        lang = request.LANGUAGE_CODE

        # Track if this is a new text search

        new_text_search = False
        if 'prev_search' in request.session:
            if not re.search("search_text=\S+", request.session['prev_search']) and \
            str(request.GET.get('search_text', '')).strip() != '':
                new_text_search = True
        request.session['prev_search'] = request.build_absolute_uri()

        # Replace search_type alias with actual search type
        if lang == 'fr':
            if search_type in self.search_alias_fr:
                search_type = self.search_alias_fr[search_type]
        else:
            if search_type in self.search_alias_en:
                search_type = self.search_alias_en[search_type]

        if search_type in self.searches and not self.searches[search_type].is_disabled:
            context = self.default_context(request, search_type, lang)
            context["search_item_snippet"] = self.searches[search_type].search_item_snippet
            context["download_ds_url"] = self.searches[search_type].dataset_download_url_fr if lang == 'fr' else self.searches[search_type].dataset_download_url_en
            context["download_ds_text"] = self.searches[search_type].dataset_download_text_fr if lang == 'fr' else self.searches[search_type].dataset_download_text_en
            context["search_text"] = request.GET.get("search_text", "")
            context["id_fields"] = self.searches[search_type].id_fields.split(',') if self.searches[
                search_type].id_fields else []
            context["export_path"] = "{0}export/".format(request.META["PATH_INFO"])
            context['export_query'] = request.META["QUERY_STRING"]
            context['export_search_path'] = request.get_full_path()
            context['about_msg'] = self.searches[search_type].about_message_fr if lang == 'fr' else self.searches[search_type].about_message_en
            context['search_toggle'] = self.reverse_search_alias_en[search_type] if lang == 'fr' else self.reverse_search_alias_fr[search_type]
            context['json_download_allowed'] = self.searches[search_type].json_response

            # Get search drop in message:
            context["general_msg"] = ""
            if lang == 'en':
                search_msg_en, is_new = Setting.objects.get_or_create(key="search.searchpage.topmessage.en")
                if not is_new:
                    context["general_msg"] = search_msg_en.value
            else:
                search_msg_fr, is_new = Setting.objects.get_or_create(key="search.searchpage.topmessage.fr")
                if not is_new:
                    context["general_msg"] = search_msg_fr.value

            solr = SolrClient(settings.SOLR_SERVER_URL)

            core_name = self.searches[search_type].solr_core_name

            # Get the search result boundaries
            start_row, page = calc_starting_row(request.GET.get('page', 1),
                                                rows_per_page=self.searches[search_type].results_page_size)

            # Compose the Solr query
            facets = self.facets_fr[search_type] if lang == 'fr' else self.facets_en[search_type]
            reversed_facets = []
            for facet in facets:
                if self.fields[search_type][facet].solr_facet_display_reversed:
                    reversed_facets.append(facet)
            context['reversed_facets'] = reversed_facets

            # Determine a default sort order - used by the query if a valid sort order is not specified --
            # unless this is the first time a user is using search text, then use best match order.
            # Use the default specified in the search model and if none is specified used best match.

            if new_text_search:
                default_sort_order = 'score desc'
            elif request.LANGUAGE_CODE == 'fr':
                default_sort_order = self.searches[search_type].results_sort_default_fr if self.searches[
                    search_type].results_sort_default_fr else 'score desc'
            else:
                default_sort_order = self.searches[search_type].results_sort_default_en if self.searches[search_type].results_sort_default_en else 'score desc'

            solr_query = create_solr_query(request, self.searches[search_type], self.fields[search_type],
                                           self.codes_fr[search_type] if lang == 'fr' else self.codes_en[search_type],
                                           facets, start_row, self.searches[search_type].results_page_size,
                                           record_id='', export=False, highlighting=True,
                                           default_sort=default_sort_order, override_sort=new_text_search)

            # Call  plugin pre-solr-query if defined
            search_type_plugin = 'search.plugins.{0}'.format(search_type)
            if search_type_plugin in self.discovered_plugins:
                context, solr_query = self.discovered_plugins[search_type_plugin].pre_search_solr_query(
                    context,
                    solr_query,
                    request,
                    self.searches[search_type], self.fields[search_type],
                    self.codes_fr[search_type] if lang == 'fr' else self.codes_en[search_type],
                    facets,
                    '')

            # Query Solr

            try:
                solr_response = solr.query(core_name, solr_query, highlight=True)

                # Call  plugin post-solr-query if it exists
                if search_type_plugin in self.discovered_plugins:
                    context, solr_response = self.discovered_plugins[search_type_plugin].post_search_solr_query(
                        context,
                        solr_response,
                        solr_query,
                        request,
                        self.searches[search_type], self.fields[search_type],
                        self.codes_fr[search_type] if lang == 'fr' else self.codes_en[search_type],
                        facets,
                        '')

                context['show_all_results'] = True
                for p in request.GET:
                    if p not in ['encoding', 'page', 'sort']:
                        context['show_all_results'] = False
                        break

                context['system_facet_fields'] = ['__label__', '__sortorder__']
                if len(facets) > 0:
                    # Facet search results
                    context['facets'] = solr_response.get_facets()
                    # Get the selected facets from the search URL
                    selected_facets = {}

                    for request_field in request.GET.keys():
                        if request_field in self.fields[search_type] and request_field in context['facets']:
                            selected_facets[request_field] = request.GET.get(request_field, "").split('|')
                    context['selected_facets'] = selected_facets
                    # Provide human friendly facet labels to the web page and any custom snippets
                    facets_custom_snippets = {}
                    for f in context['facets']:
                        context['facets'][f]['__label__'] = self.fields[search_type][f].label_fr if lang == 'fr' else self.fields[search_type][f].label_en
                        context['facets'][f]['__sortorder__'] = self.fields[search_type][f].solr_facet_sort
                        # If the facet is a code and sorting by label, then the facet needs to be resorted
                        if self.fields[search_type][f].solr_facet_sort == 'label':
                            # Create an inverted index of the facet values
                            facet_values = {}
                            for facet_value in context['facets'][f].keys():
                                if facet_value not in context['system_facet_fields'] and facet_value != '-' and facet_value in self.codes_en[search_type][f]:
                                    if request.LANGUAGE_CODE == 'fr':
                                        facet_values[self.codes_fr[search_type][f][facet_value]] = facet_value
                                    else:
                                        facet_values[self.codes_en[search_type][f][facet_value]] = facet_value
                                elif facet_value not in context['system_facet_fields'] and facet_value != '-' and facet_value not in self.codes_en[search_type][f]:
                                    self.logger.info(f"Unknown facet_value {f}:{facet_value}")
                            # Sort the facet values - use French locale for sorting
                            if lang == "fr":
                                sorted_facet_values = sorted(facet_values.keys(), key=unidecode)
                            else:
                                sorted_facet_values = sorted(facet_values.keys())
                            new_facet = collections.OrderedDict()
                            for facet_value in sorted_facet_values:
                                new_facet[facet_values[facet_value]] = context['facets'][f][facet_values[facet_value]]
                            new_facet['__label__'] = context['facets'][f]['__label__']
                            new_facet['__sortorder__'] = context['facets'][f]['__sortorder__']
                            context['facets'][f] = new_facet

                        if self.fields[search_type][f].solr_facet_snippet:
                            facets_custom_snippets[f] = self.fields[search_type][f].solr_facet_snippet
                    context['facet_snippets'] = facets_custom_snippets
                else:
                    context['facets'] = []
                    context['selected_facets'] = []

                context['total_hits'] = solr_response.num_found
                context['docs'] = solr_response.get_highlighting()

                # Prepare a dictionary of language appropriate sort options
                sort_options = {}
                sort_labels = self.searches[search_type].results_sort_order_display_fr.split(',') if lang == 'fr' else self.searches[search_type].results_sort_order_display_en.split(',')
                if lang == 'fr':
                    for i, v in enumerate(self.searches[search_type].results_sort_order_fr.split(',')):
                        sort_options[v] = str(sort_labels[i]).strip()
                else:
                    for i, v in enumerate(self.searches[search_type].results_sort_order_en.split(',')):
                        sort_options[v] = str(sort_labels[i]).strip()
                context['sort_options'] = sort_options
                context['sort'] = solr_query['sort']

                # Add code information
                context['codes'] = self.codes_fr[search_type] if lang == 'fr' else self.codes_en[search_type]

                # Save display fields
                context['default_display_fields'] = self.display_fields_fr[search_type] if lang == 'fr' else self.display_fields_en[search_type]
                context['display_field_name'] = self.display_fields_names_fr[search_type] if lang == 'fr' else self.display_fields_names_en[search_type]

                # Calculate pagination for the search page
                context['pagination'] = calc_pagination_range(solr_response.num_found, self.searches[search_type].results_page_size, page, 3)
                if len(context['pagination']) == 1:
                    context['show_pagination'] = False
                else:
                    context['show_pagination'] = True
                    context['previous_page'] = (1 if page == 1 else page - 1)
                    last_page = (context['pagination'][len(context['pagination']) - 1] if len(context['pagination']) > 0 else 1)
                    last_page = (1 if last_page < 1 else last_page)
                    context['last_page'] = last_page
                    next_page = page + 1
                    next_page = (last_page if next_page > last_page else next_page)
                    context['next_page'] = next_page
                    context['currentpage'] = page
                if search_type_plugin in self.discovered_plugins and self.discovered_plugins[search_type_plugin].plugin_api_version() >= 1.1:
                    context, template = self.discovered_plugins[search_type_plugin].pre_render_search(context,
                                                                                                      self.searches[search_type].page_template,
                                                                                                      request,
                                                                                                      lang,
                                                                                                      self.searches[search_type],
                                                                                                      self.fields[search_type],
                                                                                                      self.codes_fr[search_type] if lang == 'fr' else self.codes_en[search_type])
                # Users can optionally get the search results as a JSON object instead of the normal HTML page
                search_format = request.GET.get("search_format", "html")
                if search_format == 'json' and self.searches[search_type].json_response:
                    full_facet_dict = {}
                    for facet in context['facets'].keys():
                        facet_list = []
                        for facet_field in context['facets'][facet]:
                            if not facet_field.startswith('__'):
                                if self.fields[context['search_type']][facet].solr_field_is_coded:
                                    facet_dict = {
                                        'code': facet_field,
                                        'label_en': self.codes_en[context['search_type']][facet][facet_field],
                                        'label_fr': self.codes_fr[context['search_type']][facet][facet_field],
                                        'count': context['facets'][facet][facet_field]
                                    }
                                else:
                                    facet_dict = {
                                        'code': facet_field,
                                        'label_en': facet_field,
                                        'label_fr': facet_field,
                                        'count': context['facets'][facet][facet_field]
                                    }
                                facet_list.append(facet_dict)
                        full_facet_dict[facet] = facet_list
                    doc_dict = {'num_count': context['total_hits'],
                                'start': solr_response.data['response']['start'] + 1,
                                'end': solr_response.data['response']['start'] + solr_response.docs.__len__(),
                                'docs': context['docs'],
                                'facets': full_facet_dict,
                                'selected_facets': context['selected_facets'] if context['selected_facets'] else []}
                    return JsonResponse(doc_dict)
                elif search_format == 'solr' and self.searches[search_type].raw_solr_response:
                    return JsonResponse(solr_response.data)
                else:
                    json_link = str(request.get_full_path())
                    if json_link.endswith("/"):
                        json_link = json_link + "?search_format=json"
                    elif json_link.endswith("&") or json_link.endswith("?"):
                        json_link = json_link + "search_format=json"
                    else:
                        json_link = json_link + "&search_format=json"
                    context["json_format_url"] = json_link
                    return render(request, self.searches[search_type].page_template, context)
            except (ConnectionError, SolrError) as ce:
                return render(request, 'error.html', get_error_context(search_type, lang, ce.args[0]))
        elif search_type in self.searches and self.searches[search_type].is_disabled:
            context = self.default_context(request, search_type, lang)
            context['label_en'] = self.searches[search_type].label_en
            context['label_fr'] = self.searches[search_type].label_fr
            context['message_en'] = self.searches[search_type].disabled_message_en
            context['message_fr'] = self.searches[search_type].disabled_message_fr
            return render(request, 'no_service.html', context)
        else:
            return render(request, '404.html', get_error_context(search_type, lang))


class RecordView(SearchView):

    def get(self, request: HttpRequest, lang='en', search_type='', record_id=''):
        lang = request.LANGUAGE_CODE        # Replace search_type alias with actual search type
        if lang == 'fr':
            if search_type in self.search_alias_fr:
                search_type = self.search_alias_fr[search_type]
        else:
            if search_type in self.search_alias_en:
                search_type = self.search_alias_en[search_type]

        if search_type in self.searches:
            context = self.default_context(request, search_type, lang)
            context['record_detail_snippet'] = self.searches[search_type].record_detail_snippet
            context["download_ds_url_en"] = self.searches[search_type].dataset_download_url_fr if lang == 'fr' else self.searches[search_type].dataset_download_url_en
            context["search_text"] = request.GET.get("search_text", "")
            if 'prev_search' in request.session:
                context['back_to_url'] =  request.session['prev_search']
            request.session['prev_record'] = request.build_absolute_uri()
            solr = SolrClient(settings.SOLR_SERVER_URL)

            core_name = self.searches[search_type].solr_core_name

            # Get the search result boundaries
            start_row, page = calc_starting_row(request.GET.get('page', 1), rows_per_page=5)

            # Compose the Solr query
            facets = {}

            solr_query = create_solr_query(request, self.searches[search_type], self.fields[search_type],
                                           self.codes_fr[search_type] if lang == 'fr' else self.codes_en[search_type],
                                           facets, start_row, 25, record_id)

            # Call  plugin pre-solr-query if defined
            search_type_plugin = 'search.plugins.{0}'.format(search_type)
            if search_type_plugin in self.discovered_plugins:
                context, solr_query = self.discovered_plugins[search_type_plugin].pre_record_solr_query(
                    context,
                    solr_query,
                    request,
                    self.searches[search_type], self.fields[search_type],
                    self.codes_fr[search_type] if lang == 'fr' else self.codes_en[search_type],
                    facets,
                    record_id)

            # Query Solr
            solr_response = solr.query(core_name, solr_query)

            # Call  plugin post-solr-query if it exists
            if search_type_plugin in self.discovered_plugins:
                context, solr_response = self.discovered_plugins[search_type_plugin].post_record_solr_query(
                    context,
                    solr_response,
                    solr_query,
                    request,
                    self.searches[search_type], self.fields[search_type],
                    self.codes_fr if lang == 'fr' else self.codes_en,
                    facets,
                    record_id)

            context['facets'] = []
            context['selected_facets'] = []
            context['total_hits'] = solr_response.num_found
            context['docs'] = solr_response.get_highlighting()

            # Add code information
            context['codes'] = self.codes_fr[search_type] if lang == 'fr' else self.codes_en[search_type]

            display_fields = []
            display_field_name = {}
            for f in self.fields[search_type]:
                if self.fields[search_type][f].solr_field_lang in [request.LANGUAGE_CODE, 'bi']:
                    if request.LANGUAGE_CODE == 'en' and not f[:2] == 'fr':
                        display_fields.append(f)
                        display_field_name[f] = self.fields[search_type][f].label_en
                        continue
                    elif request.LANGUAGE_CODE == 'fr' and not f[:2] == 'en':
                        display_fields.append(f)
                        display_field_name[f] = self.fields[search_type][f].label_fr
                        continue
                    if self.fields[search_type][f].solr_extra_fields:
                        display_fields.extend(self.fields[search_type][f].solr_extra_fields.split(","))
            context['display_fields'] = display_fields
            context['display_field_name'] = display_field_name

            # Calculate pagination for the search page
            context['pagination'] = calc_pagination_range(solr_response.num_found, 10, page)
            if len(context['pagination']) == 1:
                context['show_pagination'] = False
            else:
                context['show_pagination'] = True
                context['previous_page'] = (1 if page == 1 else page - 1)
                last_page = (context['pagination'][len(context['pagination']) - 1] if len(context['pagination']) > 0 else 1)
                last_page = (1 if last_page < 1 else last_page)
                context['last_page'] = last_page
                next_page = page + 1
                next_page = (last_page if next_page > last_page else next_page)
                context['next_page'] = next_page
                context['currentpage'] = page

            if search_type_plugin in self.discovered_plugins and self.discovered_plugins[search_type_plugin].plugin_api_version() >= 1.1:
                context, template = self.discovered_plugins[search_type_plugin].pre_render_record(context,
                                                                                                  self.searches[search_type].record_template,
                                                                                                  request,
                                                                                                  lang,
                                                                                                  self.searches[search_type],
                                                                                                  self.fields[search_type],
                                                                                                  self.codes_fr[search_type] if lang == 'fr' else self.codes_en[search_type])
            return render(request, self.searches[search_type].record_template, context)

        else:
            return render(request, '404.html', get_error_context(search_type, lang))


class ExportView(SearchView):

    def __init__(self):
        super().__init__()
        self.cache_dir = settings.EXPORT_FILE_CACHE_DIR
        if not os.path.exists(self.cache_dir):
            os.mkdir(self.cache_dir)

    def cache_search_results_file(self, cached_filename: str, sr: SolrResponse, rows=100000):

        if len(sr.docs) == 0:
            return False
        if not os.path.exists(cached_filename):
            with open(cached_filename, 'w', newline='', encoding='utf8') as csv_file:
                cache_writer = csv.writer(csv_file, dialect='excel', quoting=csv.QUOTE_ALL)
                headers = list(sr.docs[0])
                headers[0] = u'\N{BOM}' + headers[0]
                cache_writer.writerow(headers)
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

    def post(self, request, *args, **kwargs):
        # create a form instance and populate it with data from the request:
        lang = request.LANGUAGE_CODE
        search_type = request.POST.get('export_search')
        if search_type in self.searches:

            solr = SolrClient(settings.SOLR_SERVER_URL)
            core_name = self.searches[search_type].solr_core_name
            facets = self.facets_fr[search_type] if lang == 'fr' else self.facets_en[search_type]
            solr_query = create_solr_query(request, self.searches[search_type], self.fields[search_type],
                                           self.codes_fr[search_type] if lang == 'fr' else self.codes_en[search_type],
                                           facets, 1, 0, record_id='', export=True)

            # Call  plugin pre-solr-query if defined
            search_type_plugin = 'search.plugins.{0}'.format(search_type)
            if search_type_plugin in self.discovered_plugins:
                solr_query = self.discovered_plugins[search_type_plugin].pre_export_solr_query(
                    solr_query,
                    request,
                    self.searches[search_type], self.fields[search_type],
                    self.codes_fr[search_type] if lang == 'fr' else self.codes_en[search_type],
                    facets)

            request_url = request.POST.get('export_search_path')
            task = export_search_results_csv.delay(request_url, solr_query, lang, core_name)
            if settings.SEARCH_LANG_USE_PATH:
                if lang == 'fr':
                    return redirect(f'/rechercher/fr/{search_type}/telecharger/{task}')
                else:
                    return redirect(f'/search/en/{search_type}/download/{task}')
            else:
                if lang == 'fr':
                    return redirect(f'{settings.SEARCH_HOST_PATH}/{search_type}/telecharger/{task}')
                else:
                    return redirect(f'{settings.SEARCH_HOST_PATH}/{search_type}/download/{task}')

        else:
            return render(request, '404.html', get_error_context(search_type, lang))

    def get(self, request: HttpRequest, lang='en', search_type=''):

        lang = request.LANGUAGE_CODE
        if search_type in self.searches:
            # Check to see if a recent cached results exists and return that instead if it exists
            # hashed_query = hashlib.sha1(request.GET.urlencode().encode('utf8')).hexdigest()
            # cached_filename = os.path.join(self.cache_dir, "{0}_{1}.csv".format(hashed_query, lang))
            # if os.path.exists(cached_filename):
            #     # If the cached file is over 5 minutes old, just delete and continue. In future, will want this to be a asynchronous opertaion
            #     if time() - os.path.getmtime(cached_filename) > 600:
            #         os.remove(cached_filename)
            #     else:
            #         if settings.EXPORT_FILE_CACHE_URL == "":
            #             return FileResponse(open(cached_filename, 'rb'), as_attachment=True)
            #         else:
            #             return HttpResponseRedirect(settings.EXPORT_FILE_CACHE_URL + "{0}_{1}.csv".format(hashed_query, lang))

            solr = SolrClient(settings.SOLR_SERVER_URL)
            core_name = self.searches[search_type].solr_core_name
            facets = self.facets_fr[search_type] if lang == 'fr' else self.facets_en[search_type]
            solr_query = create_solr_query(request, self.searches[search_type], self.fields[search_type],
                                           self.codes_fr[search_type] if lang == 'fr' else self.codes_en[search_type],
                                           facets, 1, 0, record_id='', export=True)

            # Call  plugin pre-solr-query if defined
            search_type_plugin = 'search.plugins.{0}'.format(search_type)
            if search_type_plugin in self.discovered_plugins:
                solr_query = self.discovered_plugins[search_type_plugin].pre_export_solr_query(
                    solr_query,
                    request,
                    self.searches[search_type], self.fields[search_type],
                    self.codes_fr[search_type] if lang == 'fr' else self.codes_en[search_type],
                    facets)

            request_url = request.GET.urlencode()
            task = export_search_results_csv.delay(request_url, solr_query, lang, core_name)

            # solr_response = solr.query(core_name, solr_query, request_handler='export')

            # Call  plugin post-solr-query results export if defined
            # if search_type_plugin in self.discovered_plugins:
            #     solr_query = self.discovered_plugins[search_type_plugin].post_export_solr_query(
            #         solr_response,
            #         solr_query,
            #         request,
            #         self.searches[search_type], self.fields[search_type],
            #         self.codes_fr[search_type] if lang == 'fr' else self.codes_en[search_type],
            #         facets)

            # if self.cache_search_results_file(cached_filename=cached_filename, sr=solr_response):
            #     if settings.EXPORT_FILE_CACHE_URL == "":
            #         return FileResponse(open(cached_filename, 'rb'), as_attachment=True)
            #     else:
            #         return HttpResponseRedirect(settings.EXPORT_FILE_CACHE_URL + "{0}_{1}.csv".format(hashed_query, lang))
            if settings.SEARCH_LANG_USE_PATH:
                if lang == 'fr':
                    return redirect(f'/rechercher/fr/{search_type}/telecharger/{task}')
                else:
                    return redirect(f'/search/en/{search_type}/download/{task}')
            else:
                if lang == 'fr':
                    return redirect(f'{settings.SEARCH_HOST_PATH}/{search_type}/telecharger/{task}')
                else:
                    return redirect(f'{settings.SEARCH_HOST_PATH}/{search_type}/download/{task}')

        else:
            return render(request, '404.html', get_error_context(search_type, lang))


class ExportStatusView(View):
    def __init__(self):
        super().__init__()

    @never_cache
    def get(self, request: HttpRequest, lang='en', search_type='', task_id=''):
        translation.activate(lang)
        response_dict = {"file_url": ""}
        if task_id == "":
            return render(request, '404.html', get_error_context(search_type, lang))
        else:
            http_status = 202
            try:
                # Note: as of Nov, 2022 the django-celery-results module only saves a task record
                # to the database AFTER the task has started, therefore the other status values are not
                # used at this time, but are present in anticipation of this functionality being added to the
                # module in the future.
                task = TaskResult.objects.get(task_id=task_id)
                response_dict['task_status'] = task.status
                if task.status == "SUCCESS":
                    response_dict['message'] = _("The exported data is ready")
                    response_dict['button_label'] = _("Download Search Results")
                    response_dict["file_url"] = task.result.strip('"')
                    response_dict['start'] = task.date_created.strftime("%Y-%m-%d %H:%M:%S.%f")
                    response_dict['done'] = task.date_done.strftime("%Y-%m-%d %H:%M:%S.%f")
                    http_status = 200
                elif task.status in ["PENDING", "RECEIVED"]:
                    response_dict['message'] = _("Your request has been queued for processing ...")
                elif task.status == "STARTED":
                    response_dict['message'] = _("Your request is being processed ...")
                elif task.status in ['REVOKED', 'REJECTED', 'RETRY', 'IGNORED']:
                    response_dict['message'] = _("An unexpected error has occurred. Please return to the search page and try again.")
                elif task.status == "FAILURE":
                    return render(request, '404.html', get_error_context(search_type, lang))

            except TaskResult.DoesNotExist as dne:
                # For now, assume the task is waiting to start in the Celery queue if it hasn't been added to the
                # database
                http_status = 202
                response_dict['message'] = _("Your export has been submitted for processing ...")
                response_dict['task_status'] = 'PENDING'

            return JsonResponse(response_dict, status=http_status)


class DownloadSearchResultsView(View):

    searches = {}
    search_alias_en = {}
    search_alias_fr = {}

    def __init__(self):
        super().__init__()
        # Use a local memory cache for the DB objects
        cache = caches['local']
        # Load Search and Field configuration

        if cache.get('searches') is None:
            search_queryset = Search.objects.all()
            for s in search_queryset:
                self.searches[s.search_id] = s
                if s.search_alias_en:
                    self.search_alias_en[s.search_alias_en] = s.search_id
                if s.search_alias_fr:
                    self.search_alias_fr[s.search_alias_fr] = s.search_id
            cache.set('searches', self.searches, 3600)
            cache.set('search_alias_en', self.search_alias_en, 3610)
            cache.set('search_alias_fr', self.search_alias_fr, 3610)
        else:
            self.searches = cache.get('searches')
            self.search_alias_en = cache.get('search_alias_en')
            self.search_alias_fr = cache.get('search_alias_fr')

    def get(self, request: HttpRequest, lang='en', search_type='', task_id=''):

        if settings.SEARCH_LANG_USE_PATH:
            subpaths = request.path.split('/')
            if 'fr' in subpaths:
                request.LANGUAGE_CODE = 'fr'
                lang = 'fr'
            else:
                request.LANGUAGE_CODE = 'en'
                lang = 'en'
        else:
            if request.get_host() == settings.SEARCH_FR_HOSTNAME:
                request.LANGUAGE_CODE = 'fr'
                lang = 'fr'
            else:
                request.LANGUAGE_CODE = 'en'
                lang = 'en'

        # Replace search_type alias with actual search type
        if lang == 'fr':
            if search_type in self.search_alias_fr:
                search_type = self.search_alias_fr[search_type]
        else:
            if search_type in self.search_alias_en:
                search_type = self.search_alias_en[search_type]

        if search_type in self.searches and not self.searches[search_type].is_disabled:
            context = {
                "language": lang,
                "record_breadcrumb_snippet": 'search_snippets/default_breadcrumb.html',
                "info_message_snippet": 'search_snippets/default_info_message.html',
                "about_message_snippet": 'search_snippets/default_about_message.html',
                "footer_snippet": 'search_snippets/default_footer.html',
                "cdts_version": settings.CDTS_VERSION,
                "dcterms_lang": 'fra' if lang == 'fr' else 'eng',
                "ADOBE_ANALYTICS_URL": settings.ADOBE_ANALYTICS_URL,
                "GOOGLE_ANALYTICS_GTM_ID": settings.GOOGLE_ANALYTICS_GTM_ID,
                "GOOGLE_ANALYTICS_PROPERTY_ID": settings.GOOGLE_ANALYTICS_PROPERTY_ID,
                "GOOGLE_ANALYTICS_GA4_ID": settings.GOOGLE_ANALYTICS_GA4_ID,
                "url_uses_path": settings.SEARCH_LANG_USE_PATH,
                "url_host_en": settings.SEARCH_EN_HOSTNAME,
                "url_host_fr": settings.SEARCH_FR_HOSTNAME,
                'search_label': "Download Search Results" if lang == 'en' else 'Télécharger les résultats de la recherche',
                'search_title': self.searches[search_type].label_fr if lang == 'fr' else self.searches[search_type].label_en,
                'task_id': task_id,
                'body_js_snippet': 'search_snippets/download.js',
                'debug': settings.DEBUG,
            }

            if settings.SEARCH_LANG_USE_PATH:
                if lang == 'fr':
                    context['download_status_url'] = f"/rechercher/rapport-de-recherche/fr/{search_type}/{task_id}"
                else:
                    context['download_status_url'] = f"/search/search-results/en/{search_type}/{task_id}"
            else:
                if lang == 'fr':
                    context['download_status_url'] = f"{settings.SEARCH_HOST_PATH}/rapport-de-recherche/fr/{search_type}/{task_id}"
                else:
                    context['download_status_url'] = f"{settings.SEARCH_HOST_PATH}/search-results/en/{search_type}/{task_id}"
            if 'prev_search' in request.session:
                context['back_to_url'] = request.session['prev_search']
            return render(request, 'download.html',  context)
        elif search_type in self.searches and self.searches[search_type].is_disabled:
            context = {"language": lang,}
            context['label_en'] = self.searches[search_type].label_en
            context['label_fr'] = self.searches[search_type].label_fr
            context['message_en'] = self.searches[search_type].disabled_message_en
            context['message_fr'] = self.searches[search_type].disabled_message_fr
            return render(request, 'no_service.html', context)
        else:
            return render(request, '404.html', get_error_context(search_type, lang))

class MoreLikeThisView(SearchView):

    def __init__(self):
        super().__init__()

    # @TODO  In the query class, use a shared method for fl and create new mothod fr MLT queries
    # Note, for MLT, use the standard query but specify MLT params id:XXXX mlt=true&mlt.fl=title_en,name_en,purpose_en
    # http://localhost:8983/solr/core_travelq/select?mlt.count=5&mlt.fl=title_en%2Cname_en%2Cpurpose_en%2Cid&mlt=true&q=id%3A%22aafc-aac%2CT-2017-Q1-00003%22
    # http://127.0.0.1:8000/search/en/travelq/similar/aafc-aac,T-2017-Q1-00003

    def get(self, request: HttpRequest, lang='en', search_type='', record_id=''):
        lang = request.LANGUAGE_CODE

        # Replace search_type alias with actual search type
        if lang == 'fr':
            if search_type in self.search_alias_fr:
                search_type = self.search_alias_fr[search_type]
        else:
            if search_type in self.search_alias_en:
                search_type = self.search_alias_en[search_type]

        if search_type in self.searches:
            context = self.default_context(request, search_type, lang)
            context["search_item_snippet"] = self.searches[search_type].search_item_snippet
            context["referer"] = request.META["HTTP_REFERER"] if "HTTP_REFERER" in request.META and (request.META["HTTP_REFERER"].startswith("http://" + request.META["HTTP_HOST"]) or request.META[
                    "HTTP_REFERER"].startswith("https://" + request.META["HTTP_HOST"])) else ""
            solr = SolrClient(settings.SOLR_SERVER_URL)

            core_name = self.searches[search_type].solr_core_name

            # Get the search result boundaries
            start_row, page = calc_starting_row(request.GET.get('page', 1), rows_per_page=self.searches[search_type].mlt_items)
            # Compose the Solr query
            solr_query = create_solr_mlt_query(request, self.searches[search_type], self.fields[search_type], start_row, record_id)

            # Call  plugin pre-solr-query if defined
            search_type_plugin = 'search.plugins.{0}'.format(search_type)
            if search_type_plugin in self.discovered_plugins:
                context, solr_query = self.discovered_plugins[search_type_plugin].pre_mlt_solr_query(
                    context,
                    solr_query,
                    request,
                    self.searches[search_type], self.fields[search_type],
                    self.codes_fr[search_type] if lang == 'fr' else self.codes_en[search_type],
                    record_id)

            # Query Solr
            solr_response = solr.query(core_name, solr_query)

            if search_type_plugin in self.discovered_plugins:
                context, solr_query = self.discovered_plugins[search_type_plugin].post_mlt_solr_query(
                    context,
                    solr_response,
                    solr_query,
                    request,
                    self.searches[search_type], self.fields[search_type],
                    self.codes_fr[search_type] if lang == 'fr' else self.codes_en[search_type],
                    record_id)

            context['docs'] = solr_response.data['moreLikeThis'][record_id]['docs']
            context['original_doc'] = solr_response.docs[0]

            if search_type_plugin in self.discovered_plugins and self.discovered_plugins[search_type_plugin].plugin_api_version() >= 1.1:
                context, template = self.discovered_plugins[search_type_plugin].pre_render_search(context,
                                                                                                  self.searches[search_type].page_template,
                                                                                                  request,
                                                                                                  lang,
                                                                                                  self.searches[search_type],
                                                                                                  self.fields[search_type],
                                                                                                  self.codes_fr[search_type] if lang == 'fr' else self.codes_en[search_type])

            if 'prev_record' in request.session:
                context['back_to_url'] = request.session['prev_record']
            if 'prev_search' in request.session:
                context['back_to_url'] = request.session['prev_search']
            return render(request, self.searches[search_type].more_like_this_template , context)

        else:
            return render(request, '404.html', get_error_context(search_type, lang))


class HomeView(SearchView):

    def __init__(self):
        super().__init__()

    def get(self, request: HttpRequest, lang='en'):
        lang = request.LANGUAGE_CODE
        context = {
            "language": lang,
            "cdts_version": settings.CDTS_VERSION,
            "dcterms_lang": 'fra' if lang == 'fr' else 'eng',
            "ADOBE_ANALYTICS_URL": settings.ADOBE_ANALYTICS_URL,
            "GOOGLE_ANALYTICS_GTM_ID": settings.GOOGLE_ANALYTICS_GTM_ID,
            "GOOGLE_ANALYTICS_PROPERTY_ID": settings.GOOGLE_ANALYTICS_PROPERTY_ID,
            "query_path": request.META["QUERY_STRING"],
            "path_info": request.META["PATH_INFO"],
            'parent_path': request.META["PATH_INFO"],
            "url_uses_path": settings.SEARCH_LANG_USE_PATH,
            "site_host_en": settings.OPEN_DATA_HOST_EN,
            "site_host_fr": settings.OPEN_DATA_HOST_FR,
            "footer_snippet": "search_snippets/default_footer.html",
            "breadcrumb_snippet": "search_snippets/default_breadcrumb.html",
            "info_message_snippet": "search_snippets/default_info_message.html",
            "about_message_snippet": "search_snippets/default_about_message.html",
            "search_list": list(self.searches.values())
        }

        return render(request, "homepage.html", context)


class DefaultView(View):

    def get(self, request: HttpRequest):
        if settings.SEARCH_LANG_USE_PATH:
            return redirect('/search/{0}/'.format(request.LANGUAGE_CODE) )
        else:
            return redirect('/search/')
