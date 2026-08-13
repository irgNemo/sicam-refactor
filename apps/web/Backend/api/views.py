from django.db.models import OuterRef, Subquery
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
from .models import (
    AnalisisPred,
    Caso,
    MuestraSaliva,
    Paciente,
    ResultadoSegmentacion,
)
from .serializers import (
    PacienteSerializer, 
    CasoSerializer, 
    AnalisisSerializer,
    MuestraSalivaSerializer,
    ResultadoSegmentacionSerializer,
)
from .services.segmentation.exceptions import (
    InvalidSegmentationResponseError,
    SegmentationConnectionError,
    SegmentationServiceError,
    SegmentationTimeoutError,
)
from .services.segmentation.factory import segment_image
from .services.segmentation.normalizers import normalize_segmentation_result


SUMMARY_LABELS = ('membrana', 'nucleo', 'micronucleo')


def _is_valid_number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _extract_valid_segmentation_summary(resultado_normalizado):
    if not isinstance(resultado_normalizado, dict):
        return None

    summary = resultado_normalizado.get('summary')
    if not isinstance(summary, dict):
        return None

    counts_by_label = summary.get('counts_by_label')
    if not isinstance(counts_by_label, dict):
        return None

    normalized_counts = {}
    for label, count in counts_by_label.items():
        if not _is_valid_number(count):
            return None
        normalized_counts[label] = count

    calculated_total = sum(normalized_counts.values())
    total_objects = summary.get('total_objects')

    if total_objects is None:
        total_objects = calculated_total
    elif not _is_valid_number(total_objects):
        return None
    elif total_objects != calculated_total:
        return None

    return {
        'counts_by_label': {
            label: normalized_counts.get(label, 0)
            for label in SUMMARY_LABELS
        },
        'total_objects': total_objects,
    }


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

    @action(detail=True, methods=['get'], url_path='resumen-segmentacion')
    def resumen_segmentacion(self, request, pk=None):
        """Resumen operativo de segmentacion para todas las muestras del caso."""
        caso = self.get_object()
        latest_completed = ResultadoSegmentacion.objects.filter(
            muestra=OuterRef('pk'),
            estado='COMPLETADO',
        ).order_by('-creado_en', '-id_resultado_segmentacion')

        muestras = list(
            MuestraSaliva.objects.filter(
                analisis__id_caso_fk=caso
            ).annotate(
                latest_result_id=Subquery(
                    latest_completed.values('id_resultado_segmentacion')[:1]
                )
            ).values('id_muestra', 'latest_result_id')
        )
        result_ids = [
            muestra['latest_result_id']
            for muestra in muestras
            if muestra['latest_result_id'] is not None
        ]
        resultados = {
            resultado.id_resultado_segmentacion: resultado
            for resultado in ResultadoSegmentacion.objects.filter(
                id_resultado_segmentacion__in=result_ids
            )
        }

        summary = {
            'caso_id': caso.id_caso,
            'total_muestras': len(muestras),
            'muestras_segmentadas': 0,
            'muestras_pendientes': 0,
            'muestras_resultado_invalido': 0,
            'counts_by_label': {
                'membrana': 0,
                'nucleo': 0,
                'micronucleo': 0,
            },
            'total_objects': 0,
        }

        for muestra in muestras:
            latest_result_id = muestra['latest_result_id']
            if latest_result_id is None:
                summary['muestras_pendientes'] += 1
                continue

            resultado = resultados.get(latest_result_id)
            normalized_summary = _extract_valid_segmentation_summary(
                resultado.resultado_normalizado if resultado else None
            )

            if normalized_summary is None:
                summary['muestras_resultado_invalido'] += 1
                continue

            summary['muestras_segmentadas'] += 1
            summary['total_objects'] += normalized_summary['total_objects']
            for label in summary['counts_by_label']:
                summary['counts_by_label'][label] += (
                    normalized_summary['counts_by_label'].get(label, 0)
                )

        return Response(summary)

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

    @action(detail=True, methods=['get'], url_path='resultados-segmentacion')
    def resultados_segmentacion(self, request, pk=None):
        """Consultar resultados de segmentacion asociados a la muestra."""
        muestra = self.get_object()
        resultados = muestra.resultados_segmentacion.order_by(
            '-creado_en',
            '-id_resultado_segmentacion'
        )
        serializer = ResultadoSegmentacionSerializer(resultados, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def segmentar(self, request, pk=None):
        """Solicitar segmentacion de una muestra de saliva existente."""
        muestra = self.get_object()

        if not muestra.imagen:
            return Response(
                {'error': 'La muestra no tiene imagen asociada'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            muestra.imagen.open('rb')
            try:
                image_bytes = muestra.imagen.read()
            finally:
                muestra.imagen.close()
        except (OSError, ValueError) as exc:
            return Response(
                {'error': f'No se pudo leer la imagen de la muestra: {str(exc)}'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if not image_bytes:
            return Response(
                {'error': 'La imagen de la muestra esta vacia'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            result = segment_image(
                'SALIVA',
                image_bytes,
                filename=muestra.imagen.name
            )
        except SegmentationTimeoutError as exc:
            return Response(
                {'error': str(exc)},
                status=status.HTTP_504_GATEWAY_TIMEOUT
            )
        except SegmentationConnectionError as exc:
            return Response(
                {'error': str(exc)},
                status=status.HTTP_503_SERVICE_UNAVAILABLE
            )
        except InvalidSegmentationResponseError as exc:
            return Response(
                {'error': str(exc)},
                status=status.HTTP_502_BAD_GATEWAY
            )
        except SegmentationServiceError as exc:
            return Response(
                {'error': str(exc)},
                status=status.HTTP_502_BAD_GATEWAY
            )
        except Exception:
            return Response(
                {'error': 'Error inesperado al solicitar segmentacion'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        try:
            normalized_result = normalize_segmentation_result(
                result,
                sample_type='SALIVA'
            )
        except ValueError as exc:
            return Response(
                {'error': str(exc)},
                status=status.HTTP_502_BAD_GATEWAY
            )
        except Exception:
            return Response(
                {'error': 'Error inesperado al normalizar resultado de segmentacion'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        try:
            resultado = ResultadoSegmentacion.objects.create(
                muestra=muestra,
                tipo_muestra='SALIVA',
                respuesta_json=result,
                resultado_normalizado=normalized_result,
                estado='COMPLETADO',
            )
        except Exception:
            return Response(
                {'error': 'Error al persistir resultado de segmentacion'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        response_data = {
            **result,
            'resultado_segmentacion': {
                'id': resultado.id_resultado_segmentacion,
                'estado': resultado.estado,
                'tipo_muestra': resultado.tipo_muestra,
                'creado_en': resultado.creado_en.isoformat(),
            },
            'resultado_normalizado': normalized_result,
        }

        return Response(response_data, status=status.HTTP_200_OK)
