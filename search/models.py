from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils.translation import gettext_lazy as _
from datetime import datetime, timezone, MINYEAR, MAXYEAR


class Search(models.Model):
    """
    Stores metadata about a Search application, related to :model: 'search.Field' and :model: 'search.Code'.
    """
    search_id = models.CharField(primary_key=True, max_length=32, unique=True, verbose_name="Search ID")
    label_en = models.CharField(blank=False, max_length=132, verbose_name="Search Title (English)")
    label_fr = models.CharField(blank=False, max_length=132, verbose_name="Search Title (Françias)")
    desc_en = models.TextField(blank=True, default="", help_text="Brief description of the search (in English)",
                               verbose_name="Description (English)")
    desc_fr = models.TextField(blank=True, default="", help_text="Brief description of the search (en Français)",
                               verbose_name="Description (Françias)")
    about_message_en = models.TextField(blank=True, default="", help_text="Informational message displayed at the top "
                                                                          "of the search page. Uses Markdown (in English)",
                                        verbose_name="About the search message (English)")
    about_message_fr = models.TextField(blank=True, default="", help_text="Informational message displayed at the top "
                                                                          "of the search page. Uses Markdown (en Français)",
                                        verbose_name="About the search message (Français)")
    search_alias_en = models.CharField(blank=True, max_length=64, default="", help_text="Optional search ID alias (in English)",
                                       verbose_name="Search alias (English)")
    search_alias_fr = models.CharField(blank=True, max_length=64, default="", help_text="Optional search ID alias (en Français)",
                                       verbose_name="Search alias (Français)")
    is_disabled = models.BooleanField(blank=False, default=False, verbose_name="Search is disabled",
                                      help_text="Disable the search. Useful for applying code updates.")
    disabled_message_en = models.TextField(blank=False, default="This search is currently unavailable for maintenance",
                                           verbose_name="Disabled Search Message - English")
    disabled_message_fr = models.TextField(blank=False, default="Ce service de recherche est actuellement indisponible pour cause de maintenance.",
                                           verbose_name="Disabled Search Message - French")
    imported_on = models.DateTimeField(blank=True, null=True, help_text="If an import script is used to create the "
                                                                        "search, this is the last date it was run.",
                                       verbose_name="Last imported on")
    solr_core_name = models.CharField(blank=False, default="solr_core", max_length=64, verbose_name="Solr Core name")
    solr_default_op = models.CharField(blank=False, default="AND", max_length=3,
                                       help_text="Default Solr operator - choices are 'AND' and 'OR'")
    solr_debugging = models.BooleanField(blank=False, default=False, help_text="Log Solr debugging information, Should be off in production")
    results_page_size = models.IntegerField(blank=False, default=10, verbose_name="No. of Search Results Per Page")
    results_sort_order_en = models.CharField(blank=False, max_length=132, default="score desc", verbose_name="Sort-by Categories (English)")
    results_sort_order_fr = models.CharField(blank=False, max_length=132, default="score desc", verbose_name="Sort-by Categories (Français)")
    results_sort_order_display_en = models.CharField(blank=False, max_length=200, default="Best Match", verbose_name="Sort-by Category Labels (English)")
    results_sort_order_display_fr = models.CharField(blank=False, max_length=200, default="Pertinence", verbose_name="Sort-by Category Labels (Français)")
    results_sort_default_en = models.CharField(blank=False, max_length=132, default="score desc", verbose_name="Default Sort-by Category used when no search terms provided (English)")
    results_sort_default_fr = models.CharField(blank=False, max_length=132, default="score desc", verbose_name="Default Sort-by Category used when no search terms provided (Français)")
    page_template = models.CharField(blank=False, default="search.html", max_length=132, verbose_name="Search Page Template")
    record_template = models.CharField(blank=False, default="record.html", max_length=132, verbose_name="Record Page Template")
    breadcrumb_snippet = models.CharField(blank=False, default="search_snippets/default_breadcrumb.html", max_length=132,
                                          verbose_name="Breadcrumb Snippet Path")
    footer_snippet = models.CharField(blank=False, default="search_snippets/default_footer.html", max_length=132,
                                      verbose_name="Footer Snippet Path")
    info_message_snippet = models.CharField(blank=False, default="search_snippets/default_info_message.html", max_length=250,
                                            verbose_name="Search Information Message Snippet Path")
    about_message_snippet = models.CharField(blank=False, default="search_snippets/default_about_message.html", max_length=250,
                                             verbose_name="About Search Message Snippet Path")
    header_js_snippet = models.CharField(blank=True, default="search_snippets/default_header.js", max_length=250,
                                         verbose_name="Custom Javascript for Header file path")
    header_css_snippet = models.CharField(blank=True, default="search_snippets/default_header.css", max_length=250,
                                          verbose_name="Custom CSS file path")
    body_js_snippet = models.CharField(blank=True, default="", max_length=250, verbose_name="Custom Javascript for Body file path")
    search_item_snippet = models.CharField(blank=True, default="search_snippets/default_search_item.html", max_length=250,
                                           verbose_name="Custom Search Item snippet",
                                           help_text="Recommended custom snippet to used to display individual search result records on the search page")
    record_detail_snippet = models.CharField(blank=True, default="", max_length=250, verbose_name="Custom Record snippet",
                                             help_text="Optional custom snippet to used to display individual records")
    record_breadcrumb_snippet = models.CharField(blank=True, default="search_snippets/default_record_breadcrumb.html", max_length=250,
                                                 verbose_name="Custom Record Breadcrumb snippet",
                                                 help_text="Optional custom breadcrumb snippet for the records page")
    dataset_download_url_en = models.URLField(verbose_name="Download Dataset URL (English)", default="https://open.canada.ca")
    dataset_download_url_fr = models.URLField(verbose_name="Download Dataset URL (French)", default="https://ouvert.canada.ca")
    dataset_download_text_en = models.CharField(blank=True, default="Download Complete Dataset", max_length=100, verbose_name="Download Dataset Link Text (English)")
    dataset_download_text_fr = models.CharField(blank=True, default="Télécharger le jeu de données complet", max_length=100, verbose_name="Download Dataset Link Text (Frrançais)")
    id_fields = models.CharField(blank=True, default="", max_length=132, help_text="Comma separated list of fields that form the Solr primiary key",
                                 verbose_name="Unique ID Definition")
    alt_formats = models.CharField(blank=True, default="", max_length=132, verbose_name="Alternate Record Formats",
                                   help_text="Comma separated list of alternate record formst, for example NTR (Nothing to Report)")
    mlt_enabled = models.BooleanField(blank=True, default=False, verbose_name="Enable More-Like-This",
                                      help_text="Indicate if the this search will be using Solr's 'More Like This' functionality")
    mlt_items = models.IntegerField(blank=True, default=10, verbose_name="No. Items returned for More-Like-This",
                                    help_text="Number of itemsto show on the More-Like-This search results page. Default is 10")

    def __str__(self):
        return '%s (%s)' % (self.label_en, self.search_id)


