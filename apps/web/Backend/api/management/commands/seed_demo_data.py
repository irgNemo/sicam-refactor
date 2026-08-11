from pathlib import Path

from django.core.files.base import ContentFile
from django.core.files import File
from django.core.management.base import BaseCommand, CommandError

from api.models import AnalisisPred, Caso, MuestraSaliva, Paciente


DEMO_IDENTIFICACION = 'SICAM-DEMO-001'
DEMO_CASE_TITLE = 'Caso demo SICAM'
DEMO_IMAGE_NAME = 'sicam_demo_saliva.png'
SUPPORTED_IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.tif', '.tiff'}

# 1x1 PNG transparente. Sirve solo para poblar la galeria sin usar datos reales.
SYNTHETIC_PNG_BYTES = (
    b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01'
    b'\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89'
    b'\x00\x00\x00\rIDATx\x9cc\xf8\xff\xff?\x00\x05\xfe'
    b'\x02\xfeA\xe2`\x82\x00\x00\x00\x00IEND\xaeB`\x82'
)


class Command(BaseCommand):
    help = 'Crea datos demo minimos para validar el flujo local SICAM.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--image',
            dest='image_path',
            help=(
                'Ruta local opcional de una imagen de prueba. '
                'La imagen se copia a MEDIA_ROOT y no se agrega al repositorio.'
            ),
        )
        parser.add_argument(
            '--image-dir',
            dest='image_dir',
            help=(
                'Directorio local opcional con imagenes de prueba. '
                'Se procesan archivos no recursivos con extensiones soportadas.'
            ),
        )

    def handle(self, *args, **options):
        image_path = self._validate_image_path(options.get('image_path'))
        image_dir = self._validate_image_dir(options.get('image_dir'))

        paciente, paciente_created = Paciente.objects.get_or_create(
            identificacion=DEMO_IDENTIFICACION,
            defaults={
                'nombre': 'Demo',
                'apellido': 'SICAM',
                'fecha_nacimiento': '1990-01-01',
                'email': 'demo@example.invalid',
                'telefono': '',
            },
        )

        caso, caso_created = Caso.objects.get_or_create(
            paciente=paciente,
            titulo=DEMO_CASE_TITLE,
            defaults={
                'descripcion': 'Caso ficticio para validacion local.',
            },
        )

        analisis, analisis_created = AnalisisPred.objects.get_or_create(
            id_paciente_fk=paciente,
            id_caso_fk=caso,
            defaults={
                'estado': 0,
                'observaciones': 'Analisis demo para validacion local.',
            },
        )

        candidates, ignored_count = self._collect_image_candidates(
            image_path,
            image_dir,
        )
        summary = self._create_missing_muestras(analisis, candidates)
        summary['ignored'] += ignored_count

        self._write_result('Paciente', paciente.id_paciente, paciente_created)
        self._write_result('Caso', caso.id_caso, caso_created)
        self._write_result('AnalisisPred', analisis.id_analisis, analisis_created)
        self.stdout.write(f"Muestras creadas: {summary['created']}")
        self.stdout.write(f"Muestras existentes: {summary['existing']}")
        self.stdout.write(f"Archivos ignorados: {summary['ignored']}")
        self.stdout.write(f"Archivos con error: {summary['errors']}")
        self.stdout.write(
            self.style.SUCCESS(
                'Datos demo listos. No se eliminaron ni sobrescribieron datos.'
            )
        )

    def _validate_image_path(self, image_path):
        if not image_path:
            return None

        path = Path(image_path).expanduser()
        if not path.exists():
            raise CommandError(f'La imagen indicada no existe: {path}')
        if not path.is_file():
            raise CommandError(f'La ruta indicada no es un archivo: {path}')

        return path

    def _validate_image_dir(self, image_dir):
        if not image_dir:
            return None

        path = Path(image_dir).expanduser()
        if not path.exists():
            raise CommandError(f'El directorio indicado no existe: {path}')
        if not path.is_dir():
            raise CommandError(f'La ruta indicada no es un directorio: {path}')

        return path

    def _collect_image_candidates(self, image_path, image_dir):
        candidates = []
        ignored_count = 0

        if image_path is not None:
            candidates.append(image_path)

        if image_dir is not None:
            for path in sorted(image_dir.iterdir(), key=lambda item: item.name.lower()):
                if not path.is_file():
                    ignored_count += 1
                    continue

                if path.suffix.lower() not in SUPPORTED_IMAGE_EXTENSIONS:
                    ignored_count += 1
                    continue

                candidates.append(path)

        if not candidates and image_path is None and image_dir is None:
            candidates.append(None)

        return candidates, ignored_count

    def _create_missing_muestras(self, analisis, candidates):
        existing_names = {
            Path(muestra.imagen.name).name.lower()
            for muestra in MuestraSaliva.objects.filter(analisis=analisis)
            if muestra.imagen
        }
        seen_names = set()
        summary = {
            'created': 0,
            'existing': 0,
            'ignored': 0,
            'errors': 0,
        }

        for candidate in candidates:
            filename = DEMO_IMAGE_NAME if candidate is None else candidate.name
            filename_key = filename.lower()

            if filename_key in seen_names:
                summary['ignored'] += 1
                continue

            seen_names.add(filename_key)

            if filename_key in existing_names:
                summary['existing'] += 1
                continue

            try:
                self._create_muestra(analisis, candidate, filename)
            except OSError as exc:
                summary['errors'] += 1
                self.stderr.write(
                    f'No se pudo leer la imagen {filename}: {exc}'
                )
                continue

            existing_names.add(filename_key)
            summary['created'] += 1

        return summary

    def _create_muestra(self, analisis, image_path, filename):
        muestra = MuestraSaliva(analisis=analisis)

        if image_path is None:
            muestra.imagen.save(
                filename,
                ContentFile(SYNTHETIC_PNG_BYTES),
                save=False,
            )
        else:
            with image_path.open('rb') as image_file:
                muestra.imagen.save(
                    filename,
                    File(image_file),
                    save=False,
                )

        muestra.save()

    def _write_result(self, label, object_id, created):
        action = 'creado' if created else 'existente'
        self.stdout.write(f'{label} {action}: {object_id}')
