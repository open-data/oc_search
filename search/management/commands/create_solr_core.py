from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from search.models import Search, Field
from SolrClient import SolrClient
import logging

# Custom Solr schema definition for English search text
search_text_en = {
    "name": "search_text_en",
    "class": "solr.TextField",
    "positionIncrementGap": "100",
    "indexAnalyzer": {
        "charFilters": [{"class": "solr.HTMLStripCharFilterFactory"}],
        "tokenizer": {"class": "solr.WhitespaceTokenizerFactory"},
        "filters": [
            {"class": "solr.WordDelimiterGraphFilterFactory", "preserveOriginal": "1", "splitOnCaseChange": "0", "catenateAll": "1"},
            {"class": "solr.FlattenGraphFilterFactory"},
            {"class": "solr.SynonymGraphFilterFactory", "expand": "true", "ignoreCase": "true", "synonyms": "lang/synonyms_en.txt"},
            {"class": "solr.FlattenGraphFilterFactory"},
            {"class": "solr.StopFilterFactory", "words": "lang/stopwords_en.txt", "ignoreCase": "true"},
            {"class": "solr.LowerCaseFilterFactory"},
            {"class": "solr.EnglishPossessiveFilterFactory"},
            {"class": "solr.KeywordMarkerFilterFactory", "protected": "protwords.txt"},
            {"class": "solr.PorterStemFilterFactory"}
        ]
    },
    "queryAnalyzer": {
        "charFilters": [{"class": "solr.HTMLStripCharFilterFactory"}],
        "tokenizer": {"class": "solr.WhitespaceTokenizerFactory"},
        "filters": [
            {"class": "solr.WordDelimiterGraphFilterFactory", "preserveOriginal": "1", "splitOnCaseChange": "0", "catenateAll": "1"},
            {"class": "solr.StopFilterFactory", "words": "lang/stopwords_en.txt", "ignoreCase": "true"},
            {"class": "solr.SynonymGraphFilterFactory", "expand": "true", "ignoreCase": "true", "synonyms": "lang/synonyms_en.txt"},
            {"class": "solr.LowerCaseFilterFactory"},
            {"class": "solr.EnglishPossessiveFilterFactory"},
            {"class": "solr.KeywordMarkerFilterFactory", "protected": "protwords.txt"},
            {"class": "solr.PorterStemFilterFactory"}
        ]
    }
}

# Custom Solr schema definition for French search text
search_text_fr = {
    "name": "search_text_fr",
    "class": "solr.TextField",
    "positionIncrementGap": "100",
    "analyzer": {
        "charFilters": [{"class": "solr.HTMLStripCharFilterFactory"}],
        "tokenizer": {"class": "solr.StandardTokenizerFactory"},
        "filters": [
            {"class": "solr.SynonymGraphFilterFactory", "expand": "true", "ignoreCase": "true", "synonyms": "lang/synonyms_fr.txt"},
            {"class": "solr.FlattenGraphFilterFactory"},
            {"class": "solr.ElisionFilterFactory", "articles": "lang/contractions_fr.txt", "ignoreCase": "true"},
            {"class": "solr.LowerCaseFilterFactory"},
            {"class": "solr.StopFilterFactory", "format": "snowball", "words": "lang/stopwords_fr.txt", "ignoreCase": "true"},
            {"class": "solr.SynonymGraphFilterFactory", "expand": "true", "ignoreCase": "true", "synonyms": "lang/synonyms_fr.txt"},
            {"class": "solr.FrenchLightStemFilterFactory"}
        ]
    }
}