class Field(models.Model):
    """
    Stores metadata about individual fields in each search application, related to :model: 'search.Search' and :model: 'search.Code'.
    """

    SOLR_FIELD_TYPES = [
        ('search_text_en', 'Search Text English'),
        ('search_text_fr', 'Search Text French'),
        ('text_general', 'Generic Text'),
        ('pint', 'Integer'),
        ('string', 'String'),
        ('pdate', 'Date'),
        ('pfloat', 'Float/Currency')
    ]
    SOLR_FIELD_LANGS = [
        ('en', 'English'),
        ('fr', 'Français'),
        ('bi', 'Bilingual/Bilangue')
    ]

    id = models.AutoField(primary_key=True)
    field_id = models.CharField(blank=False, max_length=64, verbose_name="Unique Field Identifier")
    search_id = models.ForeignKey(Search, on_delete=models.CASCADE)
    format_name = models.CharField(default='', max_length=132, verbose_name="Format Name")
    label_en = models.CharField(blank=False, max_length=132, verbose_name="Engliah Label")
    label_fr = models.CharField(blank=False, max_length=132, verbose_name="French Label")
    solr_field_type = models.CharField(blank=False, choices=SOLR_FIELD_TYPES, default='string', max_length=20,
                                       verbose_name="Solr Field Type")
    solr_field_lang = models.CharField(blank=False, choices=SOLR_FIELD_LANGS, default='bi', max_length=2,
                                       verbose_name='Language Type')
    solr_field_export = models.CharField(blank=True, max_length=65, verbose_name='Copy field for export',
                                         default='',
                                         help_text='Name of a string field that will be created to hold export values. '
                                                   'Note that export fields are automatically created for '
                                                   'Interger and Date fields. *Note* Add manually for multi-valued string fields.')
    solr_field_is_coded = models.BooleanField(blank=False, default=False, verbose_name="Contains Code Values",
                                              help_text="The values in this field are code values whose values are in the Code tabke")
    solr_extra_fields = models.CharField(blank=True, default="", verbose_name="Extra Solr Copyfields", max_length=132,
                                         help_text="A comma separated list of auto-generated Solr copy-fields that are populated by this field")

    solr_field_stored = models.BooleanField(blank=False, default=True, verbose_name="Field is stored on Solr")
    solr_field_indexed = models.BooleanField(blank=False, default=True, verbose_name="Field is indexed on Solr")
    solr_field_multivalued = models.BooleanField(blank=False, default=False, verbose_name="Field supports multiple values")
    solr_field_multivalue_delimeter = models.CharField(blank=True, default=",", max_length=1, verbose_name="Multivalue Field Delimeter",
                                                       help_text="Delimeter character for use with multi-value fields")
    solr_field_is_currency = models.BooleanField(blank=False, default=False, verbose_name="Is a monetary field")
    is_search_facet = models.BooleanField(blank=False, default=False, help_text="Is a search facet field, should never have blank values",
                                          verbose_name="Search Facet field")
    solr_facet_sort = models.CharField(blank=True, max_length=5,
                                       choices=[('count', 'By highest count'), ('index', 'By value A-Z'), ('label', 'By Label A-Z (for codes)')],
                                       default='count', verbose_name="Sort Order",
                                       help_text='Select facet sort order when field is used as a facet field')
    solr_facet_limit = models.IntegerField(blank=True, default=100, help_text='Maximum number of facet values to return',
                                           validators=[MinValueValidator(-1), MaxValueValidator(250)],
                                           verbose_name="Facet Item Maximum")
    solr_facet_snippet = models.CharField(blank=True, default="", max_length=250, verbose_name="Custom facet snippet",
                                          help_text="Optional custom snippet to use if the field is a facet filter")
    solr_facet_display_reversed = models.BooleanField(blank=False, default=False, verbose_name="Display Facet in Reversed Orderd")
    solr_facet_display_order = models.IntegerField(blank=True, default=0, verbose_name="Facet Display Order",
                                                   help_text="Ordered place in which to display the facets on the page, if this field is a facet")
    alt_format = models.CharField(blank=True, default='', max_length=30, verbose_name="Alternate Record Type",
                                  help_text="This field is part of an alternate format (e.g. Nothing To Report). Use 'ALL' if the field appears in all formats")
    is_default_display = models.BooleanField(blank=False, default=False, verbose_name="Default search item field",
                                             help_text="Include field in default search item template")
    default_export_value = models.CharField(blank=True, default='str|-', verbose_name="Default value for empty fields", max_length=132,
                                            help_text="A default value used for empty or blank values. Examples: str:-, int:0, date:2000-01-01T00:00:00Z. ")
    is_default_year = models.BooleanField(blank=False, default=False, verbose_name="Field is the search's default year field")
    is_default_month = models.BooleanField(blank=False, default=False, verbose_name="Field is the search's default month field")

    def __str__(self):
        return '%s - (%s) %s' % (self.label_en, self.field_id, self.search_id)

    class Meta:
        unique_together = (('field_id', 'search_id'),)


