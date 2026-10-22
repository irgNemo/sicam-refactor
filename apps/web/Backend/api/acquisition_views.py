import json

from django.core.exceptions import ValidationError as ModelValidationError
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from django.shortcuts import get_object_or_404
from rest_framework import mixins, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import (AcquisitionProfile, Calibration, CalibrationReference, AcquisitionSeries,
                     MuestraSaliva, MuestraSangre)
from .acquisition_serializers import (AcquisitionProfileSerializer, CalibrationSerializer,
                                     CalibrationReferenceSerializer, AcquisitionSeriesSerializer, AutomaticCalibrationSerializer)
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

    def run_automatic(self, request, persist):
        try:
            metadata = json.loads(request.data.get('references', '[]'))
        except (TypeError, ValueError):
            raise ValidationError({'references': 'Metadata JSON inválida.'})
        if not isinstance(metadata, list) or any(not isinstance(item, dict) for item in metadata):
            raise ValidationError({'references': 'Se requiere una lista de referencias.'})
        expected_files = {f'reference_{index}' for index in range(len(metadata))}
        if set(request.FILES) != expected_files or any(len(request.FILES.getlist(key)) != 1 for key in expected_files):
            raise ValidationError({'references': 'Cada referencia debe tener exactamente un archivo.'})
        data = {
            'acquisition_profile': request.data.get('acquisition_profile'),
            'label': request.data.get('label', ''), 'source_token': request.data.get('source_token', ''),
            'references': [{**item, 'file': request.FILES.get(f'reference_{index}')} for index, item in enumerate(metadata)],
        }
        serializer = AutomaticCalibrationSerializer(data=data)
        serializer.is_valid(raise_exception=True)
        values = serializer.validated_data
        if persist and not values['label']:
            raise ValidationError({'label': 'Indique un nombre para la calibración.'})
        from .services.acquisition.automatic import automatic_calibration
        try:
            output = automatic_calibration(values['acquisition_profile'], values['references'],
                label=values['label'], expected_token=values.get('source_token'), persist=persist)
        except ModelValidationError as exc:
            raise ValidationError(getattr(exc, 'message_dict', exc.messages))
        if persist:
            output['calibration'] = CalibrationSerializer(output['calibration']).data
        return Response(output, status=201 if persist else 200)

    @action(detail=False, methods=['post'], url_path='automatic-preview')
    def automatic_preview(self, request):
        return self.run_automatic(request, False)

    @action(detail=False, methods=['post'], url_path='automatic')
    def automatic(self, request):
        return self.run_automatic(request, True)


class CalibrationReferenceViewSet(MetadataViewSet):
    queryset = CalibrationReference.objects.order_by('pk')
    serializer_class = CalibrationReferenceSerializer


class AcquisitionSeriesViewSet(MetadataViewSet):
    queryset = AcquisitionSeries.objects.order_by('pk')
    serializer_class = AcquisitionSeriesSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        patient = self.request.query_params.get('patient')
        if patient is not None:
            if not patient.isdigit():
                raise ValidationError({'patient': 'Identificador de paciente inválido.'})
            queryset = queryset.filter(patient_id=int(patient))
        return queryset


class AcquisitionCompatibilityView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, sample_type, pk):
        models = {'SALIVA': MuestraSaliva, 'SANGRE': MuestraSangre}
        if sample_type not in models:
            from rest_framework.exceptions import NotFound
            raise NotFound('Tipo de muestra desconocido.')
        sample = get_object_or_404(models[sample_type], pk=pk)
        return Response(physical_compatibility(sample))


class AcquisitionOperatorView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response({'authenticated': True})
