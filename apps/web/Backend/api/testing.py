"""Explicit platform identity for pre-18T scientific regression fixtures.
Security/role tests use DRF's unmodified APIClient instead.
"""
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient, APITestCase, APITransactionTestCase
from api.models import Institution


def tenant_fixture():
    return Institution.objects.get_or_create(code='TEST', defaults={'name': 'Synthetic tests'})[0]


class PlatformClient(APIClient):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        user, _ = get_user_model().objects.get_or_create(username='regression-platform', defaults={'is_superuser': True, 'is_staff': True})
        self.force_authenticate(user)

    def post(self, path, data=None, *args, **kwargs):
        if path in ('/api/pacientes/', '/api/acquisition-profiles/') and isinstance(data, dict) and 'institution' not in data:
            data = {**data, 'institution': tenant_fixture().pk}
        return super().post(path, data, *args, **kwargs)


class PlatformAPITestCase(APITestCase):
    client_class = PlatformClient


class PlatformAPITransactionTestCase(APITransactionTestCase):
    client_class = PlatformClient
