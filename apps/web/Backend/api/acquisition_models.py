"""Acquisition metadata. No physical conversion and no calibration engine calls."""
from decimal import Decimal
import uuid
import hashlib
import warnings

from PIL import Image
from pathlib import Path

from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator, RegexValidator
from django.db import models, transaction

POSITIVE = MinValueValidator(1)
SCALE_MIN = Decimal('0.000000000000001')


def scale_field(**kwargs):
    return models.DecimalField(max_digits=24, decimal_places=15,
                               validators=[MinValueValidator(SCALE_MIN)], **kwargs)


def evidence_path(instance, filename):
    suffix = Path(filename).suffix.lower()
    return f'calibration/references/{instance.calibration_id}/{uuid.uuid4().hex}{suffix}'


def previous(instance):
    return type(instance).objects.filter(pk=instance.pk).first() if instance.pk else None


def unchanged(instance, old, fields):
    if old:
        errors = {field: 'IMMUTABLE_ACQUISITION_DATA: cree un nuevo registro para cambiar estos valores.'
                  for field in fields if getattr(instance, field) != getattr(old, field)}
        if errors:
            raise ValidationError(errors)


class ValidatedAcquisitionModel(models.Model):
    """Normal ORM saves validate; bulk SQL/update is not a supported domain write."""
    id = models.AutoField(primary_key=True)

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        with transaction.atomic():
            self.lock_parents()
            if self.pk:
                type(self).objects.select_for_update().filter(pk=self.pk).first()
            self.full_clean()
            return super().save(*args, **kwargs)

    def lock_parents(self):
        pass


class AcquisitionProfile(ValidatedAcquisitionModel):
    name = models.CharField(max_length=150)
    microscope_manufacturer = models.CharField(max_length=100, blank=True, default='')
    microscope_model = models.CharField(max_length=100, blank=True, default='')
    camera_manufacturer = models.CharField(max_length=100, blank=True, default='')
    camera_model = models.CharField(max_length=100, blank=True, default='')
    adapter_model = models.CharField(max_length=100, blank=True, default='')
    objective_magnification = models.DecimalField(max_digits=8, decimal_places=3, null=True, blank=True,
                                                validators=[MinValueValidator(Decimal('0.001'))])
    image_width_px = models.PositiveIntegerField(validators=[POSITIVE])
    image_height_px = models.PositiveIntegerField(validators=[POSITIVE])
    image_mode = models.CharField(max_length=32, blank=True, default='')
    binning_x = models.PositiveSmallIntegerField(null=True, blank=True, validators=[POSITIVE])
    binning_y = models.PositiveSmallIntegerField(null=True, blank=True, validators=[POSITIVE])
    notes = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    physical_fields = ('microscope_manufacturer', 'microscope_model', 'camera_manufacturer',
                       'camera_model', 'adapter_model', 'objective_magnification', 'image_width_px',
                       'image_height_px', 'image_mode', 'binning_x', 'binning_y')

    class Meta:
        constraints = [models.CheckConstraint(check=models.Q(image_width_px__gt=0, image_height_px__gt=0), name='acq_profile_dimensions_positive'),
                       models.CheckConstraint(check=models.Q(objective_magnification__isnull=True) | models.Q(objective_magnification__gt=0), name='acq_profile_objective_positive'),
                       models.CheckConstraint(check=models.Q(binning_x__isnull=True) | models.Q(binning_x__gt=0), name='acq_profile_binning_x_positive'),
                       models.CheckConstraint(check=models.Q(binning_y__isnull=True) | models.Q(binning_y__gt=0), name='acq_profile_binning_y_positive')]

    def clean(self):
        super().clean()
        if self.pk and (self.calibrations.exists() or self.series.exists()):
            unchanged(self, previous(self), self.physical_fields)


