from api.management.tenant import require_institution
import fcntl
import hashlib
import json
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand
from api.services.acquisition.optika_seed import seed_optika


class Command(BaseCommand):
    help = 'Registra el consenso PROVISIONAL 18S-A.1 sin recalcularlo ni crear series.'

    def add_arguments(self, parser):
        parser.add_argument("--institution", required=True, help="Código de institución operativa existente.")
        parser.add_argument('--include-evidence', action='store_true')
        parser.add_argument('--source-dir', type=Path, default=settings.BASE_DIR.parents[2] / 'data/calibration')

    def handle(self, *args, **options):
        institution = require_institution(options["institution"])
        # Serialize this controlled local command, including the first profile creation.
        key = hashlib.sha256(str(settings.DATABASES['default']['NAME']).encode()).hexdigest()
        with open(f'/tmp/sicam-optika-seed-{key}.lock', 'a') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            result = seed_optika(options['source_dir'] if options['include_evidence'] else None, institution=institution)
        self.stdout.write(json.dumps(result))
