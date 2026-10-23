from getpass import getpass
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from api.management.tenant import require_institution
from api.models import SicamUserProfile


class Command(BaseCommand):
    help = 'Crea un ADMIN institucional interactivamente, sin contraseña en argumentos.'

    @transaction.atomic
    def handle(self, *args, **options):
        tenant = require_institution(input('Institución (código): ').strip())
        user = get_user_model()(username=input('Usuario: ').strip(), email=input('Correo: ').strip())
        password = getpass('Contraseña temporal: ')
        if password != getpass('Confirmación: '):
            raise CommandError('Las contraseñas no coinciden.')
        try:
            validate_password(password, user)
            user.set_password(password)
            user.full_clean()
        except ValidationError as exc:
            raise CommandError('; '.join(exc.messages)) from None
        user.save()
        SicamUserProfile.objects.create(user=user, institution=tenant, role='ADMIN', must_change_password=True)
        self.stdout.write('ADMIN creado. Debe cambiar su contraseña al iniciar sesión.')