class Calibration(ValidatedAcquisitionModel):
    PROVISIONAL, VALIDATED, RETIRED = 'PROVISIONAL', 'VALIDATED', 'RETIRED'
    acquisition_profile = models.ForeignKey(AcquisitionProfile, on_delete=models.PROTECT, related_name='calibrations')
    label = models.CharField(max_length=150)
    status = models.CharField(max_length=16, choices=[(v,v) for v in (PROVISIONAL, VALIDATED, RETIRED)], default=PROVISIONAL)
    scale_x_um_per_px = scale_field()
    scale_y_um_per_px = scale_field()
    source_width_px = models.PositiveIntegerField(validators=[POSITIVE])
    source_height_px = models.PositiveIntegerField(validators=[POSITIVE])
    method = models.CharField(max_length=100)
    algorithm_version = models.CharField(max_length=100)
    provenance = models.JSONField(default=dict, blank=True)
    notes = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    immutable_fields = ('acquisition_profile_id', 'scale_x_um_per_px', 'scale_y_um_per_px',
                        'source_width_px', 'source_height_px', 'method', 'algorithm_version', 'provenance')

    class Meta:
        constraints = [models.CheckConstraint(check=models.Q(scale_x_um_per_px__gt=0, scale_y_um_per_px__gt=0), name='calibration_scales_positive'),
                       models.CheckConstraint(check=models.Q(source_width_px__gt=0, source_height_px__gt=0), name='calibration_dimensions_positive'),
                       models.CheckConstraint(check=models.Q(status__in=['PROVISIONAL','VALIDATED','RETIRED']), name='calibration_status_valid')]

    def lock_parents(self):
        AcquisitionProfile.objects.select_for_update().filter(pk=self.acquisition_profile_id).first()

    def clean(self):
        super().clean()
        profile = AcquisitionProfile.objects.filter(pk=self.acquisition_profile_id).first()
        if profile and (self.source_width_px, self.source_height_px) != (profile.image_width_px, profile.image_height_px):
            raise ValidationError({'source_width_px': 'RESOLUTION_MISMATCH: la calibración debe coincidir con el perfil.'})
        old = previous(self)
        unchanged(self, old, self.immutable_fields)
        if old and self.status != old.status:
            allowed = {self.PROVISIONAL: {self.VALIDATED,self.RETIRED}, self.VALIDATED: {self.RETIRED}, self.RETIRED: set()}
            if self.status not in allowed[old.status]:
                raise ValidationError({'status': 'Transición de estado no permitida.'})


class CalibrationReference(ValidatedAcquisitionModel):
    calibration = models.ForeignKey(Calibration, on_delete=models.PROTECT, related_name='references')
    pattern_type = models.CharField(max_length=20, choices=[('GRADUATED_GRID','Graduated grid'),('CIRCLE','Circle')])
    source_filename = models.CharField(max_length=255)
    source_sha256 = models.CharField(max_length=64, validators=[RegexValidator(r'\A[a-f0-9]{64}\Z', 'SHA-256 hexadecimal requerido.')])
    source_width_px = models.PositiveIntegerField(validators=[POSITIVE])
    source_height_px = models.PositiveIntegerField(validators=[POSITIVE])
    known_dimension_um = scale_field()
    measured_scale_x_um_per_px = scale_field(null=True, blank=True)
    measured_scale_y_um_per_px = scale_field(null=True, blank=True)
    measurement_status = models.CharField(max_length=80)
    diagnostics = models.JSONField(default=dict, blank=True)
    source_image = models.ImageField(upload_to=evidence_path, max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.CheckConstraint(check=models.Q(source_width_px__gt=0, source_height_px__gt=0, known_dimension_um__gt=0), name='cal_reference_dimensions_positive'),
                       models.CheckConstraint(check=models.Q(measured_scale_x_um_per_px__isnull=True) | models.Q(measured_scale_x_um_per_px__gt=0), name='cal_reference_scale_x_positive'),
                       models.CheckConstraint(check=models.Q(measured_scale_y_um_per_px__isnull=True) | models.Q(measured_scale_y_um_per_px__gt=0), name='cal_reference_scale_y_positive')]

    def lock_parents(self):
        Calibration.objects.select_for_update().filter(pk=self.calibration_id).first()

    def clean(self):
        super().clean()
        old = previous(self)
        if old and self.source_image and not self.source_image._committed:
            raise ValidationError({'source_image': 'IMMUTABLE_ACQUISITION_DATA'})
        # Evidence is append-only. Attach a new reference rather than replace bytes.
        if old:
            unchanged(self, old, [f.attname for f in self._meta.concrete_fields if f.name not in ('id','created_at')])
        calibration = Calibration.objects.filter(pk=self.calibration_id).first()
        if calibration and not old and (calibration.status != Calibration.PROVISIONAL or calibration.series.exists()):
            raise ValidationError({'calibration': 'La evidencia está cerrada al usar o validar la calibración.'})
        if calibration and self.measurement_status == 'MEASURED':
            if (self.source_width_px,self.source_height_px) != (calibration.source_width_px,calibration.source_height_px):
                raise ValidationError({'source_width_px': 'RESOLUTION_MISMATCH: referencia medida incompatible.'})
            if self.measured_scale_x_um_per_px is None or self.measured_scale_y_um_per_px is None:
                raise ValidationError({'measurement_status': 'MEASURED requiere ambas escalas.'})

        if self.source_image and not self.source_image._committed:
            stream = self.source_image.file
            position = stream.tell()
            try:
                stream.seek(0)
                hasher = hashlib.sha256()
                for chunk in iter(lambda: stream.read(1024 * 1024), b''):
                    hasher.update(chunk)
                digest = hasher.hexdigest()
                stream.seek(0)
                with warnings.catch_warnings():
                    warnings.simplefilter('error', Image.DecompressionBombWarning)
                    image = Image.open(stream)
                    dimensions = image.size
                    image.verify()
                    stream.seek(0)
                    Image.open(stream).load()
                if digest != self.source_sha256:
                    raise ValidationError({'source_image': 'SOURCE_HASH_MISMATCH'})
                if dimensions != (self.source_width_px, self.source_height_px):
                    raise ValidationError({'source_image': 'RESOLUTION_MISMATCH'})
            except (OSError, ValueError, SyntaxError, Image.DecompressionBombWarning, Image.DecompressionBombError):
                raise ValidationError({'source_image': 'INVALID_IMAGE'})
            finally:
                stream.seek(position)

    def save(self, *args, **kwargs):
        new_upload = bool(self.source_image and not self.source_image._committed)
        try:
            return super().save(*args, **kwargs)
        except Exception:
            # Storage is not transactional. Only remove this write's new UUID file.
            if new_upload and self.source_image._committed:
                self.source_image.storage.delete(self.source_image.name)
            raise


