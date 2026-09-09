from api.services.segmentation.types import SampleType


CHARACTERIZATION_ALGORITHM_VERSION = '1.0'
SALIVA_CHARACTERIZATION_ALGORITHM_VERSION = '2.0'
BLOOD_CHARACTERIZATION_ALGORITHM_VERSION = CHARACTERIZATION_ALGORITHM_VERSION

CAPABILITY_COUNTS = 'counts'
CAPABILITY_GENOTOXICITY_INDEX = 'genotoxicity_index'
CAPABILITY_CYTOTOXICITY_INDEX = 'cytotoxicity_index'
CAPABILITY_BINUCLEATE_TRINUCLEATE = 'binucleate_trinucleate'

STATUS_AVAILABLE = 'AVAILABLE'
STATUS_NOT_DEFINED = 'NOT_DEFINED'
STATUS_BLOCKED_SCIENTIFIC_RULE = 'BLOCKED_SCIENTIFIC_RULE'

WARNING_SALIVA_SPATIAL_ASSOCIATION_BLOCKED = (
    'La regla legacy de asociacion citoplasma-nucleo-micronucleo depende '
    'de recortes y mascaras de segmentacion que no estan disponibles en el '
    'contrato normalizado actual.'
)
WARNING_BLOOD_CHARACTERIZATION_NOT_DEFINED = (
    'No existe una regla cientifica versionada para caracterizacion de '
    'SANGRE; se reportan solo conteos.'
)


def get_characterization_algorithm_version(sample_type):
    if sample_type == SampleType.SALIVA:
        return SALIVA_CHARACTERIZATION_ALGORITHM_VERSION
    if sample_type == SampleType.BLOOD:
        return BLOOD_CHARACTERIZATION_ALGORITHM_VERSION
    return CHARACTERIZATION_ALGORITHM_VERSION
