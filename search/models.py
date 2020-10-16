from django.db import models


class Organizations(models.Model):
    name = models.CharField(null=False, primary_key=True, max_length=32)
    title_en = models.CharField(null=False, max_length=132)
    title_fr = models.CharField(null=False, max_length=132)
    id = models.UUIDField(null=True)


class Search(models.Model):
    search_id = models.CharField(primary_key=True, max_length=32, unique=True)
    label_en = models.CharField(blank=False, max_length=132)
    label_fr = models.CharField(blank=False, max_length=132)
    desc_en = models.TextField(blank=True)
    desc_fr = models.TextField(blank=True)
    imported_on = models.DateTimeField(blank=True, null=True, help_text="If an import script is used to create the "
                                                                        "search, this is the last date it was run.")
    solr_core_name = models.CharField(blank=True, max_length=64)


class Field(models.Model):

    SOLR_FIELD_TYPES = [
        ('search_text_en', 'Search Text English'),
        ('search_text_fr', 'Search Text French'),
        ('pint', 'Integer'),
        ('string', 'String'),
        ('pdate', 'Date'),
        ('pfloat', 'Float/Currency')
    ]
    SOLR_FIELD_LANG = [
        ('en', 'English'),
        ('fr', 'Français'),
        ('bi', 'Bilingual/Bilangue')
    ]
    field_id = models.CharField(primary_key=True, max_length=64)
    search_id = models.ForeignKey(Search, on_delete=models.CASCADE)
    label_en = models.CharField(blank=False, max_length=132)
    label_fr = models.CharField(blank=False, max_length=132)
    solr_field = models.CharField(blank=True, max_length=32)
    solr_field_type = models.CharField(blank=False, choices=SOLR_FIELD_TYPES, default='string', max_length=20)
    solr_field_lang = models.CharField(blank=False, choices=SOLR_FIELD_LANG, default='bi', max_length=2,
                                       verbose_name='Language Type')
    solr_field_export = models.CharField(blank=True, max_length=65, verbose_name='Copy field for export',
                                         default='',
                                         help_text='Name of a string field that will be created to hold export values. '
                                                   'Note that export fields are automatically created for '
                                                   'Interger and Date fields')
    solr_field_stored = models.BooleanField(blank=False, default=True)
    solr_field_indexed = models.BooleanField(blank=False, default=True)
    solr_field_multivalued = models.BooleanField(blank=False, default=False)
    solr_field_is_currency = models.BooleanField(blank=False, default=False)
    solr_field_is_coded = models.BooleanField(blank=False, default=False)
    csv_field_name = models.CharField(blank=True, max_length=132)
    is_ntr_field = models.BooleanField(blank=False, default=False)
    is_default_year = models.BooleanField(blank=False, default=False)
    is_default_month = models.BooleanField(blank=False, default=False)

    class Meta:
        unique_together = (('field_id', 'search_id', 'is_ntr_field'),)


class Code(models.Model):

    code_id = models.CharField(primary_key=True, max_length=32)
    field_id = models.ForeignKey(Field, on_delete=models.CASCADE)
    label_en = models.CharField(blank=False, max_length=132)
    label_fr = models.CharField(blank=False, max_length=132)

    class Meta:
        unique_together = (('field_id', 'code_id'),)
