from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    PacienteViewSet,
    CasoViewSet,
    AnalisisViewSet,
    MuestraSalivaViewSet,
    ResultadoSegmentacionViewSet,
    RevisionSegmentacionViewSet,
)

router = DefaultRouter()
router.register(r'pacientes', PacienteViewSet, basename='paciente')
router.register(r'casos', CasoViewSet, basename='caso')
router.register(r'analisis', AnalisisViewSet, basename='analisis')
router.register(r'muestras', MuestraSalivaViewSet, basename='muestra')
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
    path('', include(router.urls)),
]