class AcquisitionSeries(ValidatedAcquisitionModel):
    patient = models.ForeignKey('api.Paciente', on_delete=models.PROTECT, related_name='acquisition_series')
    acquisition_profile = models.ForeignKey(AcquisitionProfile, on_delete=models.PROTECT, related_name='series')
    calibration = models.ForeignKey(Calibration, on_delete=models.PROTECT, related_name='series', null=True, blank=True)
    label = models.CharField(max_length=150)
    acquisition_date = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def lock_parents(self):
        AcquisitionProfile.objects.select_for_update().filter(pk=self.acquisition_profile_id).first()
        Calibration.objects.select_for_update().filter(pk=self.calibration_id).first()

    def clean(self):
        super().clean()
        old = previous(self)
        # Series identify an acquisition, not a mutable pointer to another patient/profile.
        unchanged(self, old, ('patient_id','acquisition_profile_id'))
        if old and old.calibration_id:
            unchanged(self, old, ('calibration_id',))
        calibration = Calibration.objects.filter(pk=self.calibration_id).first()
        if calibration:
            if calibration.acquisition_profile_id != self.acquisition_profile_id:
                raise ValidationError({'calibration': 'PROFILE_MISMATCH'})
            if calibration.status == Calibration.RETIRED and (not old or old.calibration_id != calibration.pk):
                raise ValidationError({'calibration': 'CALIBRATION_RETIRED'})


class AcquisitionSampleMixin(models.Model):
    acquisition_series = models.ForeignKey(AcquisitionSeries, on_delete=models.PROTECT, null=True, blank=True,
                                           related_name='%(class)s_samples')

    class Meta:
        abstract = True

    def clean(self):
        super().clean()
        old = previous(self)
        if old and old.acquisition_series_id:
            if self.imagen and not self.imagen._committed:
                raise ValidationError({'imagen': 'IMMUTABLE_ACQUISITION_DATA'})
            unchanged(self, old, ('acquisition_series_id','analisis_id','imagen'))
        if self.acquisition_series_id and self.analisis_id:
            series = AcquisitionSeries.objects.filter(pk=self.acquisition_series_id).first()
            from .models import AnalisisPred
            analysis = AnalisisPred.objects.filter(pk=self.analisis_id).first()
            if series is None or analysis is None:
                raise ValidationError({'acquisition_series': 'Serie o análisis inexistente.'})
            if series.patient_id != analysis.id_paciente_fk_id:
                raise ValidationError({'acquisition_series': 'PATIENT_MISMATCH'})

    def save(self, *args, **kwargs):
        with transaction.atomic():
            from .models import AnalisisPred
            AnalisisPred.objects.select_for_update().filter(pk=self.analisis_id).first()
            if self.acquisition_series_id:
                AcquisitionSeries.objects.select_for_update().filter(pk=self.acquisition_series_id).first()
            if self.pk:
                type(self).objects.select_for_update().filter(pk=self.pk).first()
            self.clean()
            return super().save(*args, **kwargs)
