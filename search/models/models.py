import json

from django.db import models
from django.forms.models import model_to_dict
from django.core.validators import MinLengthValidator, MinValueValidator, MaxValueValidator
from django.utils.translation import gettext_lazy as _
from django.utils import timezone as utimezone
from datetime import datetime, timezone, MINYEAR, MAXYEAR
from inflection import parameterize


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
    more_like_this_template = models.CharField(blank=False, default="more_like_this.html", max_length=132, verbose_name="More-like-This Page Template")
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
    json_response = models.BooleanField(blank=False, default=False, verbose_name="Enable JSON format response",
                                        help_text="Allows JSON style responses suitable for REST API")
    raw_solr_response = models.BooleanField(blank=False, default=False, verbose_name="Enable raw Solr format response",
                                            help_text="Allows returning the raw Solr engine responses suitable for REST API")

    def __str__(self):
        return '%s (%s)' % (self.label_en, self.search_id)

    def to_json(self):
        """
        Function used by the search export utility. Note that auto-generated fields are ignored
        """
        interim_dict = model_to_dict(self)
        if self.imported_on:
            interim_dict['imported_on'] = self.imported_on.strftime("%Y-%m-%dT%H:%M:%S+00:00")
        return json.dumps(interim_dict)

    def from_dict(self, data_dict: dict):
        """
        Function used by the search import utility. Note that auto-generated fields are ignored
        """
        self.search_id = data_dict['search_id']
        self.label_en = data_dict['label_en']
        self.label_fr = data_dict['label_fr']
        self.desc_en = data_dict["desc_en"]
        self.desc_fr = data_dict["desc_fr"]
        self.about_message_en = data_dict["about_message_en"]
        self.about_message_fr = data_dict["about_message_fr"]
        self.search_alias_en = data_dict["search_alias_en"]
        self.search_alias_fr = data_dict["search_alias_fr"]
        self.is_disabled = data_dict["is_disabled"]
        self.disabled_message_en = data_dict["disabled_message_en"]
        self.disabled_message_fr = data_dict["disabled_message_fr"]
        if data_dict["imported_on"]:
            self.imported_on = datetime.fromisoformat(data_dict["imported_on"])
        self.solr_core_name = data_dict["solr_core_name"]
        self.solr_default_op = data_dict["solr_default_op"]
        self.solr_debugging = data_dict["solr_debugging"]
        self.results_page_size = data_dict["results_page_size"]
        self.results_sort_order_en = data_dict["results_sort_order_en"]
        self.results_sort_order_fr = data_dict["results_sort_order_fr"]
        self.results_sort_order_display_en = data_dict["results_sort_order_display_en"]
        self.results_sort_order_display_fr = data_dict["results_sort_order_display_fr"]
        self.results_sort_default_en = data_dict["results_sort_default_en"]
        self.results_sort_default_fr = data_dict["results_sort_default_fr"]
        self.page_template = data_dict["page_template"]
        self.record_template = data_dict["record_template"]
        self.more_like_this_template = data_dict["more_like_this_template"]
        self.breadcrumb_snippet = data_dict["breadcrumb_snippet"]
        self.footer_snippet = data_dict["footer_snippet"]
        self.info_message_snippet = data_dict["info_message_snippet"]
        self.about_message_snippet = data_dict["about_message_snippet"]
        self.header_js_snippet = data_dict["header_js_snippet"]
        self.header_css_snippet = data_dict["header_css_snippet"]
        self.body_js_snippet = data_dict["body_js_snippet"]
        self.search_item_snippet = data_dict["search_item_snippet"]
        self.record_detail_snippet = data_dict["record_detail_snippet"]
        self.record_breadcrumb_snippet = data_dict["record_breadcrumb_snippet"]
        self.dataset_download_url_en = data_dict["dataset_download_url_en"]
        self.dataset_download_url_fr = data_dict["dataset_download_url_fr"]
        self.dataset_download_text_en = data_dict["dataset_download_text_en"]
        self.dataset_download_text_fr = data_dict["dataset_download_text_fr"]
        self.id_fields = data_dict["id_fields"]
        self.alt_formats = data_dict["alt_formats"]
        self.mlt_enabled = data_dict["mlt_enabled"]
        self.mlt_items = data_dict["mlt_items"]
        self.json_response = data_dict["json_response"]
        self.raw_solr_response = data_dict["raw_solr_response"]


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
    fid = models.CharField(max_length=1024, editable=False, unique=True)
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

    def save(self, *args, **kwargs):
        self.fid = f'{self.search_id_id}_{self.field_id}'
        super().save(*args, **kwargs)

    def to_json(self):
        """
        Function used by the search export utility. Note that auto-generated fields are ignored
        """
        d = model_to_dict(self, None, ["id"])
        d['fid'] = self.fid
        return json.dumps(d)

    def from_dict(self, data_dict: dict, my_search: Search):
        """
        Function used by the search import utility. Note that auto-generated fields are ignored
        """
        self.fid = data_dict["fid"]
        self.field_id = data_dict["field_id"]
        self.search_id = my_search
        self.format_name = data_dict["format_name"]
        self.label_en = data_dict["label_en"]
        self.label_fr = data_dict["label_fr"]
        self.solr_field_type = data_dict["solr_field_type"]
        self.solr_field_lang = data_dict["solr_field_lang"]
        self.solr_field_export = data_dict["solr_field_export"]
        self.solr_field_is_coded = data_dict["solr_field_is_coded"]
        self.solr_extra_fields = data_dict["solr_extra_fields"]
        self.solr_field_stored = data_dict["solr_field_stored"]
        self.solr_field_indexed = data_dict["solr_field_indexed"]
        self.solr_field_multivalued = data_dict["solr_field_multivalued"]
        self.solr_field_multivalue_delimeter = data_dict["solr_field_multivalue_delimeter"]
        self.solr_field_is_currency = data_dict["solr_field_is_currency"]
        self.is_search_facet = data_dict["is_search_facet"]
        self.solr_facet_sort = data_dict["solr_facet_sort"]
        self.solr_facet_limit = data_dict["solr_facet_limit"]
        self.solr_facet_snippet = data_dict["solr_facet_snippet"]
        self.solr_facet_display_reversed = data_dict["solr_facet_display_reversed"]
        self.solr_facet_display_order = data_dict["solr_facet_display_order"]
        self.alt_format = data_dict["alt_format"]
        self.is_default_display = data_dict["is_default_display"]
        self.default_export_value = data_dict["default_export_value"]
        self.is_default_year = data_dict["is_default_year"]
        self.is_default_month = data_dict["is_default_month"]

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
    cid = models.CharField(max_length=1024, editable=False, unique=True,)
    code_id = models.CharField(blank=False, max_length=64, verbose_name="Unique code Identifier")
    field_fid = models.ForeignKey(Field, on_delete=models.CASCADE, to_field="fid", )
    label_en = models.CharField(blank=False, max_length=1024, verbose_name="English Code Value")
    label_fr = models.CharField(blank=False, max_length=1024, verbose_name="French Code Value")
    lookup_codes_default = models.CharField(blank=True, default="", max_length=1024, verbose_name="Default Lookup Codes")
    lookup_codes_conditional = models.CharField(blank=True, default="", max_length=1024, verbose_name="Conditional Lookup Codes")
    lookup_date_field = models.CharField(blank=True, default="", max_length=64, verbose_name="Date field to be evaluated")
    lookup_date = models.DateTimeField(blank=True, verbose_name="Lookup Date",
                                       default=datetime(MINYEAR, 1, 1, 0, 0, 0, 0, timezone.utc))
    lookup_test = models.CharField(blank=True, default="", max_length=2, choices=LookupTests.choices, verbose_name="Lookup Test")
    is_lookup = models.BooleanField(blank=False, default=False, verbose_name="Is a Choice Lookup Code")
    extra_01 = models.CharField(blank=True, max_length=1024, verbose_name="Optional value for any use - 01")
    extra_01_en = models.CharField(blank=True, max_length=1024, verbose_name="Optional value for any use - 01 - English")
    extra_01_fr = models.CharField(blank=True, max_length=1024, verbose_name="Optional value for any use - 01 - French")
    extra_02 = models.CharField(blank=True, max_length=1024, verbose_name="Optional value for any use - 02")
    extra_02_en = models.CharField(blank=True, max_length=1024, verbose_name="Optional value for any use - 02 - English")
    extra_02_fr = models.CharField(blank=True, max_length=1024, verbose_name="Optional value for any use - 02 - French")
    extra_03 = models.CharField(blank=True, max_length=1024, verbose_name="Optional value for any use - 03")
    extra_03_en = models.CharField(blank=True, max_length=1024, verbose_name="Optional value for any use - 03 - English")
    extra_03_fr = models.CharField(blank=True, max_length=1024, verbose_name="Optional value for any use - 03 - French")
    extra_04 = models.CharField(blank=True, max_length=1024, verbose_name="Optional value for any use - 04")
    extra_04_en = models.CharField(blank=True, max_length=1024, verbose_name="Optional value for any use - 04 - English")
    extra_04_fr = models.CharField(blank=True, max_length=1024, verbose_name="Optional value for any use - 04 - French")
    extra_05 = models.CharField(blank=True, max_length=1024, verbose_name="Optional value for any use - 05")
    extra_05_en = models.CharField(blank=True, max_length=1024, verbose_name="Optional value for any use - 05 - English")
    extra_05_fr = models.CharField(blank=True, max_length=1024, verbose_name="Optional value for any use - 05 - French")

    def __str__(self):
        return '%s - (%s) %s' % (self.label_en, self.code_id, self.field_fid)

    def to_json(self):
        """
        Function used by the search export utility. Note that auto-generated fields are ignored
        """
        interim_dict = model_to_dict(self, None, ["id"])
        interim_dict['lookup_date'] = self.lookup_date.strftime("%Y-%m-%dT%H:%M:%S+00:00")
        interim_dict['cid'] = self.cid
        return json.dumps(interim_dict)

    def save(self, *args, **kwargs):
        if not self.cid:
            self.cid = f'{self.field_fid.search_id.search_id}_{self.field_fid.field_id}_{self.code_id}'
        if not self.field_fid_id:
            self.field_fid = Field.objects.get(fid=self.field_fid.fid)
        super().save(*args, **kwargs)

    def from_dict(self, data_dict: dict, my_field: Field):
        """
        Function used by the search import utility. Note that auto-generated fields are ignored
        """
        self.cid = data_dict["cid"]
        self.code_id = data_dict["code_id"]
        self.field_fid = my_field
        self.label_en = data_dict["label_en"]
        self.label_fr = data_dict["label_fr"]
        self.lookup_codes_default = data_dict["lookup_codes_default"]
        self.lookup_codes_conditional = data_dict["lookup_codes_conditional"]
        self.lookup_date_field = data_dict["lookup_date_field"]
        t_index = data_dict["lookup_date"].find('T')
        if data_dict["lookup_date"][0:t_index] == '1-01-01':
            self.lookup_date = datetime.fromisoformat("0001-01-01")
        else:
            self.lookup_date = datetime.fromisoformat(data_dict["lookup_date"][0:t_index])
        self.lookup_test = data_dict["lookup_test"]
        self.is_lookup = data_dict["is_lookup"]
        self.extra_01 = data_dict["extra_01"]
        self.extra_01_en = data_dict["extra_01_en"]
        self.extra_01_fr = data_dict["extra_01_fr"]
        self.extra_02 = data_dict["extra_02"]
        self.extra_02_en = data_dict["extra_02_en"]
        self.extra_02_fr = data_dict["extra_02_fr"]
        self.extra_03 = data_dict["extra_03"]
        self.extra_03_en = data_dict["extra_03_en"]
        self.extra_03_fr = data_dict["extra_03_fr"]
        self.extra_04 = data_dict["extra_04"]
        self.extra_04_en = data_dict["extra_04_en"]
        self.extra_04_fr = data_dict["extra_04_fr"]
        self.extra_05 = data_dict["extra_05"]
        self.extra_05_en = data_dict["extra_05_en"]
        self.extra_05_fr = data_dict["extra_05_fr"]



