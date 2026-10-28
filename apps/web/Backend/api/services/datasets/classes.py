"""Dataset-local labels; comparison never infers medical meaning."""
from rest_framework.exceptions import ValidationError


def class_key(label):
    return label.strip().casefold()


def class_catalog(labels):
    accepted = {}
    for label in labels:
        key = class_key(label)
        if not key:
            raise ValidationError('El nombre de clase no puede estar vacío.')
        if key in accepted:
            raise ValidationError('Ya existe una clase equivalente con ese nombre.')
        accepted[key] = label.strip()
    return accepted


def validate_assignments(labels, patients, require_complete=False):
    catalog = class_catalog(labels)
    for patient in patients:
        key = class_key(patient['class_label'])
        if not key and not require_complete:
            patient['class_label'] = ''
            continue
        if key not in catalog:
            raise ValidationError('Asigne a cada paciente una clase de las definidas en el conjunto.')
        patient['class_label'] = catalog[key]
    return list(catalog.values())
