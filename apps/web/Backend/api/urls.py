from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    PacienteViewSet,
    CasoViewSet,
    AnalisisViewSet,
    MuestraSalivaViewSet
)

router = DefaultRouter()
router.register(r'pacientes', PacienteViewSet, basename='paciente')
router.register(r'casos', CasoViewSet, basename='caso')
router.register(r'analisis', AnalisisViewSet, basename='analisis')
router.register(r'muestras', MuestraSalivaViewSet, basename='muestra')

urlpatterns = [
    path('', include(router.urls)),
]