from rest_framework import serializers
from django.core.exceptions import ValidationError as ModelValidationError
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

    def validate(self, attrs):
        patient = Paciente()
        if self.instance:
            for field in Paciente._meta.concrete_fields:
                setattr(patient, field.attname, getattr(self.instance, field.attname))
        for key, value in attrs.items():
            setattr(patient, key, value)
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
                raise serializers.ValidationError('La identidad externa ya existe.')
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

class MuestraSalivaSerializer(serializers.ModelSerializer):
    class Meta:
        model = MuestraSaliva
        fields = '__all__'


class MuestraSangreSerializer(serializers.ModelSerializer):
    class Meta:
        model = MuestraSangre
        fields = '__all__'


class ResultadoAnalisisSerializer(serializers.ModelSerializer):
    class Meta:
        model = ResultadoAnalisis
        fields = '__all__'

class SalivaSegmentationRequestSerializer(serializers.Serializer):
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
    class Meta:
        model = RevisionSegmentacion
        fields = (
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
        if instance.estado == RevisionSegmentacion.ESTADO_VALIDADA:
            raise serializers.ValidationError(
                'Una revision VALIDADA es inmutable'
            )

        resultado_editado = validated_data.get('resultado_editado')
        if resultado_editado is not None:
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
