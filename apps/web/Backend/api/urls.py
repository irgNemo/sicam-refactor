from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    PacienteViewSet,
    CasoViewSet,
    AnalisisViewSet,
    MuestraSalivaViewSet,
    MuestraSangreViewSet,
    ResultadoSegmentacionViewSet,
    RevisionSegmentacionViewSet,
)

from .acquisition_views import (
    AcquisitionProfileViewSet, CalibrationViewSet, CalibrationReferenceViewSet,
    AcquisitionSeriesViewSet, AcquisitionCompatibilityView,
)

router = DefaultRouter()
router.register('acquisition-profiles', AcquisitionProfileViewSet, basename='acquisition-profile')
router.register('calibrations', CalibrationViewSet, basename='calibration')
router.register('calibration-references', CalibrationReferenceViewSet, basename='calibration-reference')
router.register('acquisition-series', AcquisitionSeriesViewSet, basename='acquisition-series')
router.register(r'pacientes', PacienteViewSet, basename='paciente')
router.register(r'casos', CasoViewSet, basename='caso')
router.register(r'analisis', AnalisisViewSet, basename='analisis')
router.register(r'muestras', MuestraSalivaViewSet, basename='muestra')
router.register(
    r'muestras-sangre',
    MuestraSangreViewSet,
    basename='muestra-sangre'
)
router.register(
    r'resultados-segmentacion',
    ResultadoSegmentacionViewSet,
    basename='resultado-segmentacion'
)
router.register(
    r'revisiones-segmentacion',
    RevisionSegmentacionViewSet,
    basename='revision-segmentacion'
)

urlpatterns = [
    path('acquisition-compatibility/<str:sample_type>/<int:pk>/', AcquisitionCompatibilityView.as_view()),
    path('', include(router.urls)),
]
