"""Dataset snapshots are separate from clinical identity and scientific results."""
import uuid
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models


class MLDataset(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    institution = models.ForeignKey('api.Institution', on_delete=models.PROTECT)
    name = models.CharField(max_length=160)
    description = models.TextField(blank=True)
    status = models.CharField(max_length=12, choices=[('DRAFT','Draft'),('GENERATED','Generated')], default='DRAFT')
    dataset_type = models.CharField(max_length=32, default='SALIVA_NUCLEAR_FEATURES', editable=False)
    characterization_version = models.CharField(max_length=8, choices=[('2.1','2.1'),('2.2','2.2')])
    units_mode = models.CharField(max_length=8, choices=[('PIXELS','Pixels'),('PHYSICAL','Physical'),('BOTH','Both')], default='PIXELS')
    config = models.JSONField(default=dict)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.PROTECT)
    created_at = models.DateTimeField(auto_now_add=True)
    generated_at = models.DateTimeField(null=True)
    version = models.PositiveIntegerField(default=1)
    row_count = models.PositiveIntegerField(default=0)
    patient_count = models.PositiveIntegerField(default=0)
    sample_count = models.PositiveIntegerField(default=0)
    content_hash = models.CharField(max_length=64, blank=True)
    snapshot = models.JSONField(default=dict)
    manifest = models.JSONField(default=dict)

    def save(self, *args, **kwargs):
        if not self._state.adding and type(self).objects.filter(pk=self.pk,status='GENERATED').exists():
            raise ValidationError('GENERATED_DATASET_IMMUTABLE')
        super().save(*args, **kwargs)


class MLDatasetPatient(models.Model):
    dataset = models.ForeignKey(MLDataset, related_name='patients', on_delete=models.CASCADE)
    patient = models.ForeignKey('api.Paciente', on_delete=models.PROTECT)
    class_label = models.CharField(max_length=100)
    local_id = models.CharField(max_length=20)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['dataset','patient'],name='dataset_patient_unique'),
                       models.UniqueConstraint(fields=['dataset','local_id'],name='dataset_patient_local_unique')]


class MLDatasetSample(models.Model):
    dataset = models.ForeignKey(MLDataset, related_name='samples', on_delete=models.CASCADE)
    sample = models.ForeignKey('api.MuestraSaliva', on_delete=models.PROTECT)
    characterization = models.ForeignKey('api.ResultadoCaracterizacion', null=True, on_delete=models.PROTECT)
    local_id = models.CharField(max_length=40)
    included = models.BooleanField()
    reason = models.CharField(max_length=64, blank=True)
    source_snapshot = models.JSONField(default=dict)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['dataset','sample'],name='dataset_sample_unique')]
