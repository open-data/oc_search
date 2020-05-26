from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from search.models import Search, Field
from SolrClient import SolrClient
import logging

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
    help = 'Create a Solr core using the Solr Schema API'

    logger = logging.getLogger(__name__)

    def _add_or_update_solr_field(self, solr_client, collection, new_field):
        if solr_client.schema.does_field_exist(collection, new_field["name"]):
            solr_client.schema.replace_field(collection, new_field)
            self.logger.info("Updated field " + new_field['name'])
        else:
            solr_client.schema.create_field(collection, new_field)
            self.logger.info("Created field " + new_field['name'])

    def add_arguments(self, parser):
        parser.add_argument('search', type=str)

    def handle(self, *args, **options):
        try:
            search_id = options['search']
            search_target = Search.objects.get(search_id=search_id)
            solr = SolrClient(settings.SOLR_SERVER_URL)
            if not solr.schema.does_field_type_exist(settings.SOLR_COLLECTION, 'search_text_en'):
                solr.schema.create_field_type(settings.SOLR_COLLECTION, search_text_en)
            if not solr.schema.does_field_type_exist(settings.SOLR_COLLECTION, 'search_text_fr'):
                solr.schema.create_field_type(settings.SOLR_COLLECTION, search_text_fr)

            # Create the schema fields according to the definition from the search record
            for solr_field in  Field.objects.all():
                new_field = {"name": solr_field.field_id,
                             "type": solr_field.solr_field_type,
                             "stored": solr_field.solr_field_stored,
                             "indexed": solr_field.solr_field_indexed,
                             "multiValued": solr_field.solr_field_multivalued
                             }
                if solr_field.solr_field_type in ("string", "pint", "pdate"):
                    new_field["docValues"] = True
                self._add_or_update_solr_field(solr, settings.SOLR_COLLECTION, new_field)

                if solr_field.solr_field_type in ("pint", "pdate"):
                    # Create English and French strings for holding locale formatted numbers and dates
                    new_loc_field = {"name": "{0}_en".format(solr_field.field_id),
                                     "type": "string",
                                     "stored": True,
                                     "indexed": True,
                                     "docValues": True}
                    self._add_or_update_solr_field(solr, settings.SOLR_COLLECTION, new_loc_field)
                    new_loc_field["name"] = "{0}_fr".format(solr_field.field_id)
                    self._add_or_update_solr_field(solr, settings.SOLR_COLLECTION, new_loc_field)

                if solr_field.solr_field_export != "":
                    # create a string copy field for export
                    export_field = {"name": solr_field.solr_field_export,
                                    "type": "string",
                                    "stored": True,
                                    "indexed": False,
                                    "docValues": True
                                    }
                    export_copy_field = {'source': solr_field.field_id,
                                         'dest': solr_field.solr_field_export}
                    self._add_or_update_solr_field(solr, settings.SOLR_COLLECTION, export_field)
                    if not solr.schema.does_copy_field_exist(settings.SOLR_COLLECTION, solr_field.field_id,
                                                             solr_field.solr_field_export):
                        solr.schema.create_copy_field(settings.SOLR_COLLECTION, export_copy_field)

        except Exception as x:
            self.logger.error('Unexpected Error "{0}"'.format(x))

