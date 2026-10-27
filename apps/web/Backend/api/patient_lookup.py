"""Minimal identity/search shared by operational lists and patient selection."""
from django.db.models import Q
from rest_framework.pagination import PageNumberPagination


def search_patients(queryset, text):
    text = text.strip()[:150]
    if not text:
        return queryset
    return queryset.filter(
        Q(initials__icontains=text) | Q(identificacion__icontains=text) |
        Q(external_id_namespace__icontains=text) | Q(external_patient_id__icontains=text))


def patient_identity(patient):
    return {'id': patient.pk, 'initials': patient.initials,
            'identificacion': patient.identificacion, 'identity_mode': patient.identity_mode,
            'external_id_namespace': patient.external_id_namespace,
            'external_patient_id': patient.external_patient_id}


def patient_label(patient):
    return patient.initials or patient.identificacion


class PatientLookupPagination(PageNumberPagination):
    page_size = 20
