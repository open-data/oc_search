# coding=utf-8


from babel.dates import format_date
from babel.numbers import format_currency, format_decimal, parse_decimal
import bleach
from datetime import datetime
from django import template
from django.conf import settings
from django.utils.translation import gettext
from dateutil import parser
import json
import markdown2
import re


register = template.Library()


@register.filter('SwapLangCode', autoescape=True)
def other_lang_code(value):
    if str(value).lower() == 'en':
        return 'fr'
    elif str(value).lower() == 'fr':
        return 'en'
    else:
        return ''


@register.filter('SwapLangName', autoescape=True)
def other_lang(value):
    if str(value) == 'en':
        return 'Français'
    elif str(value) == 'fr':
        return 'English'
    else:
        return ''

@register.filter('EmptyFacetMessage', autoescape=True)
def search_facet_is_empty_message(value):
    msg = ''
    if type(value) is dict:
        c = 0
        for k,v in value.items():
            c = c + v
        if c == 0:
            msg = gettext("There are no filters for this search")
    return msg


@register.filter('ToMonth', autoescape=True)
def to_month(value):
    months = [
        'January',
        'February',
        'March',
        'April',
        'May',
        'June',
        'July',
        'August',
        'September',
        'October',
        'November',
        'December'
    ]
    month_int = 0
    try:
        month_int = int(value)
    except ValueError:
        pass
    if month_int < 1 or month_int > 12:
        return ''
    else:
        return gettext(months[month_int - 1])


@register.filter('isoDateTimeToDate')
def iso_date_time_to_date(value):
    my_date = parser.parse(value)
    return my_date.strftime("%Y-%m-%d")


@register.filter('service_standards_en')
def si_std_json_to_html_en(value):
    std_obj = json.loads(value)
    return "<strong>Standard: {0}</strong><br>{1}<br>".format(
        std_obj['service_std_id'],
        std_obj['service_std_en'])


@register.filter('service_standards_fr')
def si_std_json_to_html_fr(value):
    std_obj = json.loads(value)
    return "<strong>Norme : {0}</strong><br>{1}<br>".format(
        std_obj['service_std_id'],
        std_obj['service_std_fr'])


@register.filter('nap_status')
def nap_status_alert(value):
    if value in ('Not started', 'Non commencé'):
        return '<span class="label label-default">{0}</span>'.format(value)
    elif value in ('Limited progress', 'Progrès limité'):
        return '<span class="label label-warning">{0}</span>'.format(value)
    elif value in ('Substantial progress', 'Progrès important'):
        return '<span class="label label-info">{0}</span>'.format(value)
    elif value in ('Complete', 'Réalisé'):
        return '<span class="label label-success">{0}</span>'.format(value)
    else:
        return value


@register.filter('friendly_date_en')
def human_friendly_date_en(value: str):
    if len(value) == 10:
        my_date = parser.parse(value)
        return format_date(my_date, 'medium', locale='en_CA')
    else:
        return ""


@register.filter('friendly_date_fr')
def human_friendly_date_fr(value: str):
    if len(value) == 10:
        my_date = parser.parse(value)
        return format_date(my_date, 'medium', locale='fr_CA')
    else:
        return ""


@register.filter('trim_left')
def trim_left(value: str, arg: int):
    if len(value) < arg:
        return value
    else:
        return value[arg:]


@register.filter('friendly_reporting_period')
def friendly_reporting_period(value: str):
    if len(value.split('-')) == 3:
        rp = value.split('-')
        return "{2} {0}-{1}".format(rp[0], rp[1], rp[2])
    else:
        return value


@register.filter('normalize_headings')
def normalize_headings(value: str):
    headings = {
        '</h4>': '</h6>',
        '<h4>': '<h6>',
        '</h3>': '</h5>',
        '<h3>': '<h5>',
        '</h2>': '</h4>',
        '<h2>': '<h4>',
        '</h1>': '</h3>',
        '<h1>': '<h3>',
    }
    for key in headings:
        if value.find(key) >= 0:
            value = value.replace(key, headings[key])
    return value


@register.filter('markdown_filter')
def markdown_filter(text):
    text = markdown2.markdown(text, extras=settings.MARKDOWN_FILTER_EXTRAS)
    attrs = {**bleach.sanitizer.ALLOWED_ATTRIBUTES, **settings.MARKDOWN_FILTER_ALLOWED_ATTRIBUTES}
    html = bleach.clean(text, tags=settings.MARKDOWN_FILTER_WHITELIST_TAGS,
                        attributes=attrs)
    return bleach.linkify(html)


@register.filter('strip_paragraph')
def strip_paragraph(text):
    return re.sub("(^<P>|</P>$)", "", text, flags=re.IGNORECASE)


@register.filter('url_part_unescape')
def url_part_unescape_filter(value: str):
    return ''.join(
        bytes.fromhex(s).decode('utf-8') if i % 2 else s
        for i, s in enumerate(value.split('_'))
    )


@register.filter('strip_whitespace')
def strip_whitespace(text):
    return str(text).strip()


@register.filter('get_dict_value')
def get_dict_value(dict_data, key):
    if key:
        return dict_data.get(key)


@register.filter('unspecified')
def unspecified(value: str, lang: str):
    if value == '-':
        if lang == 'fr':
            return 'Type non spécifié'
        else:
            return 'Unspecified'
    else:
        return value


@register.filter('unspecified_date')
def unspecified_date(value: datetime, lang: str):
    if value == datetime(1, 1, 1, 0, 0):
        if lang == 'fr':
            return 'Type non spécifié'
        else:
            return 'Unspecified'
    else:
        return value


@register.filter('friendly_currency')
def friendly_currency(value: int, currency_locale_str: str):
    currency_locale = currency_locale_str.split(",")
    return format_currency(value, currency=currency_locale[0], locale=currency_locale[1])


@register.filter('is_list')
def is_list(value):
    if type(value) == list:
        return True
    else:
        return False


@register.filter(name='split')
def split(value, key):
    if type(value) == str:
        return value.split(key)
    elif type(value) == list:
        return value
    else:
        return [value]


@register.filter(name='add_str')
def add_str(value: str, arg1: str):
    return value + arg1



@register.filter('replace_pageno')
def trim_left(value: str, arg: int):
    return value.replace("__page__", str(arg))
    

@register.filter('ds_status_label')
def ds_status_label(value: str):
    if value in ['In Progess', 'En cours']:
        return 'label label-primary'
    elif value in ['Behind']:
        return 'label label-warning'
    elif value in ['Completed', 'Terminé']:
        return 'label label-success'
    elif value in ['Paused', 'En pause']:
        return 'label label-info'
    else:
        return 'label label-default'


@register.filter('intformat')
def int_format(value: int, formatstr: str):
    return formatstr.format(value)

