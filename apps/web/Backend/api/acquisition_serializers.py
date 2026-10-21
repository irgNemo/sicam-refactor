"""Validated metadata writes for acquisition APIs, including partial updates."""
import copy

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


class ValidatedSerializer(serializers.ModelSerializer):
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