class Command(BaseCommand):
    help = 'Using the specified Search model, create a Solr core using the Solr Schema API'

    logger = logging.getLogger(__name__)

    # simple helper function for add or delete
    def _add_or_update_solr_field(self, solr_client, collection, new_field):
        if solr_client.schema.does_field_exist(collection, new_field["name"]):
            solr_client.schema.replace_field(collection, new_field)
            self.logger.info("Updated field " + new_field['name'])
        else:
            solr_client.schema.create_field(collection, new_field)
            self.logger.info("Created field " + new_field['name'])

    def add_arguments(self, parser):
        parser.add_argument('--search', help='Unique Search model identifier', type=str)

    def handle(self, *args, **options):
        try:
            search_id = options['search']
            search_target = Search.objects.get(search_id=search_id)
            solr_core = search_target.solr_core_name
            solr = SolrClient(settings.SOLR_SERVER_URL)

            # create custom Solr field types if necessary
            if not solr.schema.does_field_type_exist(solr_core, 'search_text_en'):
                solr.schema.create_field_type(solr_core, search_text_en)
            if not solr.schema.does_field_type_exist(solr_core, 'search_text_fr'):
                solr.schema.create_field_type(solr_core, search_text_fr)
            create_year_field = False
            create_month_field = False

            # Create the schema fields according to the definition from the search model record
            for solr_field in Field.objects.filter(search_id=search_target):
                new_field = {"name": solr_field.field_id,
                             "type": solr_field.solr_field_type,
                             "stored": solr_field.solr_field_stored,
                             "indexed": solr_field.solr_field_indexed,
                             "multiValued": solr_field.solr_field_multivalued
                             }
                extra_copy_fields = []
                if solr_field.solr_field_type in ("string", "pint", "pdate"):
                    new_field["docValues"] = True
                self._add_or_update_solr_field(solr, solr_core, new_field)

                # Create English and French strings for holding: locale formatted numbers and dates as well as code values
                if solr_field.solr_field_type in ("pint", "pdate", "pfloat") and solr_field.field_id != 'year':
                    new_loc_field = {"name": "{0}_en".format(solr_field.field_id),
                                     "type": "string",
                                     "stored": True,
                                     "indexed": True,
                                     "docValues": True}
                    self._add_or_update_solr_field(solr, solr_core, new_loc_field)
                    extra_copy_fields.append(new_loc_field["name"])
                    new_loc_field["name"] = "{0}_fr".format(solr_field.field_id)
                    self._add_or_update_solr_field(solr, solr_core, new_loc_field)
                    extra_copy_fields.append(new_loc_field["name"])
                elif solr_field.solr_field_type == 'string' and solr_field.solr_field_is_coded:
                    new_loc_field = {"name": "{0}_en".format(solr_field.field_id),
                                     "type": "string",
                                     "stored": True,
                                     "indexed": True,
                                     "docValues": True}
                    if solr_field.solr_field_multivalued:
                        new_loc_field['multiValued'] = True
                    self._add_or_update_solr_field(solr, solr_core, new_loc_field)
                    new_loc_field["name"] = "{0}_fr".format(solr_field.field_id)
                    self._add_or_update_solr_field(solr, solr_core, new_loc_field)
                elif solr_field.solr_field_type == 'string' and solr_field.solr_extra_fields:
                    # If the user has manually specified extra copy fields for bilingual strings like names
                    for extra_field in solr_field.solr_extra_fields.split(","):
                        new_loc_field = {"name": extra_field.strip(),
                                         "type": "search_text_fr" if extra_field.endswith('_fr') else "search_text_en",
                                         "stored": True,
                                         "indexed": True,
                                         "docValues": False}
                        if solr_field.solr_field_multivalued:
                            new_loc_field['multiValued'] = True
                        self._add_or_update_solr_field(solr, solr_core, new_loc_field)
                        export_copy_field = {'source': solr_field.field_id,
                                             'dest': extra_field}
                        if not solr.schema.does_copy_field_exist(solr_core, solr_field.field_id,
                                                                 extra_field):
                            solr.schema.create_copy_field(solr_core, export_copy_field)

                # Create default year and month if so required
                if solr_field.solr_field_type == 'pdate':
                    if solr_field.is_default_year:
                        create_year_field = True
                    if solr_field.is_default_month:
                        create_month_field = True

                # create a string copy field for export
                if solr_field.solr_field_export != "":
                    for export_field_name in solr_field.solr_field_export.split(","):
                        export_field = {"name": export_field_name,
                                        "type": "string",
                                        "stored": True,
                                        "indexed": False,
                                        "docValues": True
                                        }

                        export_copy_field = {'source': solr_field.field_id,
                                             'dest': export_field_name}
                        self._add_or_update_solr_field(solr, solr_core, export_field)
                        if not solr.schema.does_copy_field_exist(solr_core, solr_field.field_id, export_field_name):
                            if not solr_field.solr_field_multivalued:
                                solr.schema.create_copy_field(solr_core, export_copy_field)
                                extra_copy_fields.append(export_field['name'])

                # Update the Field db record with the list of copy fields
                solr_field.solr_extra_fields = ",".join(extra_copy_fields)
                solr_field.save()

            # Create default year and month fields if specified
            if create_year_field:
                new_field = {"name": "year",
                             "type": "pint",
                             "stored": True,
                             "indexed": True,
                             "docValues": True}
                self._add_or_update_solr_field(solr, solr_core, new_field)
            if create_month_field:
                new_field = {"name": "month",
                             "type": "pint",
                             "stored": True,
                             "indexed": True,
                             "docValues": True}
                self._add_or_update_solr_field(solr, solr_core, new_field)

        except Exception as x:
            self.logger.error('Unexpected Error "{0}"'.format(x))

