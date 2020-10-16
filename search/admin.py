from django.contrib import admin
from import_export import resources
from import_export.admin import ImportExportModelAdmin
from .models import Search, Field, Code, Organizations


class SearchResource(resources.ModelResource):

    class Meta:
        model = Search


class SearchAdmin(ImportExportModelAdmin):
    resource_class = SearchResource


class FieldResource(resources.ModelResource):

    class Meta:
        model = Field


class FieldAdmin(ImportExportModelAdmin):
    resource_class = FieldResource


class CodeResource(resources.ModelResource):

    class Meta:
        model = Code


class CodeAdmin(ImportExportModelAdmin):
    resource_class = CodeResource


class OrganizationResource(resources.ModelResource):

    class Meta:
        model = Organizations


class OrganizationAdmin(ImportExportModelAdmin):
    resource_class = OrganizationResource

# Register your models here.


admin.site.register(Search, SearchAdmin)
admin.site.register(Field, FieldAdmin)
admin.site.register(Code, CodeAdmin)
admin.site.register(Organizations, OrganizationAdmin)
