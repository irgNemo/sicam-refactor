from django.core.management.base import BaseCommand
from api.models import Institution


class Command(BaseCommand):
    help = 'Crea una institución sin alterar metadata si ya existe.'

    def add_arguments(self, parser):
        parser.add_argument('--code', required=True)
        parser.add_argument('--name', required=True)

    def handle(self, *args, **options):
        candidate = Institution(code=options['code'], name=options['name'])
        candidate.full_clean(validate_unique=False)
        obj, created = Institution.objects.get_or_create(code=candidate.code, defaults={'name': candidate.name})
        self.stdout.write(f'{"CREATED" if created else "ALREADY_EXISTS"}: institution_id={obj.pk}')
