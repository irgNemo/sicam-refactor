from django.shortcuts import render

from rest_framework.decorators import api_view
from rest_framework.response import Response

@api_view(['GET'])
def saludo(request):
    return Response({
        "mensaje": "Hola desde Django API",
        "status": "ok"
    })

# CARGA DE DATOS
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from .models import Paciente, Caso, AnalisisPred, MuestraSaliva
from .serializers import (
    PacienteSerializer, 
    CasoSerializer, 
    AnalisisSerializer,
    MuestraSalivaSerializer
)

class PacienteViewSet(viewsets.ModelViewSet):
    queryset = Paciente.objects.all()
    serializer_class = PacienteSerializer
    
    @action(detail=True, methods=['get'])
    def casos(self, request, pk=None):
        """Obtener todos los casos de un paciente"""
        paciente = self.get_object()
        casos = paciente.casos.all()
        serializer = CasoSerializer(casos, many=True)
        return Response(serializer.data)

class CasoViewSet(viewsets.ModelViewSet):
    queryset = Caso.objects.all()
    serializer_class = CasoSerializer
    
    @action(detail=True, methods=['get'])
    def analisis(self, request, pk=None):
        """Obtener todos los análisis de un caso"""
        caso = self.get_object()
        analisis = caso.analisis.all()
        serializer = AnalisisSerializer(analisis, many=True)
        return Response(serializer.data)

class AnalisisViewSet(viewsets.ModelViewSet):
    queryset = AnalisisPred.objects.all()
    serializer_class = AnalisisSerializer
    
    @action(detail=True, methods=['post'])
    def cambiar_estado(self, request, pk=None):
        """Cambiar el estado de un análisis"""
        analisis = self.get_object()
        nuevo_estado = request.data.get('estado')
        
        if nuevo_estado is not None and nuevo_estado in [0, 1, 2]:
            analisis.estado = nuevo_estado
            analisis.save()
            return Response({'mensaje': 'Estado actualizado correctamente'})
        
        return Response(
            {'error': 'Estado inválido'}, 
            status=status.HTTP_400_BAD_REQUEST
        )

class MuestraSalivaViewSet(viewsets.ModelViewSet):
    queryset = MuestraSaliva.objects.all()
    serializer_class = MuestraSalivaSerializer
    parser_classes = (MultiPartParser, FormParser)
    
    def create(self, request, *args, **kwargs):
        """Crear nueva muestra con imagen"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response(serializer.data, status=status.HTTP_201_CREATED)