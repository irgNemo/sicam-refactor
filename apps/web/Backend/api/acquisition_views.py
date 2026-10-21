from django.shortcuts import get_object_or_404
from rest_framework import mixins, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import (AcquisitionProfile, Calibration, CalibrationReference, AcquisitionSeries,
                     MuestraSaliva, MuestraSangre)
from .acquisition_serializers import (AcquisitionProfileSerializer, CalibrationSerializer,
                                     CalibrationReferenceSerializer, AcquisitionSeriesSerializer)
from .services.acquisition import physical_compatibility


class MetadataViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin,
                      mixins.CreateModelMixin, mixins.UpdateModelMixin, viewsets.GenericViewSet):
    permission_classes = [IsAuthenticated]
    # No destroy action. Referenced metadata additionally uses database PROTECT.


class AcquisitionProfileViewSet(MetadataViewSet):
    queryset = AcquisitionProfile.objects.order_by('pk')
    serializer_class = AcquisitionProfileSerializer


class CalibrationViewSet(MetadataViewSet):
    queryset = Calibration.objects.order_by('pk')
    serializer_class = CalibrationSerializer


class CalibrationReferenceViewSet(MetadataViewSet):
    queryset = CalibrationReference.objects.order_by('pk')
    serializer_class = CalibrationReferenceSerializer


class AcquisitionSeriesViewSet(MetadataViewSet):
    queryset = AcquisitionSeries.objects.order_by('pk')
    serializer_class = AcquisitionSeriesSerializer


class AcquisitionCompatibilityView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, sample_type, pk):
        models = {'SALIVA': MuestraSaliva, 'SANGRE': MuestraSangre}
        if sample_type not in models:
            from rest_framework.exceptions import NotFound
            raise NotFound('Tipo de muestra desconocido.')
        sample = get_object_or_404(models[sample_type], pk=pk)
        return Response(physical_compatibility(sample))
