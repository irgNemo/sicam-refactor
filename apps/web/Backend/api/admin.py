from django.contrib import admin

from .models import ResultadoSegmentacion, RevisionSegmentacion


@admin.register(ResultadoSegmentacion)
class ResultadoSegmentacionAdmin(admin.ModelAdmin):
    list_display = (
        'id_resultado_segmentacion',
        'muestra',
        'tipo_muestra',
        'estado',
        'creado_en',
    )
    list_filter = ('tipo_muestra', 'estado', 'creado_en')
    search_fields = ('id_resultado_segmentacion', 'muestra__id_muestra')


@admin.register(RevisionSegmentacion)
class RevisionSegmentacionAdmin(admin.ModelAdmin):
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
        'numero_revision',
        'estado',
        'resumen',
        'creado_en',
        'actualizado_en',
        'validado_en',
    )
