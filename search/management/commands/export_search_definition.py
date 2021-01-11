from distutils.dir_util import copy_tree
from search.admin import SearchResource, FieldResource, CodeResource
from search.models import Search, Field, Code
from django.core.management.base import BaseCommand, CommandError
import logging
from os import path, mkdir
from pathlib import Path
from shutil import copyfile


class ExportSearchResource(SearchResource):

    def __init__(self, search_id):
        super().__init__()
        self.search_id = search_id

    def get_queryset(self):
        return Search.objects.filter(search_id=self.search_id)


class ExportFieldResource(FieldResource):

    def __init__(self, search_id):
        super().__init__()
        self.search_id = search_id

    def get_queryset(self):
        sid = Search.objects.get(search_id=self.search_id)
        return Field.objects.filter(search_id=sid)


class ExportCodeResource(CodeResource):

    def __init__(self, search_id):
        super().__init__()
        self.search_id = search_id

    def get_queryset(self):
        sid = Search.objects.get(search_id=self.search_id)
        return Code.objects.filter(field_id__search_id=sid)


class Command(BaseCommand):
    help = 'Export selected search model definitions'

    logger = logging.getLogger(__name__)

    def add_arguments(self, parser):
        parser.add_argument('--export_dir', type=str, help='Directory to write export files to', required=True)
        parser.add_argument('--search', type=str, help='A unique code identifier for the Search', required=True)

    def handle(self, *args, **options):
        if not path.exists(options['export_dir']):
            raise CommandError('Export directory not found: ' + options['export_dir'])

        root_path = path.join(options['export_dir'], options['search'])
        if not path.exists(root_path):
            mkdir(root_path)

        # Create the default directories of an exported search
        db_path = path.join(root_path, 'db')
        if not path.exists(db_path):
            mkdir(db_path)
        snippet_path = path.join(root_path, 'snippets')
        if not path.exists(snippet_path):
            mkdir(snippet_path)
        plugin_path = path.join(root_path, 'plugins')
        if not path.exists(plugin_path):
            mkdir(plugin_path)
        data_path = path.join(root_path, 'data')
        if not path.exists(data_path):
            mkdir(data_path)
        locale_path = path.join(root_path, 'locale')
        if not path.exists(locale_path):
            mkdir(locale_path)

        # Export Search
        dataset = ExportSearchResource(options['search']).export()
        searches_path = path.join(db_path, "{0}_search.json".format(options['search']))
        with open(searches_path, 'w', encoding='utf-8', errors="ignore") as search_file:
            search_file.write(dataset.json)
        logging.info("Search exported to {0}".format(searches_path))

        # Export Fields
        dataset = ExportFieldResource(options['search']).export()
        field_path = path.join(db_path, "{0}_fields.json".format(options['search']))
        with open(field_path, 'w', encoding='utf-8', errors="ignore") as search_file:
            search_file.write(dataset.json)
        logging.info("Fields exported to {0}".format(field_path))

        # Export Codes
        dataset = ExportCodeResource(options['search']).export()
        code_path = path.join(db_path, "{0}_codes.json".format(options['search']))
        with open(code_path, 'w', encoding='utf-8', errors="ignore") as search_file:
            search_file.write(dataset.json)
        logging.info("Fields exported to {0}".format(code_path))

        # Copy custom snippets. The convention is for templates to be deployed to : BASE_DIr/templates/snippets/<search ID>/
        BASE_DIR = Path(__file__).resolve().parent.parent.parent
        custom_template_dir = path.join(BASE_DIR, 'templates', 'snippets', 'custom', options['search'])
        if path.exists(custom_template_dir):
            copy_tree(custom_template_dir, snippet_path)
            logging.info("Copying custom snippets to {0}".format(snippet_path))

        # Copy custom plugin - if one exists. The convention is for plugin file to be named : BASE_DIr/plugins/<search ID>.py
        custom_plug_in = path.join(BASE_DIR, 'plugins', "{0}.py".format(options['search']))
        if path.exists(custom_plug_in):
            copyfile(custom_plug_in, path.join(plugin_path, "{0}.py".format(options['search'])))
            logging.info("Copying custom plugin to {0}".format(path.join(plugin_path, "{0}.py".format(options['search']))))

        # Copy custom locale file <search ID>.po if one exists. For simplicity, currently assuming there is only Freench locales
        custom_locale = path.join(Path(__file__).resolve().parent.parent.parent.parent, 'locale', 'fr', 'LC_MESSAGES', "{0}.po".format(options['search']))
        if path.exists(custom_locale):
            copyfile(custom_locale, path.join(locale_path, "{0}.po".format(options['search'])))
            logging.info("Copying custom locale file to {0}".format(path.join(plugin_path, "{0}.po".format(options['search']))))