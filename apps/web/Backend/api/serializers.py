from collections.abc import Mapping

from rest_framework import serializers
from django.core.exceptions import ValidationError as ModelValidationError
from django.utils import timezone
from .services.patient_identity import pseudonymized_identification
from .segmentation_strategies import SalivaSegmentationStrategy
from .models import (
    AnalisisPred,
    Caso,
    MuestraSaliva,
    MuestraSangre,
    Paciente,
    ResultadoAnalisis,
    ResultadoCaracterizacion,
    ResultadoSegmentacion,
    RevisionSegmentacion,
)
from .services.segmentation.revisions import (
    calculate_revision_summary,
    validate_revision_snapshot,
)

class PacienteSerializer(serializers.ModelSerializer):
    display_name = serializers.CharField(read_only=True)

    class Meta:
        model = Paciente
        fields = '__all__'
        extra_kwargs = {'identificacion': {'required': False}}

    def to_internal_value(self, data):
        if not isinstance(data, Mapping):
            return super().to_internal_value(data)
        mode = data.get('identity_mode', getattr(self.instance, 'identity_mode', Paciente.IDENTIFIED))
        if mode == Paciente.PSEUDONYMIZED:
            # A client cannot supply/override the internally derived identifier.
            data = data.copy()
            data.pop('identificacion', None)
        return super().to_internal_value(data)

    def validate_fecha_nacimiento(self, value):
        if value > timezone.localdate():
            raise serializers.ValidationError('La fecha de nacimiento no puede ser futura.')
        return value

    def validate(self, attrs):
        patient = Paciente()
        if self.instance:
            for field in Paciente._meta.concrete_fields:
                setattr(patient, field.attname, getattr(self.instance, field.attname))
        for key, value in attrs.items():
            setattr(patient, key, value)
        errors = {}
        if patient.identity_mode == Paciente.IDENTIFIED:
            if not self.partial and 'identificacion' not in attrs:
                errors['identificacion'] = 'Este campo es obligatorio.'
            for field in ('nombre', 'apellido', 'identificacion'):
                if not getattr(patient, field, '').strip():
                    errors[field] = 'Este campo es obligatorio.'
        elif patient.identity_mode == Paciente.PSEUDONYMIZED:
            for field in ('initials', 'external_id_namespace', 'external_patient_id'):
                if not getattr(patient, field, '').strip():
                    errors[field] = 'Este campo es obligatorio.'
            for field in ('nombre', 'apellido'):
                if getattr(patient, field):
                    errors[field] = 'Debe estar vacío para un paciente pseudonimizado.'
        if errors:
            raise serializers.ValidationError(errors)
        try:
            patient.clean()
        except ModelValidationError as exc:
            raise serializers.ValidationError(exc.messages)
        namespace, external_id = patient.external_id_namespace, patient.external_patient_id
        if namespace and external_id:
            existing = Paciente.objects.filter(external_id_namespace=namespace, external_patient_id=external_id)
            if self.instance:
                existing = existing.exclude(pk=self.instance.pk)
            if existing.exists():
                raise serializers.ValidationError({
                    'external_patient_id': 'Ya existe un paciente con este ID en el origen seleccionado.',
                })
        if patient.identity_mode == Paciente.PSEUDONYMIZED:
            changed_authority = not self.instance or (
                self.instance.identity_mode != patient.identity_mode
                or self.instance.external_id_namespace != namespace
                or self.instance.external_patient_id != external_id
            )
            if changed_authority:
                identification = pseudonymized_identification(namespace, external_id)
                collision = Paciente.objects.filter(identificacion=identification)
                if self.instance:
                    collision = collision.exclude(pk=self.instance.pk)
                if collision.exists():
                    raise serializers.ValidationError({
                        'external_patient_id': 'La identidad indicada entra en conflicto con un paciente existente.',
                    })
                attrs['identificacion'] = identification
        return attrs

class CasoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Caso
        fields = '__all__'

    def validate(self, attrs):
        patient = attrs.get('paciente', getattr(self.instance, 'paciente', None))
        number = attrs.get('case_number', getattr(self.instance, 'case_number', None))
        if number is not None:
            if number < 1:
                raise serializers.ValidationError({'case_number': 'Debe ser positivo.'})
            existing = Caso.objects.filter(paciente=patient, case_number=number)
            if self.instance:
                existing = existing.exclude(pk=self.instance.pk)
            if existing.exists():
                raise serializers.ValidationError({'case_number': 'Ya existe para este paciente.'})
        return attrs

class SampleUploadSerializer(serializers.ModelSerializer):
    """Shared admission rule for new samples; existing samples remain readable."""

    def validate_analisis(self, value):
        if self.instance is None and value.estado == 2:
            raise serializers.ValidationError(
                'No se pueden agregar imágenes a un análisis cerrado.'
            )
        return value


class MuestraSalivaSerializer(SampleUploadSerializer):
    class Meta:
        model = MuestraSaliva
        fields = '__all__'


