from django.contrib import admin

from .models import ResultadoSegmentacion


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
