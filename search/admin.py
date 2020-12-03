from django.contrib import admin
from import_export import resources
from import_export.admin import ImportExportModelAdmin
from .models import Search, Field, Code


class SearchResource(resources.ModelResource):

    class Meta:
        model = Search


class SearchAdmin(ImportExportModelAdmin):
    resource_class = SearchResource
    list_display = ['search_id', 'label_en', 'solr_core_name']


class FieldResource(resources.ModelResource):

    class Meta:
        model = Field


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


class FieldAdmin(ImportExportModelAdmin):
    resource_class = FieldResource
    list_display = ('field_id', 'is_search_facet', 'is_default_display', 'search_id', 'solr_field_type')
    actions = [make_facet_field, make_default_display_field, clear_facet_field, clear_default_display_field]
    search_fields = ['field_id', 'is_search_facet']
    list_filter = ['search_id']


class CodeResource(resources.ModelResource):

    class Meta:
        model = Code


class CodeAdmin(ImportExportModelAdmin):
    resource_class = CodeResource
    list_display = ['code_id', 'field_id', 'label_en']
    search_fields = ['code_id', 'label_en', 'label_fr']
    list_filter = [('field_id', admin.RelatedOnlyFieldListFilter)]


admin.site.register(Search, SearchAdmin)
admin.site.register(Field, FieldAdmin)
admin.site.register(Code, CodeAdmin)
