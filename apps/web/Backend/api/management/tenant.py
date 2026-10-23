from django.core.management.base import CommandError
from api.models import Institution


def require_institution(code):
    try:
        return Institution.objects.get(code=code, active=True)
    except Institution.DoesNotExist:
        raise CommandError('ACTIVE_INSTITUTION_REQUIRED') from None
