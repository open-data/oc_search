from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
import glob
from os import path, listdir, remove, rmdir
from pathlib import Path
from search.models import Search, Field, Code, ChronologicCode
import logging


class Command(BaseCommand):
    help = 'Delete a search from the database and its associated files'

    logger = logging.getLogger(__name__)
    is_dry_run = False

    def add_arguments(self, parser):
        parser.add_argument('--search', type=str, help='Unique code identifier for the search', required=True)
        parser.add_argument('--include_db', required=False, action='store_true',
                            help='Remove the search definition data from the Django database')
        parser.add_argument('--dry_run', required=False, action='store_true',
                            help='Do a dry run, show what will be deleted but do not delete the search definition data')

    def safe_delete(self, filename):
        if path.exists(filename):
            msg = f'Deleting {filename}' if path.isfile(filename) else f'Removing directory {filename}'
            self.logger.info(msg)
            if not self.is_dry_run:
                if path.isfile(filename):
                    remove(filename)
                elif path.isdir(filename):
                    rmdir(filename)

    def handle(self, *args, **options):

        self.is_dry_run = options['dry_run']
        try:
            # CLean out the Search database
            if options['include_db']:
                field_ctr = 0
                code_ctr = 0
                chr_code_ctr = 0
                search = Search.objects.get(search_id=options['search'])
                fields = Field.objects.filter(search_id__search_id=search.search_id)
                for f in fields:
                    codes = Code.objects.filter(field_fid__fid=f.fid)
                    for code in codes:
                        c_codes = ChronologicCode.objects.filter(code_cid__cid=code.cid)
                        if c_codes.count() > 0:
                            for cc in c_codes:
                                chr_code_ctr += 1
                                if not self.is_dry_run:
                                    cc.delete()
                        code_ctr += 1
                        if not self.is_dry_run:
                            code.delete()
                    field_ctr += 1
                    if not self.is_dry_run:
                        f.delete()
                if not self.is_dry_run:
                    search.delete()
                self.logger.info(f'Deleted search definition data including {field_ctr} Fields, {code_ctr} Codes, and {chr_code_ctr} Chronological Codes')
        except Search.DoesNotExist:
            raise CommandError(f'Search {options["search"]} not found in Django database')

        try:
            # Identify directories to be cleaned out
            BASE_DIR = Path(__file__).resolve().parent.parent.parent

            # Remove custom templates
            custom_template_dir = path.join(BASE_DIR, 'templates', 'snippets', 'custom', options['search'])
            if path.exists(custom_template_dir):
                for f in listdir(custom_template_dir):
                    self.safe_delete(path.join(custom_template_dir, f))
                self.safe_delete(custom_template_dir)

            # Remove search custom code
            custom_plug_in = path.join(BASE_DIR, 'plugins', "{0}.py".format(options['search']))
            self.safe_delete(custom_plug_in)

            # Remove custom source and compiled locale files
            locale_export_po = path.join(Path(__file__).resolve().parent.parent.parent.parent, 'locale', 'fr', 'LC_MESSAGES', f"{options['search']}.po")
            self.safe_delete(locale_export_po)
            locale_export_mo = path.join(Path(__file__).resolve().parent.parent.parent.parent, 'locale', 'fr', 'LC_MESSAGES', f"{options['search']}.mo")
            self.safe_delete(locale_export_mo)

            # Remove and extra files fo the custom search
            data_export_dir = path.join(BASE_DIR, 'data', options['search'])
            if path.exists(data_export_dir):
                for f in listdir(data_export_dir):
                    self.safe_delete(path.join(data_export_dir, f))
                self.safe_delete(data_export_dir)

            # Remove any custom commands for the search
            cmd_export_dir = path.join(BASE_DIR, 'management', 'commands')
            cmd_export_filter = path.join(BASE_DIR, 'management', 'commands', options['search'] + '_*.py')
            if path.exists(cmd_export_dir):
                for cmd in glob.glob(cmd_export_filter):
                    self.safe_delete(cmd)

            # Remove any custom Django database models
            model_export = path.join(BASE_DIR, 'models', 'custom', f"{options['search']}_model.py")
            self.safe_delete(model_export)

            extra_export_dir = path.join(BASE_DIR, 'extras', options['search'])
            if path.exists(extra_export_dir):
                for f in listdir(extra_export_dir):
                    self.safe_delete(path.join(extra_export_dir, f))
                self.safe_delete(extra_export_dir)

        except Exception as x:
            self.logger.error(x)

        self.logger.info("Completed.")
        self.logger.info('\nAfter running this command, it is still necessary to manually remove the Solr core '
                         'that was created for the search,\n'
                         'It is recommended to run the Django "collectstatic" management command next.\n'
                         'It is also recommended to run the Django and Search locale management commands.\n'
                         'If there were any custom Django database models it is _STRONGLY_ recommended to manually '
                         'run the Django database management and migration commands next.')
