
from django.conf import settings
from django.http import HttpRequest
from django.views.generic import View
from django.shortcuts import render
import re
from SolrClient2 import SolrClient, SolrResponse
from SolrClient2.exceptions import ConnectionError, SolrError


class RampView(View):

    def __init__(self):
        super().__init__()

    def uuid_pattern(self):
        return re.compile(
            (
                    '[a-f0-9]{8}-' +
                    '[a-f0-9]{4}-' +
                    '[a-f0-9]{4}-' +
                    '[a-f0-9]{4}-' +
                    '[a-f0-9]{12}$'
            ),
            re.IGNORECASE
        )

    def get(self, request: HttpRequest, lang='en', keys=''):
        lang = request.LANGUAGE_CODE
        uuid_regex = self.uuid_pattern()
        uuids = keys.split(',')
        valid_uuids = []
        for uuid in uuids:
            if uuid_regex.match(uuid):
                valid_uuids.append(uuid)
        keys = ",".join(valid_uuids)
        ga_keys = "|".join([f"id:{x}" for x in valid_uuids])

        # Get the titles

        solr = SolrClient(settings.OPEN_DATA_SOLR_SERVER_URL)
        q_text = " OR id:".join(valid_uuids)
        q_text = "id:" + q_text
        solr_query = {'q': q_text, 'defType': 'edismax', 'sow': True}
        solr_response = solr.query(settings.OPEN_DATA_CORE, solr_query)
        titles = {}
        title_field = 'title_translated_fr' if lang == "fr" else 'title_translated_en'
        for doc in solr_response.docs:
            titles[doc['id']] = doc[title_field]

        context = {
            "language": lang,
            "keys": keys,
            "titles": titles,
            "open_data_url": settings.OPEN_DATA_BASE_URL_FR if lang == "fr" else settings.OPEN_DATA_BASE_URL_EN,
            "rcs_config": 'ramp/config.rcs.fr-CA.json' if lang == "fr" else 'ramp/config.rcs.en-CA.json',
            "toggle_url": self._get_toggle(lang, keys),
            "show_alert_info": settings.RAMP_SHOW_ALERT_INFO if hasattr(settings, "RAMP_SHOW_ALERT_INFO") else False,
            "ADOBE_ANALYTICS_URL": settings.ADOBE_ANALYTICS_URL,
            "GOOGLE_ANALYTICS_GTM_ID": settings.GOOGLE_ANALYTICS_GTM_ID,
            "GOOGLE_ANALYTICS_PROPERTY_ID": settings.GOOGLE_ANALYTICS_PROPERTY_ID,
            "GOOGLE_ANALYTICS_GA4_ID": settings.GOOGLE_ANALYTICS_GA4_ID,
        }

        # Get the configured RAMP URLs

        ramp_urls = {
            "range_slider_css": settings.RAMP_RANGE_SLIDER_CSS_URL,
            "range_slider_js": settings.RAMP_RANGE_SLIDER_JS_URL,
            "chart_css": settings.RAMP_CHART_CSS_URL,
            "chart_js": settings.RAMP_CHART_JS_URL,
            "rv_css": settings.RAMP_STYLE_CSS_URL,
            "rv_main_js": settings.RAMP_MAIN_JS_URL,
            "legacy_api": settings.RAMP_LEGACY_API_JS_URL,
        }
        context.update(ramp_urls)

        if hasattr(settings, "RAMP_GA_RESOURCE_EN"):
            context['ramp_ga_resource_en'] = f"{settings.RAMP_GA_RESOURCE_EN}?filters={ga_keys}"
            context['ramp_ga_resource_fr'] = f"{settings.RAMP_GA_RESOURCE_FR}?filters={ga_keys}"

        return render(request, 'ramp.html', context)

    def _get_toggle(self, lang, keys):
        if lang == 'fr':
            toggle_url = '/openmap/en/{0}'.format(keys) if settings.SEARCH_LANG_USE_PATH else "https://{0}/openmap/{1}".format(settings.SEARCH_EN_HOSTNAME, keys)
        else:
            toggle_url = '/carteouverte/fr/{0}'.format(keys) if settings.SEARCH_LANG_USE_PATH else "https://{0}/carteouverte/{1}".format(settings.SEARCH_FR_HOSTNAME, keys)
        return toggle_url
