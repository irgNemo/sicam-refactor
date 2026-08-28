CHARACTERIZATION_ALGORITHM_VERSION = '1.0'

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
