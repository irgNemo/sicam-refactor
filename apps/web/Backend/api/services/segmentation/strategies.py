"""Resolve SALIVA services without assigning a strategy to BLOOD."""
from django.conf import settings

from api.segmentation_strategies import SalivaSegmentationStrategy
from .exceptions import SegmentationServiceError


def resolve_saliva_segmentation_service(strategy=None):
    if strategy is None:
        strategy = SalivaSegmentationStrategy.CURRENT_CUSTOM_V1
    if strategy not in SalivaSegmentationStrategy.values:
        raise ValueError('Unknown SALIVA segmentation_strategy')

    if strategy == SalivaSegmentationStrategy.CURRENT_CUSTOM_V1:
        config = getattr(settings, 'SEGMENTATION_SERVICES', {}).get('SALIVA')
        default_timeout = 30
    else:
        config = getattr(settings, 'SALIVA_ALT_SEGMENTATION_SERVICE', None)
        default_timeout = 240

    if not config:
        raise SegmentationServiceError(f'Servicio SALIVA no configurado: {strategy}')
    return {
        'strategy': str(strategy),
        'url': config['url'],
        'timeout': config.get('timeout', default_timeout),
    }
