from django.contrib import admin

from .models import (
    ResultadoCaracterizacion,
    ResultadoSegmentacion,
    RevisionSegmentacion,
)


class HistoricalAdmin(admin.ModelAdmin):
    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(ResultadoSegmentacion)
class ResultadoSegmentacionAdmin(HistoricalAdmin):
    list_display = (
        'id_resultado_segmentacion',
        'muestra',
        'muestra_sangre',
        'tipo_muestra',
        'estado',
        'creado_en',
    )
    list_filter = ('tipo_muestra', 'estado', 'creado_en')
    search_fields = (
        'id_resultado_segmentacion',
        'muestra__id_muestra',
        'muestra_sangre__id_muestra',
    )


@admin.register(RevisionSegmentacion)
class RevisionSegmentacionAdmin(HistoricalAdmin):
    list_display = (
        'id_revision_segmentacion',
        'resultado_segmentacion',
        'numero_revision',
        'estado',
        'creado_en',
        'validado_en',
    )
    list_filter = ('estado', 'creado_en', 'validado_en')
    search_fields = (
        'id_revision_segmentacion',
        'resultado_segmentacion__id_resultado_segmentacion',
    )
    readonly_fields = (
        'created_by', 'updated_by',
        'numero_revision',
        'estado',
        'resumen',
        'creado_en',
        'actualizado_en',
        'validado_en',
    )


@admin.register(ResultadoCaracterizacion)
class ResultadoCaracterizacionAdmin(HistoricalAdmin):
    list_display = (
        'id_resultado_caracterizacion',
        'resultado_segmentacion',
        'revision_segmentacion',
        'source_type',
        'sample_type',
        'algorithm_version',
        'created_at',
    )
    list_filter = (
        'source_type',
        'sample_type',
        'algorithm_version',
        'created_at',
    )
    search_fields = (
        'id_resultado_caracterizacion',
        'resultado_segmentacion__id_resultado_segmentacion',
        'revision_segmentacion__id_revision_segmentacion',
    )
    readonly_fields = (
        'created_by', 'updated_by',
        'resultado_segmentacion',
        'revision_segmentacion',
        'source_type',
        'sample_type',
        'algorithm_version',
        'resultado_json',
        'created_at',
    )

# The Django admin is a platform console, never an institutional privilege bypass.
from .access import operational
admin.site.has_permission = lambda request: bool(request.user.is_superuser and operational(request.user))
from .models import Institution, SicamUserProfile
@admin.register(Institution)
class InstitutionAdmin(admin.ModelAdmin):
    def formfield_for_dbfield(self, db_field, request, **kwargs):
        if db_field.name == 'active':
            kwargs['help_text'] = 'Desactivar la institución impide operar a todos sus usuarios, incluidas las sesiones abiertas.'
        return super().formfield_for_dbfield(db_field, request, **kwargs)

    def has_delete_permission(self, request, obj=None):
        return False

admin.site.register(SicamUserProfile)

# Account deactivation preserves ownership and attribution; no physical deletion
# through the platform console either.
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin


class SicamPlatformUserAdmin(UserAdmin):
    def has_delete_permission(self, request, obj=None):
        return False


admin.site.unregister(get_user_model())
admin.site.register(get_user_model(), SicamPlatformUserAdmin)


from .models import LifecycleEvent

@admin.register(LifecycleEvent)
class LifecycleEventAdmin(admin.ModelAdmin):
    list_display = ('id', 'created_at', 'institution', 'actor', 'action', 'target_type', 'target_id')
    list_filter = ('institution', 'action', 'target_type')

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
