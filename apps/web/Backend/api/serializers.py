from rest_framework import serializers
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
    class Meta:
        model = Paciente
        fields = '__all__'

class CasoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Caso
        fields = '__all__'

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
