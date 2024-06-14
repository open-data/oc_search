from distutils.dir_util import copy_tree

import django.db.models.query
from django.core import serializers
from django.forms.models import model_to_dict
from search.models import Search, Field, Code, ChronologicCode
from django.core.management.base import BaseCommand, CommandError
import logging
import glob
import json
from os import path, mkdir
from pathlib import Path
from shutil import copy,copyfile


# def to_json(instance):
#     d = model_to_dict(instance)
#     for k,v in d:

class Command(BaseCommand):
    help = 'Export a search model definitions to a directory'

    logger = logging.getLogger(__name__)

    def add_arguments(self, parser):
        parser.add_argument('--export_dir', type=str, help='Directory to write export files to', required=True)
        parser.add_argument('--search', type=str, help='A unique code identifier for the Search', required=True)
        parser.add_argument('--include_db', action='store_true', help='Include the database in the export')

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
        cmd_path = path.join(root_path, "commands")
        if not path.exists(cmd_path):
            mkdir(cmd_path)
        model_path = path.join(root_path, 'models')
        if not path.exists(model_path):
            mkdir(model_path)
        extra_path = path.join(root_path, "extras")
        if not path.exists(extra_path):
            mkdir(extra_path)
        tests_path = path.join(root_path, 'tests')
        if not path.exists(tests_path):
            mkdir(tests_path)

        # Export Database values - this is no longer recommended, instead use the database dump command
        if options['include_db']:
            # Export Search
            ex_search = Search.objects.get(search_id=options['search'])
            searches_path = path.join(db_path, "{0}_search.json".format(options['search']))
            with open(searches_path, 'w', encoding='utf-8', errors="ignore") as search_file:
                d = ex_search.to_json()
                search_file.write(d)
            logging.info("Search exported to {0}".format(searches_path))

            # Export Fields
            ex_fields = Field.objects.filter(search_id__search_id=options['search'])
            ex_fields_list = [f.to_json() for f in ex_fields]
            field_path = path.join(db_path, "{0}_fields.json".format(options['search']))
            with open(field_path, 'w', encoding='utf-8', errors="ignore") as search_file:
                fs = f'[{",".join(ex_fields_list)}]'
                search_file.write(fs)
            logging.info(f"{len(ex_fields_list)} Fields exported to {field_path}")

            # Export Codes
            code_path = path.join(db_path, "{0}_codes.json".format(options['search']))
            ex_codes_list = []
            for f in ex_fields:
                ex_codes = Code.objects.filter(field_fid__fid=f.fid)
                if ex_codes.count() > 0:
                    ex_codes_list = ex_codes_list + [c.to_json() for c in ex_codes]
            if len(ex_codes_list) > 0:
                with open(code_path, 'w', encoding='utf-8', errors="ignore") as search_file:
                    cs = f'[{",".join(ex_codes_list)}]'
                    search_file.write(cs)
                logging.info(f'{len(ex_codes_list)} Codes exported to {code_path}')
            else:
                logging.info("No Codes exported")

            # Export Chronologic Codes
            code_path = path.join(db_path, "{0}_chronologiccodes.json".format(options['search']))
            ex_ccodes_list = []
            with open(code_path, 'w', encoding='utf-8', errors="ignore") as search_file:
                for f in ex_fields:
                    ex_codes = Code.objects.filter(field_fid__fid=f.fid)
                    if ex_codes.count() > 0:
                        for c in ex_codes:
                            ex_ccodes = ChronologicCode.objects.filter(code_cid__cid=c.cid)
                            if ex_ccodes.count() > 0:
                                ex_ccodes_list = ex_ccodes_list + [c.to_json() for c in ex_ccodes]
            if len(ex_ccodes_list) > 0:
                with open(code_path, 'w', encoding='utf-8', errors="ignore") as search_file:
                    ccs = f'[{",".join(ex_ccodes_list)}]'
                    search_file.write(ccs)
                logging.info(f'{len(ex_ccodes_list)} Chrono Codes exported to {code_path}')
            else:
                logging.info("No Chrono Codes exported")

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

        # Copy custom Django commands
        custom_commands = path.join(BASE_DIR, 'management', 'commands', options['search'] + '_*.py')
        for cmd in glob.glob(custom_commands):
            copy(cmd, cmd_path)
        logging.info("Copying custom commands to {0}".format(cmd_path))

        # Copy custom data s
        custom_data = path.join(BASE_DIR, 'data', options['search'], '*')
        for data_file in glob.glob(custom_data):
            copy(data_file, data_path)
        logging.info("Copying custom data files to {0}".format(data_path))

        # Copy custom Django database model file
        custom_model = path.join(BASE_DIR, 'models', 'custom', f"{options['search']}_model.py")
        if path.exists(custom_model):
            copyfile(custom_model, path.join(model_path, f"{options['search']}_model.py"))
            logging.info("Copying custom models files to {0}".format(extra_path))

        # Copy custom extras s
        custom_extras = path.join(BASE_DIR, 'extras', options['search'], '*')
        for extra_file in glob.glob(custom_extras):
            copy(extra_file, extra_path)
            logging.info("Copying custom extra files to {0}".format(extra_path))

        DJANGO_DIR = Path(__file__).resolve().parent.parent.parent.parent
        custom_tests = path.join(DJANGO_DIR, 'tests', f"test_{options['search']}*.py")
        for test_file in glob.glob(custom_tests):
            copy(test_file, tests_path)
            logging.info("Copying custom PyTest files to {0}".format(tests_path))
