from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator


class Search(models.Model):
    search_id = models.CharField(primary_key=True, max_length=32, unique=True)
    label_en = models.CharField(blank=False, max_length=132)
    label_fr = models.CharField(blank=False, max_length=132)
    desc_en = models.TextField(blank=True, default="")
    desc_fr = models.TextField(blank=True, default="")
    imported_on = models.DateTimeField(blank=True, null=True, help_text="If an import script is used to create the "
                                                                        "search, this is the last date it was run.")
    solr_core_name = models.CharField(blank=False, default="solr_core", max_length=64)
    results_page_size = models.IntegerField(blank=False, default=10)
    results_sort_order = models.CharField(blank=False, max_length=132, default="score desc")
    results_sort_order_display_en = models.CharField(blank=False, max_length=200, default="Best Match")
    results_sort_order_display_fr = models.CharField(blank=False, max_length=200, default="Pertinence")
    page_template = models.CharField(blank=False, default="search.html", max_length=132)
    breadcrumb_snippet = models.CharField(blank=False, default="search_snippets/default_breadcrumb.html", max_length=132)
    footer_snippet = models.CharField(blank=False, default="search_snippets/default_footer.html", max_length=132)
    info_message_snippet = models.CharField(blank=False, default="search_snippets/default_info_message.html", max_length=250)
    about_message_snippet = models.CharField(blank=False, default="search_snippets/default_about_message.html", max_length=250)
    header_js_snippet = models.CharField(blank=True, default="search_snippets/default_header.js", max_length=250)
    header_css_snippet = models.CharField(blank=True, default="search_snippets/default_header.css", max_length=250)
    body_js_snippet = models.CharField(blank=True, default="", max_length=250)
    search_item_snippet = models.CharField(blank=True, default="search_snippets/default_search_item.html", max_length=250, verbose_name="Custom Search Item snippet",
                                          help_text="Recommended custom snippet to used to display individual search result records on the search page")
    record_detail_snippet = models.CharField(blank=True, default="", max_length=250, verbose_name="Custom Record snippet",
                                          help_text="Optional custom snippet to used to display individual records")
    record_breadcrumb_snippet = models.CharField(blank=True, default="search_snippets/default_record_breadcrumb.html", max_length=250, verbose_name="Custom Record Breadcrumb snippet",
                                          help_text="Optional custom breadcrumb snippet for the records page")
    dataset_download_url_en = models.URLField(verbose_name="Download Dataset URL (English)", default="https://open.canada.ca")
    dataset_download_url_fr = models.URLField(verbose_name="Download Dataset URL (Fench)", default="https://ouvert.canada.ca")
    id_fields = models.CharField(blank=True, default="", max_length=132, help_text="Comma separated list of fields that form the Solr primiary key")
    alt_formats = models.CharField(blank=True, default="", max_length=132, help_text="Comma separated list of alternate record formst, for example NTR (Nothing to Report)")

    def __str__(self):
        return '%s (%s)' % (self.label_en, self.search_id)


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

    field_id = models.CharField(blank=False, max_length=64, verbose_name="Unique Field Identifier")
    search_id = models.ForeignKey(Search, on_delete=models.CASCADE)
    label_en = models.CharField(blank=False, max_length=132, verbose_name="Engliah Label")
    label_fr = models.CharField(blank=False, max_length=132, verbose_name="French Label")
    solr_field_type = models.CharField(blank=False, choices=SOLR_FIELD_TYPES, default='string', max_length=20,
                                       verbose_name="Solr Field Type")
    solr_field_lang = models.CharField(blank=False, choices=SOLR_FIELD_LANG, default='bi', max_length=2,
                                       verbose_name='Language Type')
    solr_field_export = models.CharField(blank=True, max_length=65, verbose_name='Copy field for export',
                                         default='',
                                         help_text='Name of a string field that will be created to hold export values. '
                                                   'Note that export fields are automatically created for '
                                                   'Interger and Date fields')
    solr_field_stored = models.BooleanField(blank=False, default=True, verbose_name="Field is stored on Solr")
    solr_field_indexed = models.BooleanField(blank=False, default=True, verbose_name="Field is indexed on Solr")
    solr_field_multivalued = models.BooleanField(blank=False, default=False, verbose_name="Field supports multiple values")
    solr_field_is_currency = models.BooleanField(blank=False, default=False, verbose_name="Is a monetary field")
    solr_field_is_coded = models.BooleanField(blank=False, default=False, verbose_name="Contains Code Values",
                                              help_text="The values in this field are code values whose values are in the Code tabke")
    #csv_field_name = models.CharField(blank=True, max_length=132, verbose_name="Friendly CSV export field name")
    is_default_year = models.BooleanField(blank=False, default=False, verbose_name="Field is the search's default year field")
    is_default_month = models.BooleanField(blank=False, default=False, verbose_name="Field is the search's default month field")
    is_search_facet = models.BooleanField(blank=False, default=False, help_text="Is a search facet field, should never have blank values",
                                          verbose_name="Search Facet field")
    solr_facet_sort = models.CharField(blank=True, max_length=5, choices=[
        ('count', 'By highest count'),
        ('index', 'Lexicographic order')],
                                       default='count',
                                       help_text='Select facet sort order when field is used as a facet field')
    solr_facet_limit = models.IntegerField(blank=True, default=100, help_text='Maximum number of facet values to return',
                                          validators=[MinValueValidator(-1), MaxValueValidator(250)])
    solr_facet_snippet = models.CharField(blank=True, default="", max_length=250, verbose_name="Custom facet snippet",
                                          help_text="Optional custom snippet to use if the field is a facet filter")
    solr_facet_display_reversed = models.BooleanField(blank=False, default=False, verbose_name="Display Facet in Reversed Orderd")
    solr_facet_display_order = models.IntegerField(blank=True, default=0, verbose_name="Facet Display Order",
                                                   help_text="Ordered place in which to display the facets on the page, if this field is a facet")
    solr_extra_fields = models.CharField(blank=True, default="", verbose_name="Extra Solr Copyfields", max_length=132,
                                         help_text="A comma separated list of auto-generated Solr copy-fields that are populated by this field")
    alt_format = models.CharField(blank=True, default='', max_length=30, verbose_name="Alternate Record Type",
                                  help_text="This field is part of an alternate format (e.g. Nothing To Report). Use 'ALL' if the field appears in all formats")
    is_default_display = models.BooleanField(blank=False, default=False, verbose_name="Default search item field",
                                             help_text="Include field in default search item template")
    default_export_value = models.CharField(blank=True, default='str|-', verbose_name="Default value for empty fields", max_length=132,
                                         help_text="A default value used for empty or blank values. Examples: str:-, int:0, date:2000-01-01T00:00:00Z. ")

    def __str__(self):
        return '%s (%s)' % (self.label_en, self.field_id)

    class Meta:
        unique_together = (('field_id', 'search_id'),)


class Code(models.Model):

    code_id = models.CharField(primary_key=True, max_length=32)
    field_id = models.ForeignKey(Field, on_delete=models.CASCADE)
    label_en = models.CharField(blank=False, max_length=132)
    label_fr = models.CharField(blank=False, max_length=132)

    class Meta:
        unique_together = (('field_id', 'code_id'),)
