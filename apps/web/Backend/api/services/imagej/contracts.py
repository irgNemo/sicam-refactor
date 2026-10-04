import hashlib
import json

CONVERTER_VERSION = '1.0'
CONTRACT_VERSION = 'imagej-gray-v1'
KEY_NAMESPACE = 'sicam.imagej.import.v1'
LABELS = ((170, 'membrana'), (255, 'nucleo'), (85, 'micronucleo'))


class ImportProblem(ValueError):
    """Only non-sensitive codes/context may be exposed in CLI reports."""
    def __init__(self, code, detail=''):
        self.code = code
        self.detail = detail
        super().__init__(code)


def patient_key(value):
    return str(value).strip().casefold()


def sha256_file(file):
    digest = hashlib.sha256()
    for block in iter(lambda: file.read(1024 * 1024), b''):
        digest.update(block)
    return digest.hexdigest()


def sha256_path(path):
    with path.open('rb') as file:
        return sha256_file(file)


def canonical_hash(values):
    return hashlib.sha256(json.dumps(values, ensure_ascii=False, separators=(',', ':'), allow_nan=False).encode('utf-8')).hexdigest()


def import_keys(dataset, namespace, external_id, case_number, basename, image_hash, mask_hash):
    identity = [KEY_NAMESPACE, dataset, namespace, external_id, case_number]
    sample = canonical_hash(['sample', *identity, image_hash])
    return {
        'sample_key': sample,
        'annotation_key': canonical_hash(['annotation', sample, mask_hash, CONVERTER_VERSION, CONTRACT_VERSION]),
        'logical_key': canonical_hash(['logical', *identity, basename]),
    }
