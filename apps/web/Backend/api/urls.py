from .record_management import RecordManagementView, SeriesOptionsView, AssignSeriesView
from .admin_audit import AuditEventViewSet, AuditOptionsView, ArchivedView, OperationalHealthView
from .lifecycle_views import LifecycleView
from .auth_views import AuthContext, LoginView, LogoutView, PasswordView, UserViewSet, InstitutionViewSet, PrivateMediaView
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
    AcquisitionSeriesViewSet, AcquisitionCompatibilityView, AcquisitionOperatorView,
)

router = DefaultRouter()
router.register('admin-audit/events', AuditEventViewSet, basename='audit-event')
router.register('users', UserViewSet, basename='sicam-user')
router.register('institutions', InstitutionViewSet, basename='institution')
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
    path('record-management/series/', SeriesOptionsView.as_view()),
    path('record-management/series/<str:operation>/', AssignSeriesView.as_view()),
    path('record-management/<str:resource>/', RecordManagementView.as_view()),
    path('admin-audit/options/', AuditOptionsView.as_view()),
    path('admin-audit/archived/', ArchivedView.as_view()),
    path('admin-audit/health/', OperationalHealthView.as_view()),
    path('lifecycle/<str:resource>/<int:pk>/', LifecycleView.as_view()),
    path('auth/me/', AuthContext.as_view()),
    path('auth/login/', LoginView.as_view()),
    path('auth/logout/', LogoutView.as_view()),
    path('auth/password/', PasswordView.as_view()),
    path('private-media/<str:kind>/<str:pk>/', PrivateMediaView.as_view(), name='private-media'),
    path('acquisition-operator/', AcquisitionOperatorView.as_view()),
    path('acquisition-compatibility/<str:sample_type>/<int:pk>/', AcquisitionCompatibilityView.as_view()),
    path('', include(router.urls)),
]
