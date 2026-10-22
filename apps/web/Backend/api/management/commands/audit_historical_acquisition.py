"""Read-only dimensional inventory. Matching resolution is NOT matching optics."""
import json
from collections import Counter
from django.core.management.base import BaseCommand
from django.db import connection
from PIL import Image
from api.models import Paciente, MuestraSaliva, MuestraSangre


class Command(BaseCommand):
    help = 'Audita dimensiones por paciente sin asociar series ni inferir óptica.'

    def add_arguments(self, parser):
        parser.add_argument('--width', type=int, default=4928)
        parser.add_argument('--height', type=int, default=4928)

    def handle(self, *args, **options):
        rows = []
        # The command contains no mutation. SQLite additionally refuses writes.
        query_only = None
        if connection.vendor == 'sqlite':
            with connection.cursor() as cursor:
                cursor.execute('PRAGMA query_only')
                query_only = cursor.fetchone()[0]
                cursor.execute('PRAGMA query_only=ON')
        try:
            for patient in Paciente.objects.order_by('pk'):
                dimensions, types = Counter(), Counter()
                matched = invalid = assigned = 0
                for label, model in (('SALIVA', MuestraSaliva), ('SANGRE', MuestraSangre)):
                    for sample in model.objects.filter(analisis__id_paciente_fk=patient).iterator():
                        types[label] += 1
                        assigned += sample.acquisition_series_id is not None
                        try:
                            with sample.imagen.storage.open(sample.imagen.name, 'rb') as stream:
                                with Image.open(stream) as image:
                                    size = image.size
                            dimensions[f'{size[0]}x{size[1]}'] += 1
                            matched += size == (options['width'], options['height'])
                        except (OSError, ValueError, Image.DecompressionBombError):
                            invalid += 1
                rows.append({'patient_alias': f'PATIENT_{patient.pk:03d}', 'samples': sum(types.values()),
                             'sample_types': dict(types), 'dimensions': dict(sorted(dimensions.items())),
                             'resolution_matches_only': matched, 'invalid_or_missing': invalid,
                             'samples_with_series': assigned, 'series_ids': list(patient.acquisition_series.values_list('id', flat=True))})
        finally:
            if query_only is not None:
                with connection.cursor() as cursor:
                    cursor.execute(f'PRAGMA query_only={int(query_only)}')
        self.stdout.write(json.dumps({'status':'HISTORICAL_ACQUISITION_ASSOCIATION_PENDING_MANUAL_CONFIRMATION',
            'caveat':'La coincidencia de resolución no prueba cámara, objetivo ni compatibilidad óptica.',
            'target_dimensions':[options['width'],options['height']], 'patients':rows}, indent=2))