class ChronologicCode(models.Model):
    """
    Codes with a date range.
    """
    id = models.AutoField(primary_key=True)
    ccid = models.CharField(max_length=1024, editable=False, unique=True,)
    code_cid = models.ForeignKey(Code, on_delete=models.CASCADE, to_field="cid",)
    label = models.CharField(blank=False, max_length=1024, verbose_name="Unique code Identifier")
    label_en = models.CharField(blank=False, max_length=1024, verbose_name="English Code Value")
    label_fr = models.CharField(blank=False, max_length=1024, verbose_name="French Code Value")
    start_date = models.DateTimeField(blank=False, verbose_name="Start Date", default=datetime(MINYEAR, 1, 1, 0, 0, 0, 0, timezone.utc))
    end_date = models.DateTimeField(blank=False, verbose_name="End Date", default=datetime(2999, 12, 31, 23, 59, 59, 999999, timezone.utc))

    def to_json(self):
        """
        Function used by the search export utility. Note that auto-generated fields are ignored
        """
        interim_dict = model_to_dict(self, None, ["id", 'code_cid__field_fid'])
        interim_dict['start_date'] = self.start_date.strftime("%Y-%m-%dT%H:%M:%S+00:00")
        interim_dict['end_date'] = self.end_date.strftime("%Y-%m-%dT%H:%M:%S+00:00")
        interim_dict['ccid'] = self.ccid
        return json.dumps(interim_dict)

    def save(self, *args, **kwargs):
        self.ccid = f'{self.code_cid.field_fid.search_id.search_id}_{self.code_cid.field_fid.field_id}_{self.code_cid.code_id}_{parameterize(self.label)}_{self.start_date.strftime("%Y%m%d")}_{self.end_date.strftime("%Y%m%d")}'
        self.code_cid = Code.objects.get(cid=self.code_cid.cid)
        super().save(*args, **kwargs)

    def from_dict(self, data_dict: dict, my_code: Code):
        """
        Function used by the search import utility. Note that auto-generated fields are ignored
        """
        self.ccid = data_dict["ccid"]
        self.code_cid = my_code
        self.label = data_dict["label"]
        self.label_en = data_dict["label_en"]
        self.label_fr = data_dict["label_fr"]
        self.start_date = datetime.fromisoformat(data_dict["start_date"])
        self.end_date = datetime.fromisoformat(data_dict["end_date"])