class Code(models.Model):
    """
    Stores metadata about individual Codes associated with a particular field in a search application, related to :model: 'search.Search' and :model: 'search.Field'.
    Note that codes are _not_ shared between fields or searches
    """
    class LookupTests(models.TextChoices):

        EQUAL = 'EQ', _('Equal')
        NOTEQUAL = 'NE', _('Not Equal')
        LESSTHAN = 'LT', _('Less Than')
        GREATERTHAN = 'GT', _('Greater Than')
        LESSTHANEQUAL = 'LE', _('Less Than or Equal')
        GREATERTHANEQUAL = 'GE', _('Greater Than or Equal')

    id = models.AutoField(primary_key=True)
    code_id = models.CharField(blank=False, max_length=32, verbose_name="Unique code Identifier")
    field_id = models.ForeignKey(Field, on_delete=models.CASCADE)
    label_en = models.CharField(blank=False, max_length=512, verbose_name="English Code Value")
    label_fr = models.CharField(blank=False, max_length=2512, verbose_name="French Code Value")
    lookup_codes_default = models.CharField(blank=True, default="", max_length=512, verbose_name="Default Lookup Codes")
    lookup_codes_conditional = models.CharField(blank=True, default="", max_length=512, verbose_name="Conditional Lookup Codes")
    lookup_date_field = models.CharField(blank=True, default="", max_length=64, verbose_name="Date field to be evaluated")
    lookup_date = models.DateTimeField(blank=True, verbose_name="Lookup Date",
                                       default=datetime(MINYEAR, 1, 1, 0, 0, 0, 0, timezone.utc))
    lookup_test = models.CharField(blank=True, default="", max_length=2, choices=LookupTests.choices, verbose_name="Lookup Test")
    is_lookup = models.BooleanField(blank=False, default=False, verbose_name="Is a Choice Lookup Code")

    def __str__(self):
        return '%s - (%s) %s' % (self.label_en, self.code_id, self.field_id)

    class Meta:
        unique_together = (('field_id', 'code_id'),)


class ChronologicCode(models.Model):
    """
    Codes with a date range.
    """
    id = models.AutoField(primary_key=True)
    code_id = models.ForeignKey(Code, on_delete=models.CASCADE)
    label = models.CharField(blank=False, max_length=512, verbose_name="Unique code Identifier")
    label_en = models.CharField(blank=False, max_length=512, verbose_name="English Code Value")
    label_fr = models.CharField(blank=False, max_length=512, verbose_name="French Code Value")
    start_date = models.DateTimeField(blank=False, verbose_name="Start Date", default=datetime(MINYEAR, 1, 1, 0, 0, 0, 0, timezone.utc))
    end_date = models.DateTimeField(blank=False, verbose_name="End Date", default=datetime(2999, 12, 31, 23, 59, 59, 999999, timezone.utc))

    class Meta:
        unique_together = (('code_id', 'start_date'),)