class MuestraSangreSerializer(SampleUploadSerializer):
    class Meta:
        model = MuestraSangre
        fields = '__all__'


class ResultadoAnalisisSerializer(serializers.ModelSerializer):
    class Meta:
        model = ResultadoAnalisis
        fields = '__all__'

class SalivaSegmentationRequestSerializer(serializers.Serializer):
    target = serializers.ChoiceField(choices=['ALL', 'MEMBRANES', 'NUCLEI_AND_MICRONUCLEI'], default='ALL')
    resultado_segmentacion_id = serializers.IntegerField(min_value=1, required=False)
    source_token = serializers.RegexField(r'^[a-f0-9]{64}$', required=False)
    confirm_replacement = serializers.BooleanField(default=False)

    def validate(self, attrs):
        if attrs['target'] != 'ALL':
            for field in ('resultado_segmentacion_id', 'source_token'):
                if field not in attrs:
                    raise serializers.ValidationError({field: 'Requerido para segmentación parcial.'})
        return attrs

    segmentation_strategy = serializers.ChoiceField(
        choices=SalivaSegmentationStrategy.choices,
        default=SalivaSegmentationStrategy.CURRENT_CUSTOM_V1,
    )


class ResultadoSegmentacionSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(
        source='id_resultado_segmentacion',
        read_only=True
    )

    class Meta:
        model = ResultadoSegmentacion
        fields = (
            'id',
            'tipo_muestra',
            'base_origin',
            'segmentation_strategy',
            'estado',
            'respuesta_json',
            'resultado_normalizado',
            'creado_en',
            'actualizado_en',
        )
        read_only_fields = fields


class ResultadoCaracterizacionSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(
        source='id_resultado_caracterizacion',
        read_only=True
    )
    vigente = serializers.SerializerMethodField()

    class Meta:
        model = ResultadoCaracterizacion
        fields = (
            'id',
            'resultado_segmentacion',
            'revision_segmentacion',
            'source_type',
            'sample_type',
            'algorithm_version',
            'resultado_json',
            'created_at',
            'vigente',
        )
        read_only_fields = fields

    def get_vigente(self, instance):
        from .services.characterization.service import is_characterization_current

        return is_characterization_current(instance)


class RevisionSegmentacionSerializer(serializers.ModelSerializer):
    expected_updated_at = serializers.DateTimeField(write_only=True, required=False)
    class Meta:
        model = RevisionSegmentacion
        fields = (
            'expected_updated_at',
            'id_revision_segmentacion',
            'resultado_segmentacion',
            'numero_revision',
            'estado',
            'resultado_editado',
            'resumen',
            'creado_en',
            'actualizado_en',
            'validado_en',
        )
        read_only_fields = (
            'id_revision_segmentacion',
            'resultado_segmentacion',
            'numero_revision',
            'estado',
            'resumen',
            'creado_en',
            'actualizado_en',
            'validado_en',
        )

    def validate_resultado_editado(self, value):
        sample_type = self.instance.resultado_segmentacion.tipo_muestra
        validate_revision_snapshot(value, sample_type=sample_type)
        return value

    def update(self, instance, validated_data):
        expected = validated_data.pop('expected_updated_at', None)
        if expected is not None and expected != instance.actualizado_en:
            from rest_framework.exceptions import APIException
            error = APIException('La revisión cambió. Recargue antes de guardar.', code='SEGMENTATION_SOURCE_CHANGED')
            error.status_code = 409
            raise error
        if instance.estado == RevisionSegmentacion.ESTADO_VALIDADA:
            raise serializers.ValidationError(
                'Una revision VALIDADA es inmutable'
            )

        resultado_editado = validated_data.get('resultado_editado')
        if resultado_editado is not None:
            from .services.segmentation.selective import advance_allocator
            parent = instance.resultado_segmentacion
            advance_allocator(parent, resultado_editado)
            parent.save(update_fields=['next_editorial_id'])
            instance.resultado_editado = resultado_editado
            instance.resumen = calculate_revision_summary(
                resultado_editado,
                sample_type=instance.resultado_segmentacion.tipo_muestra,
            )
            instance.save(update_fields=[
                'resultado_editado',
                'resumen',
                'actualizado_en',
            ])

        return instance

class AnalisisSerializer(serializers.ModelSerializer):
    muestras_saliva = MuestraSalivaSerializer(many=True, read_only=True)
    
    class Meta:
        model = AnalisisPred
        fields = '__all__'

    def validate(self, attrs):
        paciente = attrs.get('id_paciente_fk', getattr(self.instance, 'id_paciente_fk', None))
        caso = attrs.get('id_caso_fk', getattr(self.instance, 'id_caso_fk', None))
        if paciente and caso and caso.paciente_id != paciente.pk:
            raise serializers.ValidationError({
                'id_caso_fk': 'El caso no pertenece al paciente seleccionado.',
            })
        return attrs