class Setting(models.Model):

    key = models.CharField(max_length=512, primary_key=True, verbose_name="Setting Keyword (must be unique)",
                           validators=[MinLengthValidator(2)])
    value = models.CharField(max_length=1024, verbose_name="Setting Value", blank=True, null=True)


class Event(models.Model):
    EVENT_CATEGORY = [
        ('notset', 'Undefined / Intéterminé'),
        ('error', 'Error / Erreur'),
        ('success', 'Success / Succès'),
        ('info', 'Information'),
        ('warning', 'Warning / Notification'),
        ('critical', 'Critical / Urgent'),
    ]
    id = models.AutoField(primary_key=True)
    search_id = models.CharField(max_length=32, verbose_name="Search ID", blank=False, default="None")
    component_id = models.CharField(max_length=64, verbose_name="Search 2 Component", blank=False, default="None")
    title = models.CharField(max_length=512, verbose_name="Log entry name or title", blank=False)
    event_timestamp = models.DateTimeField()
    category = models.CharField(max_length=12, verbose_name="Category", default="notset", blank=False, choices=EVENT_CATEGORY)
    message = models.TextField(blank=True, default="", verbose_name="Detailed Event Message")

    def save(self, *args, **kwargs):
        if not self.id and not self.event_timestamp:
            self.event_timestamp = utimezone.now()
        super().save(*args, **kwargs)


class SearchLog(models.Model):
    id = models.AutoField(primary_key=True)
    timestamp = models.DateTimeField()
    hostname = models.CharField(max_length=512, verbose_name="Hostname", blank=False)
    search_type = models.CharField(max_length=32, verbose_name="Search ID", blank=False, default="None")
    page_type = models.CharField(max_length=32, verbose_name="Page Type", blank=False, default="search")
    search_format = models.CharField(max_length=32, verbose_name="Search Format", blank=False, default="html")
    session_id = models.CharField(max_length=128, verbose_name="Session ID", blank=False, default="None")
    page_no = models.IntegerField(verbose_name="Page Number", blank=False, default=1)
    sort_order = models.CharField(max_length=64, verbose_name="Sort Order", blank=False, default="asc")
    search_text = models.TextField(verbose_name="Search Text", blank=False, default="None")
    facets = models.TextField(verbose_name="Facets", blank=False, default="None")
    results_no = models.IntegerField(verbose_name="Results Number", blank=False, default=0)
