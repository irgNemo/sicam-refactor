from .access import ScopedSerializerMixin
"""Validated metadata writes for acquisition APIs, including partial updates."""
import copy
from decimal import Decimal

from django.core.exceptions import ValidationError as ModelValidationError
from rest_framework import serializers

from .models import AcquisitionProfile, Calibration, CalibrationReference, AcquisitionSeries


def validate_candidate(model, instance, attrs, *, full=False):
    candidate = copy.copy(instance) if instance else model()
    # Avoid updating the live instance's cached related objects during validation.
    candidate._state = copy.copy(candidate._state)
    candidate._state.fields_cache = {}
    for key, value in attrs.items():
        setattr(candidate, key, value)
    try:
        candidate.full_clean() if full else candidate.clean()
    except ModelValidationError as exc:
        raise serializers.ValidationError(getattr(exc, 'message_dict', exc.messages))
    return attrs


class ValidatedSerializer(ScopedSerializerMixin, serializers.ModelSerializer):
    def validate(self, attrs):
        return validate_candidate(self.Meta.model, self.instance, attrs, full=True)

    def create(self, validated_data):
        try:
            return super().create(validated_data)
        except ModelValidationError as exc:
            raise serializers.ValidationError(getattr(exc, 'message_dict', exc.messages))

    def update(self, instance, validated_data):
        try:
            return super().update(instance, validated_data)
        except ModelValidationError as exc:
            raise serializers.ValidationError(getattr(exc, 'message_dict', exc.messages))


class AcquisitionProfileSerializer(ValidatedSerializer):
    physical_fields_locked = serializers.SerializerMethodField()

    def get_physical_fields_locked(self, instance):
        return instance.calibrations.exists() or instance.series.exists()

    class Meta:
        model = AcquisitionProfile
        fields = '__all__'


class CalibrationSerializer(ValidatedSerializer):
    class Meta:
        model = Calibration
        fields = '__all__'


class CalibrationReferenceSerializer(ValidatedSerializer):
    class Meta:
        model = CalibrationReference
        fields = '__all__'


class AcquisitionSeriesSerializer(ValidatedSerializer):
    class Meta:
        model = AcquisitionSeries
        fields = '__all__'


class AutomaticReferenceSerializer(serializers.Serializer):
    file = serializers.ImageField()
    pattern_type = serializers.ChoiceField(choices=['CIRCLE', 'GRADUATED_GRID'])
    known_dimension_um = serializers.DecimalField(max_digits=24, decimal_places=15, min_value=Decimal('0.000000000000001'))
    grid_reference = serializers.ChoiceField(choices=['uniform_lattice'], required=False)

    def validate(self, attrs):
        if attrs['file'].size > 30 * 1024 * 1024:
            raise serializers.ValidationError('Cada referencia debe ocupar como máximo 30 MiB.')
        if attrs['pattern_type'] != 'GRADUATED_GRID' and 'grid_reference' in attrs:
            raise serializers.ValidationError('La declaración de retícula sólo corresponde al patrón GRID.')
        return attrs


class AutomaticCalibrationSerializer(ScopedSerializerMixin, serializers.Serializer):
    acquisition_profile = serializers.PrimaryKeyRelatedField(queryset=AcquisitionProfile.objects.all())
    label = serializers.CharField(max_length=150, required=False, default='', allow_blank=True)
    source_token = serializers.CharField(required=False, allow_blank=True)
    references = AutomaticReferenceSerializer(many=True, allow_empty=False, max_length=8)

    def validate_references(self, value):
        if sum(entry['file'].size for entry in value) > 128 * 1024 * 1024:
            raise serializers.ValidationError('El lote excede 128 MiB.')
        return value
