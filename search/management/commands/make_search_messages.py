from django.core.management.base import BaseCommand
from django.core.management.utils import popen_wrapper
from os import path, listdir, walk
from django.utils.translation import templatize
from pathlib import Path
from tempfile import TemporaryDirectory


class Command(BaseCommand):
    help = 'Extracts the translations from a search definition and write them to a PO file'

    requires_system_checks = False
    BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent

    def add_arguments(self, parser):
        parser.add_argument('--search', type=str, help='The Search ID of the templates to be extracted', required=True)

    def handle(self, *args, **options):
        custom_dir = path.join(self.BASE_DIR, 'search', 'templates', 'snippets', 'custom', options['search'])
        output_path = path.join(self.BASE_DIR, 'locale', 'fr', 'LC_MESSAGES', options['search'] + '.po')
        temp_dir = TemporaryDirectory(dir=path.join(self.BASE_DIR, 'search', 'templates', 'snippets', 'custom'))
        template_files = []
        for dirpath, dirnames, filenames in walk(custom_dir, topdown=True, onerror=None, followlinks=False):
            for filename in filenames:
                file_path = path.normpath(path.join(dirpath, filename))
                file_ext = path.splitext(filename)[1]
                if file_ext in ['.html', '.py', '.txt']:
                    with open(file_path, encoding='utf-8') as fp:
                        src_data = fp.read()
                        rc = templatize(src_data, origin=dirpath)
                        temp_file = path.join(temp_dir.name, filename)
                        with open(temp_file, 'w', encoding='utf-8') as ofp:
                            ofp.write(rc)
                            template_files.append(temp_file)

        args = [
            'xgettext',
            '-d', options['search'],
            '--language=Python',
            '--no-wrap',
            '--from-code=utf-8',
            '--sort-by-file',
            '--copyright-holder="Government of Canada, Gouvernement du Canada"',
            '--package-name="Open Canada Search - {0} Module"'.format(options['search']),
            '--keyword=gettext_noop',
            '--keyword=gettext_lazy',
            '--keyword=ngettext_lazy:1,2',
            '--keyword=ugettext_noop',
            '--keyword=ugettext_lazy',
            '--keyword=ungettext_lazy:1,2',
            '--keyword=pgettext:1c,2',
            '--keyword=npgettext:1c,2,3',
            '--keyword=pgettext_lazy:1c,2',
            '--keyword=npgettext_lazy:1c,2,3',
            '-o', output_path
        ]
        #
        if path.exists(output_path):
            args += ['--join-existing']
        args += template_files
        rc = popen_wrapper(args)
        if rc[2] != 0:
            print(rc[1])
        else:
            print("Created {0}.po".format(options['search']))

        temp_dir.cleanup()
