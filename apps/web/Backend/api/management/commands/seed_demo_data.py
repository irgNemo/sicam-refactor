from pathlib import Path

from django.core.files.base import ContentFile
from django.core.files import File
from django.core.management.base import BaseCommand, CommandError

from api.models import AnalisisPred, Caso, MuestraSaliva, Paciente


DEMO_IDENTIFICACION = 'SICAM-DEMO-001'
DEMO_CASE_TITLE = 'Caso demo SICAM'
DEMO_IMAGE_NAME = 'sicam_demo_saliva.png'

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

    def handle(self, *args, **options):
        image_path = self._validate_image_path(options.get('image_path'))

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

        muestra = MuestraSaliva.objects.filter(analisis=analisis).first()
        muestra_created = False

        if muestra is None:
            muestra = MuestraSaliva(analisis=analisis)
            if image_path is None:
                muestra.imagen.save(
                    DEMO_IMAGE_NAME,
                    ContentFile(SYNTHETIC_PNG_BYTES),
                    save=False,
                )
            else:
                with image_path.open('rb') as image_file:
                    muestra.imagen.save(
                        image_path.name,
                        File(image_file),
                        save=False,
                    )
            muestra.save()
            muestra_created = True

        self._write_result('Paciente', paciente.id_paciente, paciente_created)
        self._write_result('Caso', caso.id_caso, caso_created)
        self._write_result('AnalisisPred', analisis.id_analisis, analisis_created)
        self._write_result('MuestraSaliva', muestra.id_muestra, muestra_created)
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

    def _write_result(self, label, object_id, created):
        action = 'creado' if created else 'existente'
        self.stdout.write(f'{label} {action}: {object_id}')
