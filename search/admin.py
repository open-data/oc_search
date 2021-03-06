from django.contrib import admin
from import_export import resources
from import_export.admin import ImportExportModelAdmin
from .models import Search, Field, Code

# -- Searches ---

class SearchResource(resources.ModelResource):

    class Meta:
        model = Search
        import_id_fields = ('search_id')
        skip_unchanged = True
        report_skipped = True


class SearchAdmin(ImportExportModelAdmin):
    resource_class = SearchResource
    list_display = ['search_id', 'label_en', 'solr_core_name']
    fieldsets = (
        (None, {'fields': ('search_id', 'solr_core_name', 'id_fields', 'alt_formats', 'label_en', 'label_fr',
                           'dataset_download_text_en', 'dataset_download_url_en',
                           'dataset_download_text_fr', 'dataset_download_url_fr', 'desc_en', 'desc_fr',
                           'about_message_en', 'about_message_fr', 'imported_on')}),
        ('Results', {'fields': ('results_page_size', 'results_sort_order_en', 'results_sort_order_fr',
                                'results_sort_order_display_en', 'results_sort_order_display_fr')}),
        ('Templates', {'fields': ('page_template', 'record_template', 'breadcrumb_snippet', 'footer_snippet',
                                  'info_message_snippet', 'about_message_snippet', 'header_js_snippet',
                                  'header_css_snippet', 'body_js_snippet', 'search_item_snippet',
                                  'record_detail_snippet', 'record_breadcrumb_snippet')}),
        ('More-like-this', {'fields': ('mlt_enabled', 'mlt_items')})
    )

    # -- Fields ---

class FieldResource(resources.ModelResource):

    class Meta:
        model = Field
        import_id_fields = ('field_id', 'search_id',)
        skip_unchanged = True
        report_skipped = True


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


class FieldAdmin(ImportExportModelAdmin):
    resource_class = FieldResource
    list_display = ('field_id', 'is_search_facet', 'is_default_display', 'search_id', 'format_name', 'solr_field_type')
    actions = [make_facet_field, make_default_display_field, clear_facet_field, clear_default_display_field, make_currency_field]
    search_fields = ['field_id', 'is_search_facet']
    list_filter = ['search_id']
    fieldsets = (
        (None, {'fields': ('field_id', 'search_id', 'label_en', 'label_fr', 'format_name', 'solr_field_type', 'solr_field_lang', 'solr_field_export', 'solr_field_is_coded', 'solr_extra_fields')}),
        ('Solr Attributes', {'fields': ('solr_field_stored', 'solr_field_indexed', 'solr_field_multivalued', 'solr_field_is_currency')}),
        ('Facets', {'fields': ('is_search_facet', 'solr_facet_sort', 'solr_facet_limit', 'solr_facet_snippet', 'solr_facet_display_reversed', 'solr_facet_display_order')}),
        ('Advanced', {'fields': ('alt_format', 'is_default_display', 'default_export_value')}),
        ('Search Default', {'fields': ('is_default_year', 'is_default_month')}),
    )

# -- Codes ---

class CodeResource(resources.ModelResource):

    class Meta:
        model = Code
        import_id_fields = ('field_id', 'code_id')
        fields = ('field_id__search_id', 'field_id__field_id', 'id', 'field_id', 'code_id', 'label_en', 'label_fr')
        skip_unchanged = True
        report_skipped = True

    def before_import_row(self, row, row_number=None, **kwargs):
        fq = Field.objects.filter(search_id_id=row['field_id__search_id']).filter(field_id=row['field_id__field_id'])
        for f in fq:
            row['field_id'] = f.id


class CodeAdmin(ImportExportModelAdmin):
    resource_class = CodeResource
    list_display = ['code_id', 'field_id', 'label_en', 'label_fr']
    search_fields = ['code_id', 'label_en', 'label_fr']
    list_filter = [('field_id', admin.RelatedOnlyFieldListFilter)]
    save_as = True


admin.site.register(Search, SearchAdmin)
admin.site.register(Field, FieldAdmin)
admin.site.register(Code, CodeAdmin)
