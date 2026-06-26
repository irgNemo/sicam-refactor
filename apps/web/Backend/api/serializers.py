from rest_framework import serializers
from .models import Paciente, Caso, AnalisisPred, MuestraSaliva, ResultadoAnalisis

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

class AnalisisSerializer(serializers.ModelSerializer):
    muestras_saliva = MuestraSalivaSerializer(many=True, read_only=True)
    
    class Meta:
        model = AnalisisPred
        fields = '__all__'