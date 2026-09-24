from django.db import models


class SalivaSegmentationStrategy(models.TextChoices):
    CURRENT_CUSTOM_V1 = 'CURRENT_CUSTOM_V1', 'Current custom v1'
    ALT_CPSAM_MORPHOLOGICAL_V1 = 'ALT_CPSAM_MORPHOLOGICAL_V1', 'ALT cpsam morphological v1'
