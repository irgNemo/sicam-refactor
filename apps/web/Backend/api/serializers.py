from rest_framework import serializers
from .models import (
    AnalisisPred,
    Caso,
    MuestraSaliva,
    Paciente,
    ResultadoAnalisis,
    ResultadoSegmentacion,
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
            'creado_en',
            'actualizado_en',
        )
        read_only_fields = fields

class AnalisisSerializer(serializers.ModelSerializer):
    muestras_saliva = MuestraSalivaSerializer(many=True, read_only=True)
    
    class Meta:
        model = AnalisisPred
        fields = '__all__'
