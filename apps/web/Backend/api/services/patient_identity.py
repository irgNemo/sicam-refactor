"""Stable external patient identity, shared by the API and ImageJ importer."""
import uuid


def pseudonymized_identification(namespace, external_id):
    # Preserve ImageJ's original serialization and UUID namespace exactly.
    return 'ext:' + uuid.uuid5(uuid.NAMESPACE_URL, repr((namespace, external_id))).hex
