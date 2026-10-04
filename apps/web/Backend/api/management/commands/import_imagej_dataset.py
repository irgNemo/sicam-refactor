import json
from django.core.management.base import BaseCommand, CommandError
from api.services.imagej.contracts import ImportProblem
from api.services.imagej.importer import run_import


class Command(BaseCommand):
    help = 'Import manual ImageJ SALIVA annotations. Use --dry-run before any import.'

    def add_arguments(self, parser):
        for name in ('source', 'patients-file', 'dataset-key', 'patient-namespace'):
            parser.add_argument('--' + name, required=True)
        parser.add_argument('--case-number', type=int, default=1)
        parser.add_argument('--dry-run', action='store_true')
        parser.add_argument('--patient', action='append')
        parser.add_argument('--limit', type=int)
        parser.add_argument('--strict', action='store_true')
        parser.add_argument('--layout', choices=['official', 'legacy-flat', 'legacy-repeated'], default='official')
        parser.add_argument('--patients-format', choices=['standard', 'ijc1'], default='standard')

    def handle(self, *args, **options):
        names = ('source', 'patients_file', 'dataset_key', 'patient_namespace', 'case_number', 'dry_run',
                 'patient', 'limit', 'strict', 'layout', 'patients_format')
        try:
            report = run_import(**{key: options[key] for key in names})
        except ImportProblem as exc:
            raise CommandError(exc.code) from None
        self.stdout.write(json.dumps(report, ensure_ascii=False, indent=2))
        if report['errors']:
            raise CommandError('IMPORT_HAS_REJECTED_PAIRS', returncode=2)
