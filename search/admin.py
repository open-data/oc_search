from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html
from .models import Search, Field, Code, ChronologicCode, Setting, Event

# -- Searches ---


class SearchAdmin(admin.ModelAdmin):

    change_list_template = 'smuggler/change_list.html'
    list_display = ['search_id', 'label_en', 'solr_core_name']
    fieldsets = (
        (None, {'fields': ('search_id', 'solr_core_name', 'solr_default_op', 'solr_debugging', 'id_fields', 'alt_formats', 'label_en', 'label_fr',
                           'dataset_download_text_en', 'dataset_download_url_en',
                           'dataset_download_text_fr', 'dataset_download_url_fr', 'desc_en', 'desc_fr',
                           'about_message_en', 'about_message_fr', 'search_alias_en', 'search_alias_fr',
                           'imported_on')}),
        ('Disabled', {'fields': ('is_disabled', 'disabled_message_en', 'disabled_message_fr')}),
        ('Results', {'fields': ('results_page_size', 'results_sort_order_en', 'results_sort_order_fr',
                                'results_sort_order_display_en', 'results_sort_order_display_fr',
                                'results_sort_default_en','results_sort_default_fr',
                                'json_response', 'raw_solr_response')}),
        ('Templates', {'fields': ('page_template', 'record_template', 'breadcrumb_snippet', 'footer_snippet',
                                  'info_message_snippet', 'about_message_snippet', 'header_js_snippet',
                                  'header_css_snippet', 'body_js_snippet', 'search_item_snippet',
                                  'record_detail_snippet', 'record_breadcrumb_snippet',
                                  'main_content_body_top_snippet', 'more_like_this_template')}),
        ('More-like-this', {'fields': ('mlt_enabled', 'mlt_items')})
    )

    # -- Fields ---


def make_facet_field(modeladmn, request, queryset):
    queryset.update(is_search_facet=True)


make_facet_field.short_description = 'Mark selected fields as search facets'


def clear_facet_field(modeladmn, request, queryset):
    queryset.update(is_search_facet=False)


clear_facet_field.short_description = 'Clear selected fields as search facets'


def make_default_display_field(modeladmn, request, queryset):
    queryset.update(is_default_display=True)


make_default_display_field.short_description = 'Mark selected fields for default search results'


def clear_default_display_field(modeladmn, request, queryset):
    queryset.update(is_default_display=False)


clear_default_display_field.short_description = 'Clear selected fields for default search results'


def make_currency_field(modeladmn, request, queryset):
    queryset.update(solr_field_is_currency=True, solr_field_type='pfloat')


make_currency_field.short_description = 'Mark selected fields as currency, float'


class FieldAdmin(admin.ModelAdmin):

    change_list_template = 'smuggler/change_list.html'
    list_display = ('field_id', 'is_search_facet', 'is_default_display', 'search_id', 'format_name', 'solr_field_is_coded', 'solr_field_type', 'solr_field_lang')
    actions = [make_facet_field, make_default_display_field, clear_facet_field, clear_default_display_field, make_currency_field]
    search_fields = ['field_id', 'is_search_facet']
    list_filter = ['search_id']
    fieldsets = (
        (None, {'fields': ('field_id', 'search_id', 'label_en', 'label_fr', 'format_name', 'solr_field_type', 'solr_field_lang', 'solr_field_export', 'solr_field_is_coded', 'solr_extra_fields')}),
        ('Solr Attributes', {'fields': ('solr_field_stored', 'solr_field_indexed', 'solr_field_multivalued', 'solr_field_multivalue_delimeter','solr_field_is_currency')}),
        ('Facets', {'fields': ('is_search_facet', 'solr_facet_sort', 'solr_facet_limit', 'solr_facet_snippet', 'solr_facet_display_reversed', 'solr_facet_display_order')}),
        ('Advanced', {'fields': ('alt_format', 'is_default_display', 'default_export_value')}),
        ('Search Default', {'fields': ('is_default_year', 'is_default_month')}),
    )

# -- Codes ---


class CodeAdmin(admin.ModelAdmin):

    change_list_template = 'smuggler/change_list.html'
    list_display = ['code_id', 'field_fid', 'label_en', 'label_fr']
    search_fields = ['code_id', 'label_en', 'label_fr']
    list_filter = [('field_fid', admin.RelatedOnlyFieldListFilter)]
    save_as = True

# -- ChronologicCode ---


class ChronologicCodesAdmin(admin.ModelAdmin):

    change_list_template = 'smuggler/change_list.html'
    list_display = ['label', 'codes', 'label_en', 'start_date', 'end_date']
    search_fields = ['code_cid__code_id', 'label', 'label_en', 'label_fr']
    list_filter = [('code_cid', admin.RelatedOnlyFieldListFilter)]
    save_as = True

    def codes(self, obj):
        return format_html('<a href="{0}?q={1}">{2}</a>', reverse('admin:search_chronologiccode_changelist'), obj.code_cid.code_id, obj.code_cid.code_id)


class SettingsAdmin(admin.ModelAdmin):

    list_display = ['key', 'value']
    save_as = True


class EventAdmin(admin.ModelAdmin):

    list_display = ['search_id', 'component_id', 'category', 'title', 'event_timestamp']
    list_filter = ['search_id', 'category', 'component_id']
    search_fields = ['search_id', 'title', 'category']


admin.site.register(Search, SearchAdmin)
admin.site.register(Field, FieldAdmin)
admin.site.register(Code, CodeAdmin)
admin.site.register(ChronologicCode, ChronologicCodesAdmin)
admin.site.register(Setting, SettingsAdmin)
admin.site.register(Event, EventAdmin)

