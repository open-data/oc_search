from django.core.management.base import BaseCommand, CommandError
from django.core.management.utils import popen_wrapper
from os import path, listdir
from pathlib import Path


class Command(BaseCommand):
    help = 'Combines .po files to the django.po file for use with builtin gettext support.'

    requires_system_checks = False
    BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent
    program = 'msgcat'
    french_locale_dir = path.join(BASE_DIR, 'locale', 'fr', 'LC_MESSAGES')
    program_options = ['--use-first', '--no-wrap']
    output_options = ['-o', '{0}'.format(path.join(french_locale_dir, 'django.po'))]

    def handle(self, *args, **options):

        po_files = []
        for file in listdir(self.french_locale_dir):
            if file.endswith(".po"):
                if file != "django.po":
                    po_files.append(path.join(self.french_locale_dir, file))
        args = [self.program] + self.program_options + po_files + self.output_options
        rc = popen_wrapper(args)
        if rc[2] != 0:
            print(rc[1])
        else:
            print("Created django.po")



